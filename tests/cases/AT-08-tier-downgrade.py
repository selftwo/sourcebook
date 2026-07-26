from _common import *  # noqa: F403


def _forum_number_claim(d, confidence):
    src = source_ids(d)["forum-thread.md"]
    needle = "Bring cash."
    start, end = span(d, src, needle)
    return add_claim(d, {
        "text": "Three travellers in the thread reported the same failure.",
        "topic_key": "fixture.reports.count", "kind": "number", "confidence": confidence,
        "evidence": [{"source_id": src, "start": start, "end": end, "quote": needle}]})


def test_weak_tier_cannot_be_verified():
    """AT-08: a number cited only to tier C cannot be marked verified."""
    with tempdir() as d:
        bootstrap(d)
        cid = _forum_number_claim(d, "verified")
        rc, out = sb(d, "verify")
        assert rc == 2 and "E-TIER-WEAK" in out and cid in out, out


def test_downgraded_claim_must_carry_the_reported_mark():
    """AT-08: after downgrade, the wrong mark in the DOM is E-MARK-WRONG."""
    with tempdir() as d:
        bootstrap(d)
        cid = _forum_number_claim(d, "reported")
        write_plan(d, [{"id": "answer", "heading": "What travellers report",
                        "intent": "pattern evidence", "claim_ids": [cid]}])
        ordered = ordered_claims(d)
        compose(d, ordered, override_marks={cid: ["m-checked"]})
        render_and_inject(d)
        rc, out = sb(d, "verify")
        assert rc == 2 and "E-MARK-WRONG" in out, out

        compose(d, ordered)
        render_and_inject(d)
        rc, out = sb(d, "verify")
        assert rc == 0, out
