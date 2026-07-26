import json

from _common import *  # noqa: F403

FIG = ('<figure><img src="assets/{name}" alt="A bar chart of live partner schemes">'
       '<figcaption>{caption}</figcaption></figure>')


def _artifact(d, name, caption):
    (d / "assets").mkdir(parents=True, exist_ok=True)
    (d / "assets" / name).write_bytes(b"not really an image, but it is on disk")
    path = d / "build" / "answer.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SHELL.format(body=FIG.format(name=name, caption=caption)),
                    encoding="utf-8")
    return path


def _credits(d, payload):
    (d / "assets").mkdir(parents=True, exist_ok=True)
    (d / "assets" / "credits.json").write_text(json.dumps(payload), encoding="utf-8")


def test_a_uncredited_generated_image():
    """AT-14a: a generated image with no credits entry fails `sb licenses`."""
    with tempdir() as d:
        bootstrap(d)
        _artifact(d, "diagram.png", "Generated illustration")
        _credits(d, {})
        rc, out = sb(d, "licenses", "--html", "build/answer.html")
        assert rc == 2, out
        assert "E-IMG-UNCREDITED" in out, out


def test_b_cc_by_needs_visible_credit():
    """AT-14b: a CC BY asset whose credit string is absent from the DOM fails."""
    with tempdir() as d:
        bootstrap(d)
        _artifact(d, "terminal.jpg", "A quayside terminal")
        _credits(d, {"terminal.jpg": {
            "origin": "sourced", "source": "https://example.org/terminal.jpg",
            "credit": "A. Photographer / Example Commons", "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/"}})
        rc, out = sb(d, "licenses", "--html", "build/answer.html")
        assert rc == 2, out
        assert "E-IMG-ATTRIB" in out, out

        _artifact(d, "terminal.jpg", "A quayside terminal. A. Photographer / Example Commons")
        rc, out = sb(d, "licenses", "--html", "build/answer.html")
        assert rc == 0, out


def test_c_generated_image_needs_a_visible_label():
    """AT-14c: a generated image with no visible label fails E-IMG-UNLABELED."""
    with tempdir() as d:
        bootstrap(d)
        _artifact(d, "diagram.png", "A flow of the settlement path")
        _credits(d, {"diagram.png": {
            "origin": "generated", "generator": "an image model",
            "prompt": "a plain two-column settlement flow diagram, no text",
            "created_at": "2026-07-26T10:22:00Z"}})
        rc, out = sb(d, "licenses", "--html", "build/answer.html")
        assert rc == 2, out
        assert "E-IMG-UNLABELED" in out, out

        _artifact(d, "diagram.png", "A flow of the settlement path. Generated illustration")
        rc, out = sb(d, "licenses", "--html", "build/answer.html")
        assert rc == 0, out


def test_denied_license_fails():
    """AT-14: NonCommercial and unknown licenses are not usable."""
    with tempdir() as d:
        bootstrap(d)
        _artifact(d, "photo.jpg", "A photo. Someone / Somewhere")
        _credits(d, {"photo.jpg": {
            "origin": "sourced", "source": "https://example.org/photo.jpg",
            "credit": "Someone / Somewhere", "license": "CC BY-NC 4.0"}})
        rc, out = sb(d, "licenses", "--html", "build/answer.html")
        assert rc == 2 and "E-IMG-LICENSE" in out, out
