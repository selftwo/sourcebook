# sourcebook — Specification

Version 0.1.0 · Status: buildable draft · License: Apache-2.0

## 1. What this is

**sourcebook** is a portable kit that lets any capable coding agent turn a pile of URLs and files into
**claim-cited artifacts**: interactive HTML answers, one-slide explainers, decks, visual briefs,
infographics, and podcast scripts with audio hooks.

It ships three things and nothing else:

| Part | What it is | Who runs it |
|---|---|---|
| **Skill** | `skills/sourcebook/SKILL.md` plus on-demand reference files | The agent reads it |
| **Command kit** | `commands/*.md`, installed into whichever harness is present | The user types it |
| **Scripts** | `scripts/sb.py`, one deterministic Python CLI | The agent shells out to it |

### The one architectural decision

> **Scripts never reason. The agent never computes.**

Deterministic Python owns: fetching, normalizing, hashing, chunking, lexical search, offset
resolution, citation verification, contradiction detection, design linting, license checking,
ledger rendering, packaging.

The running agent owns: judgment. What to search, what a source means, which claim is worth making,
how to adjudicate a conflict, what the artifact should say, how it should look.

The contract between them is a directory of JSON and Markdown files. No database, no service,
no daemon, no vector store, no embedding call, no model call from any script.

### Non-goals

- Not a NotebookLM clone. There is no server, no UI, no accounts, no sync.
- Not an Open Notebook install or dependency. sourcebook borrows ideas (retrieval-then-cite,
  heading-aware chunking, outline-then-transcript podcasts) and reimplements a much smaller
  version of them with no shared code and no shared runtime.
- Not a hosted product. Everything runs from a checkout, offline where possible.
- Not an LLM wrapper. sourcebook does not know what model you are, does not hold API keys,
  and does not make network calls to any model provider.

### Hard requirements

- Python ≥ 3.10, **standard library only** for every gate-blocking path.
- Optional extras (`pypdf`, `httpx`) improve ingestion; their absence degrades to an
  agent-assisted fallback, never to a failure.
- Artifacts are **single self-contained HTML files**. No CDN, no external font, no build step,
  no framework. They open from `file://` and they work offline forever.
- Every gate is a script exit code, not a model's opinion.

---

## 2. Repository tree

```
sourcebook/
├── SPEC.md                       # this file
├── BUILD.md                      # implementation plan
├── README.md
├── LICENSE                       # Apache-2.0
├── NOTICE
│
├── skills/sourcebook/
│   ├── SKILL.md                  # portable skill, hot path only (<200 lines)
│   └── reference/
│       ├── evidence.md           # source tiers, confidence, contradiction, uncertainty
│       ├── visual.md             # agent-judged anti-slop (the half a linter cannot see)
│       ├── images.md             # generate / source / none paths
│       ├── licensing.md          # quote budget, attribution, asset rules
│       ├── answer.md             # artifact playbook: interactive HTML answer
│       ├── explainer.md          # artifact playbook: one slide
│       ├── deck.md               # artifact playbook: N-slide deck
│       ├── brief.md              # artifact playbook: visual brief
│       ├── infographic.md        # artifact playbook: data-forward single page
│       └── podcast.md            # artifact playbook: script + audio hooks
│
├── commands/                     # harness-neutral slash commands (Markdown + frontmatter)
│   ├── sourcebook.md             # router / status
│   ├── sb-add.md
│   ├── sb-ask.md
│   ├── sb-explainer.md
│   ├── sb-deck.md
│   ├── sb-brief.md
│   ├── sb-infographic.md
│   ├── sb-podcast.md
│   ├── sb-verify.md
│   └── sb-ledger.md
│
├── scripts/
│   ├── sb.py                     # single CLI entrypoint, dispatch only
│   ├── install.py                # copy skill + commands into a harness
│   └── sourcebook/               # the implementation package
│       ├── __init__.py
│       ├── ids.py                # deterministic identifier derivation
│       ├── manifest.py           # sourcebook.json read/write/state machine
│       ├── collect.py            # add: fetch, copy, capture provenance
│       ├── extract.py            # normalize to normalized.md
│       ├── chunk.py              # deterministic heading-aware chunker
│       ├── index.py              # BM25 lexical index (pure Python)
│       ├── search.py             # search / find / quote
│       ├── ledger.py             # claims, adjudications, ledger rendering
│       ├── contradict.py         # contradiction clustering
│       ├── verify.py             # the ship gate
│       ├── lint/
│       │   ├── __init__.py
│       │   ├── rules.py          # the anti-slop + a11y rule registry
│       │   ├── css.py            # tiny CSS tokenizer, var() resolution
│       │   ├── color.py          # hex/rgb → OKLCH, WCAG contrast
│       │   └── html.py           # stdlib HTMLParser walker
│       ├── licenses.py           # credits.json validation
│       ├── tts.py                # provider-agnostic synthesis plan
│       └── package.py            # checksums, PROVENANCE.json, public redaction
│
├── schemas/                      # JSON Schema draft 2020-12
│   ├── manifest.schema.json
│   ├── source.schema.json
│   ├── chunk.schema.json
│   ├── claim.schema.json
│   ├── adjudication.schema.json
│   ├── plan.schema.json
│   ├── credits.schema.json
│   └── ttsplan.schema.json
│
├── templates/                    # inert HTML shells the agent fills in
│   ├── answer.html
│   ├── explainer.html
│   ├── deck.html
│   ├── brief.html
│   ├── infographic.html
│   └── _partials/
│       ├── marks.css             # the five uncertainty marks + legend
│       └── ledger.html           # generated citation apparatus target
│
├── tests/
│   ├── run.py                    # stdlib test runner, no pytest required
│   ├── fixtures/                 # hermetic synthetic corpus, no network
│   │   ├── corpus/*.md
│   │   └── html/*.html           # lint fixtures, one per rule family
│   └── cases/AT-*.py             # one file per acceptance test
│
└── examples/demo/
    ├── BRIEF.md                  # the end-to-end demo runbook
    ├── sources.txt               # live URLs
    └── frozen/                   # created by `make demo-freeze`, gitignored
```

### Workspace tree (what a run produces)

A workspace is any directory. It is git-friendly, diffable, and disposable.

