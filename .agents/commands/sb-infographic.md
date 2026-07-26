---
name: sb-infographic
description: Derive a data-forward page where every number is a cited claim from the existing ledger, with no re-research.
---

Load the `sourcebook` skill, `reference/visual.md`, and `reference/infographic.md`.

The ledger is already built. Do not collect new sources unless the user asks. Run:

```
sb plan --type infographic --title "$ARGUMENTS"
```

Edit `plan.json` so every section lists the claim ids it will render, then
`sb template infographic`, compose past the template, and:

```
sb ledger --html --out build/ledger.html
sb inject build/infographic.html --ledger build/ledger.html
sb verify --artifact infographic
```

Every `contested` claim must appear in this artifact too. A different format is not a
licence to drop the disagreement.
