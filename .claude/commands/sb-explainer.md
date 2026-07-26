---
name: sb-explainer
description: Derive a one-screen, one-idea explainer from the existing ledger, with no re-research.
---

Load the `sourcebook` skill, `reference/visual.md`, and `reference/explainer.md`.

The ledger is already built. Do not collect new sources unless the user asks. Run:

```
sb plan --type explainer --title "$ARGUMENTS"
```

Edit `plan.json` so every section lists the claim ids it will render, then
`sb template explainer`, compose past the template, and:

```
sb ledger --html --out build/ledger.html
sb inject build/explainer.html --ledger build/ledger.html
sb verify --artifact explainer
```

Every `contested` claim must appear in this artifact too. A different format is not a
licence to drop the disagreement.
