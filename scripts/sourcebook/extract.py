"""`sb extract` — turn raw captures into the one canonical text per source.

`normalized.md` is written once and never edited. Every citation is a byte span into it.
When the script cannot parse the bytes it says so (`needs_extraction`) and hands the file
to the agent. It never produces a lossy guess and calls it canonical.
"""

from __future__ import annotations

import json
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from . import EXIT_GATE, EXIT_OK
from .ids import NORMALIZER_VERSION, decode_bytes, normalize, sha256_text
from .manifest import advance, write_json

try:  # optional; its absence degrades, never fails
    import pypdf  # type: ignore
except ImportError:  # pragma: no cover - environment dependent
    pypdf = None

EXTRACTOR_VERSION = 1

DROP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "aside", "form",
             "header", "template", "iframe", "button", "select"}
DROP_ATTR = re.compile(r"(nav|menu|sidebar|cookie|banner|promo|share|related|comment|subscribe|newsletter|breadcrumb)", re.I)
BLOCK_TAGS = {"p", "div", "section", "article", "main", "ul", "ol", "li", "blockquote",
              "pre", "table", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "figure",
              "figcaption", "dl", "dt", "dd", "hr"}


class _Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text")

    def __init__(self, tag: str, attrs: dict | None = None, parent=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.children: list = []
        self.parent = parent
        self.text = ""

    def text_len(self) -> int:
        n = len(self.text.strip())
        for c in self.children:
            n += c.text_len() if isinstance(c, _Node) else len(c.strip())
        return n


VOID = {"br", "hr", "img", "meta", "link", "input", "source", "area", "base", "col", "embed", "param", "track", "wbr"}


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("#root")
        self.cur = self.root
        self.meta: dict[str, str] = {}
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key and a.get("content"):
                self.meta.setdefault(key, a["content"])
            return
        if tag == "time" and a.get("datetime"):
            self.meta.setdefault("time:datetime", a["datetime"])
        if tag in VOID:
            self.cur.children.append(_Node(tag, a, self.cur))
            return
        node = _Node(tag, a, self.cur)
        self.cur.children.append(node)
        self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(_Node(tag, {k.lower(): (v or "") for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        node = self.cur
        while node is not self.root:
            if node.tag == tag:
                self.cur = node.parent or self.root
                return
            node = node.parent or self.root

    def handle_data(self, data):
        if self._in_title:
            self.meta.setdefault("#title", (self.meta.get("#title", "") + data))
            return
        self.cur.children.append(data)


def _keep(node: _Node) -> bool:
    if node.tag in DROP_TAGS:
        return False
    ident = f"{node.attrs.get('class', '')} {node.attrs.get('id', '')}"
    if ident.strip() and DROP_ATTR.search(ident):
        return False
    return True


def _inline_text(node, base_url: str) -> str:
    if isinstance(node, str):
        return node
    if node.tag == "br":
        return "\n"
    if node.tag == "img":
        alt = node.attrs.get("alt", "").strip()
        return f"![{alt}]({urljoin(base_url, node.attrs.get('src', ''))})" if alt else ""
    if not _keep(node):
        return ""
    inner = "".join(_inline_text(c, base_url) for c in node.children)
    if node.tag == "a":
        href = node.attrs.get("href", "").strip()
        label = re.sub(r"\s+", " ", inner).strip()
        if href and label and not href.startswith("#"):
            return f"[{label}]({urljoin(base_url, href)})"
        return inner
    if node.tag in ("strong", "b"):
        return f"**{inner.strip()}**" if inner.strip() else ""
    if node.tag in ("em", "i"):
        return f"*{inner.strip()}*" if inner.strip() else ""
    if node.tag == "code":
        return f"`{inner.strip()}`" if inner.strip() else ""
    return inner


def _clean(s: str) -> str:
    return re.sub(r"[ \t]+", " ", s.replace("\xa0", " ")).strip()


def _render(node: _Node, out: list[str], base_url: str, depth: int = 0) -> None:
    if isinstance(node, str):
        t = _clean(node)
        if t:
            out.append(t)
        return
    if not _keep(node):
        return
    tag = node.tag
    if re.fullmatch(r"h[1-6]", tag):
        t = _clean(_inline_text(node, base_url))
        if t:
            out.append("\n" + "#" * int(tag[1]) + " " + t + "\n")
        return
    if tag == "p":
        t = _clean(_inline_text(node, base_url))
        if t:
            out.append(t + "\n")
        return
    if tag == "blockquote":
        inner: list[str] = []
        for c in node.children:
            _render(c, inner, base_url, depth)
        body = "\n".join(x for x in inner if x.strip())
        if body.strip():
            out.append("\n".join("> " + ln for ln in body.split("\n")) + "\n")
        return
    if tag == "pre":
        raw = "".join(_inline_text(c, base_url) for c in node.children)
        if raw.strip():
            out.append("```\n" + raw.strip("\n") + "\n```\n")
        return
    if tag in ("ul", "ol"):
        i = 0
        for c in node.children:
            if isinstance(c, _Node) and c.tag == "li":
                i += 1
                marker = f"{i}. " if tag == "ol" else "- "
                t = _clean(_inline_text(c, base_url))
                sub: list[str] = []
                for gc in c.children:
                    if isinstance(gc, _Node) and gc.tag in ("ul", "ol"):
                        _render(gc, sub, base_url, depth + 1)
                if t:
                    out.append(marker + t)
                for line in sub:
                    out.extend("  " + ln for ln in line.split("\n") if ln.strip())
        out.append("")
        return
    if tag == "table":
        rows: list[list[str]] = []
        for tr in _descend(node, "tr"):
            cells = [_clean(_inline_text(td, base_url)) for td in tr.children
                     if isinstance(td, _Node) and td.tag in ("td", "th")]
            if cells:
                rows.append(cells)
        if rows:
            width = max(len(r) for r in rows)
            rows = [r + [""] * (width - len(r)) for r in rows]
            out.append("| " + " | ".join(rows[0]) + " |")
            out.append("|" + "|".join([" --- "] * width) + "|")
            for r in rows[1:]:
                out.append("| " + " | ".join(r) + " |")
            out.append("")
        return
    if tag == "hr":
        out.append("\n---\n")
        return
    if tag in BLOCK_TAGS or tag == "#root":
        for c in node.children:
            _render(c, out, base_url, depth)
        return
    t = _clean(_inline_text(node, base_url))
    if t:
        out.append(t)


def _descend(node: _Node, tag: str):
    for c in node.children:
        if isinstance(c, _Node):
            if c.tag == tag:
                yield c
            else:
                yield from _descend(c, tag)


def _main_subtree(root: _Node) -> _Node:
    for want in ("article", "main"):
        for n in _descend(root, want):
            if n.text_len() > 200:
                return n
    for n in _descend(root, "div"):
        if n.attrs.get("role") == "main":
            return n
    best, best_len = root, 0
    for n in _descend(root, "div"):
        if not _keep(n):
            continue
        length = n.text_len()
        if length > best_len:
            best, best_len = n, length
    for n in _descend(root, "section"):
        if _keep(n) and n.text_len() > best_len:
            best, best_len = n, n.text_len()
    body = next(_descend(root, "body"), None)
    if body is not None and best_len < body.text_len() * 0.4:
        return body
    return best


def html_to_markdown(html: str, base_url: str = "") -> tuple[str, dict]:
    """A small, honest HTML reader. No BeautifulSoup, no readability heuristics beyond size."""
    tree = _Tree()
    tree.feed(html)
    tree.close()
    node = _main_subtree(tree.root)
    out: list[str] = []
    _render(node, out, base_url)
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    meta = {
        "title": _clean(unescape(tree.meta.get("#title", ""))) or None,
        "author": tree.meta.get("author") or tree.meta.get("article:author") or None,
        "published_at": (tree.meta.get("article:published_time")
                         or tree.meta.get("time:datetime")
                         or tree.meta.get("date") or None),
        "publisher": tree.meta.get("og:site_name") or None,
        "lang": tree.meta.get("og:locale") or None,
    }
    return text.strip() + "\n", meta


def pdf_to_text(path: Path) -> tuple[str | None, str]:
    if pypdf is None:
        return None, "pypdf not installed; hand this file to the agent"
    try:
        reader = pypdf.PdfReader(str(path))
        pages = [(p.extract_text() or "") for p in reader.pages]
    except Exception as exc:  # pragma: no cover - depends on the file
        return None, f"pypdf failed: {exc}"
    body = "\n\n".join(pages).strip()
    if len(body) < 40:
        return None, "pypdf produced almost no text (scanned or image-only PDF)"
    return body + "\n", "pypdf"


def _raw_path(d: Path) -> Path | None:
    for p in sorted(d.glob("raw.*")):
        return p
    return None


def extract(root: Path, force: bool = False) -> int:
    root = Path(root)
    sdir = root / "sources"
    if not sdir.is_dir():
        print("E-EXTRACT  workspace  no sources/ directory; run `sb add` first", file=sys.stderr)
        return EXIT_GATE

    findings: list[str] = []
    ready = 0
    for d in sorted(sdir.iterdir()):
        meta_path = d / "source.json"
        if not meta_path.is_file():
            continue
        rec = json.loads(meta_path.read_text(encoding="utf-8"))
        norm_path = d / "normalized.md"

        if rec["status"] == "ready" and norm_path.is_file() and not force:
            current = sha256_text(norm_path.read_text(encoding="utf-8"))
            if rec.get("normalized_sha256") and current != rec["normalized_sha256"]:
                findings.append(f"E-NORM-DRIFT  {rec['id']}  normalized.md changed after it was recorded")
            elif rec.get("normalizer_version") != NORMALIZER_VERSION:
                findings.append(
                    f"E-NORM-DRIFT  {rec['id']}  normalizer_version {rec.get('normalizer_version')} "
                    f"!= {NORMALIZER_VERSION}; offsets may have moved")
            else:
                ready += 1
            continue

        if rec["status"] == "failed":
            continue

        raw = _raw_path(d)
        if raw is None:
            rec["status"] = "pending"
            rec["extraction"]["notes"] = ["no raw capture on disk; fetch it and save as raw.<ext>"]
            write_json(meta_path, rec)
            continue

        media = rec.get("media_type") or ""
        text: str | None = None
        tool = "sb.text"
        note = ""

        if media in ("text/markdown", "text/plain", "text/x-markdown") or raw.suffix in (".md", ".txt"):
            text = decode_bytes(raw.read_bytes())
            tool = "sb.text"
        elif media in ("text/html", "application/xhtml+xml") or raw.suffix in (".html", ".htm"):
            body = decode_bytes(raw.read_bytes())
            base = rec["locator"] if rec["kind"] == "url" else ""
            text, meta = html_to_markdown(body, base)
            tool = "sb.html"
            for key in ("title", "author", "published_at", "publisher", "lang"):
                if rec.get(key) in (None, "") and meta.get(key):
                    rec[key] = meta[key]
        elif media == "application/pdf" or raw.suffix == ".pdf":
            text, note = pdf_to_text(raw)
            tool = "sb.pdf"
        else:
            note = f"no extractor for media type {media or 'unknown'}"

        if text is None or not text.strip():
            rec["status"] = "needs_extraction"
            rec["extraction"] = {"tool": tool, "version": EXTRACTOR_VERSION, "ok": False,
                                 "notes": [note or "extractor produced no text",
                                           "AGENT: read the raw file yourself and write "
                                           "sources/%s/normalized.md, then re-run `sb extract`." % rec["id"]]}
            write_json(meta_path, rec)
            print(f"needs-extraction  {rec['id']}  {note}")
            continue

        normalized = normalize(text)
        if norm_path.is_file():
            existing = norm_path.read_text(encoding="utf-8")
            if existing != normalized and rec.get("normalized_sha256") and not force:
                findings.append(
                    f"E-NORM-DRIFT  {rec['id']}  refusing to rewrite normalized.md "
                    f"(re-run with --force only if no claim cites this source)")
                continue
        norm_path.write_text(normalized, encoding="utf-8")
        rec["normalized_sha256"] = sha256_text(normalized)
        rec["normalizer_version"] = NORMALIZER_VERSION
        rec["extraction"] = {"tool": tool, "version": EXTRACTOR_VERSION, "ok": True,
                             "notes": [note] if note and note != tool else []}
        rec["status"] = "ready"
        write_json(meta_path, rec)
        ready += 1
        print(f"ready    {rec['id']}  {len(normalized)} chars  via {tool}")

    for f in findings:
        print(f, file=sys.stderr)
    if findings:
        return EXIT_GATE
    if ready == 0:
        print("E-EXTRACT  workspace  no source reached status=ready", file=sys.stderr)
        return EXIT_GATE
    advance(root, "EXTRACT", f"{ready} source(s) ready")
    return EXIT_OK
