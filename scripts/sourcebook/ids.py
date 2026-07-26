"""Deterministic identifier derivation and hashing.

Every id in a sourcebook workspace is a pure function of content or locator, so a
re-run over the same inputs produces the same workspace, byte for byte.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit, urlencode

# Versioned algorithms. Changing one bumps the constant; verify reports drift.
NORMALIZER_VERSION = 1
CHUNKER_VERSION = 1
INDEXER_VERSION = 1

_TRACKING = re.compile(r"^(utm_.*|gclid|fbclid|mc_[ce]id|ref|si|igshid)$", re.I)
_WS = re.compile(r"\s+")


def norm_ws(s: str) -> str:
    """Collapse every whitespace run to a single space and strip the ends."""
    return _WS.sub(" ", s).strip()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical_url(url: str) -> str:
    """Lowercase scheme+host, drop default port, fragment, and tracking params.

    Path case is preserved. Remaining query params are sorted by key then value.
    A lone trailing slash is stripped only when the path is exactly "/".
    """
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        host = f"{host}:{port}"
    if parts.username:
        cred = parts.username + (f":{parts.password}" if parts.password else "")
        host = f"{cred}@{host}"
    path = parts.path
    if path == "/":
        path = ""
    query = sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _TRACKING.match(k)
    )
    return urlunsplit((scheme, host, path, urlencode(query), ""))


def canonical_locator(kind: str, locator: str, root: Path) -> str:
    """URL: canonicalized URL. File: POSIX path relative to the workspace when possible."""
    if kind == "url":
        return canonical_url(locator)
    if kind == "paste":
        return "paste:" + sha256_text(norm_ws(locator))[:16]
    p = Path(locator)
    try:
        rel = p.resolve().relative_to(Path(root).resolve())
        return rel.as_posix()
    except (ValueError, OSError):
        return p.as_posix()


def src_id(canonical: str, raw_sha256: str) -> str:
    return "src_" + sha256_text(f"{canonical}\n{raw_sha256}")[:12]


def chunk_id(src: str, ordinal: int) -> str:
    return f"{src}#c{ordinal:04d}"


def claim_id(text: str) -> str:
    return "clm_" + sha256_text(norm_ws(text).lower())[:12]


def cluster_id(topic_key: str) -> str:
    return "cls_" + sha256_text(topic_key)[:12]


def normalize(text: str) -> str:
    """The canonical text transform. SPEC section 3. normalizer_version = 1.

    Never re-wraps, re-orders, strips Markdown, or injects anything.
    """
    s = unicodedata.normalize("NFC", text)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(line.rstrip() for line in s.split("\n"))
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = s.rstrip("\n") + "\n"
    return s


def decode_bytes(b: bytes, charset: str | None = None) -> str:
    for enc in [charset, "utf-8"]:
        if not enc:
            continue
        try:
            return b.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return b.decode("utf-8", errors="replace")


_BOMS = [(b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe\x00\x00", "utf-32-le"),
         (b"\x00\x00\xfe\xff", "utf-32-be"), (b"\xff\xfe", "utf-16-le"),
         (b"\xfe\xff", "utf-16-be")]
_META_CHARSET = re.compile(rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9_.:-]+)""", re.I)


def sniff_charset(b: bytes) -> str | None:
    """The encoding the bytes declare about themselves: a BOM, then a `<meta charset>`.

    Only a declaration is honoured; nothing here guesses. A Windows-1252 page that says so
    decodes as Windows-1252 instead of becoming U+FFFD-laced canonical text.
    """
    for bom, enc in _BOMS:
        if b.startswith(bom):
            return enc
    m = _META_CHARSET.search(b[:4096])
    if m:
        try:
            return m.group(1).decode("ascii").strip().lower()
        except UnicodeDecodeError:
            return None
    return None
