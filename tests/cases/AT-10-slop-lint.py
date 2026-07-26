import json

from _common import *  # noqa: F403

EXPECTED = {
    "slop.gradient-text", "slop.side-stripe", "slop.over-round",
    "slop.stripe-bg", "slop.cream-band", "slop.eyebrow-reflex",
}


def test_slop_fixture_fires_exactly_six_errors():
    """AT-10: the slop fixture produces exactly the six expected error ids."""
    with tempdir() as d:
        rc, out = sb(d, "lint", str(HTML_FIXTURES / "slop.html"), "--json")
        assert rc == 2, out
        report = json.loads(out)
        ids = [e["rule"] for e in report["errors"]]
        assert len(ids) == 6, f"expected 6 errors, got {len(ids)}: {ids}"
        assert set(ids) == EXPECTED, f"{set(ids) ^ EXPECTED}"


def test_clean_fixture_is_silent():
    """AT-10: the reference artifact produces zero findings."""
    with tempdir() as d:
        rc, out = sb(d, "lint", str(HTML_FIXTURES / "clean.html"), "--json")
        report = json.loads(out)
        assert report["errors"] == [] and report["warns"] == [], out
        assert rc == 0, out
