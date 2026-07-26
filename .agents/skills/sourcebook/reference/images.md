# Images: generate, source, or none

`plan.json.images.mode` is one of three. **`none` is the default and must be fully excellent.**

## `none`

Zero `<img>` elements. Visual interest comes from typography, rule work, a committed palette,
tables, CSS-drawn diagrams, and inline SVG that encodes ledger data. Every artifact type has
a complete shippable no-image design in `templates/`. The gate suite runs identically. An
artifact is never weaker for having no images. It is only weaker for having bad ones.

Choose `none` unless you can answer: what does this specific image tell the reader that the
type and the structure cannot?

## `source`

Fetch openly licensed images. Every asset gets an `assets/credits.json` entry:

```json
{
  "harbour-terminal.jpg": {
    "origin": "sourced",
    "source": "https://upload.wikimedia.org/wikipedia/commons/...",
    "credit": "A. Photographer / Wikimedia Commons",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "retrieved_at": "2026-07-26T09:41:00Z",
    "sha256": "..."
  }
}
```

`sb licenses` enforces coverage, the permitted license set, and visible attribution for
`CC BY*`. `NC`, `ND`, `unknown`, and absent licenses fail. `SA` warns, because the composite
artifact inherits a share-alike obligation.

## `generate`

Use whatever image capability your harness gives you. sourcebook ships none, calls none, and
does not care which it is. Record it:

```json
{
  "diagram-flow.png": {
    "origin": "generated",
    "generator": "<model or tool name>",
    "prompt": "<the exact prompt used, verbatim>",
    "created_at": "2026-07-26T10:22:00Z",
    "sha256": "..."
  }
}
```

Hard rules:

- **A generated image is never evidence.** It may not sit adjacent to a `data-claim` element
  as illustration of that claim's content (`E-IMG-EVIDENCE`).
- **No real people, no real logos, no real places presented as documentary.** A generated
  photo of a real location is a fabrication with a caption.
- Every generated image renders a visible `Generated illustration` label (`E-IMG-UNLABELED`).
- Alt text describes what the image shows, not that it was generated.
- The prompt is recorded verbatim. That is provenance, not trivia.

## If the capability is absent

`sb config set capabilities.image_gen=none` and take the `none` path. There is a working path
for every combination, and no artifact type requires an image to pass its gates.
