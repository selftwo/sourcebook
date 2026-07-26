# sourcebook — Build Plan

Companion to [SPEC.md](SPEC.md). This is the implementation order, the algorithms that must be exact,
and the checkpoint at the end of each milestone. Target: one pass, ~2,000 lines of Python, zero
required dependencies.

## Ground rules for the implementer

1. **Standard library only** on every gate-blocking path. `urllib`, `html.parser`, `json`, `hashlib`,
   `unicodedata`, `re`, `argparse`, `pathlib`, `math`. Optional imports go behind
   `try: import pypdf except ImportError: pypdf = None` and degrade to `status: needs_extraction`.
2. **No script calls a model. Ever.** If you find yourself wanting to, that work belongs in
   `skills/sourcebook/reference/`.
3. **Every algorithm below is versioned.** Changing one bumps its version constant and the verifier
   reports drift rather than silently accepting stale artifacts.
4. **Exit codes are the API.** `0` pass, `1` usage/input error, `2` gate failure. Gate failures print
   one line per finding: `ERROR_CODE  <subject>  <message>`.
5. **Write the acceptance test with the feature, not after.** Each milestone lists the AT ids it must
   turn green.

---

## Milestone map

| M | Scope | New files | LOC | Turns green |
|---|---|---|---|---|
| **M0** | Skeleton, schemas, manifest, state machine, `status` | `sb.py`, `manifest.py`, `ids.py`, `schemas/*` | ~350 | AT-16 |
| **M1** | Collect, extract, chunk, index, search, find, quote | `collect.py`, `extract.py`, `chunk.py`, `index.py`, `search.py` | ~550 | AT-01, AT-02, AT-04, AT-18 |
| **M2** | Claims, ledger, contradictions, verify core | `ledger.py`, `contradict.py`, `verify.py` | ~500 | AT-03, AT-05, AT-07, AT-08, AT-09 |
| **M3** | Lint: CSS tokenizer, color math, rule registry | `lint/*` | ~450 | AT-10, AT-11, AT-12 |
| **M4** | Templates, `inject`, HTML verification | `templates/*`, verify HTML pass | ~250 | AT-06, AT-13 |
| **M5** | Assets, credits, licenses | `licenses.py` | ~120 | AT-14 |
| **M6** | Podcast script verify, tts-plan | `tts.py` | ~120 | AT-15 |
| **M7** | Package, install, skill, commands, demo | `package.py`, `install.py`, `skills/`, `commands/` | ~300 | AT-17, AT-19, AT-20 |

Build strictly in order. Each milestone leaves the tree working and its ATs passing.

---

## M0 — Skeleton and state

### `scripts/sb.py`

Dispatch only. No logic.

```python
COMMANDS = {
  "init", "config", "add", "extract", "chunk", "index", "search", "find", "quote",
  "claim", "contradictions", "ledger", "plan", "inject", "lint", "verify",
  "licenses", "tts-plan", "package", "status",
}
def main(argv) -> int:   # resolves workspace root by walking up for sourcebook.json
```

Workspace resolution: walk up from `cwd` looking for `sourcebook.json`, or use `--dir`. Fail with
exit 1 and a message naming `sb init` if none found.

### `sourcebook/ids.py`

```python
NORMALIZER_VERSION = 1
CHUNKER_VERSION = 1
INDEXER_VERSION = 1

def canonical_locator(kind: str, locator: str, root: Path) -> str
def src_id(canonical: str, raw_sha256: str) -> str      # "src_" + sha256(f"{canonical}\n{raw}")[:12]
def chunk_id(src: str, ordinal: int) -> str             # f"{src}#c{ordinal:04d}"
def claim_id(text: str) -> str                          # "clm_" + sha256(norm_ws(text).lower())[:12]
def cluster_id(topic_key: str) -> str                   # "cls_" + sha256(topic_key)[:12]
def norm_ws(s: str) -> str                              # collapse all whitespace runs to one space, strip
def sha256_file(p: Path) -> str
def sha256_text(s: str) -> str                          # over UTF-8 bytes
```

