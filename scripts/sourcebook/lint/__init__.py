"""Design linting: the half of the anti-slop rules a machine can check honestly."""

from .rules import RULES, RULES_VERSION, Finding, lint_file, run  # noqa: F401
