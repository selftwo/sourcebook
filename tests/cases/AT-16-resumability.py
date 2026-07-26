from _common import *  # noqa: F403


def test_status_is_derived_from_the_filesystem():
    """AT-16: deleting index/ mid-run puts status back at CHUNK with `sb index` next."""
    with tempdir() as d:
        bootstrap(d)
        rc, out = sb(d, "status")
        assert rc == 0 and "INDEX" in out, out

        shutil.rmtree(d / "index")
        rc, out = sb(d, "status")
        assert rc == 0, out
        assert "CHUNK" in out, out
        assert "sb index" in out, out

        rc, out = sb(d, "index")
        assert rc == 0, out
        rc, out = sb(d, "status")
        assert "INDEX" in out, out
