"""Workspace manifest, filesystem-derived state machine, and a small JSON Schema checker.

`sb status` never trusts the stored state. It recomputes from the files on disk, which is
what lets a compacted, crashed, or entirely different agent pick the work up tomorrow.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .ids import CHUNKER_VERSION, INDEXER_VERSION, NORMALIZER_VERSION

MANIFEST_NAME = "sourcebook.json"

STATES = [
    "INIT", "COLLECT", "EXTRACT", "CHUNK", "INDEX", "PLAN", "GROUND",
    "ADJUDICATE", "COMPOSE", "RENDER", "VERIFY", "PACKAGE", "DONE", "REVISE", "BLOCKED",
]

NEXT_COMMAND = {
    "INIT": "sb add <url|file> --tier <A|B|C|D> --reason <why>",
    "COLLECT": "sb extract",
    "EXTRACT": "sb chunk",
    "CHUNK": "sb index",
    "INDEX": "sb plan --type answer --title <title> --thesis <thesis>",
    "PLAN": "sb search \"<query>\"  then  sb find <src_id> \"<sentence>\"  then  sb claim add --file <claim.json>",
    "GROUND": "sb contradictions",
    "ADJUDICATE": "write ledger/adjudications.json for every OPEN cluster",
    "COMPOSE": "compose build/<type>.html from templates/, then sb ledger --html > build/ledger.html && sb inject build/<type>.html --ledger build/ledger.html",
    "RENDER": "sb verify",
    "VERIFY": "sb package --out dist/",
    "PACKAGE": "sb package --out dist/",
    "REVISE": "sb verify",
    "DONE": "nothing; the artifact is built and packaged",
}

ESCALATION = (
    "ESCALATE: three verify loops have failed. Stop revising. Report to the user which "
    "claims and error codes are blocking, and ask how to proceed. Do not loosen a claim "
    "to make a gate pass."
)

ARTIFACT_TYPES = ["answer", "explainer", "deck", "brief", "infographic", "podcast"]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- io


def find_root(start: Path | None = None, explicit: str | None = None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser()
        return p if (p / MANIFEST_NAME).exists() else None
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / MANIFEST_NAME).exists():
            return candidate
    return None


def load(root: Path) -> dict:
    return json.loads((Path(root) / MANIFEST_NAME).read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> None:
    """Atomic, sorted, newline-terminated. Sorted keys are what make AT-02 pass."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def save(root: Path, m: dict) -> None:
    write_json(Path(root) / MANIFEST_NAME, m)


def new_manifest(question: str = "") -> dict:
    return {
        "schema_version": 1,
        "sb_version": __version__,
        "created_at": now(),
        "question": question,
        "state": "INIT",
        "artifact_type": None,
        "revise_count": 0,
        "capabilities": {"web_fetch": "agent", "image_gen": "none", "tts": "none"},
        "config": {"chunk_target": 1600, "chunk_overlap": 240},
        "lint_waivers": {},
        "blockers": [],
        "tool_versions": {
            "normalizer": NORMALIZER_VERSION,
            "chunker": CHUNKER_VERSION,
            "indexer": INDEXER_VERSION,
        },
        "history": [{"state": "INIT", "at": now(), "note": "init"}],
    }


def advance(root: Path, to_state: str, note: str = "") -> dict:
    m = load(root)
    if m.get("state") != to_state or note:
        m["history"].append({"state": to_state, "at": now(), "note": note})
    m["state"] = to_state
    save(root, m)
    return m


# ------------------------------------------------------------------ derived state


def sources(root: Path) -> list[dict]:
    out = []
    sdir = Path(root) / "sources"
    if not sdir.is_dir():
        return out
    for d in sorted(sdir.iterdir()):
        f = d / "source.json"
        if f.is_file():
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                out.append({"id": d.name, "status": "failed", "error": "unparseable source.json"})
    return out


def artifact_paths(root: Path) -> list[Path]:
    build = Path(root) / "build"
    if not build.is_dir():
        return []
    return sorted(p for p in build.glob("*.html") if p.name != "ledger.html")


LEDGER_OPEN = "<!-- SB:LEDGER -->"
LEDGER_CLOSE = "<!-- /SB:LEDGER -->"


