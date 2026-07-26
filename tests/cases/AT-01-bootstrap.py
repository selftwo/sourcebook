from _common import *  # noqa: F403


def test_zero_dependency_bootstrap():
    """AT-01: stdlib-only, no network, init through index exits 0."""
    with tempdir() as d:
        init(d)
        add_corpus(d)
        for cmd in (["extract"], ["chunk"], ["index"]):
            rc, out = sb(d, *cmd)
            assert rc == 0, f"`sb {' '.join(cmd)}` exited {rc}:\n{out}"
        assert (d / "index" / "lexical.json").is_file()
        rc, out = sb(d, "search", "interoperability live partner")
        assert rc == 0 and "src_" in out, out


def test_no_third_party_imports():
    """AT-01: no gate-blocking path imports a third-party package."""
    allowed = {"sourcebook", "pypdf"}
    import ast

    for path in (ROOT / "scripts").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for n in names:
                assert n in allowed or n in sys.stdlib_module_names, \
                    f"{path.name} imports third-party module {n!r}"
