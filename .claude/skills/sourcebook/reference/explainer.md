# Playbook: `explainer`

**One screen, one idea.** `build/explainer.html`.

## Hard constraints

- At most 60 words of body copy. Count them.
- At most 5 claims.
- One visual, and only if it encodes a number from the ledger.
- Fits 16:9 (1920x1080) and portrait phone (390x844) without scrolling or overflow.
- A compact footnote strip instead of a full ledger section, still with real ledger entries
  and real anchors.

## What it is for

The explainer is what someone screenshots. It has to survive being read in eight seconds and
being wrong-quoted in a group chat. That is why the marks stay visible and the date stays on
the claim: the screenshot has to carry its own provenance.

## The discipline

The hardest part is choosing which single claim is the idea. Do not answer the question and
then also gesture at the nuance. Pick the sentence that changes what the reader does, put the
mark on it, and let the ledger strip carry the rest.

If the honest answer needs three sentences of qualification, this is the wrong artifact type.
Build a `brief` or an `answer` instead and say so.

```
sb plan --type explainer --title "..." --thesis "..."
sb template explainer
sb ledger --html --out build/ledger.html
sb inject build/explainer.html --ledger build/ledger.html
sb verify --artifact explainer
```
