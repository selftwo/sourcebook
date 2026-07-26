"""sourcebook — deterministic ingest, search, ledger, and gates for claim-cited artifacts.

Nothing in this package calls a model, opens a socket to a model provider, or reasons.
It fetches, hashes, chunks, ranks, compares strings, and returns exit codes.
"""

__version__ = "0.1.0"

# Exit codes are the API.
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_GATE = 2