def is_injected(path: Path) -> bool:
    """True when the ledger apparatus has been rendered into the artifact."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    a, b = text.find(LEDGER_OPEN), text.find(LEDGER_CLOSE)
    return a != -1 and b > a and 'class="ledger"' in text[a:b]


def derive_state(root: Path) -> str:
    """The files are the truth; the stored state is a hint."""
    root = Path(root)
    m = load(root)
    if m.get("revise_count", 0) >= 3:
        return "BLOCKED"
    if m.get("blockers"):
        return "BLOCKED"

    srcs = sources(root)
    if not srcs:
        return "INIT"

    ready = [s for s in srcs if s.get("status") == "ready"]
    unsettled = [s for s in srcs if s.get("status") in ("pending", "needs_extraction")]
    if unsettled or not ready:
        return "COLLECT"

    chunk_dir = root / "chunks"
    have_chunks = all((chunk_dir / f"{s['id']}.jsonl").is_file() for s in ready)
    if not have_chunks:
        return "EXTRACT"

    if not (root / "index" / "lexical.json").is_file():
        return "CHUNK"

    if not (root / "plan.json").is_file():
        return "INDEX"

    claims = []
    cf = root / "ledger" / "claims.json"
    if cf.is_file():
        try:
            claims = json.loads(cf.read_text(encoding="utf-8")).get("claims", [])
        except json.JSONDecodeError:
            claims = []
    if not claims:
        return "PLAN"

    from .contradict import open_clusters  # local import, avoids a cycle

    if open_clusters(root):
        return "GROUND"

    arts = artifact_paths(root)
    if not arts:
        return "ADJUDICATE"

    if not any(is_injected(p) for p in arts):
        return "COMPOSE"

    if not (root / "build" / "PROVENANCE.json").is_file():
        return "RENDER" if m.get("state") not in ("VERIFY", "PACKAGE", "DONE") else "VERIFY"
    return "DONE"


def status_report(root: Path) -> dict:
    m = load(root)
    state = derive_state(root)
    srcs = sources(root)
    rep = {
        "state": state,
        "stored_state": m.get("state"),
        "question": m.get("question", ""),
        "artifact_type": m.get("artifact_type"),
        "revise_count": m.get("revise_count", 0),
        "sources": len(srcs),
        "sources_ready": sum(1 for s in srcs if s.get("status") == "ready"),
        "blockers": m.get("blockers", []),
        "capabilities": m.get("capabilities", {}),
    }
    if state == "BLOCKED":
        rep["next"] = ESCALATION
    else:
        rep["next"] = NEXT_COMMAND.get(state, "sb status")
    return rep


# -------------------------------------------------------------- schema checking


_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")
_URI = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "number": (int, float), "integer": int, "null": type(None),
}


def _type_ok(value, t: str) -> bool:
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    py = _TYPES.get(t)
    return py is not None and isinstance(value, py)


def validate(instance, schema: dict, pointer: str = "") -> list[tuple[str, str]]:
    """A deliberately small draft-2020-12 subset checker. Returns [(pointer, message)]."""
    errs: list[tuple[str, str]] = []

    if "const" in schema and instance != schema["const"]:
        errs.append((pointer, f"must equal {schema['const']!r}"))

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(instance, t) for t in types):
            errs.append((pointer, f"expected type {'|'.join(types)}, got {type(instance).__name__}"))
            return errs

    if "enum" in schema and instance not in schema["enum"]:
        errs.append((pointer, f"must be one of {schema['enum']}"))

    if isinstance(instance, str):
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errs.append((pointer, f"does not match {schema['pattern']}"))
        fmt = schema.get("format")
        if fmt == "date" and not _DATE.match(instance):
            errs.append((pointer, "not an ISO date (YYYY-MM-DD)"))
        elif fmt == "date-time" and not _DATETIME.match(instance):
            errs.append((pointer, "not an RFC 3339 date-time"))
        elif fmt == "uri" and not _URI.match(instance):
            errs.append((pointer, "not a URI (no scheme)"))
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append((pointer, f"shorter than {schema['minLength']}"))

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append((pointer, f"below minimum {schema['minimum']}"))
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append((pointer, f"above maximum {schema['maximum']}"))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errs.append((pointer, f"needs at least {schema['minItems']} items"))
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errs.append((pointer, f"allows at most {schema['maxItems']} items"))
        if "items" in schema:
            for i, item in enumerate(instance):
                errs += validate(item, schema["items"], f"{pointer}/{i}")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errs.append((pointer, f"missing required property '{key}'"))
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in instance:
                errs += validate(instance[key], sub, f"{pointer}/{key}")
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(props))
            for key in extra:
                errs.append((pointer, f"unexpected property '{key}'"))
        elif isinstance(schema.get("additionalProperties"), dict):
            for key in sorted(set(instance) - set(props)):
                errs += validate(instance[key], schema["additionalProperties"], f"{pointer}/{key}")

    return errs


_SCHEMA_CACHE: dict[str, dict] = {}


def schema_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "schemas"


def load_schema(name: str) -> dict:
    if name not in _SCHEMA_CACHE:
        _SCHEMA_CACHE[name] = json.loads(
            (schema_dir() / f"{name}.schema.json").read_text(encoding="utf-8")
        )
    return _SCHEMA_CACHE[name]


def check(instance, schema_name: str, subject: str) -> list[str]:
    """Validate and return a list of formatted `E-SCHEMA` findings."""
    errs = validate(instance, load_schema(schema_name))
    return [f"E-SCHEMA  {subject}{ptr or '/'}  {msg}" for ptr, msg in errs]
