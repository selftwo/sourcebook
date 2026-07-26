"""A stdlib DOM walker. Enough structure to answer questions honestly, no more."""

from __future__ import annotations

import re
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr"}
RAW_TEXT = {"script", "style"}

BLOCKISH = {"p", "div", "section", "article", "li", "td", "th", "blockquote", "figure",
            "figcaption", "aside", "header", "footer", "main", "dd", "dt",
            "h1", "h2", "h3", "h4", "h5", "h6"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "line", "text_parts")

    def __init__(self, tag, attrs=None, parent=None, line=0):
        self.tag = tag
        self.attrs: dict[str, str] = attrs or {}
        self.children: list[Node] = []
        self.parent: Node | None = parent
        self.line = line
        self.text_parts: list[str] = []

    # -- convenience ------------------------------------------------------

    @property
    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()

    def own_text(self) -> str:
        return "".join(self.text_parts)

    def text(self) -> str:
        out = list(self.text_parts)
        for c in self.children:
            out.append(c.text())
        return "".join(out)

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def find_all(self, tag: str):
        return [n for n in self.walk() if n.tag == tag]

    def ancestors(self):
        n = self.parent
        while n is not None:
            yield n
            n = n.parent

    def path(self) -> list["Node"]:
        chain = [self]
        for a in self.ancestors():
            chain.append(a)
        return list(reversed(chain))

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"<{self.tag} {self.attrs.get('class','')}>"


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.cur = self.root
        self.styles: list[tuple[str, int]] = []
        self.scripts: list[str] = []
        self._raw: str | None = None

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k.lower(): (v if v is not None else "") for k, v in attrs},
                    self.cur, self.getpos()[0])
        self.cur.children.append(node)
        if tag in RAW_TEXT:
            self._raw = tag
            self.cur = node
            return
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(
            Node(tag, {k.lower(): (v if v is not None else "") for k, v in attrs},
                 self.cur, self.getpos()[0]))

    def handle_endtag(self, tag):
        if self._raw == tag:
            self._raw = None
        node = self.cur
        while node is not self.root:
            if node.tag == tag:
                self.cur = node.parent or self.root
                return
            node = node.parent or self.root

    def handle_data(self, data):
        if self._raw == "style":
            self.styles.append((data, self.getpos()[0]))
            return
        if self._raw == "script":
            self.scripts.append(data)
            return
        self.cur.text_parts.append(data)


class Document:
    def __init__(self, html: str, path: str = "<html>"):
        b = _Builder()
        b.feed(html)
        b.close()
        self.raw = html
        self.path = path
        self.root = b.root
        self.styles = b.styles
        self.scripts = b.scripts
        self.css = "\n".join(s for s, _ in b.styles)

    def find_all(self, tag: str) -> list[Node]:
        return self.root.find_all(tag)

    def walk(self):
        return self.root.walk()

    def text(self) -> str:
        return self.root.text()

    def body_text(self) -> str:
        body = self.find_all("body")
        node = body[0] if body else self.root
        return re.sub(r"\s+", " ", node.text())


def parse(html: str, path: str = "<html>") -> Document:
    return Document(html, path)
