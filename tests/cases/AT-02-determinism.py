import hashlib

from _common import *  # noqa: F403


def _digest(d):
    out = {}
    for rel in sorted(p.relative_to(d).as_posix() for p in d.rglob("*")
                      if p.is_file() and (p.name == "normalized.md"
                                          or p.suffix == ".jsonl"
                                          or p.name == "lexical.json")):
        out[rel] = hashlib.sha256((d / rel).read_bytes()).hexdigest()
    return out


def test_determinism():
    """AT-02: two runs over the same inputs produce byte-identical outputs."""
    with tempdir() as a, tempdir() as b:
        bootstrap(a)
        bootstrap(b)
        da, db = _digest(a), _digest(b)
        assert da and da == db, f"outputs diverged:\n{da}\n{db}"
