import json

from _common import *  # noqa: F403


def test_low_contrast_is_reported_with_its_ratio():
    """AT-11: #8a8a8a on #f7f2e8 fires a11y.contrast-body with the computed ratio."""
    with tempdir() as d:
        rc, out = sb(d, "lint", str(HTML_FIXTURES / "contrast-fail.html"), "--json")
        assert rc == 2, out
        report = json.loads(out)
        body = [e for e in report["errors"] if e["rule"] == "a11y.contrast-body"]
        assert body, report["errors"]
        assert "3.09:1" in body[0]["detail"], body[0]["detail"]
        assert "#8a8a8a on #f7f2e8" in body[0]["snippet"], body[0]["snippet"]
        assert any(e["rule"] == "a11y.contrast-large" for e in report["errors"]), report


def test_passing_fixture_has_no_contrast_errors():
    """AT-11: the clean fixture produces zero contrast findings and zero unresolved values."""
    with tempdir() as d:
        rc, out = sb(d, "lint", str(HTML_FIXTURES / "clean.html"), "--json")
        report = json.loads(out)
        assert not [e for e in report["errors"] if e["rule"].startswith("a11y.contrast")], report
        assert report["unresolved"] == 0, report["unresolved"]
