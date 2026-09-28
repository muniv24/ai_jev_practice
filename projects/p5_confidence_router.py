"""Project 5 - Confidence-gated router: Jev decides WHO handles the request.

  high confidence  -> automated handler (cheap)
  mid confidence   -> big LLM with reasoning (expensive)
  low confidence   -> human
Run:  python -m projects.p5_confidence_router
"""
from collections import Counter

from eval_harness import load_csv
from jev_client import Choice, ask

INTENT = Choice(
    instructions="What does the user want?",
    criteria={
        "status_lookup": "Check status, show, is it down, what is the state of a device or link",
        "config_change": "Change, update, add, remove, configure something",
        "troubleshoot": "Something is broken, failing, slow, dropping, needs diagnosis",
        "other": "Pricing, licenses, billing, anything else",
    },
)

HIGH, LOW = 0.9, 0.5  # start conservative, tune with eval data (see docs/confidence)


def route(text: str) -> tuple[str, str, float]:
    a = ask(text, {"intent": INTENT}).answers["intent"]
    if a.confidence >= HIGH:
        return "AUTOMATION", a.choice, a.confidence
    if a.confidence >= LOW:
        return "LLM (reasoning)", a.choice, a.confidence
    return "HUMAN", a.choice, a.confidence


def main():
    lanes = Counter()
    for row in load_csv("data/tickets.csv"):
        lane, intent, conf = route(row["text"])
        lanes[lane] += 1
        print(f"{lane:<16} {intent:<14} conf={conf:.2f} | {row['text'][:50]}")
    print("\nTraffic split:", dict(lanes))
    print("Goal: most traffic in AUTOMATION, only hard cases pay for the LLM / human.")


if __name__ == "__main__":
    main()
