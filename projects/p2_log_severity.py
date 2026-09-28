"""Project 2 - Syslog severity scoring (Score on an ordered rubric).

Run:  python -m projects.p2_log_severity
"""
from eval_harness import load_csv, report
from jev_client import Score, ask

SEVERITY = Score(
    instructions="How operationally severe is this network device log line?",
    criteria=[
        "Informational: normal up, success, synced, configured, new adjacency",
        "Warning: degraded but working, fan low, err-disable on one port, mismatch, duplicate address",
        "Major: neighbor down, supply failed, storm, repeated login failed attack, service impact",
        "Critical: crash, failover, stack split, temperature critical, shutdown imminent",
    ],
)


def main():
    results = []
    for row in load_csv("data/logs.csv"):
        s = ask(row["log"], {"sev": SEVERITY}).answers["sev"]
        level = str(round(s.score))
        results.append((level, row["severity"], s.confidence))
        flag = "PAGE ON-CALL" if s.score >= 2.5 and s.confidence > 0.5 else ""
        print(f"score={s.score:4.2f} conf={s.confidence:.2f} {flag:<13}| {row['log'][:60]}")
    report(results, "severity level (rounded score)")


if __name__ == "__main__":
    main()
