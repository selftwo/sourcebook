"""Claims, ordinals, byte-exact evidence checking, and the rendered citation apparatus.

The ledger is never hand-written. `sb ledger --html` reads claims.json and emits the
`<ol class="ledger">`; `sb inject` puts it in the artifact. Drift between prose and ledger
is therefore impossible rather than merely discouraged.
"""

from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

from . import EXIT_GATE, EXIT_OK, EXIT_USAGE
from .ids import claim_id, sha256_text
from .manifest import advance, check, write_json

# Quote budget (SPEC section 12.2). Enforced when rendering and again when verifying.
MAX_QUOTE_WORDS = 25
MAX_QUOTE_CHARS = 200
MAX_QUOTES_PER_SOURCE = 3
MAX_QUOTE_CHARS_PER_SOURCE = 500

MARK_FOR = {
    "verified": "m-checked",
    "reported": "m-reported",
    "contested": "m-contested",
    "inferred": "m-thin",
    "unsupported": "m-thin",
}
MARK_LABEL = {
    "m-checked": "checked", "m-reported": "reported", "m-contested": "contested",
    "m-moving": "moving", "m-thin": "thin",
}

CLAIM_DEFAULTS = {
    "volatile": False, "as_of": None, "recheck": None, "contradicts": [],
    "status": "active", "superseded_by": None, "notes": "",
}


def is_http_url(value: str | None) -> bool:
    """The only schemes a rendered artifact ever links to.

    `format: uri` accepts `javascript:` and `data:text/html` just as happily as `https:`, and
    the artifact is built to be shared and opened. Agent-authored URLs get an allowlist.
    """
    return isinstance(value, str) and value.lower().startswith(("http://", "https://"))


def claims_path(root: Path) -> Path:
    return Path(root) / "ledger" / "claims.json"


def adjudications_path(root: Path) -> Path:
    return Path(root) / "ledger" / "adjudications.json"


def load_claims(root: Path) -> list[dict]:
    p = claims_path(root)
    if not p.is_file():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("claims", [])


def save_claims(root: Path, claims: list[dict]) -> None:
    write_json(claims_path(root), {"schema_version": 1,
                                   "claims": sorted(claims, key=lambda c: c["id"])})


def load_adjudications(root: Path) -> list[dict]:
    p = adjudications_path(root)
    if not p.is_file():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("adjudications", [])


def save_adjudications(root: Path, adjs: list[dict]) -> None:
    write_json(adjudications_path(root),
               {"schema_version": 1, "adjudications": sorted(adjs, key=lambda a: a["cluster_id"])})


def load_plan(root: Path) -> dict | None:
    p = Path(root) / "plan.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def normalize_claim(obj: dict) -> dict:
    c = dict(CLAIM_DEFAULTS)
    c.update({k: v for k, v in obj.items() if k != "id"})
    c["id"] = claim_id(c["text"])
    for e in c.get("evidence", []):
        e.setdefault("quote", "")
    return c


def add_claim(root: Path, obj: dict) -> tuple[int, str]:
    """Content-addressed and idempotent. Editing the text mints a new claim id."""
    if "text" not in obj:
        return EXIT_USAGE, "E-CLAIM  (none)  a claim needs a `text` field"
    claim = normalize_claim(obj)
    errs = check({"schema_version": 1, "claims": [claim]}, "claim", "claim")
    if errs:
        return EXIT_USAGE, "\n".join(errs)
    claims = [c for c in load_claims(root) if c["id"] != claim["id"]]
    claims.append(claim)
    save_claims(root, claims)
    advance(root, "GROUND", f"claim {claim['id']}")
    return EXIT_OK, claim["id"]


def set_claim(root: Path, cid: str, **fields) -> tuple[int, str]:
    claims = load_claims(root)
    for c in claims:
        if c["id"] == cid:
            for k, v in fields.items():
                if v is not None:
                    c[k] = v
            save_claims(root, claims)
            return EXIT_OK, f"updated {cid}"
    return EXIT_USAGE, f"E-CLAIM-UNKNOWN  {cid}  no such claim"


