"""`sb add` — fetch or copy a source, record provenance, never guess its authority."""

from __future__ import annotations

import mimetypes
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

from . import EXIT_GATE, EXIT_OK, EXIT_USAGE
from .ids import canonical_locator, sha256_bytes, src_id
from .manifest import advance, load, now, save, write_json

UA = "sourcebook/0.1 (+https://github.com/sourcebook-kit/sourcebook) stdlib-urllib"
MAX_BYTES = 25 * 1024 * 1024
TIMEOUT = 20

EXT_FOR = {
    "text/html": ".html",
    "application/xhtml+xml": ".html",
    "text/markdown": ".md",
    "text/plain": ".txt",
    "application/pdf": ".pdf",
    "application/json": ".json",
}


def _guess_media(path: Path, declared: str | None = None) -> str:
    if declared:
        return declared.split(";")[0].strip().lower()
    suffix = path.suffix.lower()
    if suffix in (".md", ".markdown"):
        return "text/markdown"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _fetch(url: str) -> tuple[bytes, str, str]:
    """Returns (body, media_type, charset). Raises on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = resp.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError(f"response exceeds {MAX_BYTES} bytes")
        ctype = resp.headers.get("Content-Type", "") or ""
        media = ctype.split(";")[0].strip().lower() or "application/octet-stream"
        charset = resp.headers.get_content_charset() or ""
    return body, media, charset


def _record(root: Path, rec: dict) -> Path:
    d = root / "sources" / rec["id"]
    d.mkdir(parents=True, exist_ok=True)
    write_json(d / "source.json", rec)
    return d


def add(root: Path, args) -> int:
    m = load(root)
    web_fetch = m.get("capabilities", {}).get("web_fetch", "agent")
    failures = 0
    added: list[str] = []

    locators: list[tuple[str, str]] = []  # (kind, locator)
    if args.text is not None:
        locators.append(("paste", args.text))
    if args.stdin:
        locators.append(("paste", sys.stdin.read()))
    for loc in args.locators:
        locators.append(("url" if loc.startswith(("http://", "https://")) else "file", loc))

    if not locators:
        print("usage: sb add <url|file>... --tier {A,B,C,D} --reason TEXT", file=sys.stderr)
        return EXIT_USAGE

    for kind, loc in locators:
        canonical = canonical_locator(kind, loc, root)
        rec = {
            "schema_version": 1,
            "id": "",
            "kind": kind,
            "locator": loc if kind != "paste" else canonical,
            "canonical_locator": canonical,
            "title": args.title,
            "author": args.author,
            "publisher": args.publisher,
            "published_at": args.published,
            "retrieved_at": now(),
            "tier": args.tier,
            "tier_reason": args.reason,
            "license": args.license,
            "media_type": None,
            "lang": args.lang,
            "raw_sha256": None,
            "normalized_sha256": None,
            "normalizer_version": None,
            "extraction": {"tool": None, "version": 0, "ok": False, "notes": []},
            "status": "pending",
            "error": None,
        }

        raw: bytes | None = None
        ext = ".bin"

        if kind == "paste":
            raw = loc.encode("utf-8")
            rec["media_type"] = "text/markdown"
            ext = ".md"
        elif kind == "file":
            p = Path(loc).expanduser()
            if not p.is_file():
                rec["status"] = "failed"
                rec["error"] = f"no such file: {loc}"
                rec["raw_sha256"] = ""
                rec["id"] = src_id(canonical, "")
                _record(root, rec)
                print(f"E-ADD-MISSING  {loc}  no such file", file=sys.stderr)
                failures += 1
                continue
            raw = p.read_bytes()
            rec["media_type"] = _guess_media(p)
            ext = p.suffix or EXT_FOR.get(rec["media_type"], ".bin")
        else:  # url
            if web_fetch == "none":
                rec["status"] = "failed"
                rec["error"] = "capabilities.web_fetch=none and the locator is a URL"
            elif web_fetch == "agent":
                rec["status"] = "pending"
                rec["extraction"]["notes"].append(
                    "capabilities.web_fetch=agent: save the page bytes to "
                    "sources/<id>/raw.html yourself, then run `sb extract`."
                )
                rec["media_type"] = "text/html"
                rec["raw_sha256"] = ""
                rec["id"] = src_id(canonical, "")
                d = _record(root, rec)
                print(f"pending  {rec['id']}  {loc}\n  -> write the fetched bytes to {d}/raw.html, then: sb extract")
                added.append(rec["id"])
                continue
            else:
                try:
                    raw, media, charset = _fetch(loc)
                    rec["media_type"] = media
                    ext = EXT_FOR.get(media, ".bin")
                    if charset:
                        rec["extraction"]["notes"].append(f"charset={charset}")
                except (urllib.error.URLError, ValueError, OSError) as exc:
                    rec["status"] = "failed"
                    rec["error"] = f"fetch failed: {exc}"

        if rec["status"] == "failed":
            rec["raw_sha256"] = ""
            rec["id"] = src_id(canonical, "")
            _record(root, rec)
            print(f"E-ADD-FAILED  {loc}  {rec['error']}", file=sys.stderr)
            failures += 1
            continue

        assert raw is not None
        rec["raw_sha256"] = sha256_bytes(raw)
        rec["id"] = src_id(canonical, rec["raw_sha256"])
        d = root / "sources" / rec["id"]
        existing = d / "source.json"
        if existing.is_file():
            import json as _json

            prev = _json.loads(existing.read_text(encoding="utf-8"))
            prev["retrieved_at"] = rec["retrieved_at"]
            prev["tier"] = rec["tier"]
            prev["tier_reason"] = rec["tier_reason"]
            write_json(existing, prev)
            print(f"exists   {rec['id']}  {loc}  (retrieved_at refreshed)")
            added.append(rec["id"])
            continue

        d.mkdir(parents=True, exist_ok=True)
        (d / f"raw{ext}").write_bytes(raw)
        if rec["title"] is None and kind == "file":
            rec["title"] = Path(loc).stem.replace("-", " ").replace("_", " ")
        write_json(d / "source.json", rec)
        print(f"added    {rec['id']}  tier {rec['tier']}  {loc}")
        added.append(rec["id"])

    if added:
        advance(root, "COLLECT", f"added {len(added)} source(s)")
    return EXIT_GATE if failures and not added else (EXIT_USAGE if failures else EXIT_OK)


def seed_from(root: Path, src_dir: Path) -> int:
    """`sb init --from <dir>`: copy a frozen capture into a fresh workspace."""
    src_dir = Path(src_dir)
    if not src_dir.is_dir():
        print(f"E-SEED  {src_dir}  not a directory", file=sys.stderr)
        return EXIT_USAGE
    inner = src_dir / "sources" if (src_dir / "sources").is_dir() else src_dir
    n = 0
    for d in sorted(inner.iterdir()):
        if d.is_dir() and (d / "source.json").is_file():
            shutil.copytree(d, root / "sources" / d.name, dirs_exist_ok=True)
            n += 1
    print(f"seeded   {n} source(s) from {src_dir}")
    if n:
        advance(root, "COLLECT", f"seeded from {src_dir}")
    return EXIT_OK
