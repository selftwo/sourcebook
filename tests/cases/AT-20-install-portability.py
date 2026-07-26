import json

from _common import *  # noqa: F403

HARNESS_DIRS = {
    ".claude": ".claude/commands",
    ".agents": ".agents/commands",
    ".codex": ".codex/prompts",
    ".cursor": ".cursor/commands",
}
FORBIDDEN = ["WebFetch", "Bash(", "str_replace", "read_file", "apply_patch", "mcp__"]


def test_install_all_harnesses():
    """AT-20: one command installs the kit into four harnesses."""
    with tempdir() as d:
        rc, out = _install(d, "all")
        assert rc == 0, out
        for base, cmds in HARNESS_DIRS.items():
            skill = d / base / "skills" / "sourcebook" / "SKILL.md"
            assert skill.is_file(), f"{base}: no SKILL.md"
            assert (d / base / "skills" / "sourcebook" / "reference").is_dir(), base
            assert list((d / cmds).glob("*.md")), f"{base}: no commands in {cmds}"
        assert (d / ".sourcebook" / "bin" / "sb").is_file()


def test_skill_names_no_harness_specific_tool():
    """AT-20: the skill body says `sb ...` and `read the file`, never which tool does it."""
    with tempdir() as d:
        rc, out = _install(d, "all")
        assert rc == 0, out
        for base in HARNESS_DIRS:
            root = d / base / "skills" / "sourcebook"
            for path in sorted(root.rglob("*.md")):
                body = path.read_text(encoding="utf-8")
                for token in FORBIDDEN:
                    assert token not in body, f"{path.relative_to(d)} names {token!r}"


def _install(dest, harness):
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "install.py"),
         "--harness", harness, "--dest", str(dest)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode, r.stdout
