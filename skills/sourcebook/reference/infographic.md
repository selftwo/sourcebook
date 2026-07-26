# Playbook: `infographic`

Data-forward, single page. `build/infographic.html`.

## The one rule that matters

**Every number on the page is a claim of `kind: number` in the ledger.** If you cannot cite
it, it does not go on the page. This is the type where the temptation to invent a plausible
figure is highest, and it is the type where doing so is most obvious in the gate output.

## Figures

- Inline SVG only. No canvas, no chart library, no external anything.
- Every axis labeled. Every scale starting at zero unless the caption says otherwise and
  explains why. No 3D, no donuts with a number in the middle, no chart junk.
- One `<figcaption>` per figure carrying the source line, the mark, and the date.
- The figure element carries `data-claim` for the claims it encodes.
- When two sources disagree about a number, **draw both bars**. A contested number rendered
  as a single bar is the failure this kit exists to prevent.

## Layout

Figures are the structure. Prose is caption-length. If you find yourself writing three
paragraphs between two charts, you are building an `answer` with pictures; switch types.

The hero-metric template (one big number, three supporting stats, gradient accent) is banned.
It makes cited numbers look like marketing, which is the opposite of what this page is for.

```
sb plan --type infographic --title "..." --thesis "..."
sb template infographic
sb ledger --html --out build/ledger.html
sb inject build/infographic.html --ledger build/ledger.html
sb verify --artifact infographic
```
