#!/usr/bin/env python3
"""
Reproduce a Cassandra read-latency regression caused by tombstone buildup and a
compaction backlog, then remediate it -- capturing the metrics and log evidence a
diagnostician would actually use.

Timeline (single continuous read workload throughout):

  BASELINE  steady reads over healthy partitions; p99 is low and flat.
  FAULT     autocompaction is disabled and most rows in each partition are deleted
            with individual-row DELETEs (per-cell tombstones, not a cheap range
            tombstone). Reads now scan thousands of tombstones to return a handful
            of live rows -> p99 climbs, "tombstone cells" WARNs appear in the log,
            tombstones-per-read and SSTable count rise.
  RECOVERY  a major compaction purges the tombstones (gc_grace_seconds=0) and
            autocompaction is re-enabled -> p99 falls back to baseline.

Outputs (committed so the notebook is reproducible without re-running Docker):
  data/latency_timeseries.csv  per-window p50/p99 read latency + throughput
  data/metrics.csv             per-sample nodetool table/compaction metrics
  data/log_events.csv          tombstone WARN count over time (from the server log)
  data/phases.csv              phase boundaries for chart annotations
"""

import csv
import os
import subprocess
import threading
import time
from datetime import datetime, timezone

import numpy as np
from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args
from cassandra.query import BatchStatement

CONTAINER = "cass-latency-demo"
KEYSPACE = "demo"
TABLE = "events"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# --- experiment scale (tuned for a clear signal on a laptop) ---
DEVICES = 20               # partitions
ROWS_PER_DEVICE = 20000    # clustering rows per partition
DELETE_PER_DEVICE = 19800  # delete the FIRST 19800 ts -> reads scan them as tombstones
READ_LIMIT = 100           # fixed result size: isolates tombstone-scan cost from row-transfer cost
PAYLOAD_BYTES = 48
# Tombstones must outlive gc_grace to be scanned (and trip the warning); a grace
# window shorter than the fault lets the remediation compaction purge them so the
# recovery is clean. Deletes land at t=BASELINE_S, remediation at t=BASELINE+FAULT.
GC_GRACE_SECONDS = 90

# --- phase durations (seconds) ---
BASELINE_S = 60
FAULT_S = 120
RECOVERY_S = 60
WINDOW_S = 2               # latency aggregation window
METRIC_EVERY_S = 6         # how often to sample nodetool


def nodetool(*args):
    return subprocess.run(
        ["docker", "exec", CONTAINER, "nodetool", *args],
        capture_output=True, text=True,
    ).stdout


