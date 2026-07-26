import json

from _common import *  # noqa: F403


def test_volatile_needs_a_date():
    """AT-09: volatile with no as_of fails the gate."""
    with tempdir() as d:
        bootstrap(d)
        op = source_ids(d)["operator-status.md"]
        q = "No other scheme is live at this time."
        s, e = span(d, op, q)
        cid = add_claim(d, {
            "text": "Only two partner schemes are live on Northline services.",
            "topic_key": "fixture.live", "kind": "fact", "confidence": "verified",
            "volatile": True, "as_of": None, "recheck": None,
            "evidence": [{"source_id": op, "start": s, "end": e, "quote": q}]})
        rc, out = sb(d, "verify")
        assert rc == 2, out
        assert "E-VOLATILE-UNDATED" in out and cid in out, out


def test_as_of_must_reach_the_dom():
    """AT-09: a dated volatile claim must print its date in the document."""
    with tempdir() as d:
        bootstrap(d)
        op = source_ids(d)["operator-status.md"]
        q = "No other scheme is live at this time."
        s, e = span(d, op, q)
        cid = add_claim(d, {
            "text": "Only two partner schemes are live on Northline services.",
            "topic_key": "fixture.live", "kind": "fact", "confidence": "verified",
            "volatile": True, "as_of": "2026-02-12",
            "recheck": "https://example.org/northline/interoperability",
            "evidence": [{"source_id": op, "start": s, "end": e, "quote": q}]})
        order = ordered_claims(d)
        compose(d, order)               # composed, but the ledger is NOT injected
        rc, out = sb(d, "verify", "--html", "build/answer.html")
        assert rc == 2, out
        assert "E-ASOF-MISSING" in out and cid in out, out

        render_and_inject(d)            # the rendered ledger carries the date
        rc, out = sb(d, "verify", "--html", "build/answer.html")
        assert rc == 0, out
