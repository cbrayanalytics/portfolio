#!/usr/bin/env python3
"""
Smoke test for the captured experiment: fail loudly unless the data actually shows
the tombstone latency regression and its recovery. Run after run_experiment.py.
"""

import csv
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load(name):
    with open(os.path.join(DATA_DIR, name)) as f:
        return list(csv.DictReader(f))


def p99_by_phase(rows):
    out = {}
    for r in rows:
        out.setdefault(r["phase"], []).append(float(r["p99_ms"]))
    return {k: sum(v) / len(v) for k, v in out.items()}


def main():
    lat = load("latency_timeseries.csv")
    logs = load("log_events.csv")

    p99 = p99_by_phase(lat)
    base, fault, recov = p99["baseline"], p99["fault"], p99["recovery"]
    warns = [int(r["tombstone_warn_total"]) for r in logs]
    warn_growth = max(warns) - min(warns)

    print(f"mean p99  baseline={base:.2f}ms  fault={fault:.2f}ms  recovery={recov:.2f}ms")
    print(f"tombstone WARNs emitted during run: {warn_growth}")

    checks = {
        "fault p99 >= 2x baseline": fault >= 2 * base,
        "tombstone WARNs fired": warn_growth > 0,
        "recovery p99 < 0.6x fault": recov < 0.6 * fault,
    }
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    if not all(checks.values()):
        sys.exit("verification FAILED: captured data does not show the expected signal")
    print("verification PASSED")


if __name__ == "__main__":
    main()
