"""`sb licenses` — asset provenance and attribution as a gate, not a footnote."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import unquote

from . import EXIT_GATE, EXIT_OK
from .ids import sha256_file
from .lint.html import parse
from .manifest import check

PERMITTED = {"cc0", "pd", "public domain", "cc by", "cc by 2.0", "cc by 3.0", "cc by 4.0",
             "cc by-sa", "cc by-sa 2.0", "cc by-sa 3.0", "cc by-sa 4.0", "mit",
             "apache-2.0", "ogl", "generated"}
DENIED_SUBSTR = {"nc", "nd", "unknown", "all rights reserved"}
GENERATED_LABEL = "Generated illustration"


def credits_path(root: Path) -> Path:
    return Path(root) / "assets" / "credits.json"


def load_credits(root: Path) -> dict:
    p = credits_path(root)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _denied(license_str: str) -> str | None:
    low = license_str.strip().lower()
    for bad in DENIED_SUBSTR:
        if bad == "nc" and "-nc" in low:
            return "NonCommercial"
        if bad == "nd" and "-nd" in low:
            return "NoDerivatives"
        if bad in ("unknown", "all rights reserved") and bad in low:
            return bad
    return None


def check_licenses(root: Path, html_path: Path | None) -> tuple[list[str], str]:
    root = Path(root)
    credits = load_credits(root)
    findings: list[str] = check(credits, "credits", "assets/credits.json") if credits else []

    imgs: list = []
    doc_text = ""
    if html_path is not None and Path(html_path).is_file():
        doc = parse(Path(html_path).read_text(encoding="utf-8"), str(html_path))
        imgs = doc.find_all("img")
        doc_text = doc.text()

    if not imgs and not credits:
        return findings, "images.mode=none, nothing to check"

    referenced = set()
    for img in imgs:
        src = unquote(img.attrs.get("src", ""))
        name = Path(src).name
        if not src or src.startswith("data:"):
            continue
        referenced.add(name)
        if name not in credits:
            findings.append(f"E-IMG-UNCREDITED  {name}  no assets/credits.json entry")

    for name, entry in sorted(credits.items()):
        origin = entry.get("origin")
        if origin == "sourced":
            for required in ("source", "credit", "license"):
                if not entry.get(required):
                    findings.append(f"E-IMG-FIELDS  {name}  sourced assets need '{required}'")
            lic = (entry.get("license") or "").strip()
            reason = _denied(lic)
            if reason:
                findings.append(f"E-IMG-LICENSE  {name}  license '{lic}' is not usable ({reason})")
            elif lic.lower() not in PERMITTED:
                findings.append(f"E-IMG-LICENSE  {name}  license '{lic}' is not in the permitted set")
            if lic.lower().startswith("cc by") and entry.get("credit"):
                if entry["credit"] not in doc_text:
                    findings.append(f"E-IMG-ATTRIB  {name}  CC BY requires the credit string "
                                    f"'{entry['credit']}' to be visible in the artifact")
            if "-sa" in lic.lower():
                findings.append(f"W-IMG-SHAREALIKE  {name}  the composite artifact inherits a "
                                f"share-alike obligation; prefer a non-SA alternative")
        elif origin == "generated":
            for required in ("generator", "prompt"):
                if not entry.get(required):
                    findings.append(f"E-IMG-FIELDS  {name}  generated assets need '{required}'")
            if name in referenced and GENERATED_LABEL not in doc_text:
                findings.append(f"E-IMG-UNLABELED  {name}  a generated image must render a visible "
                                f"'{GENERATED_LABEL}' label")
        else:
            findings.append(f"E-IMG-FIELDS  {name}  origin must be 'sourced' or 'generated'")

        digest = entry.get("sha256")
        asset = root / "assets" / name
        if digest and asset.is_file() and sha256_file(asset) != digest:
            findings.append(f"E-IMG-HASH  {name}  file on disk does not match the recorded sha256")

    return findings, f"{len(credits)} asset(s), {len(referenced)} referenced"


def licenses_cmd(root: Path, html: str | None) -> int:
    html_path = Path(html) if html else None
    if html_path is None:
        candidates = sorted((Path(root) / "build").glob("*.html"))
        html_path = next((c for c in candidates if c.name != "ledger.html"), None)
    findings, note = check_licenses(Path(root), html_path)
    hard = [f for f in findings if f.startswith("E-")]
    for f in findings:
        print(f, file=sys.stderr if f.startswith("E-") else sys.stdout)
    if not hard:
        print(f"licenses ok  {note}")
    return EXIT_GATE if hard else EXIT_OK
