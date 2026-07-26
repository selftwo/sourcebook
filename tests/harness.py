"""Shared test scaffolding.

`sb()` shells out to scripts/sb.py rather than importing it, so every case exercises the
real exit codes the whole design rests on. No case touches the network.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SB = [sys.executable, str(ROOT / "scripts" / "sb.py")]
CORPUS = ROOT / "tests" / "fixtures" / "corpus"
HTML_FIXTURES = ROOT / "tests" / "fixtures" / "html"

TIERS = {
    "operator-status.md": ("A", "the operator's own page, primary for its own live status"),
    "trade-report.md": ("B", "bylined dated trade reporting"),
    "forum-thread.md": ("C", "pattern evidence about what travellers hit"),
}


def sb(workdir: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(SB + list(args), cwd=str(workdir), text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode, r.stdout


@contextmanager
def tempdir():
    d = Path(tempfile.mkdtemp(prefix="sb-test-"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def init(d: Path, question: str = "Does the fixture pipeline work?") -> None:
    rc, out = sb(d, "init", "--question", question)
    assert rc == 0, out


def add_corpus(d: Path, names: list[str] | None = None) -> None:
    (d / "input").mkdir(exist_ok=True)
    for name in names or sorted(TIERS):
        shutil.copy2(CORPUS / name, d / "input" / name)
        tier, reason = TIERS[name]
        rc, out = sb(d, "add", f"input/{name}", "--tier", tier, "--reason", reason,
                     "--title", name.replace(".md", "").replace("-", " "),
                     "--publisher", "Fixture Corpus")
        assert rc == 0, out


def pipeline(d: Path) -> None:
    for cmd in (["extract"], ["chunk"], ["index"]):
        rc, out = sb(d, *cmd)
        assert rc == 0, out


def bootstrap(d: Path) -> None:
    init(d)
    add_corpus(d)
    pipeline(d)


def source_ids(d: Path) -> dict[str, str]:
    """Map fixture filename -> derived source id."""
    out = {}
    for sd in sorted((d / "sources").iterdir()):
        rec = json.loads((sd / "source.json").read_text(encoding="utf-8"))
        out[Path(rec["canonical_locator"]).name] = rec["id"]
    return out


def span(d: Path, src: str, needle: str) -> tuple[int, int]:
    """Use `sb find` itself to resolve the span, which keeps the tests honest."""
    rc, out = sb(d, "find", src, needle)
    assert rc == 0, f"sb find failed for {needle!r}:\n{out}"
    m = re.search(r"(\d+)\.\.(\d+)", out)
    assert m, out
    return int(m.group(1)), int(m.group(2))


def add_claim(d: Path, claim: dict) -> str:
    path = d / "_claim.json"
    path.write_text(json.dumps(claim), encoding="utf-8")
    rc, out = sb(d, "claim", "add", "--file", str(path))
    assert rc == 0, out
    return out.strip().split()[-1]


def claims(d: Path) -> list[dict]:
    p = d / "ledger" / "claims.json"
    return json.loads(p.read_text(encoding="utf-8"))["claims"] if p.is_file() else []


def write_plan(d: Path, sections: list[dict], ptype: str = "answer") -> None:
    plan = {
        "schema_version": 1, "type": ptype,
        "title": "A fixture artifact",
        "thesis": "The fixture pipeline produces a verifiable artifact.",
        "audience": "the test runner",
        "images": {"mode": "none", "slots": []},
        "sections": sections,
    }
    (d / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")


MARK_LABEL = {"m-checked": "checked", "m-reported": "reported", "m-contested": "contested",
              "m-moving": "moving", "m-thin": "thin"}
MARK_FOR = {"verified": "m-checked", "reported": "m-reported", "contested": "m-contested",
            "inferred": "m-thin", "unsupported": "m-thin"}

SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Fixture artifact</title>
<style>
:root{{--ground:#ffffff;--ink:#16181d;--muted:#4b5261;--hairline:#d4d7de;--accent:#8a1f2e;
--checked:#1c5c3a;--reported:#7a4a10;--contested:#8a1f2e;--moving:#1f4b8f;--thin:#4b5261;
--sans:ui-sans-serif,system-ui,Helvetica,Arial,sans-serif;
--serif:"Iowan Old Style",Palatino,Georgia,serif}}
html{{background:var(--ground);color:var(--ink)}}
body{{margin:0;padding:2rem;background:var(--ground);color:var(--ink);
font-family:var(--serif);font-size:1rem;line-height:1.55}}
main{{max-width:66ch}}
h1{{font-size:1.953125rem;font-weight:600;margin:0 0 1rem}}
a{{color:var(--accent)}}
a:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
.mark{{font-family:var(--sans);font-size:0.64rem;font-weight:600;line-height:1;
border-bottom:2px solid currentColor;padding:0.18em 0 0.1em}}
.m-checked{{color:var(--checked)}}
.m-reported{{color:var(--reported)}}
.m-contested{{color:var(--contested)}}
.m-moving{{color:var(--moving)}}
.m-thin{{color:var(--thin)}}
.mark-legend{{font-family:var(--sans);font-size:0.8rem;color:var(--muted);margin:1.5rem 0}}
sup.ref{{font-family:var(--sans);font-size:0.64rem;font-weight:600;line-height:0}}
sup.ref a{{color:var(--accent);text-decoration:none}}
.ledger{{list-style:none;margin:0;padding:0}}
.ledger-entry{{border-top:1px solid var(--hairline);padding:0.75rem 0}}
.ledger-claim{{margin:0 0 0.35rem}}
.ledger-meta,.ledger-source{{font-family:var(--sans);font-size:0.8rem;color:var(--muted);margin:0}}
.ledger-quote{{display:block;color:var(--ink);font-family:var(--serif)}}
.ledger-note{{font-family:var(--sans);font-size:0.8rem;color:var(--muted)}}
.tier{{font-family:var(--sans);font-size:0.64rem;font-weight:600;color:var(--ink)}}
@media (prefers-reduced-motion: reduce){{*{{transition-duration:0.01ms !important}}}}
</style>
</head>
<body>
<main>
<h1>A fixture artifact</h1>
{body}
<div class="mark-legend"><p>checked, reported, contested, moving, thin.</p></div>
<!-- SB:LEDGER -->
<!-- /SB:LEDGER -->
<footer><p>Built with sourcebook.</p></footer>
</main>
</body>
</html>
"""