URL canonicalization, exactly:
lowercase scheme and host, drop `:80` on http and `:443` on https, drop the fragment, drop query params
matching `^(utm_.*|gclid|fbclid|mc_[ce]id|ref|si|igshid)$`, sort remaining params by key then value,
preserve path case, strip a single trailing `/` only when the path is exactly `/`.

### `sourcebook/manifest.py`

```python
STATES = ["INIT","COLLECT","EXTRACT","CHUNK","INDEX","PLAN","GROUND",
          "ADJUDICATE","COMPOSE","RENDER","VERIFY","PACKAGE","DONE","REVISE","BLOCKED"]

NEXT_COMMAND = {          # what `sb status` tells the agent to run
  "INIT": "sb add <url|file> --tier <A|B|C|D> --reason <why>",
  "COLLECT": "sb extract",
  "EXTRACT": "sb chunk",
  ...
  "GROUND": "sb contradictions",
  "ADJUDICATE": "write ledger/adjudications.json for every OPEN cluster",
  "COMPOSE": "sb ledger --html > build/ledger.html && sb inject <artifact>",
  "RENDER": "sb verify",
}

def load(root) -> dict
def save(root, m) -> None                     # atomic: write .tmp, fsync, rename
def advance(root, to_state, note="") -> None  # appends {state, at, note} to history
def gate_report(root) -> dict                 # recomputed, never trusted from disk
```

**`sb status` derives state from the filesystem, it does not trust the stored value.** If
`index/lexical.json` is missing, the state is `CHUNK` regardless of what the manifest says. The stored
state is a hint; the files are the truth. This is what makes AT-16 pass and what makes the kit survive
a crashed or compacted agent.

### Schema validation

Write ~90 lines in `manifest.py` covering the draft 2020-12 subset actually used: `type`, `required`,
`enum`, `pattern`, `properties`, `additionalProperties`, `items`, `minItems`, `minimum`, `const`,
`format` for `date` (`^\d{4}-\d{2}-\d{2}$`), `date-time` (RFC 3339 Z), and `uri` (scheme present).
Do not vendor a validator library. Errors accumulate into a list of `(json_pointer, message)`.

**Checkpoint M0:** `sb init` creates a valid workspace. `sb status` on an empty one prints
`INIT → next: sb add …`. AT-16 passes.

---

## M1 — Ingestion pipeline

### `collect.py` — `sb add`

```
sb add <locator>... --tier {A,B,C,D} --reason TEXT [--title T] [--published DATE] [--lang L]
sb add --text "…" --title T --tier D --reason "pasted by user"
sb add --stdin --title T --tier ...
```

For each locator:
1. `url` → fetch with `urllib.request`, 20s timeout, a real UA string, follow ≤ 5 redirects,
   cap at 25 MB. On any failure write `source.json` with `status: failed` and the reason, exit 1 at
   the end but keep the successful ones. If `capabilities.web_fetch == "agent"`, skip the fetch and
   write `status: pending` with instructions for the agent to save bytes to `raw.<ext>` and re-run.
2. `file` → copy to `raw.<ext>`, record the original path.
3. Compute `raw_sha256`, derive `src_id`, write `sources/<src_id>/source.json`.

`--tier` and `--reason` are required. Refuse to add a source without a stated tier reason; this is the
single cheapest guard against an undifferentiated corpus.

Duplicate `src_id` → update the existing record's `retrieved_at`, do not create a second directory.

### `extract.py` — `sb extract`

Per source with `status in {pending, needs_extraction}` and a present `raw.*`:

| media type | Path |
|---|---|
| `text/markdown`, `text/plain` | decode and normalize directly |
| `text/html` | stdlib `HTMLParser` reader (below) |
| `application/pdf` | `pypdf` if importable, else `status: needs_extraction` |
| anything else | `status: needs_extraction` |

**HTML reader** (~120 lines, no BeautifulSoup):
- Drop `script`, `style`, `noscript`, `svg`, `nav`, `footer`, `aside`, `form`, and any element whose
  `class` or `id` matches `(nav|menu|sidebar|cookie|banner|promo|share|related|comment|subscribe)`.
- Prefer the subtree of `<article>`, `<main>`, or `[role=main]` when present; otherwise the `<body>`
  descendant with the highest text-character count among `div`/`section` candidates.