```
<workdir>/
├── sourcebook.json               # manifest: state, config, counts, gates, history
├── sources/
│   └── <src_id>/
│       ├── source.json           # metadata, tier, provenance, hashes
│       ├── normalized.md         # THE canonical text. Immutable. All offsets index into this.
│       └── raw.<ext>             # original capture (optional)
├── chunks/<src_id>.jsonl         # {chunk_id, ordinal, start, end, heading_path}
├── index/lexical.json            # BM25 postings
├── ledger/
│   ├── claims.json
│   └── adjudications.json
├── plan.json                     # the agent's artifact plan
├── assets/
│   ├── <name>.<ext>
│   └── credits.json
└── build/
    ├── <artifact>.html
    ├── ledger.html               # generated, injected, never hand-written
    ├── podcast.script.json
    ├── podcast.ttsplan.json
    └── PROVENANCE.json
```

---

## 3. The citation model

This is the load-bearing idea. Everything else serves it.

**One canonical text per source. Every citation is a byte span into that text.**

- `sources/<src_id>/normalized.md` is written once and never edited. Its SHA-256 is recorded.
- A citation is `{source_id, start, end, quote}`.
- Verification is a string comparison: `normalized_md[start:end] == quote`. No model, no fuzzy match, no
  embedding, no tolerance.

Consequences that fall out for free:

1. **Chunking is not load-bearing.** Re-chunk with any parameters; citations still verify. Chunks are a
   retrieval convenience, not a provenance record. (Open Notebook ties citations to record ids, which
   means a re-index can orphan them. This design cannot.)
2. **Hallucinated quotes are mechanically impossible to ship.** A quote that was never in the source
   fails `sb verify` with exit code 2 and the offending claim id.
3. **Offsets are cheap for the agent.** It never computes them. It pastes the sentence it wants into
   `sb find`, and gets the span back.

```
$ sb find src_9f2a1c4e "DuitNow QR is Malaysia's national QR standard"
src_9f2a1c4e  12840..12886  exact  (1 match)
```

If the pasted text does not appear byte-exact, `sb find` reports the nearest anchor and exits 1. The
agent then re-reads and pastes correctly. There is no path where an approximate quote becomes a citation.

### Identifier derivation

All deterministic, so a re-run of the same inputs produces the same workspace.

| Id | Formula |
|---|---|
| `src_id` | `"src_" + sha256(canonical_locator + "\n" + raw_sha256)[:12]` |
| `chunk_id` | `f"{src_id}#c{ordinal:04d}"` |
| `claim_id` | `"clm_" + sha256(normalize_ws(claim.text).lower())[:12]` |
| `cluster_id` | `"cls_" + sha256(topic_key)[:12]` |

`canonical_locator` for a URL: lowercase scheme and host, strip default port, strip fragment, strip
tracking params (`utm_*`, `gclid`, `fbclid`, `ref`, `si`), preserve path case, preserve remaining query
sorted. For a file: the POSIX path relative to the workspace.

Content-addressed `claim_id` means writing the same claim twice is idempotent, and editing a claim's
text creates a new claim rather than silently mutating one that an artifact already cites.

### Normalization (must be reproducible)

`normalizer_version: 1`

1. Decode to UTF-8, replacing invalid bytes with U+FFFD.
2. Unicode NFC.
3. CRLF and CR to LF.
4. Strip trailing whitespace on every line.
5. Collapse three or more consecutive blank lines to two.
6. Ensure exactly one trailing newline.
7. Never re-wrap, never re-order, never strip Markdown, never inject anything.

The result is hashed. Any change to this algorithm bumps `normalizer_version` and invalidates existing
offsets, which `sb verify` detects and reports as `E-NORM-DRIFT` rather than silently accepting.

---

## 4. Schemas and contracts

All schemas are JSON Schema draft 2020-12 in `schemas/`. Validation is a small stdlib checker
(BUILD.md §M0) covering the subset used: `type`, `required`, `enum`, `pattern`, `items`,
`properties`, `additionalProperties`, `minItems`, `format: date-time|date|uri`.

### 4.1 `source.json`

```json
{
  "schema_version": 1,
  "id": "src_9f2a1c4e0b71",
  "kind": "url",
  "locator": "https://www.paynet.my/business-solutions/duitnow-crossborder-qr-payments.html",
  "canonical_locator": "https://www.paynet.my/business-solutions/duitnow-crossborder-qr-payments.html",
  "title": "DuitNow Cross-Border QR Payments",
  "author": null,
  "publisher": "Payments Network Malaysia (PayNet)",
  "published_at": "2026-02-12",
  "retrieved_at": "2026-07-26T09:14:03Z",
  "tier": "A",
  "tier_reason": "operator of the national payment scheme, primary source for its own status",
  "license": "unknown",
  "media_type": "text/html",
  "charset": "windows-1252",
  "lang": "en",
  "raw_sha256": "…",
  "normalized_sha256": "…",
  "normalizer_version": 1,
  "extraction": { "tool": "sb.html", "version": 1, "ok": true, "notes": [] },
  "status": "ready"
}
```

`kind`: `url` | `file` | `paste`.
`status`: `pending` | `needs_extraction` | `ready` | `failed`.
`charset`: the encoding the transfer declared, else the one the bytes declare (a BOM or a `<meta charset>`).
`sb extract` decodes with it, so a non-UTF-8 source produces canonical text rather than replacement
characters. Null means "decode as UTF-8".
`needs_extraction` is the agent-assisted fallback: the script could not parse the bytes (a PDF with no
`pypdf`, a scanned image, a JS-only page), so it hands the file to the agent, which reads it with
whatever tool it has and writes `normalized.md` itself. The provenance record is identical either way.

### 4.2 Source tiers

| Tier | Definition | Examples |
|---|---|---|
| **A** | Primary or institutional. The party that holds the fact. | Standards bodies, government, regulators, the paper itself, an org's own docs, official filings, primary datasets |
| **B** | Credible secondary with named accountability. | Bylined dated journalism, peer-reviewed secondary literature, reference works, textbooks |
| **C** | Pattern evidence. Real signal about behaviour, not authority about fact. | Forums, product reviews, social posts, vendor marketing, aggregators, listing sites |
| **D** | Unknown provenance. | Undated pages, content farms, unattributed AI-generated text, scraped mirrors |