def compose(d: Path, order: list[dict], out: str = "build/answer.html",
            override_marks: dict | None = None, drop_sup: set | None = None) -> Path:
    """Render a minimal, lint-clean artifact that cites every claim in `order`."""
    override_marks = override_marks or {}
    drop_sup = drop_sup or set()
    paras = []
    for i, c in enumerate(order, 1):
        marks = override_marks.get(c["id"])
        if marks is None:
            marks = [MARK_FOR[c["confidence"]]] + (["m-moving"] if c.get("volatile") else [])
        mark_html = " ".join(f'<span class="mark {m}">{MARK_LABEL[m]}</span>' for m in marks)
        sup = "" if c["id"] in drop_sup else \
            f'<sup class="ref"><a href="#c-{c["id"]}">{i}</a></sup>'
        paras.append(f'<p data-claim="{c["id"]}">{c["text"]}{sup} {mark_html}</p>')
    path = d / out
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SHELL.format(body="\n".join(paras)), encoding="utf-8")
    return path


def render_and_inject(d: Path, artifact: str = "build/answer.html") -> None:
    rc, out = sb(d, "ledger", "--html", "--out", "build/ledger.html")
    assert rc == 0, out
    rc, out = sb(d, "inject", artifact, "--ledger", "build/ledger.html")
    assert rc == 0, out


def ordered_claims(d: Path) -> list[dict]:
    rc, out = sb(d, "ledger", "--json")
    assert rc == 0, out
    return json.loads(out)["ledger"]


def seed_claims(d: Path) -> list[str]:
    """Three well-formed claims over the fixture corpus: one verified, one reported, one
    volatile number. No two share a topic_key, so nothing is flagged as a contradiction."""
    ids = source_ids(d)
    op, ff = ids["operator-status.md"], ids["forum-thread.md"]
    out = []

    q = "No other scheme is live at this time."
    s, e = span(d, op, q)
    out.append(add_claim(d, {
        "text": "Only Calder Transit and Vantis Rail are live on Northline services.",
        "topic_key": "fixture.live", "kind": "fact", "confidence": "verified",
        "evidence": [{"source_id": op, "start": s, "end": e, "quote": q}]}))

    q = "It was declined twice."
    s, e = span(d, ff, q)
    out.append(add_claim(d, {
        "text": "Travellers report Harbour cards being declined at the gangway.",
        "topic_key": "fixture.reports", "kind": "fact", "confidence": "reported",
        "evidence": [{"source_id": ff, "start": s, "end": e, "quote": q}]}))

    q = "There are 1.4 million active Meridian Cards in circulation as of 12 February 2026."
    s, e = span(d, op, q)
    out.append(add_claim(d, {
        "text": "Northline reports 1.4 million active Meridian Cards as of 12 February 2026.",
        "topic_key": "fixture.cards", "kind": "number", "confidence": "verified",
        "volatile": True, "as_of": "2026-02-12",
        "recheck": "https://example.org/northline/interoperability",
        "evidence": [{"source_id": op, "start": s, "end": e, "quote": q}]}))
    return out


def full_build(d: Path) -> list[dict]:
    """A complete, gate-passing, image-free artifact in a temp workspace."""
    bootstrap(d)
    cids = seed_claims(d)
    write_plan(d, [{"id": "answer", "heading": "The short answer",
                    "intent": "state the finding", "claim_ids": cids}])
    order = ordered_claims(d)
    compose(d, order)
    render_and_inject(d)
    return order