- Emit Markdown: `h1..h6` → `#`..`######`, `p` → paragraph, `li` → `- ` (ordered → `1. `),
  `blockquote` → `> `, `pre`/`code` → fenced, `a` → `[text](href)` with absolute URLs,
  `table` → GFM pipe table, `br` → newline. Collapse inline whitespace, keep block boundaries.
- Extract `<title>`, `<meta name=author>`, `article:published_time` / `<time datetime>` into
  `source.json` when the fields are still null.

**Normalization** (`normalize(text) -> str`), exactly as SPEC §3, in this order: decode with
`errors="replace"` → `unicodedata.normalize("NFC", s)` → `\r\n|\r` → `\n` → strip trailing whitespace
per line → `re.sub(r"\n{3,}", "\n\n", s)` → ensure one trailing `\n`.

Write `normalized.md`, record `normalized_sha256` and `normalizer_version`, set `status: ready`.
**Never rewrite an existing `normalized.md`** whose hash already matches; if it exists and the hash
differs, that is `E-NORM-DRIFT`, not a silent overwrite.

### `chunk.py` — `sb chunk [--target 1600] [--overlap 240]`

Deterministic, heading-aware, offset-emitting. `CHUNKER_VERSION = 1`.

```
1. Scan normalized.md for headings: ^(#{1,3})\s+(.+)$  (MULTILINE), recording char offsets.
   Maintain heading_path as a list of the active h1/h2/h3 titles.
2. Split the text into blocks at blank-line boundaries, keeping exact [start,end) offsets.
   A heading line is its own block and forces a new chunk.
3. Greedily pack blocks into a chunk until adding the next block would exceed `target` chars.
4. A single block longer than `target` is split on sentence boundaries `(?<=[.!?])\s+`;
   if still too long, hard-split at `target` on the nearest preceding whitespace.
5. Overlap: each chunk after the first begins `overlap` chars earlier, snapped BACKWARD to the
   nearest whitespace boundary. Overlap never crosses a heading boundary.
6. A trailing chunk shorter than 120 chars merges into its predecessor.
7. Emit one JSON line per chunk: {chunk_id, ordinal, start, end, heading_path}.
```

Invariants asserted in code: offsets are non-decreasing; `start < end <= len(text)`; the union of
non-overlap spans covers `[0, len(text))` with no gap. A violated invariant is a crash, not a warning.

### `index.py` — `sb index`

Pure-Python BM25. `INDEXER_VERSION = 1`.

```
tokenize(s):  unicodedata NFKD → casefold → re.findall(r"[a-z0-9]+") → drop STOPWORDS (≈40 words)
              → drop tokens of length 1. No stemming (deterministic and language-agnostic).
BM25: k1 = 1.2, b = 0.75, idf = ln(1 + (N - df + 0.5) / (df + 0.5))
```

`index/lexical.json`:
```json
{ "version": 1, "n_docs": 412, "avgdl": 231.4,
  "postings": { "duitnow": [["src_9f2a…#c0031", 4], …] },
  "doclen": { "src_9f2a…#c0031": 240 } }
```

Sort postings by chunk id, and dict keys sorted on dump (`sort_keys=True`, `separators=(",",":")`),
so the file is byte-identical across runs. That is AT-02.

### `search.py` — `sb search`, `sb find`, `sb quote`

```
sb search "<query>" [-k 8] [--source src_…] [--json]
  → rank  chunk_id  score  heading_path  first-160-chars-of-span

sb find <src_id> "<exact text>" [--all]
  → src_id  START..END  exact  (n matches)
  Uses str.find on normalized.md. On zero matches: normalize whitespace in BOTH the needle and a
  working copy of the haystack, retry, and if that hits, report the ORIGINAL offsets of the matched
  region plus a `whitespace-normalized` note. On still-zero: print the three highest-BM25 chunks in
  that source as anchors and exit 1. Never return an approximate span.

sb quote <src_id> <start> <end>
  → the exact slice, for the agent to copy verbatim into a claim
```

`sb find` is the ergonomic centre of the whole kit. The agent pastes a sentence it just read and gets
a verifiable span. It never computes an offset, so it never gets one wrong.

**Checkpoint M1:** AT-01, AT-02, AT-04, AT-18 pass. `sb search` returns sane hits on the fixture corpus.

