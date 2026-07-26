"""AT-22: what the workspace accepts on the way in, and how it gets out of BLOCKED.

An approximate paste is not a span. A declared encoding is not a note. A URL is not a licence
to reach an address the machine happens to be able to route to.
"""

import json
import sys as _sys
import urllib.request

from _common import *  # noqa: F403

_sys.path.insert(0, str(ROOT / "scripts"))

CP1252 = ("<!doctype html><html><head><meta charset=\"windows-1252\">"
          "<title>Fares</title></head><body><h1>Fares</h1>"
          "<p>The operator’s café fare rose to €2.40 — a 5% rise.</p>"
          "</body></html>")

BLOCKED_URLS = [
    "http://127.0.0.1/admin",
    "http://localhost:8080/admin",
    "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
    "http://[::1]/admin",
    "http://[::ffff:127.0.0.1]/admin",
    "http://10.1.2.3/internal",
    "http://192.168.0.1/router",
    "http://172.16.4.5/internal",
    "http://0.0.0.0/",
    "http://224.0.0.1/",
    "http://240.0.0.1/",
    "file:///etc/passwd",
    "javascript:fetch('https://evil.example')",
    "http://user:secret@169.254.169.254/",
]


def test_a_whitespace_inexact_find_exits_one():
    """AT-22a: a paste that matches only after whitespace normalization exits 1."""
    with tempdir() as d:
        bootstrap(d)
        src = source_ids(d)["operator-status.md"]
        exact = "No other scheme is live at this time."
        rc, out = sb(d, "find", src, exact)
        assert rc == 0 and "exact" in out, out

        rc, out = sb(d, "find", src, exact.replace(" is ", "  is  "))
        assert rc == 1, f"an approximate paste returned a citable span:\n{out}"
        assert "E-FIND-INEXACT" in out, out
        assert "sb quote" in out, out          # it still says how to get the exact slice

        rc, out = sb(d, "find", src, "A sentence that is simply not in this source at all.")
        assert rc == 1 and "E-FIND-NOMATCH" in out, out


def test_b_declared_charset_is_used_not_just_recorded():
    """AT-22b: a Windows-1252 source normalizes to its real characters, not U+FFFD."""
    with tempdir() as d:
        init(d)
        (d / "input").mkdir(exist_ok=True)
        (d / "input" / "fares.html").write_bytes(CP1252.encode("cp1252"))
        rc, out = sb(d, "add", "input/fares.html", "--tier", "B",
                     "--reason", "bylined dated trade reporting", "--title", "Fares")
        assert rc == 0, out
        rc, out = sb(d, "extract")
        assert rc == 0, out

        sid = source_ids(d)["fares.html"]
        rec = json.loads((d / "sources" / sid / "source.json").read_text(encoding="utf-8"))
        assert rec["charset"] == "windows-1252", rec

        text = (d / "sources" / sid / "normalized.md").read_text(encoding="utf-8")
        assert "�" not in text, f"the canonical text is replacement-laced:\n{text}"
        assert "operator’s café" in text, text
        assert "€2.40" in text, text

        # And a paste of the real sentence resolves to a span, which is the whole point.
        rc, out = sb(d, "chunk")
        assert rc == 0, out
        rc, out = sb(d, "find", sid, "The operator’s café fare rose")
        assert rc == 0 and "exact" in out, out


def test_c_recorded_charset_survives_re_extraction():
    """AT-22c: the charset a fetch declared is what `sb extract` decodes with."""
    with tempdir() as d:
        init(d)
        (d / "input").mkdir(exist_ok=True)
        # No in-band declaration: the transfer's charset is the only thing that knows.
        (d / "input" / "notice.txt").write_bytes(
            "Fares rose “slightly” in café terms.".encode("cp1252"))
        rc, out = sb(d, "add", "input/notice.txt", "--tier", "B", "--reason", "a dated notice")
        assert rc == 0, out
        rc, out = sb(d, "extract")
        assert rc == 0, out

        sid = source_ids(d)["notice.txt"]
        meta = d / "sources" / sid / "source.json"
        assert "�" in (d / "sources" / sid / "normalized.md").read_text(encoding="utf-8")

        rec = json.loads(meta.read_text(encoding="utf-8"))
        assert rec["charset"] is None, rec
        rec["charset"] = "windows-1252"
        meta.write_text(json.dumps(rec), encoding="utf-8")

        rc, out = sb(d, "extract", "--force")
        assert rc == 0, out
        text = (d / "sources" / sid / "normalized.md").read_text(encoding="utf-8")
        assert "�" not in text, text
        assert "“slightly”" in text and "café" in text, text


def test_d_ssrf_destinations_are_refused():
    """AT-22d: loopback, private, link-local, reserved, and non-http targets are blocked."""
    from sourcebook.collect import BlockedURL, assert_fetchable

    for url in BLOCKED_URLS:
        try:
            assert_fetchable(url)
        except BlockedURL as exc:
            assert "blocked" in str(exc), (url, exc)
        else:
            raise AssertionError(f"{url} was not refused")


def test_e_redirects_are_checked_like_the_first_destination():
    """AT-22e: a redirect into the metadata service is refused mid-fetch."""
    from sourcebook.collect import BlockedURL, _GuardedRedirects

    handler = _GuardedRedirects()
    req = urllib.request.Request("https://example.org/start")
    try:
        handler.redirect_request(req, None, 302, "Found", {},
                                 "http://169.254.169.254/latest/meta-data/")
    except BlockedURL as exc:
        assert "link-local" in str(exc), exc
    else:
        raise AssertionError("a redirect to the metadata service was followed")


def test_f_sb_add_refuses_a_blocked_url():
    """AT-22f: end to end, the direct-fetch path records a failure and stores no bytes."""
    with tempdir() as d:
        init(d)
        rc, out = sb(d, "config", "set", "capabilities.web_fetch=script")
        assert rc == 0, out
        rc, out = sb(d, "add", "http://169.254.169.254/latest/meta-data/", "--tier", "D",
                     "--reason", "unknown provenance; this is a test of the guard")
        assert rc == 2, out
        assert "E-ADD-FAILED" in out and "blocked" in out, out
        recs = [json.loads((sd / "source.json").read_text(encoding="utf-8"))
                for sd in (d / "sources").iterdir() if (sd / "source.json").is_file()]
        assert recs and all(r["status"] == "failed" for r in recs), recs
        assert not list((d / "sources").glob("*/raw*")), "blocked fetch wrote bytes to disk"


def test_g_blocked_has_a_documented_way_out():
    """AT-22g: `sb unblock --reason` clears the ceiling and records why."""
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
        for _ in range(3):
            rc, out = sb(d, "verify")
            assert rc == 2, out

        rc, out = sb(d, "status")
        assert rc == 0 and "BLOCKED" in out, out
        assert "sb unblock --reason" in out, out      # the escalation names the way out

        rc, out = sb(d, "unblock", "--reason", "the user retracted the claim")
        assert rc == 0, out

        m = json.loads((d / "sourcebook.json").read_text(encoding="utf-8"))
        assert m["revise_count"] == 0 and m["blockers"] == [], m
        assert any("unblocked: the user retracted the claim" in h.get("note", "")
                   for h in m["history"]), m["history"]

        rc, out = sb(d, "status")
        assert rc == 0 and "BLOCKED" not in out, out
        assert "ESCALATE" not in out, out
