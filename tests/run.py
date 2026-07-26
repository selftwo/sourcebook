#!/usr/bin/env python3
"""The acceptance suite. Standard library only, no pytest, no network.

    python3 tests/run.py            # everything
    python3 tests/run.py AT-03      # one case, by id prefix
"""

from __future__ import annotations

import importlib.util
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE / "cases"
sys.path[:0] = [str(HERE), str(CASES)]


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main(argv: list[str]) -> int:
    wanted = [a.upper() for a in argv]
    files = sorted(CASES.glob("AT-*.py"))
    if wanted:
        files = [f for f in files if any(f.name.upper().startswith(w) for w in wanted)]
    if not files:
        print("no matching cases", file=sys.stderr)
        return 1

    passed = failed = 0
    started = time.time()
    for path in files:
        module = load(path)
        tests = [(n, getattr(module, n)) for n in sorted(dir(module)) if n.startswith("test_")]
        for name, fn in tests:
            label = f"{path.stem}  {name.removeprefix('test_')}"
            try:
                fn()
            except Exception:  # noqa: BLE001 - the runner reports, it does not judge
                failed += 1
                print(f"FAIL  {label}")
                print("".join("      " + line for line in
                              traceback.format_exc().splitlines(keepends=True)))
            else:
                passed += 1
                print(f"ok    {label}  {getattr(fn, '__doc__', '') or ''}".rstrip())

    elapsed = time.time() - started
    print(f"\n{passed} passed, {failed} failed in {elapsed:.1f}s")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