---

## M2 — Ledger and the gate

### `ledger.py`

```python
def add_claim(root, obj) -> str          # validates, derives claim_id, idempotent on re-add
def load_claims(root) -> list[dict]
def resolve_ordinals(root) -> dict       # claim_id -> int, by plan.json section order, then claim_id
def verify_evidence(root, claim) -> list[Finding]   # the byte-exact check
def render_html(root) -> str             # <ol class="ledger"> with id="c-{claim_id}"
def render_md(root) -> str
def render_sources(root) -> str          # grouped by source, tier badges
```

`verify_evidence` is four lines and is the most important function in the codebase:

```python
text = (root / "sources" / e["source_id"] / "normalized.md").read_text(encoding="utf-8")
if text[e["start"]:e["end"]] != e["quote"]:
    yield Finding("E-QUOTE-MISMATCH", claim["id"], f"{e['source_id']}[{e['start']}:{e['end']}]")
```

### `contradict.py` — `sb contradictions [--json]`

Group `active` claims by `topic_key`. Within each group flag on any of the five detectors in SPEC §7.

```python
NEGATIONS = {"not","no","never","cannot","can't","without","fails","lacks","absent","excludes"}
def leading_number(text) -> float | None   # first \d[\d,]*\.?\d* with k/m/bn/% suffix expansion
def numeric_conflict(a, b, tol=0.05) -> bool
def date_conflict(a, b) -> bool
def polarity_conflict(a, b) -> bool        # negation token in exactly one, within the same clause
def recency_spread(a, b, days=180) -> bool
```

Output: one line per cluster, `OPEN` or `RESOLVED <outcome>`. Exit 2 if any cluster is `OPEN` and
`--strict` is set (which `sb verify` uses).

### `verify.py` — `sb verify`

Runs every gate in order and prints a section per gate. Exit 2 on any error, 0 otherwise.

| Gate | Checks | Codes |
|---|---|---|
| schemas | manifest, every source.json, claims, adjudications, plan | `E-SCHEMA` |
| normalizer | every source's `normalizer_version` and `normalized_sha256` still match | `E-NORM-DRIFT` |
| quotes | byte-exact for every evidence entry | `E-QUOTE-MISMATCH` |
| confidence | evidence count vs confidence; no `unsupported` in plan | `E-CONF-MISMATCH`, `E-UNSUPPORTED` |
| tiers | number/date/entity claims need A or B; tier D caps at `reported`; A and D need `tier_reason` | `E-TIER-WEAK`, `E-TIER-D`, `E-TIER-REASON` |
| volatility | `volatile` requires `as_of` and `recheck` | `E-VOLATILE-UNDATED` |
| clusters | zero OPEN clusters | `E-CLUSTER-OPEN` |
| plan | every `claim_id` exists and is active; every `contested` claim is placed | `E-PLAN-ORPHAN`, `E-CONTESTED-HIDDEN` |
| html | (M4) refs, marks, `as_of` in DOM, legend, contested rendered | `E-REF-*`, `E-MARK-WRONG`, `E-ASOF-MISSING`, `E-LEGEND` |
| licenses | (M5) credits coverage and attribution | `E-IMG-*` |
| lint | (M3) zero unwaived errors | rule ids |

On failure, increment `revise_count` and set state `REVISE`. At `revise_count > 3`, set `BLOCKED` and
have `sb status` print the escalation instruction instead of a next command (AT-19).

**Checkpoint M2:** AT-03, AT-05, AT-07, AT-08, AT-09 pass.

---

## M3 — Lint

### `lint/css.py`

A ~150-line tokenizer, not a parser. Enough to be honest and never enough to guess.

```python
def rules(css: str) -> list[Rule]      # Rule(selector, decls: dict[str,str], at_rule: str|None, line: int)
def custom_props(rules) -> dict        # from :root and html/body
def resolve_var(value, props, depth=1) -> tuple[str, bool]   # (resolved, was_resolved)
```

