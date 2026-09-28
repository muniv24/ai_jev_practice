"""Project 4 - Grade LLM answers cheaply (LLM-as-judge replacement).

Score each dimension SEPARATELY, then combine in code (composite scoring).
Run:  python -m projects.p4_llm_output_grader
"""
from eval_harness import load_csv, report
from jev_client import Noul, Score, ask

QUESTIONS = {
    "correct": Score(
        instructions="Is the answer factually correct for the question?",
        criteria=[
            "Wrong: contains a false fact or wrong value",
            "Vague: not false but too short, missing the key fact",
            "Correct: accurate and names the key fact, protocol, port or value",
        ],
    ),
    "hedging": Noul(instructions="The answer hedges or guesses, e.g. I think, around, or so, it depends"),
}


def main():
    results = []
    for row in load_csv("data/answers.csv"):
        state = {"question": row["question"], "answer": row["answer"]}
        a = ask(state, QUESTIONS).answers
        grade = a["correct"].score
        if a["hedging"].noul > 0.7:
            grade = min(grade, 0.5)  # business rule applied in code
        results.append((str(round(grade)), row["grade"], a["correct"].confidence))
        print(f"grade={grade:4.2f} conf={a['correct'].confidence:.2f} | {row['answer'][:55]}")
    report(results, "answer grading (0 wrong / 1 vague / 2 correct)")


if __name__ == "__main__":
    main()
