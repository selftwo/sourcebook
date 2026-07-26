# Playbook: `brief`

A dense one-pager that prints correctly at A4 and Letter. `build/brief.html`.

## Why it exists

This is the answer to "can I have a PDF". HTML is the medium; print is one of its
stylesheets. `@page` rules, no fixed positioning, footnote ledger in columns, and the
superscripts still resolve on screen.

## Hard constraints

- One page at A4 with 16mm margins, ideally. Two if the ledger is long; the ledger may break.
- Structure carries it: headings, a small table, rules. No decorative anything.
- Inline superscripts, footer ledger. No sticky contents, no scroll effects.
- Body at 0.8rem in print is fine. Body at 0.8rem on screen is not; keep the screen size at
  1rem and shift only in `@media print`.

## Structure

A masthead with the finding and its date, then: what is the case, what is disputed, what to
do, then the ledger. An "at a glance" table in a side column is often the fastest way for a
reader to get the shape, and every row in it must be a claim in the ledger.

```
sb plan --type brief --title "..." --thesis "..."
sb template brief
sb ledger --html --out build/ledger.html
sb inject build/brief.html --ledger build/ledger.html
sb verify --artifact brief
```
