#!/usr/bin/env python3
"""Regenerate the demo's agent-authored data files with content-addressed ids.

The judgment in here (which sentences are worth claiming, what confidence each earned, how
the two conflicts should be adjudicated) is a human's. This script only derives the ids and
writes the JSON, so the checked-in files stay consistent when the wording changes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DEMO = Path(__file__).resolve().parent
sys.path.insert(0, str(DEMO.parent.parent / "scripts"))
from sourcebook.ids import claim_id, cluster_id  # noqa: E402

OP = "src_1823e227204b"   # tier A, Northline Ferries fares page, 2026-02-12
JA = "src_8c4cd8d0fb38"   # tier A, joint announcement, 2026-01-03
TW = "src_058d16216794"   # tier B, Harbour Trade Weekly, 2026-01-06
FF = "src_ccde41bed7b4"   # tier C, traveller forum thread, 2026-02-16

RECHECK_OP = "https://northline.example/fares/interoperability"
RECHECK_TW = "https://harbourtradeweekly.example/2026/01/06/interoperability-deal"


def ev(source_id, start, end, quote):
    return {"source_id": source_id, "start": start, "end": end, "quote": quote}


CLAIMS = [
    dict(key="live-no",
         text="Harbour Transit is not on Northline's live interoperability list, and a Harbour "
              "card cannot be used to pay a fare on a Northline service as of 12 February 2026.",
         topic_key="northline.harbour.live", kind="fact", confidence="verified",
         volatile=True, as_of="2026-02-12", recheck=RECHECK_OP,
         evidence=[ev(OP, 1093, 1220,
                      "Harbour Transit is not on the live\nlist above, and Harbour cards cannot "
                      "currently be used to pay a fare on a Northline service.")]),

    dict(key="enables",
         text="Trade reporting describes the January 2026 agreement as enabling Harbour cards "
              "to be used for fare payment on Northline coastal services.",
         topic_key="northline.harbour.live", kind="fact", confidence="reported",
         volatile=False, as_of="2026-01-06", recheck=None,
         evidence=[ev(TW, 164, 273,
                      "have signed an agreement that enables\nHarbour cards to be used for fare "
                      "payment on Northline coastal services")]),

    dict(key="signed",
         text="Northline Ferries and the Harbour Transit Authority signed a fare "
              "interoperability agreement on 3 January 2026.",
         topic_key="harbour.agreement.signed", kind="date", confidence="verified",
         volatile=False, as_of=None, recheck=None,
         evidence=[ev(JA, 208, 320,
                      "signed an agreement covering fare\ninteroperability between the Harbour "
                      "card and Northline coastal ferry services")]),

    dict(key="no-date",
         text="Neither operator has announced a date for passenger availability.",
         topic_key="harbour.agreement.availability", kind="fact", confidence="verified",
         volatile=True, as_of="2026-01-03", recheck=RECHECK_TW,
         evidence=[ev(JA, 599, 661,
                      "Neither party is announcing a date for passenger availability.")]),

    dict(key="terminals",
         text="The signed agreement covers forty-two terminals across the two networks.",
         topic_key="harbour.agreement.scope", kind="number", confidence="verified",
         volatile=False, as_of=None, recheck=None,
         evidence=[ev(JA, 763, 828,
                      "The agreement covers forty-two terminals across the two networks.")]),

    dict(key="cards-14",
         text="Northline reports 1.4 million active Meridian Cards in circulation as of "
              "12 February 2026.",
         topic_key="meridian.cards.active", kind="number", confidence="verified",
         volatile=True, as_of="2026-02-12", recheck=RECHECK_OP,
         evidence=[ev(OP, 410, 492,
                      "There are 1.4 million active Meridian Cards in circulation as of "
                      "12 February 2026.")]),

    dict(key="cards-19",
         text="An earlier industry estimate put the number of active Meridian Cards at "
              "1.9 million.",
         topic_key="meridian.cards.active", kind="number", confidence="reported",
         volatile=True, as_of="2026-01-06", recheck=RECHECK_TW,
         evidence=[ev(TW, 602, 685,
                      "An earlier industry\nestimate put the number of active Meridian Cards at "
                      "1.9 million")]),

    dict(key="live-list",
         text="The only partner schemes live for cross-border tap-and-go on Northline services "
              "are Calder Transit and Vantis Rail.",
         topic_key="northline.livelist", kind="entity", confidence="verified",
         volatile=True, as_of="2026-02-12", recheck=RECHECK_OP,
         evidence=[ev(OP, 692, 775,
                      "Calder Transit, live since 4 August 2025\n- Vantis Rail, live since "
                      "19 November 2025")]),

    dict(key="paper",
         text="Paper tickets and cash remain available at every Northline terminal counter and "
              "at the quayside machines.",
         topic_key="northline.paper-tickets", kind="fact", confidence="verified",
         volatile=False, as_of=None, recheck=None,
         evidence=[ev(OP, 305, 408,
                      "Paper\ntickets remain available at every terminal counter and at the "
                      "quayside machines, which take\ncash.")]),

    dict(key="declines",
         text="Travellers report Harbour cards being declined at the Northline gangway in "
              "December 2025 and again in February 2026.",
         topic_key="northline.harbour.traveller-reports", kind="fact", confidence="reported",
         volatile=False, as_of="2026-02-16", recheck=None,
         evidence=[ev(FF, 78, 160,
                      "Tried tapping my Harbour card at the Northline gangway on Tuesday. "
                      "Declined twice."),
                   ev(FF, 359, 413,
                      "Staff at the quay said the link is not switched on yet")]),

    dict(key="meridian-works",
         text="The same travellers report that Meridian card taps work on the routes they used.",
         topic_key="northline.meridian.works", kind="fact", confidence="reported",
         volatile=False, as_of="2026-02-16", recheck=None,
         evidence=[ev(FF, 563, 628,
                      "the Meridian tap works\nfine on every route I have taken this year")]),

    dict(key="plan",
         text="For a trip in the next few months, plan to pay with cash, a paper ticket, or a "
              "Meridian Card rather than a Harbour card.",
         topic_key="traveller.plan", kind="recommendation", confidence="inferred",
         volatile=False, as_of=None, recheck=None, evidence=[]),
]

IDS = {c["key"]: claim_id(c["text"]) for c in CLAIMS}

ADJUDICATIONS = [
    dict(topic_key="northline.harbour.live", outcome="both_stand", winner=None,
         claim_ids=["live-no", "enables"],
         reason="The operator's own page is a status claim: Harbour is absent from the live "
                "list and a tap is declined today. The trade report is a claim about what the "
                "signed agreement is for. Both are accurate about different things, and a "
                "traveller who reads only the second one turns up at the gangway and cannot "
                "board. Both stand, and both appear in the artifact.",
         decided_at="2026-07-26T10:02:11Z"),
    dict(topic_key="meridian.cards.active", outcome="supersede", winner="cards-14",
         claim_ids=["cards-14", "cards-19"],
         reason="Both figures describe the same population. The operator issues the cards and "
                "publishes the definition of an active card, so it is closer to the fact than "
                "an unattributed industry estimate, and its figure is five weeks more recent. "
                "Tier and recency point the same way, so this is a supersede rather than a "
                "genuine disagreement.",
         decided_at="2026-07-26T10:04:40Z"),
]

PLAN = {
    "schema_version": 1,
    "type": "answer",
    "title": "Can a Harbour card pay a fare on a Northline ferry right now?",
    "audience": "one traveller planning a coastal trip in the next few months",
    "thesis": "No. The agreement is signed, the service is not live for Harbour cards, and the "
              "plan that works today is cash, a paper ticket, or a Meridian Card.",
    "register": "editorial",
    "images": {"mode": "none", "slots": []},
    "constraints": {"palette_strategy": "committed", "motion": "minimal",
                    "breakpoints": [360, 768, 1200]},
    "sections": [
        {"id": "answer", "heading": "The short answer",
         "intent": "state the finding, its date, and what to do",
         "claim_ids": ["live-no", "plan"]},
        {"id": "signed", "heading": "What was actually signed",
         "intent": "the agreement, its scope, and what it does not yet include",
         "claim_ids": ["signed", "terminals", "no-date"]},
        {"id": "disputed", "heading": "Where the sources disagree",
         "intent": "both sides of the adjudicated conflict, side by side",
         "claim_ids": ["enables", "live-no"]},
        {"id": "ground", "heading": "What travellers are hitting at the gangway",
         "intent": "pattern evidence, held at reported",
         "claim_ids": ["declines", "meridian-works"]},
        {"id": "scale", "heading": "How big the Meridian scheme is",
         "intent": "the number, its date, and the estimate it supersedes",
         "claim_ids": ["cards-14", "live-list"]},
        {"id": "do", "heading": "What to do instead",
         "intent": "the fallback that works today",
         "claim_ids": ["paper", "plan"]},
    ],
}


def main() -> int:
    claims = []
    for c in CLAIMS:
        out = {k: v for k, v in c.items() if k != "key"}
        out["id"] = IDS[c["key"]]
        out["contradicts"] = []
        out["status"] = "active"
        out["superseded_by"] = None
        out["notes"] = ""
        claims.append(out)
    (DEMO / "claims.json").write_text(
        json.dumps({"schema_version": 1, "claims": sorted(claims, key=lambda c: c["id"])},
                   indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    adjs = []
    for a in ADJUDICATIONS:
        adjs.append({
            "cluster_id": cluster_id(a["topic_key"]),
            "topic_key": a["topic_key"],
            "claim_ids": [IDS[k] for k in a["claim_ids"]],
            "outcome": a["outcome"],
            "winner": IDS[a["winner"]] if a["winner"] else None,
            "reason": a["reason"],
            "decided_at": a["decided_at"],
        })
    (DEMO / "adjudications.json").write_text(
        json.dumps({"schema_version": 1, "adjudications": adjs}, indent=2, sort_keys=True,
                   ensure_ascii=False) + "\n", encoding="utf-8")

    plan = dict(PLAN)
    plan["sections"] = [dict(s, claim_ids=[IDS[k] for k in s["claim_ids"]])
                        for s in PLAN["sections"]]
    (DEMO / "plan.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    (DEMO / "claim-ids.json").write_text(
        json.dumps(IDS, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for key, cid in sorted(IDS.items()):
        print(f"{key:<16} {cid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