Tier is assigned by the agent at `sb add` time with a written `tier_reason`. The reason is not decorative:
`sb verify` requires a non-empty `tier_reason` for every A and every D.

### 4.3 `claims.json`

```json
{
  "schema_version": 1,
  "claims": [
    {
      "id": "clm_4b18d0e2a339",
      "text": "DuitNow QR is Malaysia's national QR payment standard, with more than 2.9 million merchant touchpoints as of 12 February 2026.",
      "topic_key": "my.duitnow.scale",
      "kind": "number",
      "confidence": "verified",
      "volatile": true,
      "as_of": "2026-02-12",
      "recheck": "https://www.paynet.my/business-solutions/duitnow-crossborder-qr-payments.html",
      "evidence": [
        { "source_id": "src_9f2a1c4e0b71", "start": 12840, "end": 12946,
          "quote": "DuitNow QR is Malaysia's National QR standard with over 2.9 million merchant touchpoints" }
      ],
      "contradicts": [],
      "status": "active",
      "superseded_by": null,
      "notes": ""
    }
  ]
}
```

| Field | Rule |
|---|---|
| `kind` | `fact` \| `number` \| `date` \| `entity` \| `quote` \| `definition` \| `interpretation` \| `recommendation` |
| `confidence` | `verified` \| `reported` \| `contested` \| `inferred` \| `unsupported` |
| `evidence` | ≥ 1 entry unless `confidence == "inferred"`, which requires exactly 0 |
| `volatile` | `true` requires a non-null `as_of` and a non-null `recheck` URL |
| `topic_key` | Dotted lowercase slug. Agent-assigned. Drives contradiction clustering. |
| `status` | `active` \| `superseded` \| `retracted`. Nothing is ever deleted. |

### 4.4 Confidence, and how it is earned

| Confidence | Earned when | Renders as |
|---|---|---|
| `verified` | ≥ 1 verifying quote from tier A or B, no live conflict | `checked` |
| `reported` | Only tier C evidence, **or** a single-source surprising claim, **or** the source itself hedges | `reported` |
| `contested` | Cluster adjudicated `both_stand`. Both sides cited in the artifact. | `contested` |
| `inferred` | The agent's own synthesis. Zero evidence entries. Never carries a citation marker. | `thin` |
| `unsupported` | Nothing supports it. | **Cannot ship.** `sb verify` exit 2 |

Plus one orthogonal mark: `volatile: true` renders as `moving` and must carry a visible `as_of` date
and a recheck link, regardless of confidence.

**Automatic downgrades enforced by `sb verify`:**

- `kind` in `number | date | entity` with evidence only from tier C or D → forced to `reported`.
  Error `E-TIER-WEAK` if the claim is marked `verified`.
- Any evidence from tier D → the claim may not exceed `reported`, and the artifact must label the
  source as pattern evidence rather than authority. Error `E-TIER-D`.
- `confidence: inferred` with any evidence entry, or any non-`inferred` claim with zero evidence →
  `E-CONF-MISMATCH`.

### 4.5 `adjudications.json`

```json
{
  "schema_version": 1,
  "adjudications": [
    {
      "cluster_id": "cls_71c0e93a1d6f",
      "topic_key": "my.upi.crossborder.live",
      "claim_ids": ["clm_aa11…", "clm_bb22…"],
      "outcome": "both_stand",
      "reason": "The operator's own page uses phased future-tense language and omits India from the live interoperability list. The news report describes the agreement as enabling payments. These are a status claim and an intent claim about different things; both are accurate and a reader needs both.",
      "decided_at": "2026-07-26T10:02:11Z",
      "winner": null
    }
  ]
}
```

`outcome`: `supersede` | `both_stand` | `scope_split` | `retract`.

### 4.6 `plan.json`

The agent writes this before composing. It is the bridge from ledger to artifact.

```json
{
  "schema_version": 1,
  "type": "answer",
  "title": "Can an Indian traveller pay by UPI in Malaysia right now?",
  "audience": "one traveller planning a trip in the next six months",
  "thesis": "No. An agreement is signed; the service is not live for India. Plan for cash and a local wallet.",
  "register": "editorial",
  "images": { "mode": "none", "slots": [] },
  "constraints": {
    "palette_strategy": "committed",
    "motion": "minimal",
    "breakpoints": [360, 768, 1200]
  },
  "sections": [
    { "id": "answer",  "heading": "The short answer", "intent": "state the finding and its date",
      "claim_ids": ["clm_aa11…", "clm_bb22…"] },
    { "id": "what",    "heading": "What was actually signed", "intent": "…", "claim_ids": ["…"] }
  ]
}
```

Every `claim_id` in `plan.json` must exist and be `active`. Every `active` claim of confidence
`contested` must appear in at least one section. Enforced by `sb verify` (`E-PLAN-ORPHAN`,
`E-CONTESTED-HIDDEN`).

### 4.7 HTML citation contract

The agent writes prose. The script writes the apparatus. The two meet at exactly two markers.

**In the body**, a citation is:

```html
<p data-claim="clm_4b18d0e2a339">DuitNow QR is Malaysia's national QR standard, with more than
2.9 million merchant touchpoints as of February 2026.<sup class="ref"><a href="#c-clm_4b18d0e2a339">11</a></sup>
<span class="mark m-checked">checked</span> <span class="mark m-moving">moving</span></p>
```

- `data-claim` on the containing block element. Multiple claims: space-separated list.
- `<sup class="ref"><a href="#c-{claim_id}">N</a></sup>` where `N` is the ledger ordinal.
- The mark spans are rendered by the agent from the claim's confidence and volatility.

**The ledger** is never hand-written. `sb ledger --html` reads `claims.json` and emits the
`<ol class="ledger">` with `id="c-{claim_id}"` on each entry, the source line, the tier badge, the
`as_of` date, and the recheck link. The agent injects it at the `<!-- SB:LEDGER -->` marker in the
template. Re-running the command re-generates it, so drift between prose and ledger is impossible.

`sb verify --html build/answer.html` then checks, deterministically:

