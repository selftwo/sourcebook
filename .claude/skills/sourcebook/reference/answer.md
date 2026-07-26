# Playbook: `answer`

The flagship. A long-form interactive reading artifact that answers one question and shows
its work. `build/answer.html`.

## Shape

Sticky contents, an in-page ledger, per-claim marks, and a colophon. Interactivity is
enhancement only: the whole document reads with JavaScript disabled.

Sections, in this order, and cut any that has nothing to say:

1. **The short answer.** Two or three sentences. The finding, the date it was true, and what
   the reader should do. If the reader stops here they should still be correctly informed.
2. **What was actually established.** The primary sources, in the order that builds the case.
3. **What is disputed.** Every `contested` claim, both sides, with the adjudication reason
   paraphrased. This section is mandatory whenever any cluster resolved `both_stand`.
4. **What is not known.** Absences are findings. Say what the sources do not say.
5. **What to do.** Recommendations, marked `thin`, because they are yours.
6. **Ledger.** Legend once, then the injected `<ol class="ledger">`.

## Rules specific to this type

- The thesis in `plan.json` is the first sentence of section 1, near enough that a reader
  cannot tell them apart.
- Every section in `plan.json` lists its `claim_ids`, and every one of them is rendered with
  a `data-claim` attribute. `sb verify` checks both directions.
- A paragraph carrying more than two claim ids is doing too much. Split it.
- The contents list is generated from your section headings, not from a guess.
- Do not open with background. Open with the answer.

## Composing

```
sb template answer
```

Then rewrite it. The template is a floor: correct type scale, correct contrast, correct
marks, zero external references. Everything about its layout is yours to replace, and
`sb lint` will tell you if the replacement drifted.

When the prose is done:

```
sb ledger --html --out build/ledger.html
sb inject build/answer.html --ledger build/ledger.html
sb verify
```
