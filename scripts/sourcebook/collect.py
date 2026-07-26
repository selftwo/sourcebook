"""`sb add` — fetch or copy a source, record provenance, never guess its authority."""

from __future__ import annotations

import ipaddress
import mimetypes
import shutil
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import EXIT_GATE, EXIT_OK, EXIT_USAGE
from .ids import canonical_locator, sha256_bytes, src_id
from .manifest import advance, load, now, save, write_json

UA = "sourcebook/0.1 (+https://github.com/sourcebook-kit/sourcebook) stdlib-urllib"
MAX_BYTES = 25 * 1024 * 1024
TIMEOUT = 20
ALLOWED_SCHEMES = ("http", "https")

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


class BlockedURL(ValueError):
    """A destination `sb add` refuses to fetch. Raised before any socket is opened."""


def _blocked_reason(addr: str) -> str | None:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return None
    # Most specific reason first: link-local and loopback are also "private".
    for flag, why in (("is_loopback", "loopback"), ("is_link_local", "link-local"),
                      ("is_multicast", "multicast"), ("is_unspecified", "unspecified"),
                      ("is_reserved", "reserved"), ("is_private", "private")):
        if getattr(ip, flag, False):
            return why
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        return _blocked_reason(str(mapped))
    return None


def assert_fetchable(url: str) -> None:
    """Refuse a destination the workspace has no business reaching.

    `sb add http://169.254.169.254/…` would otherwise pull cloud instance metadata into the
    ledger as a citable source. Every hostname is resolved and every resolved address checked,
    so a public name that points at 127.0.0.1 is refused too. Applied to the original URL and
    again to every redirect target, because a redirect is a second destination.
    """
    parts = urllib.parse.urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise BlockedURL(f"blocked: scheme '{scheme or '(none)'}' is not http or https ({url})")
    if parts.username or parts.password:
        raise BlockedURL(f"blocked: credentials in the URL are not fetched ({url})")
    host = parts.hostname
    if not host:
        raise BlockedURL(f"blocked: no host in {url}")

    literal = _blocked_reason(host)
    if literal:
        raise BlockedURL(f"blocked: {host} is a {literal} address")
    try:
        infos = socket.getaddrinfo(host, parts.port or (443 if scheme == "https" else 80),
                                   proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise BlockedURL(f"blocked: cannot resolve {host} ({exc})") from exc
    for info in infos:
        reason = _blocked_reason(info[4][0])
        if reason:
            raise BlockedURL(f"blocked: {host} resolves to {info[4][0]}, a {reason} address")


class _GuardedRedirects(urllib.request.HTTPRedirectHandler):
    """A redirect is a destination the caller never named. Check it like the first one."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        assert_fetchable(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener() -> urllib.request.OpenerDirector:
    """Only the handlers http(s) needs. No FileHandler, no FTPHandler, no DataHandler."""
    op = urllib.request.OpenerDirector()
    handlers = [urllib.request.ProxyHandler(), urllib.request.HTTPHandler(),
                _GuardedRedirects(), urllib.request.HTTPErrorProcessor(),
                urllib.request.HTTPDefaultErrorHandler()]
    if hasattr(urllib.request, "HTTPSHandler"):
        handlers.append(urllib.request.HTTPSHandler())
    for handler in handlers:
        op.add_handler(handler)
    op.addheaders = [("User-Agent", UA)]
    return op


def _fetch(url: str) -> tuple[bytes, str, str]:
    """Returns (body, media_type, charset). Raises on failure."""
    assert_fetchable(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with _opener().open(req, timeout=TIMEOUT) as resp:
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
            "charset": None,
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
                        # Recorded, and actually used: `sb extract` decodes with it.
                        rec["charset"] = charset
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
