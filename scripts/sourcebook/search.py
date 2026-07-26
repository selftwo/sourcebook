"""`sb search`, `sb find`, `sb quote`.

`sb find` is the ergonomic centre of the kit: the agent pastes a sentence it just read and
gets back a byte span. It never computes an offset, so it never gets one wrong. There is no
path here that returns an approximate span.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from . import EXIT_GATE, EXIT_OK, EXIT_USAGE
from .chunk import load_chunks
from .index import bm25, load_index

_WS = re.compile(r"\s+")


def _text(root: Path, source_id: str) -> str | None:
    p = Path(root) / "sources" / source_id / "normalized.md"
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _chunk_map(root: Path) -> dict[str, dict]:
    return {c["chunk_id"]: c for c in load_chunks(root)}


def search(root: Path, query: str, k: int = 8, source: str | None = None, as_json: bool = False) -> int:
    idx = load_index(root)
    if idx is None:
        print("E-SEARCH  workspace  no index; run `sb index`", file=sys.stderr)
        return EXIT_GATE
    cmap = _chunk_map(root)
    hits = bm25(idx, query, restrict=source)[:k]
    if not hits:
        print(f"no hits for {query!r}")
        return EXIT_OK
    rows = []
    for rank, (cid, score) in enumerate(hits, 1):
        c = cmap.get(cid)
        if not c:
            continue
        text = _text(root, c["source_id"]) or ""
        span = text[c["start"]:c["end"]]
        rows.append({
            "rank": rank, "chunk_id": cid, "score": round(score, 4),
            "source_id": c["source_id"], "start": c["start"], "end": c["end"],
            "heading_path": c["heading_path"],
            "preview": _WS.sub(" ", span).strip()[:160],
        })
    if as_json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for r in rows:
            path = " > ".join(r["heading_path"]) or "(no heading)"
            print(f"{r['rank']:>2}  {r['chunk_id']}  {r['score']:>7.3f}  {path}")
            print(f"      {r['preview']}")
    return EXIT_OK


def find(root: Path, source_id: str, needle: str, show_all: bool = False) -> int:
    text = _text(root, source_id)
    if text is None:
        print(f"E-FIND  {source_id}  no normalized.md for that source id", file=sys.stderr)
        return EXIT_USAGE
    if not needle:
        print("E-FIND  (empty)  nothing to look for", file=sys.stderr)
        return EXIT_USAGE

    spans: list[tuple[int, int]] = []
    pos = text.find(needle)
    while pos != -1:
        spans.append((pos, pos + len(needle)))
        if not show_all:
            break
        pos = text.find(needle, pos + 1)
    if spans:
        for start, end in spans:
            print(f"{source_id}  {start}..{end}  exact  ({len(spans)} match{'es' if len(spans) != 1 else ''})")
        return EXIT_OK

    # Second pass: whitespace-insensitive. Report the ORIGINAL offsets of the matched region.
    span = _ws_insensitive(text, needle)
    if span:
        start, end = span
        print(f"{source_id}  {start}..{end}  whitespace-normalized  (1 match)")
        print("  NOTE: the source text differs from your paste only in whitespace.")
        print(f"  Copy the exact slice with: sb quote {source_id} {start} {end}")
        return EXIT_OK

    print(f"E-FIND-NOMATCH  {source_id}  that text is not in this source", file=sys.stderr)
    idx = load_index(root)
    if idx is not None:
        cmap = _chunk_map(root)
        anchors = bm25(idx, needle, restrict=source_id)[:3]
        if anchors:
            print("  nearest anchors in this source:", file=sys.stderr)
            for cid, score in anchors:
                c = cmap[cid]
                preview = _WS.sub(" ", text[c["start"]:c["end"]]).strip()[:140]
                print(f"    {cid}  {c['start']}..{c['end']}  {score:.3f}  {preview}", file=sys.stderr)
    print("  Re-read the source and paste the sentence byte-exact. Never approximate a span.",
          file=sys.stderr)
    return EXIT_USAGE


def _ws_insensitive(text: str, needle: str) -> tuple[int, int] | None:
    """Match ignoring whitespace runs, then map back to original offsets."""
    flat_chars: list[str] = []
    origin: list[int] = []
    prev_space = False
    for i, ch in enumerate(text):
        if ch.isspace():
            if prev_space:
                continue
            flat_chars.append(" ")
            origin.append(i)
            prev_space = True
        else:
            flat_chars.append(ch)
            origin.append(i)
            prev_space = False
    flat = "".join(flat_chars)
    target = _WS.sub(" ", needle).strip()
    if not target:
        return None
    pos = flat.find(target)
    if pos == -1:
        return None
    start = origin[pos]
    last = origin[pos + len(target) - 1]
    return start, last + 1


def quote(root: Path, source_id: str, start: int, end: int) -> int:
    text = _text(root, source_id)
    if text is None:
        print(f"E-QUOTE  {source_id}  no normalized.md for that source id", file=sys.stderr)
        return EXIT_USAGE
    if not (0 <= start < end <= len(text)):
        print(f"E-QUOTE  {source_id}  span {start}..{end} is out of range (0..{len(text)})",
              file=sys.stderr)
        return EXIT_USAGE
    sys.stdout.write(text[start:end])
    if not text[start:end].endswith("\n"):
        sys.stdout.write("\n")
    return EXIT_OK
