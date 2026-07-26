"""`sb index` — pure-Python BM25 over chunks. No embeddings, no model, no store.

The file is dumped with sorted keys and compact separators so two runs over the same
corpus are byte-identical. That property is acceptance test AT-02.
"""

from __future__ import annotations

import json
import math
import re
import sys
import unicodedata
from pathlib import Path

from . import EXIT_GATE, EXIT_OK
from .chunk import load_chunks
from .ids import INDEXER_VERSION
from .manifest import advance, sources

K1 = 1.2
B = 0.75

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can", "for", "from",
    "had", "has", "have", "he", "her", "his", "how", "in", "into", "is", "it", "its",
    "of", "on", "or", "our", "she", "so", "than", "that", "the", "their", "them", "then",
    "there", "these", "they", "this", "to", "was", "were", "what", "when", "which", "who",
    "will", "with", "you", "your",
}

_WORD = re.compile(r"[a-z0-9]+")


def tokenize(s: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", s).casefold()
    return [t for t in _WORD.findall(folded) if len(t) > 1 and t not in STOPWORDS]


def build(root: Path) -> int:
    root = Path(root)
    ready = {s["id"] for s in sources(root) if s.get("status") == "ready"}
    texts = {
        sid: (root / "sources" / sid / "normalized.md").read_text(encoding="utf-8")
        for sid in ready
    }
    postings: dict[str, dict[str, int]] = {}
    doclen: dict[str, int] = {}

    for c in load_chunks(root):
        if c["source_id"] not in texts:
            continue
        span = texts[c["source_id"]][c["start"]:c["end"]]
        toks = tokenize(span)
        doclen[c["chunk_id"]] = len(toks)
        counts: dict[str, int] = {}
        for t in toks:
            counts[t] = counts.get(t, 0) + 1
        for t, n in counts.items():
            postings.setdefault(t, {})[c["chunk_id"]] = n

    if not postings:
        print("E-INDEX  workspace  no postings; is there any chunked text?", file=sys.stderr)
        return EXIT_GATE

    n_docs = len(doclen)
    avgdl = sum(doclen.values()) / n_docs if n_docs else 0.0
    payload = {
        "version": INDEXER_VERSION,
        "n_docs": n_docs,
        "avgdl": round(avgdl, 4),
        "postings": {t: [[cid, postings[t][cid]] for cid in sorted(postings[t])]
                     for t in sorted(postings)},
        "doclen": doclen,
    }
    out = root / "index" / "lexical.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"indexed  {n_docs} chunks  {len(postings)} terms  avgdl={payload['avgdl']}")
    advance(root, "INDEX", f"{n_docs} chunks indexed")
    return EXIT_OK


def load_index(root: Path) -> dict | None:
    p = Path(root) / "index" / "lexical.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def bm25(idx: dict, query: str, restrict: str | None = None) -> list[tuple[str, float]]:
    n_docs = idx["n_docs"]
    avgdl = idx["avgdl"] or 1.0
    doclen = idx["doclen"]
    scores: dict[str, float] = {}
    for term in tokenize(query):
        plist = idx["postings"].get(term)
        if not plist:
            continue
        df = len(plist)
        idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
        for cid, tf in plist:
            if restrict and not cid.startswith(restrict):
                continue
            dl = doclen.get(cid, 0)
            denom = tf + K1 * (1 - B + B * dl / avgdl)
            scores[cid] = scores.get(cid, 0.0) + idf * (tf * (K1 + 1)) / (denom or 1.0)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