# ------------------------------------------------------------------- verification


def verify_evidence(root: Path, claim: dict) -> list[str]:
    """The most important four lines in the codebase."""
    out: list[str] = []
    for e in claim.get("evidence", []):
        path = Path(root) / "sources" / e["source_id"] / "normalized.md"
        if not path.is_file():
            out.append(f"E-QUOTE-MISSING-SOURCE  {claim['id']}  {e['source_id']} has no normalized.md")
            continue
        text = path.read_text(encoding="utf-8")
        if not (0 <= e["start"] < e["end"] <= len(text)):
            out.append(f"E-QUOTE-RANGE  {claim['id']}  {e['source_id']}[{e['start']}:{e['end']}] "
                       f"outside 0..{len(text)}")
            continue
        actual = text[e["start"]:e["end"]]
        if e.get("redacted") or ("quote" not in e and "quote_sha256" in e):
            if sha256_text(actual) != e.get("quote_sha256", ""):
                out.append(f"E-QUOTE-MISMATCH  {claim['id']}  "
                           f"{e['source_id']}[{e['start']}:{e['end']}] hash does not match")
            continue
        if actual != e.get("quote", ""):
            out.append(f"E-QUOTE-MISMATCH  {claim['id']}  "
                       f"{e['source_id']}[{e['start']}:{e['end']}] is not the recorded quote")
    return out


# ----------------------------------------------------------------------- ordinals


def is_citable(claim: dict) -> bool:
    """An inferred claim is recorded in the ledger but never carries an ordinal, because it
    never carries a citation marker. That is what `thin` promises."""
    return claim["status"] == "active" and claim["confidence"] != "inferred"


def resolve_ordinals(root: Path) -> dict[str, int]:
    """First appearance in plan.json section order, then claim id. Stable across renders."""
    claims = {c["id"]: c for c in load_claims(root)}
    order: list[str] = []
    plan = load_plan(root)
    if plan:
        for section in plan.get("sections", []):
            for cid in section.get("claim_ids", []):
                if cid in claims and cid not in order and is_citable(claims[cid]):
                    order.append(cid)
    for cid in sorted(claims):
        if cid not in order and is_citable(claims[cid]):
            order.append(cid)
    return {cid: i + 1 for i, cid in enumerate(order)}


# ------------------------------------------------------------------------ render


def marks_for(claim: dict) -> list[str]:
    marks = [MARK_FOR.get(claim["confidence"], "m-thin")]
    if claim.get("volatile"):
        marks.append("m-moving")
    return marks


def _source_index(root: Path) -> dict[str, dict]:
    from .manifest import sources

    return {s["id"]: s for s in sources(root)}


def _budgeted_quotes(root: Path, ordered: list[dict]) -> dict[tuple[str, int, int], str | None]:
    """Decide, deterministically, which quotes a shipped artifact may print verbatim."""
    used_count: dict[str, int] = {}
    used_chars: dict[str, int] = {}
    decision: dict[tuple[str, int, int], str | None] = {}
    for claim in ordered:
        for e in claim.get("evidence", []):
            key = (e["source_id"], e["start"], e["end"])
            if key in decision:
                continue
            q = e.get("quote") or ""
            sid = e["source_id"]
            over_single = len(q) > MAX_QUOTE_CHARS or len(q.split()) > MAX_QUOTE_WORDS
            over_source = (used_count.get(sid, 0) >= MAX_QUOTES_PER_SOURCE
                           or used_chars.get(sid, 0) + len(q) > MAX_QUOTE_CHARS_PER_SOURCE)
            if not q or over_single or over_source or e.get("redacted"):
                decision[key] = None
            else:
                decision[key] = q
                used_count[sid] = used_count.get(sid, 0) + 1
                used_chars[sid] = used_chars.get(sid, 0) + len(q)
    return decision


