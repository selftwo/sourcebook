"""`sb package` — checksums, provenance, and the private/public split.

The tension is real: the ledger must be verifiable, and the ledger must not republish a
source. `--public` resolves it by replacing over-budget quotes with their hashes. Anyone
holding the same source can still verify every citation byte-for-byte. Nobody gets a free
copy of the source.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from . import EXIT_GATE, EXIT_OK, __version__
from .ids import CHUNKER_VERSION, INDEXER_VERSION, NORMALIZER_VERSION, sha256_file, sha256_text
from .ledger import (MAX_QUOTE_CHARS, MAX_QUOTE_CHARS_PER_SOURCE, MAX_QUOTE_WORDS,
                     MAX_QUOTES_PER_SOURCE, load_claims, render_json)
from .manifest import advance, load, now, sources, write_json


def _redact(root: Path) -> tuple[list[dict], int]:
    """Keep quotes inside the budget verbatim; replace the rest with a verifiable hash."""
    claims = json.loads(render_json(root))["ledger"]
    used_n: dict[str, int] = {}
    used_c: dict[str, int] = {}
    redactions = 0
    for c in claims:
        for e in c.get("evidence", []):
            q = e.get("quote") or ""
            sid = e["source_id"]
            over_single = len(q) > MAX_QUOTE_CHARS or len(q.split()) > MAX_QUOTE_WORDS
            over_source = (used_n.get(sid, 0) >= MAX_QUOTES_PER_SOURCE
                           or used_c.get(sid, 0) + len(q) > MAX_QUOTE_CHARS_PER_SOURCE)
            if q and not over_single and not over_source:
                used_n[sid] = used_n.get(sid, 0) + 1
                used_c[sid] = used_c.get(sid, 0) + len(q)
                continue
            e["quote_sha256"] = sha256_text(q)
            e["length"] = len(q)
            e["redacted"] = True
            e.pop("quote", None)
            redactions += 1
    return claims, redactions


def provenance(root: Path, gate: dict | None = None) -> dict:
    return {
        "schema_version": 1,
        "generated_at": now(),
        "sb_version": __version__,
        "question": load(root).get("question", ""),
        "tool_versions": {
            "normalizer": NORMALIZER_VERSION,
            "chunker": CHUNKER_VERSION,
            "indexer": INDEXER_VERSION,
        },
        "sources": [
            {k: s.get(k) for k in ("id", "kind", "locator", "canonical_locator", "title",
                                   "publisher", "tier", "tier_reason", "published_at",
                                   "retrieved_at", "raw_sha256", "normalized_sha256",
                                   "normalizer_version")}
            for s in sources(root)
        ],
        "claims": len(load_claims(root)),
        "gate_report": gate or {},
    }


def _gate_report(root: Path) -> dict:
    path = root / "build" / "verify.json"
    if not path.is_file():
        return {}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return report if report.get("pass") is True else {}


def package(root: Path, out: str = "dist", public: bool = False, do_verify: bool = False) -> int:
    root = Path(root)
    out_dir = Path(out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir

    if do_verify:
        return _verify_package(root, out_dir)

    build = root / "build"
    if not build.is_dir():
        print(f"E-PACKAGE  {build}  nothing built yet", file=sys.stderr)
        return EXIT_GATE

    out_dir.mkdir(parents=True, exist_ok=True)
    shipped: list[Path] = []
    for p in sorted(build.rglob("*")):
        if p.is_dir() or p.name.endswith(".tmp"):
            continue
        if public and (p.name.endswith(".src.html") or p.name == "ledger.fragment.html"):
            continue
        rel = p.relative_to(build)
        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        shipped.append(dest)
    assets = root / "assets"
    if assets.is_dir():
        for p in sorted(assets.rglob("*")):
            if p.is_file():
                dest = out_dir / "assets" / p.relative_to(assets)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dest)
                shipped.append(dest)

    claims, redactions = _redact(root) if public else (json.loads(render_json(root))["ledger"], 0)
    ledger_out = out_dir / "ledger.json"
    write_json(ledger_out, {"schema_version": 1, "visibility": "public" if public else "private",
                            "ledger": claims})
    shipped.append(ledger_out)

    prov = provenance(root, _gate_report(root))
    prov["visibility"] = "public" if public else "private"
    prov["redacted_quotes"] = redactions
    if public:
        for source in prov["sources"]:
            for key in ("locator", "canonical_locator"):
                value = source.get(key)
                if value and not value.startswith(("http://", "https://")):
                    source[key] = None
    if not public:
        for sid in [s["id"] for s in sources(root) if s.get("status") == "ready"]:
            src = root / "sources" / sid / "normalized.md"
            if src.is_file():
                dest = out_dir / "sources" / sid / "normalized.md"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                shipped.append(dest)
    prov_out = out_dir / "PROVENANCE.json"
    write_json(prov_out, prov)
    write_json(build / "PROVENANCE.json", prov)
    shipped.append(prov_out)

    sums = out_dir / "SHA256SUMS"
    lines = []
    for p in sorted(set(shipped)):
        if p == sums:
            continue
        lines.append(f"{sha256_file(p)}  {p.relative_to(out_dir).as_posix()}")
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"packaged {len(lines)} file(s) into {out_dir}"
          + (f"  ({redactions} quote(s) redacted to hashes)" if public else ""))
    advance(root, "PACKAGE", f"packaged to {out_dir}")
    return EXIT_OK


def _verify_package(root: Path, out_dir: Path) -> int:
    findings: list[str] = []
    sums = out_dir / "SHA256SUMS"
    if not sums.is_file():
        print(f"E-PKG-NOSUMS  {sums}  nothing to verify", file=sys.stderr)
        return EXIT_GATE
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, rel = line.partition("  ")
        p = out_dir / rel
        if not p.is_file():
            findings.append(f"E-PKG-MISSING  {rel}  listed in SHA256SUMS but absent")
        elif sha256_file(p) != digest:
            findings.append(f"E-PKG-CHECKSUM  {rel}  checksum does not match")

    ledger_file = out_dir / "ledger.json"
    checked = 0
    if ledger_file.is_file():
        for c in json.loads(ledger_file.read_text(encoding="utf-8")).get("ledger", []):
            for e in c.get("evidence", []):
                path = root / "sources" / e["source_id"] / "normalized.md"
                if not path.is_file():
                    findings.append(f"E-PKG-SOURCE  {c['id']}  {e['source_id']} not in the workspace")
                    continue
                text = path.read_text(encoding="utf-8")
                actual = text[e["start"]:e["end"]]
                expect = e.get("quote_sha256") or sha256_text(e.get("quote", ""))
                if sha256_text(actual) != expect:
                    findings.append(f"E-QUOTE-MISMATCH  {c['id']}  "
                                    f"{e['source_id']}[{e['start']}:{e['end']}]")
                else:
                    checked += 1
    for f in findings:
        print(f, file=sys.stderr)
    if findings:
        return EXIT_GATE
    print(f"package verified  {len(sums.read_text().splitlines())} checksum(s), "
          f"{checked} citation(s) still byte-exact against the workspace sources")
    return EXIT_OK
