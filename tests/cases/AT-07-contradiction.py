import json

from _common import *  # noqa: F403

TOPIC = "fixture.cards.active"


def _conflicting(d):
    ids = source_ids(d)
    op, tw = ids["operator-status.md"], ids["trade-report.md"]
    q1 = "There are 1.4 million active Meridian Cards in circulation as of 12 February 2026."
    s1, e1 = span(d, op, q1)
    a = add_claim(d, {
        "text": "Northline reports 1.4 million active Meridian Cards.",
        "topic_key": TOPIC, "kind": "number", "confidence": "verified",
        "evidence": [{"source_id": op, "start": s1, "end": e1, "quote": q1}]})
    q2 = "An earlier industry estimate put the number of active Meridian Cards at 1.9 million."
    s2, e2 = span(d, tw, q2)
    b = add_claim(d, {
        "text": "An industry estimate put active Meridian Cards at 1.9 million.",
        "topic_key": TOPIC, "kind": "number", "confidence": "reported",
        "evidence": [{"source_id": tw, "start": s2, "end": e2, "quote": q2}]})
    return a, b


def test_a_open_cluster_blocks():
    """AT-07a: an unadjudicated numeric conflict fails the gate."""
    with tempdir() as d:
        bootstrap(d)
        _conflicting(d)
        rc, out = sb(d, "contradictions")
        assert rc == 0 and "OPEN" in out and "numeric" in out, out
        rc, out = sb(d, "verify")
        assert rc == 2, out
        assert "E-CLUSTER-OPEN" in out, out


def test_b_both_stand_must_be_rendered():
    """AT-07b: both_stand obligates the artifact to show both sides."""
    with tempdir() as d:
        bootstrap(d)
        a, b = _conflicting(d)
        adj = {"adjudications": [{
            "cluster_id": "", "topic_key": TOPIC, "claim_ids": [a, b],
            "outcome": "both_stand", "winner": None,
            "reason": "Two figures for the same population from sources at different distances "
                      "from the fact, and a reader needs to see both to judge either.",
            "decided_at": "2026-07-26T10:00:00Z"}]}
        import sys as _s
        _s.path.insert(0, str(ROOT / "scripts"))
        from sourcebook.ids import cluster_id
        adj["adjudications"][0]["cluster_id"] = cluster_id(TOPIC)
        (d / "adj.json").write_text(json.dumps(adj), encoding="utf-8")
        rc, out = sb(d, "adjudicate", "--file", "adj.json", "--apply")
        assert rc == 0, out

        order = ordered_claims(d)
        assert all(c["confidence"] == "contested" for c in order), order

        compose(d, [order[0]])          # only one side rendered
        render_and_inject(d)
        rc, out = sb(d, "verify", "--html", "build/answer.html")
        assert rc == 2, out
        assert "E-CONTESTED-HIDDEN" in out, out


def test_c_both_rendered_passes():
    """AT-07c: with both sides on the page the gate is clean."""
    with tempdir() as d:
        bootstrap(d)
        a, b = _conflicting(d)
        import sys as _s
        _s.path.insert(0, str(ROOT / "scripts"))
        from sourcebook.ids import cluster_id
        (d / "adj.json").write_text(json.dumps({"adjudications": [{
            "cluster_id": cluster_id(TOPIC), "topic_key": TOPIC, "claim_ids": [a, b],
            "outcome": "both_stand", "winner": None,
            "reason": "Two figures for the same population from sources at different distances "
                      "from the fact, and a reader needs to see both to judge either.",
            "decided_at": "2026-07-26T10:00:00Z"}]}), encoding="utf-8")
        rc, out = sb(d, "adjudicate", "--file", "adj.json", "--apply")
        assert rc == 0, out
        order = ordered_claims(d)
        compose(d, order)
        render_and_inject(d)
        rc, out = sb(d, "verify", "--html", "build/answer.html")
        assert rc == 0, out
