"""Project 1 - Support ticket triage (Choice + Noul in ONE call).

Run:  python -m projects.p1_ticket_triage
"""
from eval_harness import load_csv, report
from jev_client import Choice, Noul, ask

QUESTIONS = {
    "team": Choice(
        instructions="Which team should handle this support ticket?",
        criteria={
            "billing": "Invoices, charges, refunds, payment, subscription billing",
            "network": "VPN, BGP, firewall, DNS, Wi-Fi, switch ports, connectivity outages",
            "identity": "Login, password, MFA, SSO, account access and permissions",
            "sales": "Quotes, pricing, licenses, demos, discounts",
        },
    ),
    "urgent": Noul(instructions="This ticket describes an outage, deadline or time-critical impact right now"),
}


def main():
    team_results, urgent_results = [], []
    for row in load_csv("data/tickets.csv"):
        a = ask(row["text"], QUESTIONS).answers
        team, urgent_p = a["team"], a["urgent"].noul
        urgent = "yes" if urgent_p >= 0.5 else "no"
        team_results.append((team.choice, row["team"], team.confidence))
        urgent_results.append((urgent, row["urgent"], abs(2 * urgent_p - 1)))
        print(f"{team.choice:<9} conf={team.confidence:.2f} urgent={urgent_p:.2f} | {row['text'][:60]}")
    report(team_results, "team routing")
    report(urgent_results, "urgency (confidence = |2p-1|)")


if __name__ == "__main__":
    main()
