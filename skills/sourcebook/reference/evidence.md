# Evidence: tiers, confidence, contradiction, uncertainty

Read this before writing the first claim.

## What is worth claiming

A claim is a sentence a reader could act on or check. Not a topic, not a summary, not a
paraphrase of a whole page. If you cannot point at the sentence in the source that makes it
true, it is not a claim yet.

Three things are claims that people routinely fail to record:

- **Absence.** "The operator's live interoperability list does not include Harbour Transit"
  is citable, and it is often the finding. Say what is not there.
- **Hedging.** If the source itself hedges ("expected to", "phased through 2026"), the claim
  inherits the hedge and the confidence drops to `reported`. Do not launder a maybe.
- **Date of truth.** For anything that moves, the claim is not "X is true", it is "X was
  true on <date>, per <source>".

## Tiers

| Tier | Definition | Examples |
|---|---|---|
| A | Primary or institutional. The party that holds the fact. | Standards bodies, regulators, the paper itself, an organization's own docs, filings, primary datasets |
| B | Credible secondary with named accountability. | Bylined dated journalism, peer-reviewed secondary literature, reference works |
| C | Pattern evidence. Real signal about behaviour, not authority about fact. | Forums, product reviews, social posts, vendor marketing, aggregators |
| D | Unknown provenance. | Undated pages, content farms, unattributed generated text, scraped mirrors |

Tier is about **position relative to the fact**, not about how much you like the source. A
national newspaper reporting what a regulator said is tier B for the regulator's position and
tier A for nothing. The regulator's own page is tier A for its own status and tier C for its
competitor's.

`tier_reason` is checked for every A and every D. Write the position, not the brand.

## Confidence, and how it is earned

| Confidence | Earned when | Renders as |
|---|---|---|
| `verified` | At least one verifying quote from tier A or B, no live conflict | `checked` |
| `reported` | Only tier C evidence, or a single-source surprising claim, or the source hedges | `reported` |
| `contested` | Cluster adjudicated `both_stand`. Both sides cited in the artifact. | `contested` |
| `inferred` | Your own synthesis. Exactly zero evidence entries. Never carries a superscript. | `thin` |
| `unsupported` | Nothing supports it. | Cannot ship. `sb verify` exit 2 |

Plus one orthogonal mark: `volatile: true` renders as `moving` and requires a non-null
`as_of` and a non-null `recheck` URL, whatever the confidence.

`sb verify` enforces the downgrades you would otherwise be tempted to skip:

- A `number`, `date`, or `entity` claim cited only to tier C or D cannot be `verified`
  (`E-TIER-WEAK`).
- Any tier D evidence caps the claim at `reported` (`E-TIER-D`).
- `inferred` with evidence, or non-`inferred` with none, is `E-CONF-MISMATCH`.

## topic_key

A dotted lowercase slug naming **the thing being claimed about**, not the source and not the
section: `northline.meridian.live`, `meridian.cards.active`, `harbour.agreement.signed`.

This is load-bearing. Contradiction detection clusters on it. Two claims that a reader would
compare must share a `topic_key`; two claims that only sound similar must not. Getting this
wrong is how a real conflict goes undetected, and it is also how you generate noise.

## Uncertainty, placed

- **`thin` is a promise, not an escape hatch.** Marking something `thin` to avoid finding a
  source is the abuse this rule names. An inferred claim carries no citation because there is
  no source, not because you did not look.
- **Never print a date you have not verified.** Festival dates, prices, availability, version
  numbers. If it came from an aggregator, print the official calendar link instead.
- **Uncertainty is placed, not appended.** The mark sits on the sentence it qualifies. A
  blanket "this may be inaccurate" banner at the top is banned and is not a substitute.
- **Mark what varies.** If every sentence renders `checked`, the mark has stopped carrying
  information. That is a signal you are marking rather than judging.
- **One legend, once.** Near the first mark, not in every section.

## When to stop and ask

Go to BLOCKED rather than improvising when:

- there are fewer than two independent tier A/B sources for a factual question;
- the central claim of the question rests only on tier C or D evidence;
- a source is paywalled or robots-disallowed and no lawful alternative exists;
- the artifact type needs a capability that is set to `none`.

Ask the user. A thin artifact that admits it is thin is worth more than a confident one.
