"""Tiny evaluation harness: accuracy + calibration (accuracy per confidence bucket).

The key skill with a System One model is not "call the API" - it is checking
that HIGH confidence really means HIGH accuracy on YOUR data, then picking
thresholds for auto-act / confirm / escalate.
"""

from __future__ import annotations

import csv
from pathlib import Path

BUCKETS = [(0.0, 0.5, "low  <0.5"), (0.5, 0.9, "mid 0.5-0.9"), (0.9, 1.01, "high >0.9")]


def load_csv(path: str | Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def report(results: list[tuple[str, str, float]], title: str) -> None:
    """results = [(predicted, expected, confidence), ...]"""
    n = len(results)
    correct = sum(p == e for p, e, _ in results)
    print(f"\n--- {title} ---")
    print(f"accuracy: {correct}/{n} = {correct / n:.0%}")
    print(f"{'confidence':<14}{'count':>6}{'accuracy':>10}")
    for lo, hi, label in BUCKETS:
        rows = [(p, e) for p, e, c in results if lo <= c < hi]
        if rows:
            acc = sum(p == e for p, e in rows) / len(rows)
            print(f"{label:<14}{len(rows):>6}{acc:>10.0%}")
        else:
            print(f"{label:<14}{0:>6}{'-':>10}")
    print("Well calibrated = accuracy rises from low -> high bucket.")
