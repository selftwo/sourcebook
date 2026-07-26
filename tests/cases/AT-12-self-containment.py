import json

from _common import *  # noqa: F403


def test_external_references_are_errors():
    """AT-12: a CDN script and a Google Fonts link both fire struct.external-ref."""
    with tempdir() as d:
        rc, out = sb(d, "lint", str(HTML_FIXTURES / "external.html"), "--json")
        assert rc == 2, out
        report = json.loads(out)
        hits = [e for e in report["errors"] if e["rule"] == "struct.external-ref"]
        assert len(hits) == 2, hits
        joined = " ".join(h["snippet"] for h in hits)
        assert "fonts.googleapis.com" in joined and "cdn.example.com" in joined, joined


def test_templates_are_self_contained():
    """AT-12: every shipped template lints clean, with no external reference."""
    with tempdir() as d:
        for tpl in sorted((ROOT / "templates").glob("*.html")):
            rc, out = sb(d, "lint", str(tpl), "--json")
            report = json.loads(out)
            assert report["errors"] == [], f"{tpl.name}: {report['errors']}"
            assert report["warns"] == [], f"{tpl.name}: {report['warns']}"
            assert rc == 0, f"{tpl.name} exited {rc}"