Handles: `@media` and `@supports` blocks (recorded as `at_rule`, contents still walked), `@keyframes`
(recorded, contents skipped), comments stripped, one level of `var()` substitution with a
`--fallback` default. Nested `var()` beyond one level returns `was_resolved=False`, and **any rule
that depends on an unresolved value does not fire.** Count those in an `unresolved` tally and print it
with the results. Guessing is worse than reporting a gap.

### `lint/color.py`

```python
def parse_color(s) -> tuple[float,float,float] | None    # #rgb #rrggbb rgb() rgba() hsl() named(≈20) oklch()
def srgb_to_oklch(r,g,b) -> tuple[float,float,float]     # sRGB → linear → LMS → OKLab → LCh
def relative_luminance(r,g,b) -> float                   # WCAG 2.1
def contrast_ratio(fg, bg) -> float                      # (L1+0.05)/(L2+0.05)
def in_cream_band(L, C, h) -> bool                       # 0.84<=L<=0.97 and C<0.06 and 40<=h<=100
```

OKLab matrices are the standard published ones. Write them as literals with a comment naming the
source; do not derive them at runtime.

**Contrast pairing.** Walk the DOM with the HTML parser, maintain an inherited `color` /
`background-color` stack from matching rules (support only `element`, `.class`, `#id`, and descendant
selectors; anything more complex is `unresolved`). For each text-bearing node, compare its resolved
color against the nearest ancestor with a non-transparent background. Size class comes from the
resolved `font-size` and `font-weight`, with `1rem = 16px` and `clamp()` evaluated at its **minimum**
(the worst case for contrast at small viewports).

### `lint/rules.py`

One registry list, mirroring impeccable's shape so the output is greppable and stable:

```python
RULES = [
  {"id": "slop.gradient-text", "severity": "error", "family": "slop",
   "message": "Gradient text is decorative, never meaningful. Use a solid color; emphasize with weight or size.",
   "check": check_gradient_text},
  ...
]
```

Each `check(doc, css, ctx) -> Iterable[Finding]` where `Finding(rule_id, severity, file, line, snippet, detail)`.
All 28 rules from SPEC §9.1. Output modes: human (grouped by severity, rule id first) and `--json`.

Waivers: `sourcebook.json.lint_waivers` is `{rule_id: reason}`. A `warn` with a waiver is suppressed
and listed at the end as `waived`. An `error` **cannot be waived**. That asymmetry is the point.

**Checkpoint M3:** AT-10, AT-11, AT-12 pass. The `tests/fixtures/html/clean.html` reference artifact
produces zero errors and zero warns.

---

## M4 — Templates and HTML verification

### Templates

Six inert HTML files, each a complete working artifact with placeholder content, each already passing
`sb lint` with zero findings. They are the floor, not the ceiling: the agent is expected to design
past them, and the lint gate is what keeps that from drifting into slop.

Every template carries:
- `<html lang>`, `<title>`, viewport meta, `<meta name="robots" content="noindex">`
- `_partials/marks.css` inlined: the five `m-*` marks plus a one-time `.mark-legend`
- `<!-- SB:LEDGER -->` injection marker
- A `@media (prefers-reduced-motion: reduce)` block covering every transition it defines
- A `:focus-visible` treatment
- A footer provenance line: `Built with sourcebook · {date} · {n} sources`
- Zero external references, zero JS-gated content

Type-specific requirements:
- `answer.html` — sticky contents, scroll progress, in-page ledger section, `scroll-margin-top` on
  sections. Interactivity is enhancement only; the whole document reads with JS disabled.
- `explainer.html` — a single `100dvh` panel that also holds at 1920×1080 and at 390×844.
- `deck.html` — sections as slides, arrow/space/swipe nav, `?print` class that unrolls all slides for
  PDF, `<aside class="notes">` per slide holding the citations.
- `brief.html` — `@page` rules for A4 and Letter, no fixed positioning, footnote ledger.
- `infographic.html` — inline SVG chart patterns with labeled axes and a per-figure `<figcaption>`
  carrying the source line.

### `sb inject <html> --ledger <file>`

Replaces the content between `<!-- SB:LEDGER -->` and `<!-- /SB:LEDGER -->` (inserting the closing
marker if absent). Idempotent. Refuses to run if the marker is missing, rather than appending
somewhere plausible.

### HTML verification pass in `verify.py`

