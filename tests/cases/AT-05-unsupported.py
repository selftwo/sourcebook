from _common import *  # noqa: F403


def test_unsupported_cannot_ship():
    """AT-05: a claim nothing supports fails the gate."""
    with tempdir() as d:
        bootstrap(d)
        cid = add_claim(d, {
            "text": "Harbour cards will certainly work by the summer.",
            "topic_key": "fixture.speculation", "kind": "fact",
            "confidence": "unsupported", "evidence": [],
        })
        write_plan(d, [{"id": "answer", "heading": "The short answer",
                        "intent": "state it", "claim_ids": [cid]}])
        rc, out = sb(d, "verify")
        assert rc == 2, out
        assert "E-UNSUPPORTED" in out and cid in out, out