def server_tombstone_warns():
    """Count tombstone WARN lines emitted in the server log so far."""
    out = subprocess.run(
        ["docker", "exec", CONTAINER, "sh", "-c",
         "grep -c 'tombstone cells' /var/log/cassandra/system.log || true"],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        return int(out)
    except ValueError:
        return 0


def parse_table_metrics(text):
    """Pull the read-path metrics we care about out of `nodetool tablestats`."""
    sstables = tomb_avg = tomb_max = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("SSTable count:"):
            sstables = int(line.split(":")[1])
        elif line.startswith("Average tombstones per slice"):
            tomb_avg = float(line.split(":")[1])
        elif line.startswith("Maximum tombstones per slice"):
            tomb_max = int(line.split(":")[1])
    return sstables, tomb_avg, tomb_max


def compaction_pending():
    out = nodetool("compactionstats")
    for line in out.splitlines():
        if line.lower().startswith("pending tasks:"):
            return int(line.split(":")[1])
    return 0


def setup_schema(session):
    session.execute(
        f"CREATE KEYSPACE IF NOT EXISTS {KEYSPACE} WITH replication = "
        "{'class':'SimpleStrategy','replication_factor':1}"
    )
    session.execute(f"DROP TABLE IF EXISTS {KEYSPACE}.{TABLE}")
    # gc_grace_seconds=0 so the remediation compaction can purge tombstones at once,
    # giving a clean recovery curve. STCS is the default read-heavy story.
    session.execute(
        f"CREATE TABLE {KEYSPACE}.{TABLE} ("
        "  device_id int, ts int, payload text,"
        "  PRIMARY KEY (device_id, ts)"
        f") WITH gc_grace_seconds = {GC_GRACE_SECONDS}"
        "   AND compaction = {'class':'SizeTieredCompactionStrategy'}"
    )


def populate(session):
    payload = "x" * PAYLOAD_BYTES
    insert = session.prepare(
        f"INSERT INTO {KEYSPACE}.{TABLE} (device_id, ts, payload) VALUES (?, ?, ?)"
    )
    for d in range(DEVICES):
        batch = BatchStatement()
        for t in range(ROWS_PER_DEVICE):
            batch.add(insert, (d, t, payload))
            if len(batch) >= 200:
                session.execute(batch)
                batch = BatchStatement()
        if len(batch) > 0:
            session.execute(batch)
    nodetool("flush", KEYSPACE, TABLE)


def inject_tombstones(session):
    """Disable autocompaction, then delete most rows row-by-row (per-cell
    tombstones). Reads must now scan these to find the few survivors."""
    nodetool("disableautocompaction", KEYSPACE, TABLE)
    delete = session.prepare(
        f"DELETE FROM {KEYSPACE}.{TABLE} WHERE device_id = ? AND ts = ?"
    )
    # Fire the deletes concurrently so injection takes seconds, not minutes -- a long
    # synchronous delete pass would stall the read loop and break the phase timeline.
    params = [(d, t) for d in range(DEVICES) for t in range(DELETE_PER_DEVICE)]
    execute_concurrent_with_args(session, delete, params, concurrency=128,
                                 raise_on_first_error=True)
    nodetool("flush", KEYSPACE, TABLE)


def remediate(session):
    """Purge tombstones with a major compaction and re-enable autocompaction."""
    nodetool("enableautocompaction", KEYSPACE, TABLE)
    nodetool("compact", KEYSPACE, TABLE)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    cluster = Cluster(["127.0.0.1"], port=9042)
    session = cluster.connect()

    print("setup schema ...")
    setup_schema(session)
    print(f"populate {DEVICES} x {ROWS_PER_DEVICE} rows ...")
    populate(session)

    read = session.prepare(
        f"SELECT * FROM {KEYSPACE}.{TABLE} WHERE device_id = ? LIMIT {READ_LIMIT}"
    )

    print("warmup ...")
    warm_end = time.monotonic() + 8
    while time.monotonic() < warm_end:
        session.execute(read, (int(np.random.default_rng().integers(0, DEVICES)),))

    lat_rows, metric_rows, log_rows = [], [], []
    phases = []

    total_s = BASELINE_S + FAULT_S + RECOVERY_S
    start = time.monotonic()
    next_metric = 0.0
    fault_injected = False
    remediated = False
    window_lat = []
    window_start = start
    rng = np.random.default_rng(7)

    def phase_at(elapsed):
        if elapsed < BASELINE_S:
            return "baseline"
        if elapsed < BASELINE_S + FAULT_S:
            return "fault"
        return "recovery"

    print("running workload ...")
    while True:
        elapsed = time.monotonic() - start
        if elapsed >= total_s:
            break

        # phase transitions
        # Run inject/remediate on background threads so the read loop never stalls --
        # the latency curve then ramps continuously as tombstones accumulate / are purged.
        if not fault_injected and elapsed >= BASELINE_S:
            print(f"[{elapsed:5.0f}s] injecting tombstones (background) ...")
            threading.Thread(target=inject_tombstones, args=(session,), daemon=True).start()
            fault_injected = True
        if not remediated and elapsed >= BASELINE_S + FAULT_S:
            print(f"[{elapsed:5.0f}s] remediating: major compaction (background) ...")
            threading.Thread(target=remediate, args=(session,), daemon=True).start()
            remediated = True

        # one read, timed
        d = int(rng.integers(0, DEVICES))
        t0 = time.perf_counter()
        session.execute(read, (d,))
        window_lat.append((time.perf_counter() - t0) * 1000.0)

        # close a latency window
        if time.monotonic() - window_start >= WINDOW_S:
            arr = np.array(window_lat)
            lat_rows.append({
                "t_s": round(time.monotonic() - start, 1),
                "wall": now_iso(),
                "phase": phase_at(elapsed),
                "p50_ms": round(float(np.percentile(arr, 50)), 3),
                "p99_ms": round(float(np.percentile(arr, 99)), 3),
                "ops": len(arr),
            })
            window_lat = []
            window_start = time.monotonic()

        # sample server-side metrics on a slower cadence
        if elapsed >= next_metric:
            sstables, tomb_avg, tomb_max = parse_table_metrics(
                nodetool("tablestats", f"{KEYSPACE}.{TABLE}")
            )
            metric_rows.append({
                "t_s": round(elapsed, 1),
                "wall": now_iso(),
                "phase": phase_at(elapsed),
                "sstable_count": sstables,
                "tombstones_per_read_avg": tomb_avg,
                "tombstones_per_read_max": tomb_max,
                "compaction_pending": compaction_pending(),
            })
            log_rows.append({
                "t_s": round(elapsed, 1),
                "wall": now_iso(),
                "phase": phase_at(elapsed),
                "tombstone_warn_total": server_tombstone_warns(),
            })
            next_metric = elapsed + METRIC_EVERY_S

    phases = [
        {"phase": "baseline", "t_start": 0, "t_end": BASELINE_S},
        {"phase": "fault", "t_start": BASELINE_S, "t_end": BASELINE_S + FAULT_S},
        {"phase": "recovery", "t_start": BASELINE_S + FAULT_S, "t_end": total_s},
    ]

    _write_csv("latency_timeseries.csv", lat_rows)
    _write_csv("metrics.csv", metric_rows)
    _write_csv("log_events.csv", log_rows)
    _write_csv("phases.csv", phases)
    print("done. wrote CSVs to", DATA_DIR)

    cluster.shutdown()


def _write_csv(name, rows):
    path = os.path.join(DATA_DIR, name)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
