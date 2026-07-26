from _common import *  # noqa: F403


def test_no_image_path_ships():
    """AT-13: a full images.mode=none build passes every gate with zero <img>."""
    with tempdir() as d:
        full_build(d)
        rc, out = sb(d, "verify")
        assert rc == 0, out
        assert "PASS" in out, out
        html = (d / "build" / "answer.html").read_text(encoding="utf-8")
        assert "<img" not in html, "the no-image path emitted an image"
        rc, out = sb(d, "licenses")
        assert rc == 0 and "nothing to check" in out, out
