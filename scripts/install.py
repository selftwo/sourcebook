#!/usr/bin/env python3
"""Install the sourcebook skill and command kit into whichever harness is present.

The skill body names no harness-specific tool. It says "run `sb ...`" and "read the file",
never which tool does it. That is the entire portability guarantee, and AT-20 tests it.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

HARNESSES = {
    "claude": {"skill": ".claude/skills/sourcebook", "commands": ".claude/commands"},
    "agents": {"skill": ".agents/skills/sourcebook", "commands": ".agents/commands"},
    "codex": {"skill": ".codex/skills/sourcebook", "commands": ".codex/prompts"},
    "cursor": {"skill": ".cursor/skills/sourcebook", "commands": ".cursor/commands"},
    "hermes": {"skill": ".hermes/skills/sourcebook", "commands": ".hermes/commands"},
}

FORBIDDEN = ["WebFetch", "Bash(", "str_replace", "read_file", "apply_patch", "mcp__"]

KIT = Path(__file__).resolve().parent.parent


def _copy(src: Path, dest: Path, link: bool) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink() or dest.is_file():
        dest.unlink()
    elif dest.is_dir():
        shutil.rmtree(dest)
    if link:
        dest.symlink_to(src.resolve(), target_is_directory=src.is_dir())
    elif src.is_dir():
        shutil.copytree(src, dest)
    else:
        shutil.copy2(src, dest)


def install(harness: str, dest_root: Path, link: bool) -> list[Path]:
    spec = HARNESSES[harness]
    written: list[Path] = []

    skill_dest = dest_root / spec["skill"]
    _copy(KIT / "skills" / "sourcebook", skill_dest, link)
    written.append(skill_dest)

    cmd_dest = dest_root / spec["commands"]
    cmd_dest.mkdir(parents=True, exist_ok=True)
    for cmd in sorted((KIT / "commands").glob("*.md")):
        _copy(cmd, cmd_dest / cmd.name, link)
        written.append(cmd_dest / cmd.name)
    return written


def write_shim(dest_root: Path) -> Path:
    bin_dir = dest_root / ".sourcebook" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    shim = bin_dir / "sb"
    shim.write_text(
        "#!/bin/sh\n"
        f'exec python3 "{KIT / "scripts" / "sb.py"}" "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return shim


def audit_skill(dest_root: Path, harness: str) -> list[str]:
    body = (dest_root / HARNESSES[harness]["skill"] / "SKILL.md").read_text(encoding="utf-8")
    return [token for token in FORBIDDEN if token in body]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="install.py", description=__doc__.splitlines()[0])
    p.add_argument("--harness", default="claude",
                   choices=[*sorted(HARNESSES), "all"])
    p.add_argument("--dest", default=".", help="destination root (default: cwd)")
    p.add_argument("--link", action="store_true",
                   help="symlink instead of copying, for developing the kit itself")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    dest_root = Path(args.dest).expanduser().resolve()
    targets = sorted(HARNESSES) if args.harness == "all" else [args.harness]

    for harness in targets:
        written = install(harness, dest_root, args.link)
        leaks = audit_skill(dest_root, harness)
        if leaks:
            print(f"E-PORTABILITY  {harness}  SKILL.md names harness-specific tools: "
                  f"{', '.join(leaks)}", file=sys.stderr)
            return 2
        print(f"{harness:<7} skill -> {written[0].relative_to(dest_root)}"
              f"   commands -> {written[1].parent.relative_to(dest_root)} ({len(written) - 1} files)")

    shim = write_shim(dest_root)
    print(f"\nsb shim -> {shim}")
    print(f"Add it to PATH:  export PATH=\"{shim.parent}:$PATH\"")
    print("Then, in any directory:  sb init --question \"...\"  &&  sb status")
    return 0


if __name__ == "__main__":
    sys.exit(main())