Parse with `html.parser`. Collect: every `data-claim` value, every `href="#c-…"`, every `id="c-…"`,
every `class="mark m-…"` and its containing block, every text node.

Then the seven checks in SPEC §4.7. `E-MARK-WRONG` compares the rendered mark against the mark implied
by `(confidence, volatile)`: `verified→m-checked`, `reported→m-reported`, `contested→m-contested`,
`inferred→m-thin`, plus `m-moving` present iff `volatile`.

**Checkpoint M4:** AT-06, AT-13 pass. A hand-built demo answer artifact passes `sb verify` end to end.

---

## M5 — Assets and licenses

### `licenses.py` — `sb licenses`

```python
PERMITTED = {"CC0","PD","CC BY","CC BY 2.0","CC BY 4.0","CC BY-SA","CC BY-SA 2.0","CC BY-SA 4.0",
             "MIT","Apache-2.0","OGL","generated"}
DENIED_SUBSTR = {"NC","ND","unknown","all rights reserved"}
```

Checks:
1. Every `<img src>` resolving inside `assets/` has a `credits.json` entry. → `E-IMG-UNCREDITED`
2. Every entry has `origin` in `{sourced, generated}` and the fields that origin requires. → `E-IMG-FIELDS`
3. `sourced`: license in `PERMITTED`, none of `DENIED_SUBSTR`. → `E-IMG-LICENSE`
4. `CC BY*`: the `credit` string appears in the rendered DOM text. → `E-IMG-ATTRIB`
5. `CC BY-SA*`: warn that the composite inherits share-alike.
6. `generated`: `generator` and `prompt` present; the string `Generated illustration` appears in the
   DOM within the image's containing figure. → `E-IMG-UNLABELED`
7. `generated` image inside or adjacent to an element carrying `data-claim`. → `E-IMG-EVIDENCE`
8. `sha256` in the entry matches the file on disk. → `E-IMG-HASH`

**Checkpoint M5:** AT-14 passes, all three sub-cases.

---

## M6 — Podcast

### Script verification

`sb verify --podcast` reads `build/podcast.script.json`:
- Schema-valid; every `speaker` is in the declared `speakers` list.
- Every line with `kind: "factual"` has ≥ 1 claim id, each active and each verifying.
- `kind` is one of `factual | opinion | banter | transition`.
- No claim id referenced that is `superseded` or `retracted`.

### `tts.py` — `sb tts-plan [--voices voices.json]`

Emits `build/podcast.ttsplan.json` per SPEC §11. One segment per line. `pause_after_ms` derived
deterministically: 320 on a speaker change, 180 on a sentence-final line within the same speaker,
600 on a segment boundary. Also writes `build/audio/concat.txt` in the ffmpeg concat-demuxer format,
so joining the pieces is one command with no adapter code at all.

`reference/podcast.md` documents the two adapter shapes (a local CLI loop and an API loop) in prose
and ships neither. Absent `build/audio/` never fails a gate.

**Checkpoint M6:** AT-15 passes.

---

## M7 — Packaging, install, skill, demo

### `package.py`

```
sb package [--public|--private] [--out dist/] [--verify]
```

- Copies `build/*` and `assets/*` to `--out`.
- Writes `PROVENANCE.json`: for each source, `{id, kind, locator, title, publisher, tier, tier_reason,
  published_at, retrieved_at, raw_sha256, normalized_sha256, normalizer_version}`, plus the toolchain
  versions and the gate report.
- Writes `SHA256SUMS` over every shipped file.
- `--public` rewrites each ledger evidence entry beyond the quote budget to
  `{source_id, start, end, quote_sha256, length}` and drops `normalized.md` from the package.
- `--verify` recomputes every checksum and re-runs the quote check against the original workspace.

Quote budget enforcement lives here and in `verify`: ≤ 25 words or ≤ 200 chars per quote, ≤ 3 quotes
and ≤ 500 chars per source in a shipped artifact. Over budget in `--public` is a redaction; over
budget in the rendered HTML is `E-QUOTE-BUDGET`, an error.

### `install.py`

```
python scripts/install.py --harness {claude,codex,cursor,agents,all} [--dest .] [--link]
```