def render_html(root: Path) -> str:
    claims = {c["id"]: c for c in load_claims(root)}
    ordinals = resolve_ordinals(root)
    srcs = _source_index(root)
    ordered = [claims[cid] for cid in sorted(ordinals, key=lambda c: ordinals[c])]
    inferred = sorted((c for c in claims.values()
                       if c["status"] == "active" and c["confidence"] == "inferred"),
                      key=lambda c: c["id"])
    budget = _budgeted_quotes(root, ordered)

    lines = ['<ol class="ledger">']
    for c in ordered:
        n = ordinals[c["id"]]
        lines.append(f'  <li class="ledger-entry" id="c-{c["id"]}" value="{n}">')
        lines.append(f'    <p class="ledger-claim">{escape(c["text"])}</p>')
        badges = " ".join(
            f'<span class="mark {m}">{MARK_LABEL[m]}</span>' for m in marks_for(c)
        )
        lines.append(f'    <p class="ledger-meta">{badges}')
        if c.get("as_of"):
            lines.append(f'      <span class="as-of">as of {escape(c["as_of"])}</span>')
        if is_http_url(c.get("recheck")):
            lines.append(f'      <a class="recheck" href="{escape(c["recheck"], quote=True)}"'
                         f' rel="nofollow noopener">recheck</a>')
        elif c.get("recheck"):
            # Never rendered as a link. `sb verify` reports it as E-RECHECK-SCHEME.
            lines.append(f'      <span class="recheck">recheck URL withheld; '
                         f'not an http(s) address: {escape(c["recheck"])}</span>')
        lines.append("    </p>")
        if not c.get("evidence"):
            lines.append('    <p class="ledger-source"><span class="tier tier-none">no source</span> '
                         "author's inference; weigh it as opinion.</p>")
        for e in c.get("evidence", []):
            s = srcs.get(e["source_id"], {})
            title = escape(s.get("title") or e["source_id"])
            pub = escape(s.get("publisher") or "")
            tier = escape(s.get("tier") or "?")
            loc = s.get("locator") or ""
            label = f"{title}{' &middot; ' + pub if pub else ''}"
            if loc.startswith("http"):
                label = f'<a href="{escape(loc, quote=True)}" rel="nofollow noopener">{label}</a>'
            lines.append(f'    <p class="ledger-source"><span class="tier tier-{tier}">tier {tier}</span> '
                         f"{label}")
            q = budget.get((e["source_id"], e["start"], e["end"]))
            if q:
                lines.append(f'      <q class="ledger-quote">{escape(q)}</q>')
            else:
                lines.append('      <span class="ledger-span">quote withheld under the quote budget; '
                             f'chars {e["start"]}&ndash;{e["end"]} of the source</span>')
            lines.append("    </p>")
        lines.append("  </li>")
    lines.append("</ol>")

    if inferred:
        lines.append('<ul class="ledger ledger-thin">')
        lines.append('  <li class="ledger-note">The author\'s inferences, recorded here and '
                     "cited nowhere, because there is no source to cite.</li>")
        for c in inferred:
            lines.append(f'  <li class="ledger-entry" id="c-{c["id"]}">')
            lines.append(f'    <p class="ledger-claim">{escape(c["text"])}</p>')
            lines.append('    <p class="ledger-meta"><span class="mark m-thin">thin</span></p>')
            lines.append("  </li>")
        lines.append("</ul>")
    return "\n".join(lines) + "\n"


def render_md(root: Path) -> str:
    claims = {c["id"]: c for c in load_claims(root)}
    ordinals = resolve_ordinals(root)
    srcs = _source_index(root)
    ordered = [claims[cid] for cid in sorted(ordinals, key=lambda c: ordinals[c])]
    budget = _budgeted_quotes(root, ordered)
    out = ["# Ledger", ""]
    for c in ordered:
        marks = " ".join(MARK_LABEL[m] for m in marks_for(c))
        out.append(f"{ordinals[c['id']]}. **{c['text']}**  ")
        meta = [f"`{marks}`"]
        if c.get("as_of"):
            meta.append(f"as of {c['as_of']}")
        if is_http_url(c.get("recheck")):
            meta.append(f"[recheck]({c['recheck']})")
        elif c.get("recheck"):
            meta.append(f"recheck URL withheld; not an http(s) address: {c['recheck']}")
        out.append("   " + " · ".join(meta))
        for e in c.get("evidence", []):
            s = srcs.get(e["source_id"], {})
            q = budget.get((e["source_id"], e["start"], e["end"]))
            snippet = f'"{q}"' if q else f"chars {e['start']}-{e['end']}"
            out.append(f"   - tier {s.get('tier','?')} · {s.get('title') or e['source_id']} · {snippet}")
        if not c.get("evidence"):
            out.append("   - no source; author's inference")
        out.append("")
    return "\n".join(out)


