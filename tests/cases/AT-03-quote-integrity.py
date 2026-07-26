import json

from _common import *  # noqa: F403


def test_flipped_quote_is_caught():
    """AT-03: one changed character fails the gate with the claim id."""
    with tempdir() as d:
        bootstrap(d)
        src = source_ids(d)["operator-status.md"]
        needle = "No other scheme is live at this time."
        start, end = span(d, src, needle)
        cid = add_claim(d, {
            "text": "Only Calder Transit and Vantis Rail are live on Northline services.",
            "topic_key": "fixture.live", "kind": "fact", "confidence": "verified",
            "evidence": [{"source_id": src, "start": start, "end": end, "quote": needle}],
        })
        rc, out = sb(d, "verify")
        assert rc == 0, out

        path = d / "ledger" / "claims.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["claims"][0]["evidence"][0]["quote"] = needle.replace("No other", "No otter")
        path.write_text(json.dumps(data), encoding="utf-8")

        rc, out = sb(d, "verify")
        assert rc == 2, f"expected gate failure, got {rc}:\n{out}"
        assert "E-QUOTE-MISMATCH" in out, out
        assert cid in out, out
