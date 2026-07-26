# sourcebook

**Turn a folder of links and files into a single HTML page you can actually trust.**

Drop the kit into any coding agent, ask a question, and get back a self-contained artifact
where every factual sentence is pinned to an exact quote in a source you supplied. Verified
claims are marked. Disputed claims are shown from both sides, because the gate will not let
the page pick one quietly. Dated claims carry the date they were true and a link to recheck.

The verification is not a model's opinion. It is a byte-for-byte string comparison run by a
dependency-free Python script, so a made-up quote cannot ship. Period.

No server. No account. No API key. No vector store. The output is one file that opens from
disk, works offline, prints to A4, and keeps working after every service you used to build it
is gone.

```
$ sb verify
sb verify  ~/work/ferry-question
  . schemas        4 sources, 12 claims
  . normalizer     4 sources at v1
  . quotes         12/12 byte-exact
  . confidence     12 claims consistent
  . tiers          0 claim(s) correctly held at reported
  . volatility     5 volatile claim(s), all dated
  . clusters       1 cluster(s), 2 adjudicated
  . plan           11 claim(s) placed in 6 sections
  . html           10 refs resolved, 11 ledger entries, 10 ordinals
  . licenses       images.mode=none, nothing to check
  . lint           0 errors, 0 waived, 0 unresolved
  PASS
```

**See it:** [`examples/demo/answer.html`](examples/demo/answer.html) is a real artifact, built
by the pipeline in this repo from the four local example sources in
[`examples/demo/sources/`](examples/demo/sources/), and it passes every gate above. Open it
from `file://`.

---

## Clone to a verified artifact in ten minutes

```bash
git clone <this repo> sourcebook && cd sourcebook

# 1. Install the skill and commands into whichever harness you use.
python3 scripts/install.py --harness claude       # or agents | codex | cursor | hermes | all
export PATH="$PWD/.sourcebook/bin:$PATH"          # gives you `sb`

# 2. Watch the whole thing run, offline, on the shipped example sources.
make demo

# 3. Watch it refuse to lie.
make demo-tamper
```

Then, in your agent, in any directory:

```
/sourcebook            # router: prints the derived state and the one next command
/sb-ask <question>     # runs the whole loop and produces a verified answer.html
```

Those two are the whole user-facing vocabulary. Everything else (`/sb-add`, `/sb-explainer`,
`/sb-deck`, `/sb-brief`, `/sb-infographic`, `/sb-podcast`, `/sb-verify`, `/sb-ledger`) is a
derivation over a ledger you already built, and `sb status` tells you when you want one.

### Without an agent

`sb` is a normal CLI. The parts a script can do deterministically, it does:

```bash
sb init --question "Can a Harbour card pay a fare on a Northline ferry right now?"
sb add ./clippings/operator-page.md --tier A --reason "the operator's own status page"
sb add ./clippings/trade-report.md  --tier B --reason "bylined dated trade reporting"
sb extract && sb chunk && sb index
sb search "cross-border interoperability live partners" -k 8
sb find src_1823e227204b "No other partner scheme is live at this time."
#   -> src_1823e227204b  777..822  exact  (1 match)
```

The judgment (what to claim, how to adjudicate a conflict, what the page should say) is the
part a person or an agent does.

---

## The one architectural decision

> **Scripts never reason. The agent never computes.**

Deterministic Python owns fetching, normalizing, hashing, chunking, lexical search, offset
resolution, citation verification, contradiction detection, design linting, license checking,
ledger rendering, and packaging.

The running agent owns judgment: what to search, what a source means, which claim is worth
making, how to adjudicate a conflict, what the artifact should say, how it should look.

The contract between them is a directory of JSON and Markdown files. No database, no service,
no daemon, no vector store, no embedding call, and no model call from any script.

## The citation model

**One canonical text per source. Every citation is a byte span into that text.**

`sources/<src_id>/normalized.md` is written once and never edited, and its SHA-256 is
recorded. A citation is `{source_id, start, end, quote}`. Verification is
`normalized_md[start:end] == quote`. No model, no fuzzy match, no embedding, no tolerance.

