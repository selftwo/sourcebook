#!/usr/bin/env python3
"""Replay the sourcebook demo end to end, offline, from the local example sources.

Everything a script can do deterministically is done here. Everything an agent judged
(tiers, claims, adjudications, the plan, the prose) is checked into this directory as data,
so the demo is reproducible without a model and the checked-in artifact is exactly what this
script produces.

    python3 examples/demo/build.py            # build and gate
    python3 examples/demo/build.py --tamper   # then watch it refuse
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

DEMO = Path(__file__).resolve().parent
KIT = DEMO.parent.parent
SB = [sys.executable, str(KIT / "scripts" / "sb.py")]
WS = DEMO / "workspace"

QUESTION = "Can a Harbour card be used to pay a fare on a Northline ferry right now?"

# tier and reason are judgment. They are recorded here because a human made them once.
SOURCES = [
    ("northline-fare-interoperability.md", "A",
     "the ferry operator's own fares page: the primary source for what its readers accept",
     "Fare payment interoperability", "Northline Ferries", "2026-02-12"),
    ("meridian-harbour-joint-announcement.md", "A",
     "joint announcement issued by both parties to the agreement",
     "Joint announcement: Northline Ferries and Harbour Transit Authority",
     "Northline Ferries and Harbour Transit Authority", "2026-01-03"),
    ("harbour-trade-weekly.md", "B",
     "bylined, dated trade reporting with named accountability",
     "Harbour and Northline sign card interoperability deal", "Harbour Trade Weekly",
     "2026-01-06"),
    ("traveller-forum-gangway.md", "C",
     "pattern evidence about what travellers actually hit at the gangway, not authority "
     "about the scheme's status",
     "Thread: Harbour card on the Northline ferry?", "Ferry Travellers Forum", "2026-02-16"),
]


def run(*args, check=True):
    """Every sb call runs with the workspace as cwd, so every locator it records is
    workspace-relative and the demo is byte-reproducible on any machine."""
    print("$ sb " + " ".join(args))
    r = subprocess.run(SB + list(args), text=True, cwd=WS)
    if check and r.returncode != 0:
        print(f"FAILED with exit {r.returncode}", file=sys.stderr)
        sys.exit(r.returncode)
    return r


def build() -> None:
    if WS.exists():
        shutil.rmtree(WS)
    WS.mkdir(parents=True)

    subprocess.run(SB + ["init", "--dir", str(WS), "--question", QUESTION],
                   check=True, text=True)

    # Copy the example sources inside the workspace so their canonical locators are
    # workspace-relative, which is what makes the derived source ids reproducible anywhere.
    (WS / "input").mkdir(exist_ok=True)
    for name, *_ in SOURCES:
        shutil.copy2(DEMO / "sources" / name, WS / "input" / name)

    for name, tier, reason, title, publisher, published in SOURCES:
        run("add", f"input/{name}", "--tier", tier, "--reason", reason,
            "--title", title, "--publisher", publisher, "--published", published,
            "--lang", "en", "--license", "example-synthetic")

    run("extract")
    run("chunk")
    run("index")

    shutil.copy2(DEMO / "plan.json", WS / "plan.json")
    (WS / "ledger").mkdir(exist_ok=True)
    shutil.copy2(DEMO / "claims.json", WS / "ledger" / "claims.json")
    run("adjudicate", "--file", str(DEMO / "adjudications.json"), "--apply")

    (WS / "build").mkdir(exist_ok=True)
    shutil.copy2(DEMO / "answer.src.html", WS / "build" / "answer.html")
    run("ledger", "--html", "--out", "build/ledger.html")
    run("inject", "build/answer.html", "--ledger", "build/ledger.html")
    run("ledger", "--md", "--out", "build/ledger.md")
    run("ledger", "--sources", "--out", "build/sources.md")

    shutil.copy2(DEMO / "podcast.script.json", WS / "build" / "podcast.script.json")
    run("tts-plan")

    run("lint", "build/answer.html")
    run("verify")
    run("verify", "--podcast")
    run("package", "--out", "dist")
    run("package", "--out", "dist", "--verify")
    run("status")

    # The checked-in demo artifact is exactly what this script just produced.
    shutil.copy2(WS / "build" / "answer.html", DEMO / "answer.html")
    shutil.copy2(WS / "build" / "ledger.md", DEMO / "ledger.md")
    print("\nBuilt " + str(DEMO / "answer.html"))


def tamper() -> None:
    """The thirty seconds that make the point: edit one digit and watch the gate refuse."""
    path = WS / "ledger" / "claims.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    target = None
    for c in data["claims"]:
        for e in c.get("evidence", []):
            if "1.4 million active Meridian Cards" in e.get("quote", ""):
                target = (c, e)
                break
    if target is None:
        print("no quote to tamper with; run the build first", file=sys.stderr)
        sys.exit(1)
    claim, ev = target
    ev["quote"] = ev["quote"].replace("1.4 million", "3.9 million")
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\ntampered: claim {claim['id']} now says 3.9 million\n")
    r = run("verify", check=False)
    print(f"\nsb verify exited {r.returncode}. "
          f"The number in the page is the number in the source, or there is no page.")
    ev["quote"] = ev["quote"].replace("3.9 million", "1.4 million")
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("\nrestored.")
    run("verify")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tamper", action="store_true",
                   help="after building, break one quote and show the gate refusing")
    args = p.parse_args()
    build()
    if args.tamper:
        tamper()
    return 0


if __name__ == "__main__":
    sys.exit(main())