def render_sources(root: Path) -> str:
    claims = load_claims(root)
    srcs = _source_index(root)
    by_source: dict[str, list[dict]] = {}
    for c in claims:
        for e in c.get("evidence", []):
            by_source.setdefault(e["source_id"], []).append(c)
    out = ["# Sources", ""]
    for sid in sorted(srcs, key=lambda s: (srcs[s].get("tier", "Z"), srcs[s].get("title") or s)):
        s = srcs[sid]
        used = {c["id"] for c in by_source.get(sid, [])}
        out.append(f"- **[{s.get('tier','?')}]** {s.get('title') or sid}")
        out.append(f"  - `{sid}` · {s.get('locator','')}")
        out.append(f"  - why this tier: {s.get('tier_reason','(none recorded)')}")
        out.append(f"  - supports {len(used)} claim(s) · retrieved {s.get('retrieved_at','?')}")
    return "\n".join(out) + "\n"


def render_json(root: Path) -> str:
    claims = {c["id"]: c for c in load_claims(root)}
    ordinals = resolve_ordinals(root)
    resolved = []
    for cid, n in sorted(ordinals.items(), key=lambda kv: kv[1]):
        c = dict(claims[cid])
        c["ordinal"] = n
        c["marks"] = marks_for(c)
        resolved.append(c)
    return json.dumps({"schema_version": 1, "ledger": resolved}, indent=2, ensure_ascii=False) + "\n"


def ledger_cmd(root: Path, fmt: str, out_path: str | None) -> int:
    body = {"html": render_html, "md": render_md, "json": render_json,
            "sources": render_sources}[fmt](root)
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(body, encoding="utf-8")
        print(f"wrote {out_path}  ({len(body)} bytes)")
    else:
        sys.stdout.write(body)
    return EXIT_OK


# ------------------------------------------------------------------------ inject

LEDGER_OPEN = "<!-- SB:LEDGER -->"
LEDGER_CLOSE = "<!-- /SB:LEDGER -->"


def inject(html_path: Path, ledger_path: Path) -> int:
    html_path, ledger_path = Path(html_path), Path(ledger_path)
    if not html_path.is_file():
        print(f"E-INJECT  {html_path}  no such file", file=sys.stderr)
        return EXIT_USAGE
    if not ledger_path.is_file():
        print(f"E-INJECT  {ledger_path}  no rendered ledger; run `sb ledger --html`", file=sys.stderr)
        return EXIT_USAGE
    doc = html_path.read_text(encoding="utf-8")
    if LEDGER_OPEN not in doc:
        print(f"E-INJECT  {html_path}  missing the {LEDGER_OPEN} marker; "
              "add it where the ledger belongs rather than letting the script guess",
              file=sys.stderr)
        return EXIT_GATE
    ledger = ledger_path.read_text(encoding="utf-8").rstrip("\n")
    start = doc.index(LEDGER_OPEN) + len(LEDGER_OPEN)
    close = doc.find(LEDGER_CLOSE, start)
    tail = doc[close + len(LEDGER_CLOSE):] if close != -1 else doc[start:]
    html_path.write_text(doc[:start] + "\n" + ledger + "\n" + LEDGER_CLOSE + tail,
                         encoding="utf-8")
    print(f"injected {ledger_path} into {html_path}")
    return EXIT_OK
