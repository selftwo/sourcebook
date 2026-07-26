---
name: sourcebook
description: Turn a pile of URLs and files into a claim-cited artifact (interactive HTML answer, one-slide explainer, deck, brief, infographic, or podcast script) where every factual sentence is pinned to a byte-exact quote in a source. Use when the user asks a research question, gives you sources to synthesize, or wants a document they can check.
version: 0.1.0
license: Apache-2.0
---

# sourcebook

You do the judgment. A small Python CLI does everything deterministic. The contract between
you is a directory of JSON and Markdown files.

**Two rules above all others:**

> Never write a sentence of fact you cannot cite with `sb find`.
> Never make a contradiction disappear by choosing a side quietly.

## 0. Setup, once

`SKILL_DIR` is the directory holding this file. The CLI is at `SKILL_DIR/../../scripts/sb.py`
in a checkout, or wherever `install.py` put it. Define `sb` as `python3 <that path>` and use
it for everything below. Then:

```
sb status
```

Do exactly what its `next` line says. If there is no workspace, `sb init --question "<the
user's question>"`. `sb status` derives the state from the files on disk, not from memory, so
it is correct after a context compaction, a crash, or a handoff to a different agent.

Defaults are already sane: `web_fetch=agent`, `image_gen=none`, `tts=none`. Only run
`sb config set capabilities.image_gen=agent` if you actually have that capability and the
artifact needs it.

## 1. The loop

| State | You do | Command |
|---|---|---|
| INIT | create the workspace | `sb init --question "..."` |
| COLLECT | judge each source's tier and write the reason | `sb add <url\|file> --tier A --reason "..."` |
| EXTRACT | nothing, unless a source needs you | `sb extract` |
| CHUNK / INDEX | nothing | `sb chunk && sb index` |
| PLAN | decide the shape | `sb plan --type answer --title "..." --thesis "..."` then edit `plan.json` |
| GROUND | read, decide what is worth claiming, get spans | `sb search`, `sb find`, `sb claim add --file c.json` |
| ADJUDICATE | judge every flagged conflict | `sb contradictions` then `sb adjudicate --file a.json --apply` |
| COMPOSE | write the HTML | `sb template answer` then design past it |
| RENDER | never hand-write the ledger | `sb ledger --html --out build/ledger.html && sb inject build/answer.html --ledger build/ledger.html` |
| VERIFY | fix what it names | `sb verify` |
| PACKAGE | ship | `sb package --out dist/` |

If a source is a PDF the script cannot read, a scanned image, or a page that needs a live
browser, it will set `status: needs_extraction` and tell you. Read the raw file yourself with
whatever you have, write `sources/<id>/normalized.md`, and re-run `sb extract`. The provenance
record is identical either way.

## 2. Tiers, assigned by you at `sb add` time

**A** primary or institutional: the party that holds the fact.
**B** credible secondary with named accountability: bylined dated journalism, peer review.
**C** pattern evidence: forums, reviews, social, vendor marketing. Real signal about
behaviour, not authority about fact.
**D** unknown provenance: undated pages, content farms, scraped mirrors.

`--reason` is required and is checked. "Tier A because it is the operator of the scheme and
therefore the primary source for its own live status" is a reason. "Official" is not.

## 3. GROUND: how a claim gets made

Read `reference/evidence.md` **before writing the first claim.** Not optional.

The move is always the same:

```
sb search "cross-border interoperability live partners" -k 8
sb quote src_9f2a1c4e0b71 12840 12946        # read the span you found
sb find src_9f2a1c4e0b71 "the exact sentence you just read"
#   -> src_9f2a1c4e0b71  12840..12886  exact  (1 match)
```

You never compute an offset. You paste a sentence and get a span. If `sb find` exits 1, the
text is not in the source: re-read and paste it byte-exact. There is no path where an
approximate quote becomes a citation.

Then write the claim to a file and add it (a file, not shell-quoted JSON: quotes contain
apostrophes and quotation marks and argv is where that goes wrong):

