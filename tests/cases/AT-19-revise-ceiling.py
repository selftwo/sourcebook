import json

from _common import *  # noqa: F403


def test_three_failures_escalate():
    """AT-19: after repeated failures the kit stops and asks rather than churning."""
    with tempdir() as d:
        bootstrap(d)
        src = source_ids(d)["operator-status.md"]
        needle = "No other scheme is live at this time."
        start, end = span(d, src, needle)
        add_claim(d, {
            "text": "Only two partner schemes are live on Northline services.",
            "topic_key": "fixture.live", "kind": "fact", "confidence": "verified",
            "evidence": [{"source_id": src, "start": start, "end": end,
                          "quote": needle.replace("No other", "No otter")}]})

        for _ in range(4):
            rc, out = sb(d, "verify")
            assert rc == 2, out

        manifest = json.loads((d / "sourcebook.json").read_text(encoding="utf-8"))
        assert manifest["revise_count"] == 3, manifest["revise_count"]

        rc, out = sb(d, "status")
        assert rc == 0, out
        assert "BLOCKED" in out, out
        assert "ESCALATE" in out, out
        assert "sb verify" not in out.split("next")[-1], out
