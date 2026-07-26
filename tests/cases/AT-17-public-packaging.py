import json

from _common import *  # noqa: F403

MAX_WORDS, MAX_CHARS = 25, 200


def test_public_package_redacts_and_still_verifies():
    """AT-17: --public keeps every citation checkable without republishing the source."""
    with tempdir() as d:
        full_build(d)
        rc, out = sb(d, "verify")
        assert rc == 0, out

        rc, out = sb(d, "package", "--public", "--out", "dist")
        assert rc == 0, out
        ledger = json.loads((d / "dist" / "ledger.json").read_text(encoding="utf-8"))
        assert ledger["visibility"] == "public"
        for c in ledger["ledger"]:
            for e in c.get("evidence", []):
                q = e.get("quote")
                if q is None:
                    assert e["quote_sha256"] and e["length"] >= 0, e
                else:
                    assert len(q) <= MAX_CHARS and len(q.split()) <= MAX_WORDS, e
        assert not (d / "dist" / "sources").exists(), "public package shipped normalized.md"
        assert (d / "dist" / "SHA256SUMS").is_file()

        rc, out = sb(d, "package", "--out", "dist", "--verify")
        assert rc == 0, out
        assert "byte-exact" in out, out


def test_public_package_includes_inferences_and_a_completed_gate_report():
    """Public provenance and the sidecar ledger must describe the artifact completely."""
    with tempdir() as d:
        full_build(d)
        inferred_id = add_claim(d, {
            "text": "This is an explicitly labelled editorial synthesis.",
            "topic_key": "fixture.synthesis", "kind": "interpretation",
            "confidence": "inferred", "evidence": [],
            "notes": "No source; author's synthesis.",
        })
        rc, report = sb(d, "verify", "--json")
        assert rc == 0, report
        (d / "build" / "verify.json").write_text(report, encoding="utf-8")

        rc, out = sb(d, "package", "--public", "--out", "dist")
        assert rc == 0, out
        ledger = json.loads((d / "dist" / "ledger.json").read_text(encoding="utf-8"))
        assert inferred_id in {c["id"] for c in ledger["ledger"]}
        prov = json.loads((d / "dist" / "PROVENANCE.json").read_text(encoding="utf-8"))
        assert prov["claims"] == len(ledger["ledger"])
        assert prov["gate_report"]["pass"] is True
        assert (d / "dist" / "verify.json").is_file()


def test_public_package_withholds_local_locators_and_uninjected_templates():
    """Public packages should not expose workspace names or ship dangling source templates."""
    with tempdir() as d:
        full_build(d)
        (d / "build" / "index.src.html").write_text(
            '<a href="#c-missing">dangling before injection</a>', encoding="utf-8")
        (d / "build" / "ledger.fragment.html").write_text(
            '<div id="c-present">ledger</div>', encoding="utf-8")
        rc, out = sb(d, "package", "--public", "--out", "dist")
        assert rc == 0, out
        assert not (d / "dist" / "index.src.html").exists()
        assert not (d / "dist" / "ledger.fragment.html").exists()
        prov = json.loads((d / "dist" / "PROVENANCE.json").read_text(encoding="utf-8"))
        assert all(s["locator"] is None and s["canonical_locator"] is None
                   for s in prov["sources"])


def test_private_package_ships_the_sources():
    """AT-17: the private default keeps normalized.md so a teammate can re-verify offline."""
    with tempdir() as d:
        full_build(d)
        rc, out = sb(d, "package", "--out", "dist")
        assert rc == 0, out
        assert (d / "dist" / "sources").is_dir()
        assert (d / "dist" / "PROVENANCE.json").is_file()
        prov = json.loads((d / "dist" / "PROVENANCE.json").read_text(encoding="utf-8"))
        assert len(prov["sources"]) == 3
        assert all(s["tier_reason"] for s in prov["sources"])
