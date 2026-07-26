---
name: sb-deck
description: Derive an N-slide deck with speaker notes carrying the citations from the existing ledger, with no re-research.
---

Load the `sourcebook` skill, `reference/visual.md`, and `reference/deck.md`.

The ledger is already built. Do not collect new sources unless the user asks. Run:

```
sb plan --type deck --title "$ARGUMENTS"
```

Edit `plan.json` so every section lists the claim ids it will render, then
`sb template deck`, compose past the template, and:

```
sb ledger --html --out build/ledger.html
sb inject build/deck.html --ledger build/ledger.html
sb verify --artifact deck
```

Every `contested` claim must appear in this artifact too. A different format is not a
licence to drop the disagreement.
