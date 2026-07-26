"""`sb contradictions` — mechanical detection, never adjudication.

The script emits candidates and stops. False positives are expected and cheap; the agent
dismisses one with `outcome: scope_split` and a written reason. Nothing here decides which
of two claims is true, because nothing here can.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from . import EXIT_GATE, EXIT_OK
from .ids import cluster_id
from .ledger import load_adjudications, load_claims

DETECTOR_VERSION = 1

NEGATIONS = {"not", "no", "never", "cannot", "can't", "without", "fails", "lacks",
             "absent", "excludes", "unavailable", "non-"}
_NEG_PHRASE = re.compile(r"\b(not|no|never|cannot|can't|without|fails to|does not|do not|"
                         r"is not|are not|lacks|absent|excludes|unavailable|non-)\b", re.I)

_NUM = re.compile(r"(-?\d[\d,]*(?:\.\d+)?)\s*(%|k\b|m\b|bn\b|b\b|million|billion|thousand)?", re.I)
_SUFFIX = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6,
           "bn": 1e9, "b": 1e9, "billion": 1e9}
_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

TOLERANCE = 0.05
RECENCY_DAYS = 180


def leading_number(text: str) -> float | None:
    m = _NUM.search(text)
    if not m:
        return None
    try:
        value = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    suffix = (m.group(2) or "").lower().rstrip(".")
    if suffix in _SUFFIX:
        value *= _SUFFIX[suffix]
    return value


def numeric_conflict(a: dict, b: dict, tol: float = TOLERANCE) -> bool:
    if a["kind"] != "number" or b["kind"] != "number":
        return False
    x, y = leading_number(a["text"]), leading_number(b["text"])
    if x is None or y is None:
        return False
    scale = max(abs(x), abs(y)) or 1.0
    return abs(x - y) / scale > tol


def _dates(text: str) -> set[str]:
    return {"-".join(m.groups()) for m in _DATE.finditer(text)}


def date_conflict(a: dict, b: dict) -> bool:
    if a["kind"] != "date" or b["kind"] != "date":
        return False
    da, db = _dates(a["text"]), _dates(b["text"])
    return bool(da and db and da != db)


def polarity_conflict(a: dict, b: dict) -> bool:
    na = bool(_NEG_PHRASE.search(a["text"]))
    nb = bool(_NEG_PHRASE.search(b["text"]))
    return na != nb


def recency_spread(a: dict, b: dict, days: int = RECENCY_DAYS) -> bool:
    if not (a.get("volatile") and b.get("volatile")):
        return False
    if not (a.get("as_of") and b.get("as_of")):
        return False
    try:
        da = date.fromisoformat(a["as_of"])
        db = date.fromisoformat(b["as_of"])
    except ValueError:
        return False
    return abs((da - db).days) > days


def explicit_link(a: dict, b: dict) -> bool:
    return b["id"] in a.get("contradicts", []) or a["id"] in b.get("contradicts", [])


DETECTORS = [
    ("numeric", numeric_conflict),
    ("date", date_conflict),
    ("polarity", polarity_conflict),
    ("explicit", explicit_link),
    ("recency", recency_spread),
]


def detect(root: Path) -> list[dict]:
    claims = [c for c in load_claims(root) if c.get("status") == "active"]
    groups: dict[str, list[dict]] = {}
    for c in claims:
        groups.setdefault(c["topic_key"], []).append(c)

    adjudicated = {a["cluster_id"]: a for a in load_adjudications(root)}
    clusters: list[dict] = []
    for topic, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        members = sorted(members, key=lambda c: c["id"])
        reasons: set[str] = set()
        involved: set[str] = set()
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                for name, fn in DETECTORS:
                    if fn(a, b):
                        reasons.add(name)
                        involved.update({a["id"], b["id"]})
        if not reasons:
            continue
        cid = cluster_id(topic)
        adj = adjudicated.get(cid)
        # An adjudication covers the claims it names. A member that arrived afterwards was
        # never weighed, so the cluster reopens rather than inheriting somebody else's verdict.
        unadjudicated = sorted(involved - set(adj.get("claim_ids", []))) if adj else []
        clusters.append({
            "cluster_id": cid,
            "topic_key": topic,
            "claim_ids": sorted(involved),
            "detectors": sorted(reasons),
            "status": "RESOLVED" if adj and not unadjudicated else "OPEN",
            "outcome": adj["outcome"] if adj else None,
            "unadjudicated_claim_ids": unadjudicated,
        })
    return clusters


def open_clusters(root: Path) -> list[dict]:
    return [c for c in detect(root) if c["status"] == "OPEN"]


def report(root: Path, as_json: bool = False, strict: bool = False) -> int:
    clusters = detect(root)
    if as_json:
        print(json.dumps(clusters, indent=2, ensure_ascii=False))
    elif not clusters:
        print("no contradiction candidates")
    else:
        for c in clusters:
            state = c["status"] + (f" {c['outcome']}" if c["outcome"] else "")
            if c["unadjudicated_claim_ids"]:
                state += " (new since the adjudication: " \
                         + ", ".join(c["unadjudicated_claim_ids"]) + ")"
            print(f"{c['cluster_id']}  {c['topic_key']}  {'+'.join(c['detectors'])}  "
                  f"{' vs '.join(c['claim_ids'])}   {state}")
        opens = [c for c in clusters if c["status"] == "OPEN"]
        if opens:
            print()
            print("Adjudicate every OPEN cluster before composing. Write ledger/adjudications.json")
            print("with one of: supersede | both_stand | scope_split | retract, and a written reason.")
            print("`both_stand` obligates the artifact to show both sides.")
    if strict and any(c["status"] == "OPEN" for c in clusters):
        for c in clusters:
            if c["status"] == "OPEN":
                print(f"E-CLUSTER-OPEN  {c['cluster_id']}  {c['topic_key']} is unadjudicated",
                      file=sys.stderr)
        return EXIT_GATE
    return EXIT_OK


def _apply(claims: dict[str, dict], adjs: list[dict]) -> list[tuple[str, str, str]]:
    """Mutate `claims` in place. Returns [(claim_id, cluster_id, what changed)].

    The single definition of what a recorded adjudication mechanically obliges. `apply_outcomes`
    writes the result; `unapplied` runs it on a throwaway copy so `sb verify` can fail on the
    difference instead of trusting that somebody remembered `--apply`.
    """
    changed: list[tuple[str, str, str]] = []
    for adj in adjs:
        cid = adj.get("cluster_id", "?")
        members = [claims[c] for c in adj["claim_ids"] if c in claims]
        if adj["outcome"] == "supersede" and adj.get("winner"):
            for c in members:
                if c["id"] != adj["winner"] and c["status"] == "active":
                    c["status"] = "superseded"
                    c["superseded_by"] = adj["winner"]
                    changed.append((c["id"], cid, f"status -> superseded by {adj['winner']}"))
        elif adj["outcome"] == "both_stand":
            for c in members:
                if c["status"] == "active" and c["confidence"] != "contested":
                    c["confidence"] = "contested"
                    changed.append((c["id"], cid, "confidence -> contested"))
        elif adj["outcome"] == "retract":
            for c in members:
                if adj.get("winner") and c["id"] != adj["winner"] and c["status"] == "active":
                    c["status"] = "retracted"
                    changed.append((c["id"], cid, "status -> retracted"))
    return changed


def apply_outcomes(root: Path) -> list[str]:
    """Enforce the mechanical consequences of a recorded adjudication.

    supersede -> losers become `superseded`; both_stand -> every member becomes `contested`.
    Returns the list of claim ids it changed. Judgment stays with the agent; only the
    bookkeeping is automatic.
    """
    from .ledger import save_claims

    claims = {c["id"]: c for c in load_claims(root)}
    changed = _apply(claims, load_adjudications(root))
    if changed:
        save_claims(root, list(claims.values()))
    return [cid for cid, _, _ in changed]


def unapplied(root: Path) -> list[tuple[str, str, str]]:
    """What `sb adjudicate --apply` would still change: an adjudication with no effect.

    A `both_stand` that never reached the claims leaves nothing for `E-CONTESTED-HIDDEN` to
    fire on, so an artifact that quietly picks a side would pass the whole gate.
    """
    claims = {c["id"]: json.loads(json.dumps(c)) for c in load_claims(root)}
    return _apply(claims, load_adjudications(root))
