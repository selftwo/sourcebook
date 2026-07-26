---
name: sb-brief
description: Derive a dense one-pager that prints to A4 and Letter from the existing ledger, with no re-research.
---

Load the `sourcebook` skill, `reference/visual.md`, and `reference/brief.md`.

The ledger is already built. Do not collect new sources unless the user asks. Run:

```
sb plan --type brief --title "$ARGUMENTS"
```

Edit `plan.json` so every section lists the claim ids it will render, then
`sb template brief`, compose past the template, and:

```
sb ledger --html --out build/ledger.html
sb inject build/brief.html --ledger build/ledger.html
sb verify --artifact brief
```

Every `contested` claim must appear in this artifact too. A different format is not a
licence to drop the disagreement.