Three things fall out of that for free:

1. **Chunking is not load-bearing.** Re-chunk with any parameters; every citation still
   verifies. Chunks are a retrieval convenience, not a provenance record.
2. **Hallucinated quotes are mechanically unshippable.** A quote that was never in the source
   fails `sb verify` with exit code 2 and the offending claim id.
3. **Offsets are cheap for the agent.** It never computes one. It pastes the sentence it just
   read into `sb find` and gets the span back. If the paste is not byte-exact, `sb find`
   reports the nearest anchors and exits 1. There is no path where an approximate quote
   becomes a citation.

## The five marks

Inline, small, never decorative. This is the visible product.

| Mark | Means | The reader should |
|---|---|---|
| `checked` | Verified against a tier A or B source. | Trust it. |
| `reported` | Real signal, weaker authority. Pattern evidence or a lone surprising source. | Trust the shape, not the number. |
| `contested` | Sources disagree and both are shown. | Read both. |
| `moving` | True as of a printed date, and the kind of thing that changes. | Recheck at the link. |
| `thin` | The author's inference. No source, because there is not one. | Weigh it as opinion. |

`thin` is a promise, not an escape hatch: an inferred claim may never carry a citation
marker, and `sb verify` enforces that.

## Contradictions cannot be tidied away

`sb contradictions` clusters active claims by `topic_key` and flags numeric divergence, date
divergence, polarity conflict, explicit links, and recency spread. It does not decide, and
false positives are expected and cheap.

The agent adjudicates, in writing, with one of four outcomes: `supersede`, `both_stand`,
`scope_split`, `retract`. Nothing is ever deleted; a superseded claim keeps its evidence and
gains `superseded_by`.

`both_stand` puts an obligation on the artifact. `sb verify` checks that every `contested`
claim id appears in the rendered HTML (`E-CONTESTED-HIDDEN`). A tidy artifact that quietly
picks a side is exactly the failure this kit exists to prevent.

## Design as a gate, not a suggestion

`sb lint` is 28 rules with stable ids, split by who can check them. Errors block the ship gate
and **cannot be waived**. Warnings must be acknowledged in `sourcebook.json.lint_waivers` with
a written reason or they become errors. That asymmetry is the point.

```
ERROR slop.cream-band            build/answer.html:3  body
      page background sits in the cream band (OKLCH L=0.96 C=0.014 h=85)
      The warm off-white page is the default 'editorial' reflex. Commit to a real ground.
```

Rules cover gradient text, side stripes, over-rounding, ghost cards, stripe backgrounds, the
cream band, the purple-gradient AI palette, hero shouting, tracking floors, eyebrow reflexes,
card-grid clones, buzzwords, em dashes, stock rhetorical moves, WCAG contrast at both sizes,
reduced motion, JS-gated content, tap targets, alt text, `lang`/`title`/viewport, focus rings,
external references, arbitrary `z-index`, and overflow risk.

The linter refuses to guess. A `var()` chain it cannot resolve is counted in an `unresolved`
tally and printed, and no rule fires on a value it could not resolve. Guessing is worse than
reporting a gap.

The half a machine cannot check (category reflex at two orders, no fake illustration, the
banned hero-metric template, marks that must vary to carry information) lives in
[`skills/sourcebook/reference/visual.md`](skills/sourcebook/reference/visual.md), and the
skill makes the agent read it before writing the first line of HTML.

## Artifact types

Six views over the same ledger. All pass the same gates, and none of them requires an image.

| Type | Output | Shape |
|---|---|---|
| `answer` | `build/answer.html` | The flagship. Long-form reading artifact, sticky contents, in-page ledger, per-claim marks. |
| `explainer` | `build/explainer.html` | One screen, one idea. 60 words of body copy, one visual, five claims. |
| `deck` | `build/deck.html` | N slides, keyboard and swipe nav, `?print` mode. One claim per slide; speaker notes carry the citations. |
| `brief` | `build/brief.html` | Dense one-pager, `@page` rules for A4 and Letter. This is the PDF answer. |
| `infographic` | `build/infographic.html` | Data-forward. Every number is a cited claim of `kind: number`. Inline SVG, labeled axes, no chart junk. |
| `podcast` | `build/podcast.script.json` + `.md` + `.ttsplan.json` | Outline then transcript, with a parallel citation track. |

