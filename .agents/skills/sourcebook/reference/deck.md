# Playbook: `deck`

N slides, keyboard and swipe navigation, a `?print` mode that unrolls everything for PDF.
`build/deck.html`.

## Hard constraints

- **One claim per slide.** If a slide needs two facts, it is two slides.
- Speaker notes (`<aside class="notes">`) carry the citations, so the slide itself stays a
  sentence and a number.
- Every slide is a section of an ordinary scrolling document when JavaScript is off. Never
  hide slides by default and reveal them with script: hide them only after script has
  confirmed it can drive the deck.
- A final ledger slide, with the legend, and the injected ledger.

## Structure

1. The question, as a title slide.
2. The answer, in one sentence, on slide two. Never build to it.
3. One slide per supporting claim, in the order that makes the case.
4. Contested claims get a single slide showing both sides. Do not put the two sides on
   consecutive slides where the second looks like a correction of the first.
5. Ledger.

## Notes

Speaker notes are not a second deck. One or two lines: where the number came from, and what
to say if someone challenges it. If you cannot say where a number came from, do not put the
number on the slide.

```
sb plan --type deck --title "..." --thesis "..."
sb template deck
sb ledger --html --out build/ledger.html
sb inject build/deck.html --ledger build/ledger.html
sb verify --artifact deck
```
