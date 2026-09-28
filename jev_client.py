"""Thin wrapper around TypeSafe Jev with an offline MOCK fallback.

- If TYPESAFE_API_KEY is set and `typesafe-sdk` is installed -> calls real Jev.
- Otherwise -> uses a crude word-overlap MOCK that returns the SAME response
  shape (choice/score/noul + probabilities + confidence), so you can build and
  test your pipeline logic before you get early-access keys.

MOCK outputs are NOT Jev outputs. Never judge Jev quality from mock numbers.
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Union


def _load_dotenv() -> None:
    """Load KEY=VALUE lines from ./.env into os.environ (shell exports win)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.removeprefix("export ").split("=", 1)
            value = value.strip().strip('"').strip("'")
            if value:
                os.environ.setdefault(key.strip(), value)


_load_dotenv()


# ---------- question specs (mirror the SDK primitives) ----------

@dataclass
class Choice:
    instructions: str
    criteria: dict[str, str | None]  # option_key -> description


@dataclass
class Score:
    instructions: str
    criteria: list[str]  # ordered levels, low -> high (2..10)


@dataclass
class Noul:
    instructions: str  # a statement; answer = P(statement is true)


Question = Union[Choice, Score, Noul]


# ---------- public API ----------

def is_mock() -> bool:
    if not os.getenv("TYPESAFE_API_KEY"):
        return True
    try:
        import typesafe_sdk  # noqa: F401
    except ImportError:
        return True
    return False


_banner_shown = False


def ask(state: str | dict, questions: dict[str, Question]):
    """Returns an object with `.answers[name]` exactly like the real SDK."""
    global _banner_shown
    if is_mock():
        if not _banner_shown:
            print("=" * 64)
            print(" MOCK MODE - word-overlap heuristic, NOT Jev.")
            print(" Set TYPESAFE_API_KEY + `pip install typesafe-sdk` for real calls.")
            print("=" * 64)
            _banner_shown = True
        return _mock(state, questions)
    return _real(state, questions)


# ---------- real Jev ----------

_client = None


def _real(state, questions):
    global _client
    import typesafe_sdk as ts

    if _client is None:
        _client = ts.TypeSafeClient()  # reads TYPESAFE_API_KEY
    sdk_questions = {}
    for name, q in questions.items():
        if isinstance(q, Choice):
            sdk_questions[name] = ts.Choice(instructions=q.instructions, criteria=q.criteria)
        elif isinstance(q, Score):
            sdk_questions[name] = ts.Score(instructions=q.instructions, criteria=q.criteria)
        else:
            sdk_questions[name] = ts.Noul(instructions=q.instructions)
    return _client.system_one(state=state, questions=sdk_questions)


# ---------- mock ----------

_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"the", "a", "an", "is", "are", "or", "and", "of", "to", "in", "on", "for",
         "with", "this", "that", "it", "be", "no", "not", "but", "just", "my", "i"}


def _tokens(text: str) -> set[str]:
    words = {w for w in _WORD.findall(text.lower()) if w not in _STOP}
    # crude stemming so "failed"/"failing"/"fails" all match "fail"
    return words | {re.sub(r"(ing|ed|es|s)$", "", w) for w in words}


def _overlap(state: set[str], text: str) -> float:
    t = _tokens(text)
    return len(state & t) / (1 + math.sqrt(len(t)))


def _softmax(xs: list[float], temp: float = 0.35) -> list[float]:
    m = max(xs)
    exps = [math.exp((x - m) / temp) for x in xs]
    s = sum(exps)
    return [e / s for e in exps]


def _concentration(ps: list[float]) -> float:
    """1 - normalized entropy. Approximates Jev's 'confidence' idea."""
    if len(ps) < 2:
        return 1.0
    h = -sum(p * math.log(p) for p in ps if p > 0)
    return round(1 - h / math.log(len(ps)), 3)


def _mock(state, questions):
    text = state if isinstance(state, str) else " ".join(f"{k} {v}" for k, v in state.items())
    st = _tokens(text)
    answers = {}
    for name, q in questions.items():
        if isinstance(q, Choice):
            keys = list(q.criteria)
            ps = _softmax([_overlap(st, f"{k} {q.criteria[k] or ''}") for k in keys])
            best = keys[ps.index(max(ps))]
            answers[name] = SimpleNamespace(
                type="choice", choice=best, confidence=_concentration(ps),
                probabilities={k: round(p, 3) for k, p in zip(keys, ps)})
        elif isinstance(q, Score):
            ps = _softmax([_overlap(st, lvl) for lvl in q.criteria])
            answers[name] = SimpleNamespace(
                type="score", score=round(sum(i * p for i, p in enumerate(ps)), 3),
                confidence=_concentration(ps),
                probabilities={str(i): round(p, 3) for i, p in enumerate(ps)},
                legend={str(i): lvl for i, lvl in enumerate(q.criteria)})
        else:
            x = _overlap(st, q.instructions)
            answers[name] = SimpleNamespace(type="noul", noul=round(1 / (1 + math.exp(-4 * (x - 0.5))), 3))
    return SimpleNamespace(model="MOCK-not-jev", answers=answers)
