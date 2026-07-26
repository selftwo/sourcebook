from _common import *  # noqa: F403


def test_chunking_is_not_load_bearing():
    """AT-04: re-chunking with different parameters cannot orphan a citation."""
    with tempdir() as d:
        bootstrap(d)
        src = source_ids(d)["operator-status.md"]
        needle = "No other scheme is live at this time."
        start, end = span(d, src, needle)
        add_claim(d, {
            "text": "Only two partner schemes are live.",
            "topic_key": "fixture.live", "kind": "fact", "confidence": "verified",
            "evidence": [{"source_id": src, "start": start, "end": end, "quote": needle}],
        })
        rc, out = sb(d, "verify")
        assert rc == 0, out

        before = (d / "chunks" / f"{src}.jsonl").read_text(encoding="utf-8")
        rc, out = sb(d, "chunk", "--target", "240", "--overlap", "60")
        assert rc == 0, out
        after = (d / "chunks" / f"{src}.jsonl").read_text(encoding="utf-8")
        assert before != after, "re-chunking with new parameters changed nothing"

        rc, out = sb(d, "index")
        assert rc == 0, out
        rc, out = sb(d, "verify")
        assert rc == 0, f"citations broke after re-chunking:\n{out}"
