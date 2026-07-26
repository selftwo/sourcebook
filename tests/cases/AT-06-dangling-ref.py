from _common import *  # noqa: F403


def test_dangling_reference():
    """AT-06: a superscript that points nowhere fails the gate."""
    with tempdir() as d:
        bootstrap(d)
        html = d / "build" / "answer.html"
        html.parent.mkdir(parents=True, exist_ok=True)
        body = ('<p>A sentence whose citation points at nothing.'
                '<sup class="ref"><a href="#c-clm_deadbeef0000">1</a></sup></p>')
        html.write_text(SHELL.format(body=body), encoding="utf-8")
        rc, out = sb(d, "verify", "--html", "build/answer.html")
        assert rc == 2, out
        assert "E-REF-DANGLING" in out and "clm_deadbeef0000" in out, out
