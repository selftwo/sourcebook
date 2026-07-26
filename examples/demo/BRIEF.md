# The sourcebook demo

**Question:** Can a Harbour card be used to pay a fare on a Northline ferry right now?

Chosen because it exercises every mechanism at once: a primary operator source, a joint
announcement, secondary trade reporting, forum pattern evidence, a genuine contradiction
between "an agreement was signed" and "the service is live", a number that two sources
disagree about, and a claim that is volatile by nature.

> The four sources in `sources/` are **synthetic**. Northline Ferries, the Harbour Transit
> Authority, the Meridian Card, Calder Transit, Vantis Rail, and Harbour Trade Weekly are
> invented and describe no real organisation. The mechanism demonstrated on them is real:
> every citation in the built artifact verifies byte-for-byte against those files, and
> breaking one character fails the gate.

## Run it

```bash
make demo            # build and gate, offline, about ten seconds
make demo-tamper     # build, then break one quote and watch sb verify refuse
```

`build.py` does everything a script can do deterministically. Everything a person judged is
checked in beside it as data, so the demo reproduces without a model:

| File | What it is | Who decided it |
|---|---|---|
| `sources/*.md` | the corpus | the person who collected it |
| `build.py` `SOURCES` | tier and `tier_reason` per source | judgment |
| `author.py` | the twelve claims and the two adjudications | judgment |
| `plan.json` | the artifact's sections and which claims land in each | judgment |
| `answer.src.html` | the prose and the design | judgment |
| `claims.json`, `adjudications.json` | generated from `author.py` with content-addressed ids | script |
| `answer.html` | the built, injected, gated artifact | script |

Re-run `python3 examples/demo/author.py` after editing a claim's wording; it re-derives every
`claim_id` and `cluster_id` so the checked-in files stay consistent.

## What it does, step by step

```
sb init --question "Can a Harbour card ... right now?"
sb add input/<each source> --tier <A|B|C> --reason "<why this tier>"
sb extract && sb chunk && sb index
sb adjudicate --file adjudications.json --apply
sb ledger --html --out build/ledger.html
sb inject build/answer.html --ledger build/ledger.html
sb tts-plan
sb lint build/answer.html
sb verify
sb verify --podcast
sb package --out dist
sb package --out dist --verify
```

Sources are copied into `workspace/input/` before `sb add`, so every recorded locator is
workspace-relative and the derived source ids are identical on any machine. That is why
`claims.json` can hard-code them.

## The two conflicts, and what happened to them

**`northline.harbour.live` → `both_stand`.** The operator's own page is a status claim:
Harbour is absent from the live list and a tap is declined today. The trade report is a claim
about what the signed agreement is *for*. Both are accurate about different things, and a
traveller who reads only the second one turns up at the gangway and cannot board. Both claims
are forced to `contested`, and `sb verify` checks that **both** appear in the rendered HTML.
Delete either one from `answer.src.html` and the build fails with `E-CONTESTED-HIDDEN`.

**`meridian.cards.active` → `supersede`.** 1.4 million (operator, 12 February) against
1.9 million (an industry estimate quoted by the trade press, 6 January). The operator issues
the cards and publishes the definition of an active card, so it is closer to the fact, and its
figure is five weeks more recent. Tier and recency point the same way, so this is a supersede
rather than a live disagreement. The estimate keeps its evidence and gains `superseded_by`.
Nothing is deleted; the artifact says in prose that a second figure was considered and why it
lost.

## The tamper moment

This is the thirty seconds worth showing anyone.

```bash
make demo            # PASS
make demo-tamper
```

`demo-tamper` edits one quote in `workspace/ledger/claims.json`, changing 1.4 million to
3.9 million, and runs `sb verify` again:

```
E-QUOTE-MISMATCH  clm_5add19271ae5  src_1823e227204b[410:492] is not the recorded quote
  FAIL  1 finding(s)
sb verify exited 2.
```

Then it restores the file and verifies clean. The line to say out loud: **the number in the
page is the number in the source, or there is no page.**

## What the artifact ends up saying

The two schemes signed an agreement, the operator's own live interoperability list does not
include Harbour, and the correct plan is cash, a paper ticket, or a Meridian Card. That answer
is only trustworthy because the reader can see a `contested` mark on the disagreement, a
`moving` mark with a February date on the scale figure, a `reported` mark on the
traveller-thread evidence, a `thin` mark on the recommendation, and a ledger entry for every
one of them.

Note the tenth ledger entry: its quote is withheld with a span reference rather than printed.
That is the quote budget working. Three quotes and 500 characters per source is the cap for a
shipped artifact, and `sb ledger --html` enforces it while rendering, so anyone holding the
source can still verify the citation from the offsets.

## The offline and online variants

`make demo` is the offline variant and is what the acceptance tests exercise. It needs no
network and no model.

`sources.txt` holds the locators for an online variant. The repository ships the runbook and
the URLs, never the captured third-party text. To run it, point `sb add` at your own real
sources, assign each a tier with a written reason, and follow the same steps; `sb status` will
tell you which one to run at every point.
