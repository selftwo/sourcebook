"""`sb verify` — the ship gate. Every check here is a string comparison or a count.

No gate in this file consults a model, and none of them can be argued with.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import EXIT_GATE, EXIT_OK
from .ids import NORMALIZER_VERSION, sha256_text
from .ledger import (MAX_QUOTE_CHARS, MAX_QUOTE_CHARS_PER_SOURCE, MAX_QUOTE_WORDS,
                     MAX_QUOTES_PER_SOURCE, is_http_url, load_adjudications, load_claims,
                     load_plan, marks_for, resolve_ordinals, verify_evidence)
from .lint.html import parse
from .manifest import check, load, now, save, sources

WEAK_KINDS = {"number", "date", "entity"}
CONF_RANK = {"unsupported": 0, "inferred": 1, "reported": 2, "contested": 3, "verified": 4}


class Report:
    def __init__(self):
        self.gates: list[tuple[str, list[str], str]] = []

    def gate(self, name: str, findings: list[str], note: str = "") -> None:
        self.gates.append((name, findings, note))

    @property
    def errors(self) -> list[str]:
        return [f for _, fs, _ in self.gates for f in fs]

    def print(self) -> None:
        for name, findings, note in self.gates:
            if findings:
                print(f"  x {name:<14} {len(findings)} finding(s)")
                for f in findings:
                    print(f"      {f}")
            else:
                print(f"  . {name:<14} {note}")
        print("  PASS" if not self.errors else f"  FAIL  {len(self.errors)} finding(s)")

    def as_dict(self) -> dict:
        return {"gates": [{"gate": n, "findings": f, "note": note} for n, f, note in self.gates],
                "pass": not self.errors}


# ----------------------------------------------------------------------- gates


def gate_schemas(root: Path, rep: Report) -> None:
    findings = check(load(root), "manifest", "sourcebook.json")
    srcs = sources(root)
    for s in srcs:
        findings += check(s, "source", f"sources/{s.get('id', '?')}/source.json")
    cp = root / "ledger" / "claims.json"
    if cp.is_file():
        findings += check(json.loads(cp.read_text(encoding="utf-8")), "claim", "ledger/claims.json")
    ap = root / "ledger" / "adjudications.json"
    if ap.is_file():
        findings += check(json.loads(ap.read_text(encoding="utf-8")), "adjudication",
                          "ledger/adjudications.json")
    plan = load_plan(root)
    if plan is not None:
        findings += check(plan, "plan", "plan.json")
    rep.gate("schemas", findings,
             f"{len(srcs)} sources, {len(load_claims(root))} claims")


def gate_normalizer(root: Path, rep: Report) -> None:
    findings = []
    for s in sources(root):
        if s.get("status") != "ready":
            continue
        p = root / "sources" / s["id"] / "normalized.md"
        if not p.is_file():
            findings.append(f"E-NORM-MISSING  {s['id']}  status=ready but no normalized.md")
            continue
        if s.get("normalizer_version") != NORMALIZER_VERSION:
            findings.append(f"E-NORM-DRIFT  {s['id']}  normalizer_version "
                            f"{s.get('normalizer_version')} != {NORMALIZER_VERSION}")
            continue
        actual = sha256_text(p.read_text(encoding="utf-8"))
        if s.get("normalized_sha256") and actual != s["normalized_sha256"]:
            findings.append(f"E-NORM-DRIFT  {s['id']}  normalized.md hash changed; "
                            f"every offset into it is suspect")
    rep.gate("normalizer", findings, f"{len(sources(root))} sources at v{NORMALIZER_VERSION}")


def gate_quotes(root: Path, rep: Report) -> None:
    claims = load_claims(root)
    findings: list[str] = []
    total = 0
    for c in claims:
        total += len(c.get("evidence", []))
        findings += verify_evidence(root, c)
    rep.gate("quotes", findings, f"{total - len(findings)}/{total} byte-exact")


def gate_confidence(root: Path, rep: Report) -> None:
    findings = []
    plan = load_plan(root)
    planned = {cid for s in (plan or {}).get("sections", []) for cid in s.get("claim_ids", [])}
    for c in load_claims(root):
        n = len(c.get("evidence", []))
        if c["confidence"] == "inferred" and n:
            findings.append(f"E-CONF-MISMATCH  {c['id']}  inferred claims carry zero evidence, found {n}")
        if c["confidence"] != "inferred" and n == 0 and c["confidence"] != "unsupported":
            findings.append(f"E-CONF-MISMATCH  {c['id']}  confidence '{c['confidence']}' with no evidence")
        if c["confidence"] == "unsupported" and c["status"] == "active":
            where = " (referenced by plan.json)" if c["id"] in planned else ""
            findings.append(f"E-UNSUPPORTED  {c['id']}  an unsupported claim cannot ship{where}")
    rep.gate("confidence", findings, f"{len(load_claims(root))} claims consistent")


def gate_tiers(root: Path, rep: Report) -> None:
    srcs = {s["id"]: s for s in sources(root)}
    findings = []
    downgraded = 0
    for s in srcs.values():
        if s.get("tier") in ("A", "D") and not (s.get("tier_reason") or "").strip():
            findings.append(f"E-TIER-REASON  {s['id']}  tier {s['tier']} needs a written reason")
    for c in load_claims(root):
        if c["status"] != "active" or not c.get("evidence"):
            continue
        tiers = {srcs.get(e["source_id"], {}).get("tier", "D") for e in c["evidence"]}
        strong = tiers & {"A", "B"}
        if "D" in tiers and CONF_RANK[c["confidence"]] > CONF_RANK["reported"]:
            findings.append(f"E-TIER-D  {c['id']}  tier D evidence caps confidence at 'reported', "
                            f"found '{c['confidence']}'")
        elif c["kind"] in WEAK_KINDS and not strong:
            if c["confidence"] == "verified":
                findings.append(f"E-TIER-WEAK  {c['id']}  kind '{c['kind']}' cited only to tier "
                                f"{'/'.join(sorted(tiers))}; downgrade to 'reported'")
            else:
                downgraded += 1
    rep.gate("tiers", findings, f"{downgraded} claim(s) correctly held at reported")


def gate_volatility(root: Path, rep: Report) -> None:
    findings = []
    n = 0
    for c in load_claims(root):
        if c.get("recheck") and not is_http_url(c["recheck"]):
            findings.append(f"E-RECHECK-SCHEME  {c['id']}  recheck must be an http(s) URL, "
                            f"found '{c['recheck']}'")
        if not c.get("volatile"):
            continue
        n += 1
        if not c.get("as_of"):
            findings.append(f"E-VOLATILE-UNDATED  {c['id']}  volatile claims need an as_of date")
        if not c.get("recheck"):
            findings.append(f"E-VOLATILE-UNDATED  {c['id']}  volatile claims need a recheck URL")
    rep.gate("volatility", findings, f"{n} volatile claim(s), all dated")


def gate_clusters(root: Path, rep: Report) -> None:
    from .contradict import detect, unapplied

    clusters = detect(root)
    findings = []
    for c in clusters:
        if c["status"] != "OPEN":
            continue
        new = c.get("unadjudicated_claim_ids") or []
        why = (f"; {', '.join(new)} joined the cluster after the adjudication" if new
               else "")
        findings.append(f"E-CLUSTER-OPEN  {c['cluster_id']}  {c['topic_key']} "
                        f"({'+'.join(c['detectors'])}) is unadjudicated{why}")
    adj = load_adjudications(root)
    for a in adj:
        if a["outcome"] == "supersede" and not a.get("winner"):
            findings.append(f"E-ADJ-NOWINNER  {a['cluster_id']}  a supersede needs a winner")
    for claim_id, cluster, what in unapplied(root):
        findings.append(f"E-ADJ-UNAPPLIED  {claim_id}  the adjudication of {cluster} still owes "
                        f"this claim {what}; run `sb adjudicate --apply`")
    rep.gate("clusters", findings, f"{len(clusters)} cluster(s), {len(adj)} adjudicated")


def gate_plan(root: Path, rep: Report) -> None:
    plan = load_plan(root)
    if plan is None:
        rep.gate("plan", [], "no plan.json yet")
        return
    claims = {c["id"]: c for c in load_claims(root)}
    findings = []
    placed = set()
    for section in plan.get("sections", []):
        for cid in section.get("claim_ids", []):
            placed.add(cid)
            c = claims.get(cid)
            if c is None:
                findings.append(f"E-PLAN-ORPHAN  {cid}  referenced by section "
                                f"'{section['id']}' but not in the ledger")
            elif c["status"] != "active":
                findings.append(f"E-PLAN-ORPHAN  {cid}  is {c['status']}, not active")
    for c in claims.values():
        if c["status"] == "active" and c["confidence"] == "contested" and c["id"] not in placed:
            findings.append(f"E-CONTESTED-HIDDEN  {c['id']}  a contested claim must be placed "
                            f"in a section; the artifact may not pick a side quietly")
    rep.gate("plan", findings, f"{len(placed)} claim(s) placed in {len(plan.get('sections', []))} sections")


# ------------------------------------------------------------------ html gate


def gate_html(root: Path, rep: Report, html_path: Path) -> None:
    doc = parse(Path(html_path).read_text(encoding="utf-8"), str(html_path))
    claims = {c["id"]: c for c in load_claims(root)}
    ordinals = resolve_ordinals(root)
    findings: list[str] = []

    ledger_ids = {n.attrs["id"][2:] for n in doc.walk()
                  if n.attrs.get("id", "").startswith("c-")}
    refs = {n.attrs["href"][3:] for n in doc.find_all("a")
            if n.attrs.get("href", "").startswith("#c-")}
    claim_blocks: list[tuple] = []
    for node in doc.walk():
        if "data-claim" in node.attrs:
            claim_blocks.append((node, node.attrs["data-claim"].split()))

    for cid in sorted(refs - ledger_ids):
        findings.append(f"E-REF-DANGLING  {cid}  href=#c-{cid} has no ledger entry")
    for cid in sorted(ledger_ids - refs):
        c = claims.get(cid)
        if c is not None and c.get("confidence") == "inferred":
            continue  # an inferred claim is recorded, never cited. That is the whole point.
        findings.append(f"E-LEDGER-ORPHAN  {cid}  ledger entry is never referenced from the prose")

    doc_text = doc.text()
    cited: set[str] = set()
    for node, ids in claim_blocks:
        marks_present = _marks_in(node)
        for cid in ids:
            cited.add(cid)
            c = claims.get(cid)
            if c is None:
                findings.append(f"E-CLAIM-UNKNOWN  {cid}  data-claim id is not in the ledger")
                continue
            if c["status"] != "active":
                findings.append(f"E-CLAIM-UNKNOWN  {cid}  is {c['status']}, not active")
                continue
            for want in marks_for(c):
                if want not in marks_present:
                    findings.append(
                        f"E-MARK-WRONG  {cid}  block is missing the '{want}' mark implied by "
                        f"confidence={c['confidence']} volatile={bool(c.get('volatile'))}")
            if c["confidence"] == "inferred" and _has_ref_sup(node):
                findings.append(f"E-CITE-INFERRED  {cid}  an inferred claim may never carry a "
                                f"citation marker")
            if c.get("volatile") and c.get("as_of") and c["as_of"] not in doc_text:
                findings.append(f"E-ASOF-MISSING  {cid}  as_of {c['as_of']} does not appear "
                                f"anywhere in the rendered document")

    for c in claims.values():
        if c["status"] == "active" and c["confidence"] == "contested" and c["id"] not in cited:
            findings.append(f"E-CONTESTED-HIDDEN  {c['id']}  contested claim is not rendered; "
                            f"both sides of an adjudicated disagreement must appear")

    legends = [n for n in doc.walk() if "mark-legend" in n.classes]
    if len(legends) != 1:
        findings.append(f"E-LEGEND  {html_path.name}  the mark legend appears {len(legends)} "
                        f"times; it belongs exactly once")

    findings += _quote_budget(root, doc_text)
    findings += _image_evidence(doc)

    rep.gate("html", findings,
             f"{len(refs)} refs resolved, {len(ledger_ids)} ledger entries, "
             f"{len(ordinals)} ordinals")


def _marks_in(node) -> set[str]:
    """Marks belonging to this claim block, excluding any nested data-claim block."""
    found: set[str] = set()

    def walk(n, top=True):
        if not top and "data-claim" in n.attrs:
            return
        for cls in n.classes:
            if cls.startswith("m-"):
                found.add(cls)
        for child in n.children:
            walk(child, False)

    walk(node)
    return found


def _has_ref_sup(node) -> bool:
    def walk(n, top=True):
        if not top and "data-claim" in n.attrs:
            return False
        if n.tag == "sup" and "ref" in n.classes:
            return True
        return any(walk(c, False) for c in n.children)

    return walk(node)


def _quote_budget(root: Path, doc_text: str) -> list[str]:
    findings = []
    per_source_count: dict[str, int] = {}
    per_source_chars: dict[str, int] = {}
    seen: set[tuple] = set()
    for c in load_claims(root):
        for e in c.get("evidence", []):
            q = e.get("quote") or ""
            key = (e["source_id"], e["start"], e["end"])
            if not q or key in seen or q not in doc_text:
                continue
            seen.add(key)
            if len(q) > MAX_QUOTE_CHARS or len(q.split()) > MAX_QUOTE_WORDS:
                findings.append(f"E-QUOTE-BUDGET  {c['id']}  a rendered quote exceeds "
                                f"{MAX_QUOTE_WORDS} words / {MAX_QUOTE_CHARS} chars")
            sid = e["source_id"]
            per_source_count[sid] = per_source_count.get(sid, 0) + 1
            per_source_chars[sid] = per_source_chars.get(sid, 0) + len(q)
    for sid, n in sorted(per_source_count.items()):
        if n > MAX_QUOTES_PER_SOURCE or per_source_chars[sid] > MAX_QUOTE_CHARS_PER_SOURCE:
            findings.append(f"E-QUOTE-BUDGET  {sid}  {n} quotes / {per_source_chars[sid]} chars "
                            f"rendered; the cap is {MAX_QUOTES_PER_SOURCE} / "
                            f"{MAX_QUOTE_CHARS_PER_SOURCE}")
    return findings


def _image_evidence(doc) -> list[str]:
    findings = []
    for img in doc.find_all("img"):
        for anc in list(img.ancestors())[:3]:
            if "data-claim" in anc.attrs and "generated" in (img.attrs.get("data-origin", "")):
                findings.append(f"E-IMG-EVIDENCE  {img.attrs.get('src','<img>')}  a generated "
                                f"image may not illustrate a cited claim")
                break
    return findings


# --------------------------------------------------------------- podcast gate


def gate_podcast(root: Path, rep: Report) -> None:
    path = root / "build" / "podcast.script.json"
    if not path.is_file():
        rep.gate("podcast", [f"E-PODCAST-MISSING  {path}  no script to verify"])
        return
    script = json.loads(path.read_text(encoding="utf-8"))
    findings = check(script, "podcast", "build/podcast.script.json")
    claims = {c["id"]: c for c in load_claims(root)}
    speakers = {s["name"] for s in script.get("speakers", [])}
    for line in script.get("lines", []):
        tag = f"line {line.get('n')}"
        if line.get("speaker") not in speakers:
            findings.append(f"E-POD-SPEAKER  {tag}  '{line.get('speaker')}' is not a declared speaker")
        if line.get("kind") == "factual" and not line.get("claims"):
            findings.append(f"E-POD-UNCITED  {tag}  a factual line needs at least one claim id")
        for cid in line.get("claims", []):
            c = claims.get(cid)
            if c is None:
                findings.append(f"E-POD-CLAIM-UNKNOWN  {tag}  {cid} is not in the ledger")
            elif c["status"] != "active":
                findings.append(f"E-POD-CLAIM-STALE  {tag}  {cid} is {c['status']}")
    rep.gate("podcast", findings, f"{len(script.get('lines', []))} lines, citation track intact")


# ------------------------------------------------------------------ licenses/lint


def gate_licenses(root: Path, rep: Report, html_path: Path | None) -> None:
    from .licenses import check_licenses

    findings, note = check_licenses(root, html_path)
    rep.gate("licenses", findings, note)


def gate_lint(root: Path, rep: Report, html_path: Path) -> None:
    from .lint.rules import run as lint_run

    waivers = load(root).get("lint_waivers", {})
    findings, waived, unresolved = lint_run(
        Path(html_path).read_text(encoding="utf-8"), str(html_path), waivers)
    out = [f"{f.rule_id}  {f.file}:{f.line}  {f.detail}" for f in findings]
    rep.gate("lint", out, f"0 errors, {len(waived)} waived, {unresolved} unresolved")


# ---------------------------------------------------------------------- driver


def verify(root: Path, html: str | None = None, artifact: str | None = None,
           podcast: bool = False, as_json: bool = False) -> int:
    root = Path(root)
    rep = Report()
    gate_schemas(root, rep)
    gate_normalizer(root, rep)
    gate_quotes(root, rep)
    gate_confidence(root, rep)
    gate_tiers(root, rep)
    gate_volatility(root, rep)
    gate_clusters(root, rep)
    gate_plan(root, rep)

    html_path: Path | None = None
    plan = load_plan(root)
    if html:
        html_path = Path(html)
    elif artifact:
        html_path = root / "build" / f"{artifact}.html"
    elif plan and plan.get("type") and plan["type"] != "podcast":
        # Expected, not merely looked for. An absent artifact is a finding, because every
        # claim-to-DOM gate, the licence check, and all 28 lint rules live behind this branch.
        html_path = root / "build" / f"{plan['type']}.html"

    if html_path is not None:
        if not html_path.is_file():
            rep.gate("html", [f"E-HTML-MISSING  {html_path}  no such artifact; the claim-to-DOM, "
                              f"licence, and lint gates cannot run against a page that is not "
                              f"there"])
            gate_licenses(root, rep, None)
        else:
            gate_html(root, rep, html_path)
            gate_licenses(root, rep, html_path)
            gate_lint(root, rep, html_path)
    else:
        why = "plan.type=podcast" if plan else "no plan.json yet"
        rep.gate("html", [], f"no artifact expected ({why})")
        gate_licenses(root, rep, None)

    if podcast or (plan or {}).get("type") == "podcast":
        gate_podcast(root, rep)

    if as_json:
        print(json.dumps(rep.as_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"sb verify  {root}")
        rep.print()

    m = load(root)
    if rep.errors:
        # "Not composed yet" is not a failed revision. It still fails the gate loudly, but it
        # must not walk a workspace toward BLOCKED for the crime of checking early.
        if all(f.startswith("E-HTML-MISSING") for f in rep.errors):
            for f in rep.errors:
                print(f, file=sys.stderr)
            return EXIT_GATE
        m["revise_count"] = min(3, m.get("revise_count", 0) + 1)
        m["state"] = "BLOCKED" if m["revise_count"] >= 3 else "REVISE"
        m["history"].append({"state": m["state"], "at": now(),
                             "note": f"verify failed with {len(rep.errors)} finding(s)"})
        save(root, m)
        if m["revise_count"] >= 3:
            print("\n" + _ESCALATE, file=sys.stderr)
        for f in rep.errors:
            print(f, file=sys.stderr)
        return EXIT_GATE

    m["revise_count"] = 0
    m["state"] = "VERIFY"
    save(root, m)
    return EXIT_OK


_ESCALATE = (
    "ESCALATE: three verify loops have failed. Stop and report to the user which claims and "
    "error codes are blocking. Do not loosen a claim to make a gate pass.\n"
    "Once the user has decided what changes, clear the block with:\n"
    "  sb unblock --reason \"<what the user decided>\""
)