```json
{ "text": "...", "topic_key": "domain.subject.aspect", "kind": "fact",
  "confidence": "verified", "volatile": true, "as_of": "2026-02-12",
  "recheck": "https://...",
  "evidence": [{"source_id": "src_9f2a1c4e0b71", "start": 12840, "end": 12886,
                "quote": "the exact bytes"}] }
```

`sb claim add --file claim.json`. Claim ids are content-addressed, so re-adding the same text
is idempotent and editing the text mints a new claim rather than silently mutating one an
artifact already cites.

## 4. ADJUDICATE: the part that cannot be automated

`sb contradictions` clusters active claims by `topic_key` and flags numeric divergence, date
divergence, polarity conflict, explicit links, and recency spread. It does not decide, and
false positives are expected and cheap.

You choose one of four outcomes and write the reason:

- `supersede` one is correct, the other stale or lower-tier. Precedence: higher tier, then
  more recent `as_of` for a volatile claim, then closeness to the fact. If none of those
  break the tie, it is not a supersede.
- `both_stand` a genuine live disagreement, or two true claims a reader will conflate. Both
  become `contested` and **both must appear in the artifact.**
- `scope_split` a false positive; they were never about the same thing. Fix a `topic_key`.
- `retract` one claim was a misreading of its own source.

Write them to a file and run `sb adjudicate --file adj.json --apply`. Nothing is ever deleted;
a superseded claim keeps its evidence and gains `superseded_by`. `--apply` is not optional
bookkeeping: without it the outcome never reaches the claims, and `sb verify` fails with
`E-ADJ-UNAPPLIED`. If a new claim later joins an adjudicated cluster, the cluster reopens and
you adjudicate it again over the full membership.

## 5. COMPOSE

Read `reference/visual.md` **before writing the first line of HTML.** Not optional.
Then read the playbook for the type you are building: `reference/answer.md`,
`explainer.md`, `deck.md`, `brief.md`, `infographic.md`, or `podcast.md`.

`sb template <type>` copies a working, lint-clean starting point into `build/`. It is the
floor, not the ceiling. Design past it; the lint gate is what keeps that from drifting.

The citation contract is exactly two markers:

```html
<p data-claim="clm_4b18d0e2a339">The sentence.<sup class="ref"><a href="#c-clm_4b18d0e2a339">11</a></sup>
<span class="mark m-checked">checked</span> <span class="mark m-moving">moving</span></p>
```

Marks, and nothing else: `m-checked`, `m-reported`, `m-contested`, `m-moving`, `m-thin`.
The mark follows from the claim: verified→checked, reported→reported, contested→contested,
inferred→thin, plus moving whenever `volatile`. An `inferred` claim may never carry a
superscript. The legend appears exactly once.

Then render the apparatus. Never hand-write a ledger entry:

```
sb ledger --html --out build/ledger.html
sb inject build/answer.html --ledger build/ledger.html
```

For images, read `reference/images.md` and `reference/licensing.md`. The default is
`images.mode: none`, and the no-image path is meant to be the good one.

## 6. Ship gate

```
sb verify
```

Exit 0 or it does not ship. Paste the gate output to the user. Do not report the work
complete on any other basis.

If it fails, fix the thing it names. `sb verify` reports one line per finding with an error
code and a subject.

**Escalation.** After three failed verify loops, stop. Tell the user which claims and which
error codes are blocking, and ask how to proceed. Silently loosening a claim to make a gate
pass is the exact failure this kit exists to prevent.

**Recovery.** BLOCKED clears with one command, and only after the user has decided what
changes: `sb unblock --reason "<what the user decided>"`. It resets the loop counter and
records the reason; it waives no gate, so the next `sb verify` still has to pass.

**Blocking conditions.** Go to BLOCKED and ask, do not improvise: fewer than two independent
tier A/B sources for a factual question; the central claim has only tier C or D evidence; a
source is paywalled or robots-disallowed with no lawful alternative; a required capability is
absent and the chosen artifact type depends on it.
