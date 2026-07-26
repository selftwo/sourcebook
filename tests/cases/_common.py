"""Every case imports the harness through this shim so `tests/cases/` needs no package."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from harness import *  # noqa: F401,F403,E402
