# Diagnosing Distributed-Storage Latency from Metrics & Logs

A self-contained, reproducible case study: a Cassandra read-latency regression is
deliberately induced, diagnosed from metrics and logs, and fixed — demonstrating the
infrastructure↔analytics bridge without any proprietary data.

**The story.** A steady read workload (`SELECT ... WHERE device_id = ? LIMIT 100`) runs
against a single-node Apache Cassandra cluster. Sixty seconds in, the workload
mass-deletes most rows at the front of each partition. Those deletes become
**tombstones** that linger until compaction; because they sit *before* the live rows in
clustering order, every read must now scan ~19,800 tombstones to return 100 live rows.
Read **p99 jumps ~6×**, throughput collapses ~4×, and the server log fills with
`tombstone cells` WARNs. A major compaction purges the tombstones and latency returns to
baseline.

The full analysis — charts and narrative — is in **[`latency_diagnosis.ipynb`](latency_diagnosis.ipynb)**.

## What's here

| File | Role |
|---|---|
| `docker-compose.yml` | Single-node Cassandra 4.1 |
| `run_experiment.py` | Drives the workload, injects the fault, remediates, captures CSVs |
| `verify.py` | Smoke test: fails unless the captured data shows the regression + recovery |
| `build_notebook.py` | Regenerates `latency_diagnosis.ipynb` from the captured CSVs |
| `data/` | Captured metrics/logs (committed, so the notebook is reproducible without re-running) |
| `latency_diagnosis.ipynb` | The diagnostic write-up |
| `observability/` | Prometheus + Grafana + JMX-exporter config for the live dashboard (Phase B) |

## Reproduce it

Requires Docker and Python 3.

```bash
# 1. start Cassandra (wait ~90s for it to become healthy)
docker compose up -d
until [ "$(docker inspect -f '{{.State.Health.Status}}' cass-latency-demo)" = healthy ]; do sleep 3; done

# 2. python environment
python3 -m venv .venv && ./.venv/bin/pip install pandas matplotlib jupyter nbconvert ipykernel cassandra-driver

# 3. run the ~4.5-minute experiment (use -u for live phase output)
./.venv/bin/python -u run_experiment.py

# 4. confirm the captured data shows the signal
./.venv/bin/python verify.py

# 5. (optional) regenerate the notebook + hero chart from the CSVs
./.venv/bin/python build_notebook.py

docker compose down -v   # tear down
```

## What to look for

- **Client latency** (`data/latency_timeseries.csv`): p99 ≈ 7 ms → 45 ms at the fault, back to baseline after compaction.
- **Server metric** (`data/metrics.csv`): `tombstones_per_read` ramps from 1 to ~9,000 (peak ~20,500); SSTable count rises, then drops to 1 after compaction.
- **Server log** (`data/sample_log_warnings.txt`): `Read 100 live rows and 19800 tombstone cells for query ...`.

## Live Grafana dashboard (optional)

`docker compose up -d` also starts a Prometheus + Grafana + JMX-exporter stack that
scrapes Cassandra's own metrics. Open **http://localhost:3000** (anonymous access) → the
*Cassandra Read Latency — Tombstone Incident* dashboard shows read p99, tombstones
scanned per read, and SSTable/compaction counts. Run the experiment and watch the
incident unfold live — this is the source of the portfolio hero image, rendered straight
from Grafana over the captured time window:

```bash
FROM=$(( $(date -v-6M +%s) * 1000 )); TO=$(( $(date +%s) * 1000 ))   # or your run's window
curl -s "http://localhost:3000/render/d/cass-latency/incident?from=${FROM}&to=${TO}&width=1500&height=680&kiosk=true" -o hero.png
```

The JMX exporter agent jar is fetched on first setup (not committed):

```bash
curl -sSL -o observability/jmx/jmx_prometheus_javaagent.jar \
  https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/0.20.0/jmx_prometheus_javaagent-0.20.0.jar
```

## The real-world fix

The remediation here is a major compaction, but the durable fix is upstream: avoid the
delete-heavy access pattern so tombstones never accumulate in the read path — e.g. TTLs
with a time-window compaction strategy, or partitioning so reads never traverse deleted
ranges.
