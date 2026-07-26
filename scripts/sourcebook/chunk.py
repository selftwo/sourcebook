"""`sb chunk` — deterministic, heading-aware, offset-emitting.

Chunks are a retrieval convenience, not a provenance record. Re-chunk with any parameters
and every existing citation still verifies, because citations index into normalized.md.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from . import EXIT_GATE, EXIT_OK
from .ids import CHUNKER_VERSION, chunk_id
from .manifest import advance, load, sources

HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.M)
SENTENCE = re.compile(r"(?<=[.!?])\s+")


BLANK = re.compile(r"\n[ \t]*\n")


def _paragraphs(text: str, start: int, end: int) -> list[tuple[int, int, int]]:
    out = []
    pos = start
    while pos < end:
        m = BLANK.search(text, pos, end)
        stop = m.end() if m else end
        out.append((pos, stop, 0))
        pos = stop
    return out


def _blocks(text: str) -> list[tuple[int, int, int]]:
    """Split into (start, end, heading_level) blocks at blank-line boundaries.

    A heading line is its own block and carries its level; every other block has level 0.
    Offsets are exact and contiguous: block[i].end == block[i+1].start.
    """
    n = len(text)
    out: list[tuple[int, int, int]] = []
    cursor = 0
    for hm in HEADING.finditer(text):
        if hm.start() < cursor:
            continue
        line_end = text.find("\n", hm.end())
        line_end = n if line_end == -1 else line_end + 1
        if hm.start() > cursor:
            out.extend(_paragraphs(text, cursor, hm.start()))
        out.append((hm.start(), line_end, len(hm.group(1))))
        cursor = line_end
    if cursor < n:
        out.extend(_paragraphs(text, cursor, n))
    return [b for b in out if b[1] > b[0]]


def _split_long(text: str, start: int, end: int, target: int) -> list[tuple[int, int]]:
    if end - start <= target:
        return [(start, end)]
    pieces: list[tuple[int, int]] = []
    cur = start
    for m in SENTENCE.finditer(text, start, end):
        if m.end() - cur >= target * 0.6:
            pieces.append((cur, m.end()))
            cur = m.end()
    if cur < end:
        pieces.append((cur, end))
    final: list[tuple[int, int]] = []
    for a, b in pieces:
        while b - a > target:
            cut = text.rfind(" ", a, a + target)
            if cut <= a:
                cut = a + target
            final.append((a, cut))
            a = cut
        if b > a:
            final.append((a, b))
    return final


def chunk_text(text: str, target: int = 1600, overlap: int = 240) -> list[dict]:
    blocks = _blocks(text)
    heading_stack: list[tuple[int, str]] = []
    packed: list[dict] = []
    cur_start = cur_end = 0
    cur_headings: list[str] = []
    started = False

    def flush():
        nonlocal started
        if started and cur_end > cur_start:
            packed.append({"start": cur_start, "end": cur_end, "heading_path": list(cur_headings)})
        started = False

    for start, end, level in blocks:
        if level:  # a heading line: close the previous chunk, update the path
            flush()
            title = HEADING.match(text[start:end].strip() + "\n")
            label = title.group(2).strip() if title else text[start:end].strip("# \n")
            heading_stack = [h for h in heading_stack if h[0] < level]
            heading_stack.append((level, label))
            cur_headings = [h[1] for h in heading_stack]
            cur_start, cur_end, started = start, end, True
            continue
        for piece_start, piece_end in _split_long(text, start, end, target):
            if not started:
                cur_start, cur_end, started = piece_start, piece_end, True
                continue
            if piece_end - cur_start > target:
                flush()
                cur_start, cur_end, started = piece_start, piece_end, True
            else:
                cur_end = piece_end
    flush()

    if len(packed) >= 2 and packed[-1]["end"] - packed[-1]["start"] < 120:
        tail = packed.pop()
        packed[-1]["end"] = tail["end"]

    # Overlap: extend each chunk backwards, snapped to whitespace, never across a heading.
    for i, c in enumerate(packed):
        c["ordinal"] = i
        if i == 0 or overlap <= 0:
            continue
        prev = packed[i - 1]
        if prev["heading_path"] != c["heading_path"]:
            continue
        want = max(prev["start"], c["start"] - overlap)
        snap = text.rfind(" ", want, c["start"])
        c["start"] = snap + 1 if snap > want else want
    return packed


def chunk(root: Path, target: int | None = None, overlap: int | None = None) -> int:
    root = Path(root)
    m = load(root)
    target = target if target is not None else m["config"].get("chunk_target", 1600)
    overlap = overlap if overlap is not None else m["config"].get("chunk_overlap", 240)
    out_dir = root / "chunks"
    out_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    written = 0
    for rec in sources(root):
        if rec.get("status") != "ready":
            continue
        path = root / "sources" / rec["id"] / "normalized.md"
        if not path.is_file():
            print(f"E-CHUNK  {rec['id']}  normalized.md missing", file=sys.stderr)
            return EXIT_GATE
        text = path.read_text(encoding="utf-8")
        chunks = chunk_text(text, target, overlap)

        # Invariants: a violation is a crash, not a warning.
        prev_end = 0
        for c in chunks:
            assert 0 <= c["start"] < c["end"] <= len(text), f"offset out of range in {rec['id']}"
            assert c["start"] <= prev_end, f"gap in coverage in {rec['id']} at {c['start']}"
            prev_end = max(prev_end, c["end"])
        assert not chunks or prev_end == len(text), f"chunks do not cover {rec['id']}"

        lines = []
        for c in chunks:
            lines.append(json.dumps({
                "chunk_id": chunk_id(rec["id"], c["ordinal"]),
                "source_id": rec["id"],
                "ordinal": c["ordinal"],
                "start": c["start"],
                "end": c["end"],
                "heading_path": c["heading_path"],
            }, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        (out_dir / f"{rec['id']}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        total += len(chunks)
        written += 1
        print(f"chunked  {rec['id']}  {len(chunks)} chunks  (target={target} overlap={overlap})")

    if written == 0:
        print("E-CHUNK  workspace  no ready sources to chunk", file=sys.stderr)
        return EXIT_GATE
    advance(root, "CHUNK", f"{total} chunks over {written} sources")
    return EXIT_OK


def load_chunks(root: Path, source_id: str | None = None) -> list[dict]:
    out: list[dict] = []
    cdir = Path(root) / "chunks"
    if not cdir.is_dir():
        return out
    names = [f"{source_id}.jsonl"] if source_id else sorted(p.name for p in cdir.glob("*.jsonl"))
    for name in names:
        p = cdir / name
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
    return out