### Why HTML and not PDF

A citation in this design is a link, and links need a live document. The superscript jumps to
a ledger entry with a tier badge and a recheck URL. Marks sit inline on the sentence they
qualify. The file opens from `file://`, offline, on a phone. A PDF flattens the apparatus into
footnotes and kills the recheck link.

The PDF question still has an answer: `brief` carries `@page` rules, so printing gives you one
for free. **HTML is the medium; PDF is one of its stylesheets.**

### Podcasts ship a plan, not audio

sourcebook has no TTS dependency and implements no adapter. `sb tts-plan` emits a
provider-agnostic `podcast.ttsplan.json` (one segment per line, deterministic pauses) plus
`build/audio/concat.txt` in ffmpeg concat-demuxer format. Any speech tool consumes it. A
missing `build/audio/` never fails a gate: the script and its citation track are the
deliverable. Every line is typed `factual`, `opinion`, `banter`, or `transition`, and
`sb verify --podcast` requires every factual line to carry a verifying claim id.

## Images: generate, source, or none

`none` is the default and is meant to be the good path: zero `<img>` elements, and visual
interest from typography, rule work, a committed palette, tables, and inline SVG that encodes
ledger data. Every template ships a complete no-image design.

`source` requires a `credits.json` entry per asset, a license from the permitted set, and a
visible credit string for `CC BY*`. `NC`, `ND`, and unknown licenses fail.

`generate` uses whatever image capability your harness has. sourcebook ships none, calls none,
and does not care which it is. Three rules are enforced or stated plainly: a generated image
is never evidence and may not illustrate a cited claim (`E-IMG-EVIDENCE`); it renders a
visible `Generated illustration` label (`E-IMG-UNLABELED`); and the prompt is recorded
verbatim, because that is provenance rather than trivia.

## Resumability

`sb status` derives the state from the files on disk. It does not trust the stored value. If
`index/lexical.json` is missing, the state is `CHUNK` and the next command is `sb index`,
whatever the manifest says. That is what lets the work survive a context compaction, a crash,
or a different agent picking it up tomorrow.

After three failed verify loops the manifest goes to `BLOCKED` and `sb status` prints an
escalation instruction instead of a next command. Silently loosening a claim to make a gate
pass is the failure that rule exists to prevent.

## Repository layout

```
SKILL.md                      portable skill, vendorable on its own
skills/sourcebook/            the same skill plus its on-demand reference files
commands/                     harness-neutral slash commands
scripts/sb.py                 the CLI (dispatch only)
scripts/sourcebook/           the implementation package, standard library only
scripts/install.py            copies the skill and commands into a harness
schemas/                      JSON Schema draft 2020-12 for every contract
templates/                    six inert, lint-clean HTML shells
tests/                        the twenty acceptance tests and their fixtures
examples/demo/                the runbook, the local example sources, the built artifact
.claude/ .agents/ .hermes/    pre-installed adapters, so the repo works as a checkout
```

## Requirements

Python 3.10 or newer. **No required dependencies.** `pypdf` improves PDF ingestion if it
happens to be installed; its absence degrades a source to `needs_extraction` (the agent reads
it instead) and never to a failure.

## Development

```bash
make test        # the 20 acceptance tests, hermetic, no network
make lint        # every template through the design rule registry
make demo        # rebuild examples/demo/answer.html from the local sources
make install     # refresh the checked-in .claude/.agents/.hermes adapters
```

Exit codes are the API: `0` pass, `1` usage or input error, `2` gate failure.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Vendoring `skills/sourcebook/` into a
private repo is the expected use, which is why it is Apache and not GPL.

The example sources in `examples/demo/sources/` are synthetic: Northline Ferries, the Harbour
Transit Authority, the Meridian Card, and Harbour Trade Weekly are invented and describe no
real organisation. The mechanism demonstrated on them is real.
