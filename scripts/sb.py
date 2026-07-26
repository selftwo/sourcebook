#!/usr/bin/env python3
"""sb — the sourcebook CLI. Dispatch only; every behaviour lives in the package.

Exit codes are the API: 0 pass, 1 usage or input error, 2 gate failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sourcebook import EXIT_GATE, EXIT_OK, EXIT_USAGE, __version__  # noqa: E402
from sourcebook import chunk as chunk_mod  # noqa: E402
from sourcebook import collect, contradict, extract, index, ledger, licenses, manifest  # noqa: E402
from sourcebook import package as package_mod  # noqa: E402
from sourcebook import search as search_mod  # noqa: E402
from sourcebook import tts, verify as verify_mod  # noqa: E402
from sourcebook.lint import rules as lint_rules  # noqa: E402

COMMANDS = [
    "init", "config", "add", "extract", "chunk", "index", "search", "find", "quote",
    "claim", "adjudicate", "contradictions", "ledger", "plan", "inject", "lint",
    "verify", "licenses", "tts-plan", "package", "status", "template",
]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sb", description=__doc__.splitlines()[0])
    p.add_argument("--version", action="version", version=f"sourcebook {__version__}")
    p.add_argument("--dir", help="workspace directory (default: walk up for sourcebook.json)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--dir", dest="dir_sub", help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd", metavar="COMMAND")

    def add(name, **kw):
        return sub.add_parser(name, parents=[common], **kw)

    s = add("init", help="create a workspace")
    s.add_argument("--question", default="", help="the question this workspace answers")
    s.add_argument("--from", dest="from_dir", help="seed sources from a frozen capture")

    s = add("config", help="read or set workspace configuration")
    s.add_argument("action", choices=["get", "set", "list"])
    s.add_argument("expr", nargs="?", help="key or key=value, dotted")

    s = add("add", help="collect a source")
    s.add_argument("locators", nargs="*")
    s.add_argument("--tier", required=True, choices=["A", "B", "C", "D"])
    s.add_argument("--reason", required=True, help="why this tier; recorded, not decorative")
    s.add_argument("--title"), s.add_argument("--author"), s.add_argument("--publisher")
    s.add_argument("--published"), s.add_argument("--lang"), s.add_argument("--license")
    s.add_argument("--text", help="add pasted text directly")
    s.add_argument("--stdin", action="store_true", help="add text from stdin")

    s = add("extract", help="normalize every collected source")
    s.add_argument("--force", action="store_true", help="rewrite normalized.md (invalidates offsets)")

    s = add("chunk", help="deterministic heading-aware chunking")
    s.add_argument("--target", type=int), s.add_argument("--overlap", type=int)

    add("index", help="build the BM25 lexical index")

    s = add("search", help="rank chunks against a query")
    s.add_argument("query")
    s.add_argument("-k", type=int, default=8), s.add_argument("--source")
    s.add_argument("--json", action="store_true")

    s = add("find", help="turn a pasted sentence into a byte span")
    s.add_argument("source_id"), s.add_argument("text")
    s.add_argument("--all", action="store_true")

    s = add("quote", help="print the exact slice at a span")
    s.add_argument("source_id"), s.add_argument("start", type=int), s.add_argument("end", type=int)

    s = add("claim", help="write to the claim ledger")
    s.add_argument("action", choices=["add", "list", "set", "import"])
    s.add_argument("claim_id", nargs="?")
    s.add_argument("--json", dest="json_text", help="a claim object as JSON")
    s.add_argument("--file", help="read the claim (or {claims:[...]}) from a file")
    s.add_argument("--stdin", action="store_true", help="read the claim JSON from stdin")
    s.add_argument("--status", choices=["active", "superseded", "retracted"])
    s.add_argument("--confidence")
    s.add_argument("--superseded-by", dest="superseded_by")
    s.add_argument("--notes")

    s = add("adjudicate", help="record a contradiction outcome")
    s.add_argument("--json", dest="json_text"), s.add_argument("--file")
    s.add_argument("--stdin", action="store_true")
    s.add_argument("--apply", action="store_true",
                   help="apply the mechanical consequences to claim statuses")

    s = add("contradictions", help="detect contradiction candidates")
    s.add_argument("--json", action="store_true"), s.add_argument("--strict", action="store_true")

    s = add("ledger", help="render the citation apparatus")
    g = s.add_mutually_exclusive_group()
    for fmt in ("html", "md", "json", "sources"):
        g.add_argument(f"--{fmt}", dest="fmt", action="store_const", const=fmt)
    s.add_argument("--out", help="write to a file instead of stdout")

    s = add("plan", help="scaffold or inspect plan.json")
    s.add_argument("--type", dest="ptype", choices=manifest.ARTIFACT_TYPES)
    s.add_argument("--title"), s.add_argument("--thesis"), s.add_argument("--audience")
    s.add_argument("--images", choices=["none", "source", "generate"], default="none")
    s.add_argument("--show", action="store_true")

    s = add("inject", help="render the ledger into an artifact")
    s.add_argument("html"), s.add_argument("--ledger", dest="ledger_file", required=True)

    s = add("lint", help="run the design rule registry")
    s.add_argument("html"), s.add_argument("--json", action="store_true")

    s = add("verify", help="the ship gate")
    s.add_argument("--html"), s.add_argument("--artifact", choices=manifest.ARTIFACT_TYPES)
    s.add_argument("--podcast", action="store_true"), s.add_argument("--json", action="store_true")

    s = add("licenses", help="check asset provenance and attribution")
    s.add_argument("--html")

    s = add("tts-plan", help="emit a provider-agnostic synthesis plan")
    s.add_argument("--voices")

    s = add("package", help="checksums, provenance, and the public/private split")
    s.add_argument("--out", default="dist")
    s.add_argument("--public", action="store_true"), s.add_argument("--private", action="store_true")
    s.add_argument("--verify", dest="do_verify", action="store_true")

    s = add("status", help="derived state and the single next command")
    s.add_argument("--json", action="store_true")

    s = add("template", help="copy a starting template into build/")
    s.add_argument("ttype", choices=["answer", "explainer", "deck", "brief", "infographic", "podcast"])
    s.add_argument("--out")
    return p


def kit_root() -> Path:
    return Path(__file__).resolve().parent.parent


def workspace_arg(args) -> str | None:
    return args.dir or getattr(args, "dir_sub", None)


def resolve_root(args) -> Path | None:
    return manifest.find_root(explicit=workspace_arg(args))


def _read_json_arg(args) -> tuple[object | None, str]:
    if getattr(args, "json_text", None):
        return json.loads(args.json_text), ""
    if getattr(args, "file", None):
        return json.loads(Path(args.file).read_text(encoding="utf-8")), ""
    if getattr(args, "stdin", False):
        return json.loads(sys.stdin.read()), ""
    return None, "provide the object with --file (preferred), --stdin, or --json"


def cmd_init(args) -> int:
    target_dir = workspace_arg(args)
    root = Path(target_dir).expanduser() if target_dir else Path.cwd()
    root.mkdir(parents=True, exist_ok=True)
    target = root / manifest.MANIFEST_NAME
    if target.exists():
        print(f"workspace already exists at {target}")
    else:
        manifest.save(root, manifest.new_manifest(args.question))
        for d in ("sources", "chunks", "index", "ledger", "assets", "build"):
            (root / d).mkdir(exist_ok=True)
        print(f"initialized {target}")
    if args.from_dir:
        rc = collect.seed_from(root, Path(args.from_dir))
        if rc != EXIT_OK:
            return rc
    print(f"next: {manifest.status_report(root)['next']}")
    return EXIT_OK


def cmd_config(root: Path, args) -> int:
    m = manifest.load(root)
    if args.action == "list" or (args.action == "get" and not args.expr):
        print(json.dumps({"capabilities": m["capabilities"], "config": m["config"],
                          "lint_waivers": m.get("lint_waivers", {})}, indent=2))
        return EXIT_OK
    if not args.expr:
        print("usage: sb config {get|set} <key[=value]>", file=sys.stderr)
        return EXIT_USAGE
    key, _, value = args.expr.partition("=")
    parts = key.split(".")
    node = m
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    if args.action == "get":
        print(json.dumps(node.get(parts[-1])))
        return EXIT_OK
    if value in ("true", "false"):
        parsed: object = value == "true"
    elif value.lstrip("-").isdigit():
        parsed = int(value)
    else:
        parsed = value
    node[parts[-1]] = parsed
    errs = manifest.check(m, "manifest", "sourcebook.json")
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return EXIT_USAGE
    manifest.save(root, m)
    print(f"{key} = {json.dumps(parsed)}")
    return EXIT_OK


def cmd_claim(root: Path, args) -> int:
    if args.action == "list":
        claims = ledger.load_claims(root)
        ordinals = ledger.resolve_ordinals(root)
        for c in sorted(claims, key=lambda c: ordinals.get(c["id"], 999)):
            n = ordinals.get(c["id"])
            print(f"{('[' + str(n) + ']') if n else '[-]':>5} {c['id']}  {c['confidence']:<11} "
                  f"{c['status']:<10} {c['topic_key']}")
            print(f"       {c['text'][:110]}")
        return EXIT_OK
    if args.action == "set":
        if not args.claim_id:
            print("usage: sb claim set <claim_id> --status ...", file=sys.stderr)
            return EXIT_USAGE
        rc, msg = ledger.set_claim(root, args.claim_id, status=args.status,
                                   confidence=args.confidence,
                                   superseded_by=args.superseded_by, notes=args.notes)
        print(msg, file=sys.stderr if rc else sys.stdout)
        return rc
    obj, err = _read_json_arg(args)
    if obj is None:
        print(f"usage: sb claim {args.action} --file <claim.json>   ({err})", file=sys.stderr)
        return EXIT_USAGE
    items = obj["claims"] if isinstance(obj, dict) and "claims" in obj else (
        obj if isinstance(obj, list) else [obj])
    rc_final = EXIT_OK
    for item in items:
        rc, msg = ledger.add_claim(root, item)
        print(msg if rc else f"claim {msg}", file=sys.stderr if rc else sys.stdout)
        rc_final = rc or rc_final
    return rc_final


def cmd_adjudicate(root: Path, args) -> int:
    if args.apply and not (args.json_text or args.file or args.stdin):
        changed = contradict.apply_outcomes(root)
        print(f"applied outcomes; {len(changed)} claim(s) changed"
              + (": " + ", ".join(changed) if changed else ""))
        return EXIT_OK
    obj, err = _read_json_arg(args)
    if obj is None:
        print(f"usage: sb adjudicate --file <adjudication.json>   ({err})", file=sys.stderr)
        return EXIT_USAGE
    items = obj["adjudications"] if isinstance(obj, dict) and "adjudications" in obj else (
        obj if isinstance(obj, list) else [obj])
    existing = {a["cluster_id"]: a for a in ledger.load_adjudications(root)}
    for item in items:
        item.setdefault("decided_at", manifest.now())
        existing[item["cluster_id"]] = item
    payload = {"schema_version": 1, "adjudications": list(existing.values())}
    errs = manifest.check(payload, "adjudication", "ledger/adjudications.json")
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return EXIT_USAGE
    ledger.save_adjudications(root, list(existing.values()))
    print(f"recorded {len(items)} adjudication(s)")
    if args.apply:
        changed = contradict.apply_outcomes(root)
        print(f"applied outcomes; {len(changed)} claim(s) changed")
    manifest.advance(root, "ADJUDICATE", f"{len(items)} adjudication(s)")
    return EXIT_OK


def cmd_plan(root: Path, args) -> int:
    path = root / "plan.json"
    if args.show or not args.ptype:
        if not path.is_file():
            print("no plan.json yet", file=sys.stderr)
            return EXIT_USAGE
        sys.stdout.write(path.read_text(encoding="utf-8"))
        return EXIT_OK
    plan = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    plan.update({
        "schema_version": 1,
        "type": args.ptype,
        "title": args.title or plan.get("title") or manifest.load(root).get("question") or args.ptype,
        "thesis": args.thesis or plan.get("thesis", "TODO: one sentence a reader could act on."),
        "audience": args.audience or plan.get("audience", ""),
        "register": plan.get("register", "editorial"),
        "images": plan.get("images", {"mode": args.images, "slots": []}),
        "constraints": plan.get("constraints",
                                {"palette_strategy": "committed", "motion": "minimal",
                                 "breakpoints": [360, 768, 1200]}),
        "sections": plan.get("sections", [
            {"id": "answer", "heading": "The short answer",
             "intent": "state the finding and its date", "claim_ids": []}]),
    })
    manifest.write_json(path, plan)
    m = manifest.load(root)
    m["artifact_type"] = args.ptype
    manifest.save(root, m)
    errs = manifest.check(plan, "plan", "plan.json")
    for e in errs:
        print(e, file=sys.stderr)
    print(f"wrote plan.json (type={args.ptype}). Fill in sections[].claim_ids as you ground claims.")
    return EXIT_USAGE if errs else EXIT_OK


def cmd_status(root: Path, args) -> int:
    rep = manifest.status_report(root)
    if args.json:
        print(json.dumps(rep, indent=2))
        return EXIT_OK
    print(f"state      {rep['state']}"
          + ("" if rep["state"] == rep["stored_state"] else f"   (stored: {rep['stored_state']})"))
    if rep["question"]:
        print(f"question   {rep['question']}")
    print(f"sources    {rep['sources_ready']}/{rep['sources']} ready")
    if rep["artifact_type"]:
        print(f"artifact   {rep['artifact_type']}")
    if rep["revise_count"]:
        print(f"revisions  {rep['revise_count']}/3")
    for b in rep["blockers"]:
        print(f"blocker    {b}")
    print(f"next       {rep['next']}")
    return EXIT_OK


def cmd_template(root: Path, args) -> int:
    src = kit_root() / "templates" / (
        f"{args.ttype}.html" if args.ttype != "podcast" else "podcast.html")
    if not src.is_file():
        print(f"E-TEMPLATE  {src}  no such template", file=sys.stderr)
        return EXIT_USAGE
    dest = Path(args.out) if args.out else root / "build" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"copied {src.name} -> {dest}")
    print("Design past it. The lint gate is what keeps that from drifting into slop.")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    if not args.cmd:
        parser.print_help()
        return EXIT_USAGE

    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "lint":
        waivers = {}
        maybe_root = resolve_root(args)
        if maybe_root:
            waivers = manifest.load(maybe_root).get("lint_waivers", {})
        return lint_rules.lint_file(Path(args.html), waivers, args.json)

    root = resolve_root(args)
    if root is None:
        print("E-NOWORKSPACE  .  no sourcebook.json here or above; run `sb init`", file=sys.stderr)
        return EXIT_USAGE

    if args.cmd == "config":
        return cmd_config(root, args)
    if args.cmd == "add":
        return collect.add(root, args)
    if args.cmd == "extract":
        return extract.extract(root, args.force)
    if args.cmd == "chunk":
        return chunk_mod.chunk(root, args.target, args.overlap)
    if args.cmd == "index":
        return index.build(root)
    if args.cmd == "search":
        return search_mod.search(root, args.query, args.k, args.source, args.json)
    if args.cmd == "find":
        return search_mod.find(root, args.source_id, args.text, args.all)
    if args.cmd == "quote":
        return search_mod.quote(root, args.source_id, args.start, args.end)
    if args.cmd == "claim":
        return cmd_claim(root, args)
    if args.cmd == "adjudicate":
        return cmd_adjudicate(root, args)
    if args.cmd == "contradictions":
        return contradict.report(root, args.json, args.strict)
    if args.cmd == "ledger":
        return ledger.ledger_cmd(root, args.fmt or "html", args.out)
    if args.cmd == "plan":
        return cmd_plan(root, args)
    if args.cmd == "inject":
        return ledger.inject(Path(args.html), Path(args.ledger_file))
    if args.cmd == "verify":
        return verify_mod.verify(root, args.html, args.artifact, args.podcast, args.json)
    if args.cmd == "licenses":
        return licenses.licenses_cmd(root, args.html)
    if args.cmd == "tts-plan":
        return tts.tts_plan(root, args.voices)
    if args.cmd == "package":
        return package_mod.package(root, args.out, args.public and not args.private, args.do_verify)
    if args.cmd == "status":
        return cmd_status(root, args)
    if args.cmd == "template":
        return cmd_template(root, args)
    parser.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:  # pragma: no cover - piping into head
        sys.exit(EXIT_OK)
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit(EXIT_USAGE)