| Check | Error code |
|---|---|
| Every `href="#c-…"` resolves to a rendered ledger entry | `E-REF-DANGLING` |
| Every `data-claim` id exists and is `active` | `E-CLAIM-UNKNOWN` |
| Every ledger entry is referenced at least once | `E-LEDGER-ORPHAN` |
| Every non-`inferred` claim carries the right `m-*` mark | `E-MARK-WRONG` |
| Every `volatile` claim shows an `as_of` date in the DOM | `E-ASOF-MISSING` |
| No `<sup class="ref">` on a block whose claim is `inferred` | `E-CITE-INFERRED` |
| The mark legend appears exactly once | `E-LEGEND` |

---

## 5. State machine

```
                       ┌────────────────────────────────────────┐
                       │                                        ▼
 INIT ─▶ COLLECT ─▶ EXTRACT ─▶ CHUNK ─▶ INDEX ─▶ PLAN ─▶ GROUND ─▶ ADJUDICATE
   │        ▲                                                        │
   │        │                                                        ▼
   │        │                                                    COMPOSE
   │        │                                                        │
   │        │                                                        ▼
   │        └────────────── REVISE ◀────── fail ────── VERIFY ◀─── RENDER
   │                          │                          │
   │                          │ >3 loops                 │ pass
   ▼                          ▼                          ▼
 BLOCKED ◀──── any state ─────┘                       PACKAGE ─▶ DONE
```

| State | Actor | Command | Produces | Gate to leave |
|---|---|---|---|---|
| `INIT` | script | `sb init` | `sourcebook.json` | manifest schema-valid |
| `COLLECT` | agent + script | `sb add …` | `sources/*/raw`, `source.json` | ≥ 1 source; every source has a tier and `tier_reason` |
| `EXTRACT` | script (agent fallback) | `sb extract` | `normalized.md` + hash | **G1**: every source `ready` or `failed` with a reason; ≥ 1 `ready` |
| `CHUNK` | script | `sb chunk` | `chunks/*.jsonl` | offsets in range, contiguous coverage |
| `INDEX` | script | `sb index` | `index/lexical.json` | postings non-empty |
| `PLAN` | agent | writes `plan.json` | `plan.json` | plan schema-valid; thesis present |
| `GROUND` | agent + `sb search` / `sb find` | `ledger/claims.json` | **G2**: every claim schema-valid; every non-`inferred` claim has ≥ 1 byte-exact quote |
| `ADJUDICATE` | script + agent | `sb contradictions`, then writes adjudications | `adjudications.json` | **G3**: zero unadjudicated clusters |
| `COMPOSE` | agent | draft HTML from a template | `build/<artifact>.html` | parses as HTML |
| `RENDER` | script | `sb ledger --html` | `build/ledger.html`, injected | **G4**: all refs resolve |
| `VERIFY` | script | `sb verify` | gate report | **G5**: exit 0 |
| `PACKAGE` | script | `sb package` | checksums, `PROVENANCE.json` | checksums recomputed and matching |
| `REVISE` | agent | back to `COMPOSE`, `GROUND`, or `COLLECT` | | `revise_count ≤ 3` |
| `BLOCKED` | agent | writes `blockers[]`, stops and asks the user | | user input, then `sb unblock --reason …` |

`sb status` prints the current state, the failing gate if any, and the single next command to run.
This is what makes the kit resumable across a context compaction, a crash, or a different agent
picking the work up tomorrow.

**Escalation rule.** After three failed `VERIFY` loops, the agent must stop and report to the user
rather than continuing to churn. Silently loosening a claim to make a gate pass is the failure mode
this rule exists to prevent.

**Recovery from `BLOCKED`.** One documented command, run only after the user has decided what
changes: `sb unblock --reason "<what the user decided>"`. It resets `revise_count`, clears
`blockers`, records the reason in `history`, and leaves the state at `REVISE`. It changes no claim
and waives no gate; the next `sb verify` still has to pass. The reason is required, so the escape
hatch always leaves a trace.

**Blocking conditions** (go to `BLOCKED`, do not improvise):
- Fewer than two independent tier A/B sources for a factual question.
- The question's central claim has only tier C or D evidence.
- A source is paywalled or robots-disallowed and no lawful alternative exists.
- A required capability is absent and the chosen artifact type depends on it.

---

## 6. Source and claim ledger

The ledger is `ledger/claims.json` plus `ledger/adjudications.json`. It is the project's memory and
the artifact's spine.

**Append-mostly.** Claims are added and their `status` changes. Claims are never deleted. A superseded
claim keeps its evidence and gains `superseded_by`. This means the ledger records not just what the
artifact says, but what it considered and rejected, which is the part that makes a research artifact
trustworthy.

**Rendered forms** (all deterministic, all from the same JSON):

```
sb ledger --html      # <ol class="ledger"> with #c-{claim_id} anchors, for injection
sb ledger --md        # Markdown source list, for a README or a memo
sb ledger --json      # the resolved ledger with ordinals assigned
sb ledger --sources   # grouped by source with tier badges, penang-packet style
```

Ledger ordinals are assigned by first appearance order in `plan.json` sections, then by claim id for
anything unreferenced. Deterministic, so ordinals are stable across re-renders.

---

## 7. Contradiction policy

**Detection is mechanical. Adjudication is judgment. Neither substitutes for the other.**

### Detection: `sb contradictions`

Clusters `active` claims by `topic_key` and flags a cluster when any of:

1. **Numeric divergence.** Two claims of `kind: number` share a `topic_key` and their extracted leading
   numeric values differ by more than `tolerance` (default 5% relative, configurable per cluster).
2. **Date divergence.** Two claims of `kind: date` share a `topic_key` with different normalized dates.
3. **Polarity conflict.** Two claims share a `topic_key` and one contains a negation token
   (`not`, `no`, `never`, `cannot`, `without`, `un-`, `fails to`, `does not`) that the other lacks,
   within the same clause window.
4. **Explicit link.** A claim lists another in its `contradicts` array.
5. **Recency spread.** Two claims share a `topic_key`, both `volatile`, and their `as_of` dates are
   more than 180 days apart.

The script emits candidates. It does **not** decide. False positives are expected and cheap; the agent
dismisses them with `outcome: scope_split` and a reason.

### Adjudication: four outcomes, all recorded