| Harness | Skill path | Command path |
|---|---|---|
| `claude` | `.claude/skills/sourcebook/` | `.claude/commands/` |
| `agents` | `.agents/skills/sourcebook/` | `.agents/commands/` |
| `codex` | `.codex/skills/sourcebook/` | `.codex/prompts/` |
| `cursor` | `.cursor/skills/sourcebook/` | `.cursor/commands/` |

`--link` symlinks instead of copying, for developing the kit itself. The installer also writes a
`sb` shim (`#!/bin/sh` → `exec python3 "<abs>/scripts/sb.py" "$@"`) into the destination and prints
the one line the user needs to add to `PATH`.

**AT-20 also asserts the skill body contains no harness-specific tool name.** Grep the installed
`SKILL.md` for `WebFetch`, `Bash(`, `str_replace`, `read_file`, `apply_patch`, and any `mcp__`
prefix. The skill says "run `sb …`" and "read the file", never which tool does it. That is the entire
portability guarantee, and it is worth a test.

### `skills/sourcebook/SKILL.md`

Frontmatter: `name`, `description`, `version`, `license`. Body under 200 lines, hot path only:

1. **Setup.** Resolve `SKILL_DIR`. Run `sb status`. Do exactly what it says next. If there is no
   workspace, `sb init`.
2. **Declare capabilities once** (`web_fetch`, `image_gen`, `tts`).
3. **The state machine table**, abbreviated, with the command per state.
4. **Load the artifact playbook** for the requested type before composing. Non-optional.
5. **Load `reference/evidence.md`** before writing the first claim. Non-optional.
6. **Load `reference/visual.md`** before writing the first line of HTML. Non-optional.
7. **Ship gate.** Do not report the work complete until `sb verify` exits 0. Paste its output.
8. **Escalation.** After three failed verifies, stop and tell the user what is blocking, with the
   specific claims and error codes. Do not loosen a claim to make a gate pass.

The two rules the skill states most bluntly, because they are what the kit is for:

> Never write a sentence of fact you cannot cite with `sb find`.
> Never make a contradiction disappear by choosing a side quietly.

### `commands/*.md`

Thin. Each names the state it targets, the `sb` commands to run, and the reference file to load.
`sourcebook.md` is the router: run `sb status`, print the state, recommend the next command.

### Demo

`examples/demo/BRIEF.md` is the SPEC §14 runbook, executable line by line.
`make demo-freeze` runs `sb add` for every URL in `sources.txt`, then copies the resulting
`sources/` tree into `examples/demo/frozen/` (gitignored). `sb init --from <dir>` seeds a workspace
from a frozen capture, which is how the demo and the ATs both run with the network off.

**Checkpoint M7:** AT-17, AT-19, AT-20 pass. The demo completes online and from frozen.

---

## Test runner

`tests/run.py`, stdlib `unittest` discovery over `tests/cases/AT-*.py`. Every case:

```python
def test():
    with tempdir() as d:
        seed(d, "fixtures/corpus")        # or fixtures/html for lint cases
        rc, out = sb(d, "verify")
        assert rc == 2 and "E-QUOTE-MISMATCH" in out
```

`sb()` invokes `scripts/sb.py` in a subprocess and captures both streams. Subprocess, not import, so
the tests exercise the real exit codes that the whole design rests on. No network in any case; a case
that needs one is a bug in the case.

---

## Definition of done, v0.1.0

- All 20 acceptance tests pass on Python 3.10, 3.11, 3.12, and 3.13 with no third-party packages installed.
- `sb verify` on `examples/demo` exits 0 online and from `examples/demo/frozen/` offline.
- All six templates lint clean.
- `install.py --harness all` produces four working installs and the skill contains no harness-specific
  tool name.
- `README.md` gets someone from clone to a verified artifact in under ten minutes.
- Total Python under 2,200 lines, excluding tests and fixtures.

## Deliberately out of scope for v0.1.0

Embeddings and semantic search (BM25 plus an agent that can read is enough at this corpus size, and
adding vectors would mean a model call, a key, and a store, which breaks the zero-dependency promise).
Incremental re-indexing. Multi-workspace linking. A web UI. Any hosted anything. Translation.
OCR. A TTS implementation. Live collaboration. Watch mode.
