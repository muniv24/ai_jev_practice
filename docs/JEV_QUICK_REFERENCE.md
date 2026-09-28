# TypeSafe Jev — Quick Reference

> Snapshot as of **Sep 2026**, early access. Jev was released 15 Sep 2026. Numbers below are
> TypeSafe's own claims unless noted. Always re-check https://docs.typesafe.ai/llms.txt.

## 1. What it is (one line)

**Jev = a "System One" decision model.** It does not write text. You give it a `state` and typed
questions, and it returns **typed answers + probabilities + confidence** that code can use directly.

| | LLM (GPT / Claude) — "System 2" | Jev — "System 1" |
|---|---|---|
| Output | Free text (you parse it) | Typed value from a set **you define** |
| Uncertainty | Not exposed reliably | `probabilities` + `confidence` on every answer |
| Speed / cost | Seconds, $/MTok out | 70–500 ms; $0.042/MTok input; output free (claimed) |
| Good at | Reasoning, generation, planning | Routing, triage, scoring, gating, tagging |
| Bad at | High-volume, sub-second decisions | Text generation, arithmetic, open-ended reasoning |

Training method: "Reinforcement Learning for Calibrated Decisions" (RLCD) with a parallel sampler,
which produces all outputs in one pass instead of token by token.

## 2. Setup

```bash
pip install typesafe-sdk          # Python >= 3.10  (verified on PyPI: 0.7.2)
export TYPESAFE_API_KEY="sk-..."  # https://console.typesafe.ai/settings/keys
```
- Playground (no code): https://console.typesafe.ai/playground
- Raw HTTP: `POST https://api.typesafe.ai/v1/systemone`
- JS/TS: `npm install @typesafe-ai/sdk` (Node 20+)

## 3. The three primitives

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient()                     # reads TYPESAFE_API_KEY
resp = client.system_one(
    state=ticket_text,                        # str or dict
    questions={
        "department": Choice(                 # pick ONE of up to 255 options
            instructions="Which team should handle this",
            criteria={                        # DICT: key -> description
                "billing": "Payment or subscription issues",
                "technical": "Bugs or integration problems",
            },
        ),
        "frustration": Score(                 # ordered spectrum, 2-10 levels
            instructions="How frustrated the customer appears",
            criteria=[                        # LIST: low -> high
                "Calm, just stating facts",
                "Frustrated but civil",
                "Very angry, strong language",
            ],
        ),
        "is_urgent": Noul(                    # probability a statement is TRUE
            instructions="The message conveys urgency or time-sensitivity",
        ),
    },
)
resp.answers["department"].choice       # "billing"
resp.answers["frustration"].score       # 1.43  (probability-weighted level)
resp.answers["is_urgent"].noul          # 0.87  (0..1)
```

| Primitive | Use when | Response fields |
|---|---|---|
| `Choice` | Unordered categories | `choice`, `probabilities{opt:p}`, `confidence` |
| `Score` | Ordered levels (severity, quality) | `score`, `probabilities{"0":p..}`, `confidence`, `legend` |
| `Noul` | Yes/no fact | `noul` (0–1) |

Example raw response:
```json
{"model": "jev-1.13.0",
 "answers": {"department": {"type": "choice", "choice": "returns", "confidence": 1.0,
             "probabilities": {"shipping": 0.0, "returns": 1.0, "billing": 0.0}}}}
```

**Criteria can be richer** when options get confused:
`{"what": "...", "not_for": "...", "examples": ["..."]}` (Choice). Score levels also accept `what`/`examples`.

## 4. Writing good questions

1. **One dimension per question.** Split "is it urgent AND risky AND billing?" into 3 questions and
   combine them **in code**. Questions run in parallel and in isolation, so adding more doesn't
   degrade the others ("no context rot").
2. **Describe concrete situations**, not degrees: "workaround exists" beats "moderately severe".
3. Use 3–10 clearly different Score levels. Add `examples` only when the model splits between levels.
4. Always read `probabilities` + `confidence`, not just the top answer. The same `score` can come from
   very different distributions.

## 5. Confidence: the most important field

Confidence = how concentrated the probability distribution is (1.0 = one peak).

| Confidence | Suggested action (docs) |
|---|---|
| < 0.5 | Route to a human / ask for clarification |
| 0.5 – 0.9 | Confirm first or verify (e.g. escalate to an LLM) |
| > 0.9 | Act automatically (if the action is reversible) |

```python
if conf < 0.5:
    route_to_human(msg)
elif action.choice == "approve_transfer":
    confirm_then_execute(id) if conf > 0.9 else ask_user_to_confirm(id)
```
Thresholds are domain-specific. **Measure calibration on your own labeled data** (see `eval_harness.py`).
Use stricter thresholds for destructive actions.

## 6. Patterns (docs.typesafe.ai/patterns)

| Pattern | Idea | Buys you |
|---|---|---|
| Speculative fan-out | Ask many (even speculative) questions in one call and let code choose | Cost, speed |
| Confidence-gated routing | Use confidence as a 2nd decision axis | Safety, reliability |
| Composite scoring | Several dimension scores combined into one | Reliability |
| Intent routing | Classify intent, then dispatch to a handler | Cost, speed |

**Hybrid architecture (the main idea):**
```
request --> Jev (70-500ms, cheap) --conf high--> deterministic code / small model
                                  --conf mid---> big LLM (reasoning / generation)
                                  --conf low---> human
LLM agent --proposed tool call--> Jev Noul "is this destructive?" --> allow / confirm / block
```

## 7. Limits (claimed)

- Context 64k tokens total, 32k max for a single question
- 250k tokens/s, 1,200 requests/min
- Choice ≤ 255 options; Score 2–10 levels
- Structured outputs rule out *type* errors, but **a well-formed answer can still be wrong.**
  Evaluate it.

## 8. Ecosystem

- LangChain: `langchain_typesafe` has `TypeSafeClassifier`, plus experimental `ModelRouterMiddleware`
  (picks a cheap vs. strong LLM) and `AutoModeMiddleware` (screens tool calls before execution).
  *Not verified locally.* See the LangChain blog below.
- Agent skill: `npx skills add typesafe-ai/skills --skill typesafe-ai`
- Also available via Vercel AI Gateway.

## 9. Links

- Docs index (LLM-friendly): https://docs.typesafe.ai/llms.txt
- Quickstart: https://docs.typesafe.ai/introduction/quickstart
- Primitives: https://docs.typesafe.ai/primitives/choice · /score · /noul
- Confidence: https://docs.typesafe.ai/confidence · Patterns: https://docs.typesafe.ai/patterns
- Launch blog: https://typesafe.ai/blog/introducing-system-one-models-and-jev
- Evals: https://evals.typesafe.ai
- LangChain harness: https://www.langchain.com/blog/building-a-harness-with-jev