| Outcome | Meaning | Effect |
|---|---|---|
| `supersede` | One claim is correct and the other is stale or lower-tier. | Loser gets `status: superseded`, `superseded_by: <winner>`. **Retained in the ledger.** |
| `both_stand` | A genuine live disagreement, or two true claims about different things a reader will conflate. | Both stay `active`, both forced to `confidence: contested`. **Both must appear in the artifact.** |
| `scope_split` | A false positive. They were never about the same thing. | Agent rewrites `topic_key` on one or both. New claim ids result. |
| `retract` | One claim was a misreading of its own source. | Loser gets `status: retracted` with a reason. |

**The non-negotiable rule:** `both_stand` puts an obligation on the artifact. `sb verify` checks that
every `contested` claim's id appears in the rendered HTML (`E-CONTESTED-HIDDEN`). A tidy artifact that
quietly picks a side is exactly the failure this kit exists to prevent.

**Precedence when adjudicating `supersede`,** in order:
1. Higher tier wins over lower tier.
2. Within the same tier, more recent `as_of` wins for a volatile claim.
3. Within the same tier and date, the source closer to the fact wins (the operator over the reporter).
4. If none of these break the tie, it is not a `supersede`. It is `both_stand`.

---

## 8. Uncertainty policy

Five marks. That is the entire vocabulary. They are inline, small, and never decorative.

| Mark | Class | Means | Reader should |
|---|---|---|---|
| `checked` | `m-checked` | Verified against a tier A/B source. | Trust it. |
| `reported` | `m-reported` | Real signal, weaker authority. Pattern evidence or a lone surprising source. | Trust the shape, not the number. |
| `contested` | `m-contested` | Sources disagree and both are shown. | Read both. |
| `moving` | `m-moving` | True as of a printed date, and the kind of thing that changes. | Recheck at the link. |
| `thin` | `m-thin` | The author's inference. No source, because there is not one. | Weigh it as opinion. |

Rules the agent must follow (and `sb verify` enforces what it can):

- **`thin` is a promise, not an escape hatch.** An `inferred` claim may never carry a citation marker.
  Marking something `thin` to avoid finding a source is the abuse this rule names.
- **Never print a date you have not verified.** Festival dates, prices, availability, model versions.
  If the date came from an aggregator, do not print it. Print the official calendar link instead.
- **Uncertainty is placed, not appended.** The mark sits on the sentence it qualifies. A blanket
  "this may be inaccurate" disclaimer at the top of the artifact is not a substitute and is banned.
- **Absence is a finding.** "The operator's live interoperability list does not include India" is a
  citable claim. Say what is not there rather than staying silent about it.
- **One legend, once.** Rendered near the first mark, not in every section.

---

## 9. Visual anti-slop rules

Split by who can check it. The machine-checkable half is a lint script with stable rule ids, so it is
a gate rather than a suggestion. The judgment half lives in `reference/visual.md`.

### 9.1 Machine-checkable: `sb lint <html>`

Severity `error` blocks the ship gate. Severity `warn` must be acknowledged in
`sourcebook.json.lint_waivers` with a written reason, or it becomes an error.

| Rule id | Severity | Detects |
|---|---|---|
| `slop.gradient-text` | error | `background-clip:text` or `-webkit-background-clip:text` with a gradient background |
| `slop.side-stripe` | error | `border-left` or `border-right` ≥ 2px in a non-neutral color on a card-like rule |
| `slop.over-round` | error | `border-radius` ≥ 24px on an element that is not a pill (height-derived) or a circle |
| `slop.ghost-card` | error | `border: 1px solid X` and `box-shadow` with blur ≥ 16px on the same rule |
| `slop.stripe-bg` | error | `repeating-linear-gradient(` used as a background |
| `slop.cream-band` | error | Body or page background in OKLCH `L 0.84–0.97`, `C < 0.06`, `hue 40–100` |
| `slop.ai-palette` | error | Purple/violet gradient pair, or cyan-on-near-black as the primary accent |
| `slop.sole-overused-font` | warn | Inter, Roboto, Geist, Space Grotesk, Plus Jakarta Sans, or Fraunces as the only declared family |
| `slop.flat-scale` | warn | Adjacent type steps with a ratio < 1.25 |
| `slop.hero-shout` | error | A `clamp()` font-size with a max > 6rem |
| `slop.tracking-floor` | error | `letter-spacing` < -0.04em on a display-size rule |
| `slop.eyebrow-reflex` | error | ≥ 3 elements matching the tiny-uppercase-tracked kicker pattern |
| `slop.numbered-scaffold` | warn | `01` / `02` / `03` style markers on ≥ 3 sections |
| `slop.card-grid-clone` | warn | ≥ 4 sibling elements with identical class lists and identical child structure |
| `copy.em-dash` | warn | `—` or ` -- ` in body text |
| `copy.buzzword` | warn | streamline, empower, supercharge, leverage, unleash, seamless, world-class, enterprise-grade, next-generation, cutting-edge, game-changer, mission-critical, deep dive, unlock |
| `copy.meta-phrase` | warn | "X theater", "not just X, it's Y", "actually X" |
| `a11y.contrast-body` | error | Resolvable text/background pair below 4.5:1 at body size |
| `a11y.contrast-large` | error | Resolvable pair below 3:1 at ≥ 18px or bold ≥ 14px |
| `a11y.reduced-motion` | error | Any `@keyframes` or `transition` without a `prefers-reduced-motion: reduce` block |
| `a11y.reveal-gate` | error | Content hidden by default and revealed only by a JS-triggered class (ships blank in headless renderers) |
| `a11y.tap-target` | warn | Interactive element with a computed box below 44×44 |
| `a11y.img-alt` | error | `<img>` without `alt` |
| `a11y.lang-title` | error | Missing `<html lang>`, `<title>`, or viewport meta |
| `a11y.focus-visible` | error | `outline: none` with no `:focus-visible` replacement |
| `struct.external-ref` | error | Any `src` / `href` / `@import` / `url()` pointing off-document for a subresource |
| `struct.zindex-arbitrary` | warn | `z-index` ≥ 100 outside a named scale |
| `struct.overflow-risk` | warn | `clamp()` max width exceeding its container's `max-width` |

Rules the linter reports honestly rather than guessing: unresolved `var()` chains deeper than one
level and colors set by JS are counted in an `unresolved` tally printed with the results. A rule never
fires on a value it could not resolve.

### 9.2 Agent-judged (`reference/visual.md`)

