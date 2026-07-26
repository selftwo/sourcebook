import json

from _common import *  # noqa: F403


def test_normalizer_drift_is_never_silent():
    """AT-18: a bumped normalizer_version invalidates the offsets and says so."""
    with tempdir() as d:
        bootstrap(d)
        seed_claims(d)
        rc, out = sb(d, "verify")
        assert rc == 0, out

        sid = source_ids(d)["operator-status.md"]
        meta = d / "sources" / sid / "source.json"
        rec = json.loads(meta.read_text(encoding="utf-8"))
        rec["normalizer_version"] = 2
        meta.write_text(json.dumps(rec), encoding="utf-8")

        rc, out = sb(d, "verify")
        assert rc == 2, out
        assert "E-NORM-DRIFT" in out and sid in out, out


def test_edited_normalized_text_is_caught():
    """AT-18: editing normalized.md after the fact is drift, not an update."""
    with tempdir() as d:
        bootstrap(d)
        seed_claims(d)
        sid = source_ids(d)["operator-status.md"]
        path = d / "sources" / sid / "normalized.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nAn appended line.\n",
                        encoding="utf-8")
        rc, out = sb(d, "verify")
        assert rc == 2 and "E-NORM-DRIFT" in out, out
