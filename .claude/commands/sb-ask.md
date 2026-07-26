---
name: sb-ask
description: Run the whole loop for a question and produce a verified, claim-cited HTML answer.
---

Load the `sourcebook` skill, `reference/evidence.md`, `reference/visual.md`, and
`reference/answer.md`.

The question is `$ARGUMENTS`. Run the full loop: init if needed, add and tier the sources,
extract, chunk, index, plan, ground every claim with `sb find`, adjudicate every flagged
cluster, compose `build/answer.html` from `templates/answer.html`, inject the rendered ledger,
and gate.

Do not report the work complete until `sb verify` exits 0. Paste its output.

If you cannot ground the central claim in at least two independent tier A/B sources, stop and
say so rather than shipping a confident-looking artifact.