- **Category-reflex, two orders.** If someone could guess the palette and type from the topic alone,
  it is the first reflex. If they could guess it from topic-plus-obvious-anti-reference ("research
  artifact that is not a dashboard, therefore editorial serif on cream"), it is the second. Rework
  until neither is guessable.
- **No illustration you cannot render for real.** Sketchy SVG, hand-drawn doodles, `feTurbulence`
  paper grain, crude 20-path scenes. If there is no real asset, ship no illustration. Structure,
  rules, type, and color carry it.
- **SVG is for data, not decoration.** Timelines, relationship maps, comparisons, small multiples.
  If it does not encode a value from the ledger, it does not belong.
- **Cards are the lazy answer.** Nested cards are always wrong.
- **The hero-metric template is banned.** Big number, small label, three supporting stats, gradient
  accent. It is the SaaS cliché and it makes cited numbers look like marketing.
- **Motion is intentional or absent.** One uniform entrance applied to every section is the tell.
- **Every mark earns its place.** If the artifact renders `checked` on every sentence, the mark has
  stopped carrying information. Mark what varies.

### 9.3 Design floor (the artifact must clear this regardless of type)

Body text ≥ 4.5:1. Measure 60–75ch. Type scale ratio ≥ 1.25 between steps. At most three families.
Tested at 360px, 768px, 1200px with no overflow. Every animation has a reduced-motion path. Works
with JavaScript disabled for all content (interactivity may enhance; it may not gate).

---

## 10. Image generation, and the path without it

`plan.json.images.mode` is one of three. **The `none` path is the default and must be fully excellent.**

### `none` (default)

Zero `<img>` elements. Visual interest comes from typography, rule work, a committed palette, tables,
CSS-drawn diagrams, and inline SVG that encodes ledger data. Every artifact type has a complete,
shippable no-image design in `templates/`. The gate suite runs identically. An artifact is never
weaker for having no images; it is only weaker for having bad ones.

### `source`

Fetch openly licensed images. Every asset gets a `credits.json` entry:

```json
{
  "clan-jetties.jpg": {
    "origin": "sourced",
    "source": "https://upload.wikimedia.org/wikipedia/commons/…",
    "credit": "Cmglee / Wikimedia Commons",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "retrieved_at": "2026-07-26T09:41:00Z",
    "sha256": "…"
  }
}
```

`sb licenses` enforces: every `<img src>` in the HTML has a credits entry; every entry has a license
from the permitted set; `CC BY*` requires the credit string to appear in the rendered DOM;
`NC`, `ND`, `unknown`, and absent licenses fail. `SA` licenses emit a warning that the composite
artifact inherits a share-alike obligation, and the agent should prefer a non-SA alternative when the
artifact will be remixed.

### `generate`

The agent uses whatever image capability its harness gives it. sourcebook does not ship one, does not
call one, and does not care which it is.

```json
{
  "diagram-flow.png": {
    "origin": "generated",
    "generator": "<model or tool name>",
    "prompt": "<the exact prompt used>",
    "created_at": "2026-07-26T10:22:00Z",
    "sha256": "…"
  }
}
```

Hard rules, enforced where mechanical and stated plainly where not:

- **A generated image is never evidence.** It may not sit adjacent to a `data-claim` element as
  illustration of that claim's content. Error `E-IMG-EVIDENCE`.
- **No real people, no real logos, no real places presented as documentary.** A generated photo of a
  real location is a fabrication with a caption.
- Every generated image renders a visible `Generated illustration` label in the artifact.
  Error `E-IMG-UNLABELED`.
- Alt text describes what the image shows, not that it was generated.
- The prompt is recorded verbatim. This is provenance, not trivia.

**Capability detection.** The agent declares what it has, once:

```
sb config set capabilities.web_fetch=agent      # agent|script|none
sb config set capabilities.image_gen=none       # agent|none
sb config set capabilities.tts=none             # agent|external|none
```

`sb status` refuses to advance to a state whose artifact type needs a capability set to `none`, and
tells the agent which fallback to take instead. There is a working path for every combination.

---

## 11. Artifact types

Six types. All are views over the same ledger and all pass the same gates.

| Type | Output | Shape | Ledger surface |
|---|---|---|---|
| `answer` | `build/answer.html` | Long-form interactive reading artifact. Sticky contents, progress, in-page ledger, per-claim marks. The flagship. | Full ledger section |
| `explainer` | `build/explainer.html` | **One screen, one idea.** ≤ 60 words of body copy, one visual, ≤ 5 claims. Fits 16:9 and portrait phone. | Compact footnote strip |
| `deck` | `build/deck.html` | N slides, keyboard and swipe nav, `?print` mode. **One claim per slide.** Speaker notes carry the citations. | Per-slide notes + final ledger slide |
| `brief` | `build/brief.html` | Dense one-pager. Print-friendly at A4 and Letter. Mostly structure and type. | Inline superscripts + footer ledger |
| `infographic` | `build/infographic.html` | Data-forward. **Every number is a cited claim of `kind: number`.** Inline SVG charts, no chart junk, no 3D, no unlabeled axes. | Per-figure source line + ledger |
| `podcast` | `build/podcast.script.json` + `.md` + `.ttsplan.json` | Outline then transcript. Every factual line carries a claim id in a parallel track. | Machine-readable citation track |

### Podcast specifics

Two-stage generation, borrowed in shape from Open Notebook's outline-then-transcript prompts and
reimplemented as agent instructions rather than a graph:

1. **Outline.** N segments with name, description, and size (`short` | `medium` | `long`).
2. **Transcript.** Per segment, in order, with the running transcript as context so the conversation
   does not restate itself.

The addition sourcebook makes: **a citation track.**

```json
{
  "episode": "…", "speakers": [{"name": "…", "voice_hint": "…"}],
  "lines": [
    { "n": 14, "speaker": "Ana", "text": "The operator's own page still uses future tense.",
      "claims": ["clm_bb22…"], "kind": "factual" },
    { "n": 15, "speaker": "Ravi", "text": "So plan as if it does not work.",
      "claims": [], "kind": "opinion" }
  ]
}
```

`sb verify --podcast` requires every line with `kind: factual` to carry ≥ 1 active claim id, and every
referenced claim to verify. Opinion and banter lines are explicitly typed as such, so the boundary
between what the sources support and what the hosts are riffing on is machine-checkable.

**Audio hooks, not audio.** sourcebook ships no TTS dependency. `sb tts-plan` emits a
provider-agnostic synthesis plan:

```json
{
  "schema_version": 1,
  "output_dir": "build/audio",
  "sample_rate": 24000,
  "format": "wav",
  "voices": { "Ana": { "hint": "warm mid-range, unhurried" }, "Ravi": { "hint": "brighter, faster" } },
  "segments": [
    { "id": "s0014", "speaker": "Ana", "text": "…", "pause_after_ms": 320,
      "out": "build/audio/s0014.wav" }
  ],
  "concat": { "manifest": "build/audio/concat.txt", "out": "build/audio/episode.wav" }
}
```

Any TTS CLI consumes this. The kit documents one local adapter shape and one API adapter shape in
`reference/podcast.md` and implements neither. Audio being absent never fails a gate; the script,
the citation track, and the plan are the deliverable.

---

## 12. Licensing

### 12.1 The kit

**Apache-2.0** for everything: scripts, schemas, templates, skill, commands, docs. Chosen over MIT for
the explicit patent grant, and over GPL because the whole point is that people vendor `skills/sourcebook/`
directly into their own private repos. `NOTICE` records that the design borrows conceptually from
Open Notebook (Apache-2.0) and from a design-rules lineage, with no code copied from either.

### 12.2 Content discipline (what artifacts may do with other people's work)

This is a working policy, not legal advice. Fair use and fair dealing vary by jurisdiction and by use.

**Quote budget.**

| Scope | Cap |
|---|---|
| Single quote | ≤ 25 words **or** ≤ 200 characters |
| Per source, in a shipped artifact | ≤ 3 quotes **and** ≤ 500 characters total |
| Per source, in the local ledger | unlimited (a working file, not a publication) |
| Full text of any source in an artifact | never |

`sb package` resolves the tension between "the ledger must be verifiable" and "the ledger must not
republish a source":

- `sb package --private` (default): ships everything, including full quotes and `normalized.md`.
  For your own machine and your own team.
- `sb package --public`: redacts every quote beyond the budget to
  `{source_id, start, end, sha256(quote), length}`. Anyone holding the same source can still verify
  every citation byte-for-byte. Nobody gets a free copy of the source.

**Attribution.** `CC BY` and `CC BY-SA` assets render their credit string visibly in the artifact, not
only in `credits.json`. Public domain and CC0 assets still record provenance.

**Collection.** Respect `robots.txt` for automated fetching. Do not circumvent paywalls, logins, or
rate limits. Do not scrape a site into a corpus wholesale; sourcebook is for a working set of sources
a person could reasonably have read. Record `retrieved_at` on everything.

**Publication defaults.** An artifact containing third-party excerpts ships with
`<meta name="robots" content="noindex">` unless the user removes it deliberately. The default is a
private reading artifact, not a competing publication.

**Attribution of the artifact itself.** Every artifact renders a footer line naming sourcebook, the
build date, and the source count. This is provenance, not branding, and it may be styled but not removed.

---

## 13. Acceptance tests

Hermetic. No network. Run with `python tests/run.py`. Each returns a clean exit code and names the rule
or error id it asserts. `sb` exit codes: `0` pass, `1` usage or input error, `2` gate failure.

| Id | Asserts | Method |
|---|---|---|
| **AT-01** | Zero-dependency bootstrap | On stdlib-only Python 3.10 with no network, `sb init && sb add tests/fixtures/corpus/*.md && sb extract && sb chunk && sb index` exits 0 |
| **AT-02** | Determinism | Run extract+chunk+index twice into two dirs. Every output file's SHA-256 is identical. |
| **AT-03** | Quote integrity | Flip one character in a claim's `quote`. `sb verify` exits 2 and prints `E-QUOTE-MISMATCH` with the claim id. |
| **AT-04** | Chunking is not load-bearing | Re-run `sb chunk --target 800 --overlap 100`. All citations still verify. |
| **AT-05** | Unsupported blocks ship | A claim with `confidence: unsupported` in `plan.json` → exit 2, `E-UNSUPPORTED`. |
| **AT-06** | Dangling reference | HTML with `href="#c-clm_deadbeef"` not in the ledger → exit 2, `E-REF-DANGLING`. |
| **AT-07** | Contradiction obligation | Two conflicting numeric claims on one `topic_key`: (a) unadjudicated → exit 2 `E-CLUSTER-OPEN`; (b) adjudicated `both_stand` but only one id in the HTML → exit 2 `E-CONTESTED-HIDDEN`; (c) both rendered → exit 0. |
| **AT-08** | Tier downgrade | `kind: number` cited only to a tier C source but marked `verified` → exit 2, `E-TIER-WEAK`. After downgrade to `reported`, HTML must carry `m-reported` or `E-MARK-WRONG`. |
| **AT-09** | Volatility | `volatile: true` with null `as_of` → exit 2 `E-VOLATILE-UNDATED`. With `as_of` but no date in the DOM → `E-ASOF-MISSING`. |
| **AT-10** | Slop lint | `tests/fixtures/html/slop.html` (gradient text, 3px left stripe, cream bg, 4 eyebrows, 32px radius, stripe bg) → exactly 6 errors with the expected rule ids. |
| **AT-11** | Contrast | `#8a8a8a` on `#f7f2e8` body text → `a11y.contrast-body` with the computed ratio in the message. A passing fixture produces zero contrast errors. |
| **AT-12** | Self-containment | A `<script src="https://cdn…">` or a Google Fonts `<link>` → `struct.external-ref`, error. |
| **AT-13** | No-image path | A full `images.mode: none` build passes every gate and contains zero `<img>` elements. |
| **AT-14** | Image licensing | (a) A generated image with no `credits.json` entry → `sb licenses` exit 2. (b) A `CC BY` asset whose credit string is absent from the DOM → exit 2. (c) A generated image with no visible label → `E-IMG-UNLABELED`. |
| **AT-15** | Podcast citation track | A `kind: factual` line with an empty `claims` array → exit 2. `sb tts-plan` output validates against `ttsplan.schema.json`. Missing `build/audio/` does not fail any gate. |
| **AT-16** | Resumability | Delete `index/` mid-run. `sb status` reports state `CHUNK` and prints `sb index` as the next command. |
| **AT-17** | Public packaging | `sb package --public` produces a ledger with no quote longer than the budget, and `sb package --verify` against the original sources still confirms every citation via hash. |
| **AT-18** | Normalizer drift | Bump `normalizer_version` in a source and re-verify → exit 2, `E-NORM-DRIFT`. Nothing silently passes. |
| **AT-19** | Revise ceiling | Simulate four consecutive `VERIFY` failures. The manifest reaches `revise_count: 3` and `sb status` prints an escalation instruction rather than a next command. |
| **AT-20** | Install portability | `python scripts/install.py --harness all` into a temp dir creates the skill and commands under `.claude/`, `.agents/`, `.codex/`, and `.cursor/`, and the skill body contains no harness-specific tool name. |
| **AT-21** | Gate reachability | (a) Deleting `build/<type>.html` → exit 2 `E-HTML-MISSING`, never a `PASS` with the html/lint rows absent. (b) A `javascript:` `recheck` → exit 2 `E-RECHECK-SCHEME`, and the rendered ledger emits no such `href`. (c) A `both_stand` recorded without `--apply` → exit 2 `E-ADJ-UNAPPLIED`. (d) A third conflicting claim on an adjudicated `topic_key` reopens the cluster → `E-CLUSTER-OPEN`. (e) A `data:` URI image with no `credits.json` entry → `E-IMG-UNCREDITED`, and an unlabelled generated one → `E-IMG-UNLABELED`. |
| **AT-22** | Ingest hardening | (a) A paste matching only after whitespace normalization → exit 1 `E-FIND-INEXACT`. (b) A Windows-1252 source with a declared charset normalizes to its real characters, with no U+FFFD. (c) `assert_fetchable` refuses loopback, private, link-local, reserved, multicast, unspecified, credentialed, and non-http destinations, on the first URL and on every redirect. (d) `sb unblock --reason` clears `BLOCKED` and records the reason. |

**Definition of done for v0.1.0:** all twenty-two pass, `examples/demo` completes end to end on a machine
with network, and the same demo completes from `examples/demo/frozen/` with the network off.

---

## 14. End-to-end demo

**Question:** *Can an Indian traveller pay by UPI in Malaysia right now?*

Chosen because it exercises every mechanism at once: a primary operator source, a secondary news
source, forum pattern evidence, a genuine contradiction between "an agreement was signed" and "the
service is live", and a claim that is volatile by nature.

```bash
# 0. install the kit into whatever harness you use
python scripts/install.py --harness claude

# 1. new workspace
sb init --dir ~/work/upi-my --question "Can an Indian traveller pay by UPI in Malaysia right now?"
cd ~/work/upi-my
sb config set capabilities.web_fetch=agent
sb config set capabilities.image_gen=none

# 2. collect. The agent assigns tier and tier_reason on each add.
sb add https://www.paynet.my/business-solutions/duitnow-crossborder-qr-payments.html \
       --tier A --reason "scheme operator, primary source for its own live status"
sb add https://www.paynet.my/about-us/media-centre/press-release/...npci... \
       --tier A --reason "joint announcement by both scheme operators"
sb add ./clippings/press-coverage.md --tier B --reason "bylined dated trade reporting"
sb add ./clippings/traveller-thread.md --tier C --reason "pattern evidence about what travellers hit"

# 3. deterministic pipeline
sb extract && sb chunk && sb index

# 4. GROUND. The agent searches, reads, and pastes exact sentences to get spans.
sb search "cross-border interoperability live countries" -k 8
sb find src_9f2a1c4e "DuitNow QR is Malaysia's National QR standard"
#   -> src_9f2a1c4e  12840..12886  exact
sb claim add --json '{ "text": "…", "topic_key": "my.upi.crossborder.live",
                       "kind": "fact", "confidence": "verified", "volatile": true,
                       "as_of": "2026-02-12", "recheck": "https://…",
                       "evidence": [{"source_id":"src_9f2a1c4e","start":12840,"end":12886,"quote":"…"}] }'

# 5. ADJUDICATE
sb contradictions
#   cls_71c0e93a  my.upi.crossborder.live  polarity  clm_aa11 vs clm_bb22   OPEN
#   -> agent writes ledger/adjudications.json with outcome "both_stand" and a reason

# 6. PLAN + COMPOSE. Agent writes plan.json, then the HTML from templates/answer.html.
# 7. RENDER the apparatus (never hand-written)
sb ledger --html > build/ledger.html
sb inject build/answer.html --ledger build/ledger.html

# 8. GATE
sb lint build/answer.html
sb verify
#   ✓ schemas        4 sources, 19 claims, 1 cluster resolved
#   ✓ quotes         19/19 byte-exact
#   ✓ references     19 resolved, 0 dangling, 0 orphan ledger entries
#   ✓ tiers          2 downgraded to reported (forum-sourced), marks correct
#   ✓ volatility     6 volatile claims, all dated, all with recheck links
#   ✓ contested      1 cluster both_stand, both claims rendered
#   ✓ licenses       images.mode=none, nothing to check
#   ✓ lint           0 errors, 2 warns waived with reasons
#   PASS

# 9. derive the other artifacts from the same ledger, no re-research
sb plan --type explainer && # agent composes
sb verify --artifact explainer
sb plan --type podcast && sb tts-plan && sb verify --podcast

# 10. ship
sb package --public --out dist/
#   dist/answer.html  dist/explainer.html  dist/podcast.script.json
#   dist/PROVENANCE.json  dist/SHA256SUMS
```

**What the artifact ends up saying**, and why that is the point: the short answer is that the two
schemes signed an agreement, the operator's own live interoperability list does not include India, and
the correct plan is cash plus a local wallet. That answer is only trustworthy because the reader can
see a `contested` mark on the disagreement, a `moving` mark with a February date on the scale figure,
a `reported` mark on the traveller-thread evidence, and a ledger entry for every one of them.

**Offline variant.** `make demo-freeze` captures the live sources into `examples/demo/frozen/` on first
run. Afterwards `sb init --from examples/demo/frozen` reproduces the entire demo with the network off,
which is also how AT-01 through AT-22 stay hermetic. The repository ships the runbook and the URLs,
never the captured third-party text.
