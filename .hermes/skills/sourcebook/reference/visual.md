# Visual judgment: the half a linter cannot see

Read this before writing the first line of HTML. `sb lint` catches the mechanical half:
gradient text, side stripes, cream grounds, contrast, external references, motion without an
escape. It cannot catch any of the following, and these are the ones that make an artifact
look generated.

## Category reflex, at two orders

**First order.** If someone could guess the palette and the type from the topic alone, that
is the reflex. Fintech becomes blue and sans. Sustainability becomes green. Research becomes
serif on cream.

**Second order.** If they could guess it from the topic plus the obvious anti-reference
("a research artifact, therefore *not* a dashboard, therefore editorial serif on warm
paper"), that is still the reflex, one step further out.

Rework until neither is guessable. Reach for a ground, a rule weight, and an accent that
belong to *this document's argument*, not to its genre.

## No illustration you cannot render for real

Sketchy SVG, hand-drawn doodles, `feTurbulence` paper grain, crude 20-path scenes: all of it
reads as a model that wanted a picture and settled. If there is no real asset, ship no
illustration. Structure, rules, type, and color carry the page perfectly well. The `none`
image path is the default and it is meant to be the good one.

## SVG is for data, not decoration

Timelines, relationship maps, comparisons, small multiples. If a figure does not encode a
value that exists in the ledger, delete it. Every axis is labeled, no bar is truncated, no
3D, no chart junk.

## The specific bans

- **Cards are the lazy answer.** Nested cards are always wrong.
- **The hero-metric template is banned.** Big number, small label, three supporting stats,
  gradient accent. It is the SaaS cliché, and it makes cited numbers look like marketing.
- **Motion is intentional or absent.** One uniform entrance animation applied to every
  section is the tell. If you cannot say what a specific transition is *for*, delete it.
- **Every mark earns its place.** If the artifact renders `checked` on every sentence, the
  mark has stopped carrying information.
- **No blanket disclaimer.** Uncertainty is placed on the sentence, not stacked at the top.

## The design floor, non-negotiable

Body text at least 4.5:1. Measure 60 to 75 characters. Type scale ratio at least 1.25 between
steps. At most three families. Tested at 360px, 768px, and 1200px with no horizontal
overflow. Every animation has a reduced-motion path. **All content readable with JavaScript
disabled**: interactivity may enhance, it may not gate.

## Prose

The linter warns on em dashes, on the buzzword list, and on stock rhetorical moves ("X
theater", "not just X, it's Y"). Those warnings are a floor, not a style. Above them:

- Write the finding, then stop. Do not restate it as a summary.
- Prefer the concrete noun to the abstract one. "The gangway reader" beats "the touchpoint".
- Do not narrate the process. Nobody wants to read that you searched, considered, and
  synthesized.
- A sentence with no claim id should not assert a fact. If it does, either cite it or cut it.
