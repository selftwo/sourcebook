# FABLE_REVIEW — product and taste review of sourcebook v0.1 spec

Reviewer: Fable 5 · 2026-07-26 · Scope: SPEC.md + BUILD.md, judged against the goal of
replacing a NotebookLM habit with a portable, source-grounded HTML artifact agent.

## Verdict

**Keep the machine. Cut the menu. Change the vocabulary.**

The core is genuinely sharp and should not be touched: byte-span citations into an immutable
`normalized.md`, verification as a string comparison, `sb find` as paste-a-sentence-get-a-span,
`sb status` as the resumability spine, and the lint gate that compiles the design rules into exit
codes. "Scripts never reason, the agent never computes" is a real architectural sentence, and the
consequence chain (hallucinated quotes are mechanically unshippable, chunking is not load-bearing)
is the best thing in the document.

The failure mode is surface area. Six artifact types, ten slash commands, a podcast subsystem that
ships no audio, a capability-declaration ceremony, and a public-redaction packaging mode are an app
wearing a kit's clothing. NotebookLM is a habit because it has roughly one verb. v0.1 should too.

### Keep
- The citation model, normalization contract, and deterministic ids. Untouched.
- The state machine, gates, revise ceiling, and `sb status` next-command output.
- The five marks (`checked` / `reported` / `contested` / `moving` / `thin`). This is excellent
  naming: human words, placed on sentences, never decorative. It is the visible product.
- The contradiction policy, especially `both_stand` obligating the artifact to show both sides.
- The full lint suite. 28 rules is a lot, but it is the design-rules skill made mechanical, errors
  are unwaivable, and the linter refuses to guess on unresolved values. This is taste as a gate and
  it is the second-best idea here.
- The `none` image path as the default that must be fully excellent.
- Stdlib-only, single-file HTML, `install.py` for four harnesses, AT-20's grep for harness-specific
  tool names.

### Cut (from v0.1, not from the design)
- **Podcast, entirely (M6, AT-15, `tts.py`, playbook, command).** NotebookLM's audio feature is
  magical because you press play. sourcebook's version is a JSON file and a plan for a tool it
  refuses to ship. That demos as homework, not magic. The citation-track idea is good; park it.
- **Explainer, deck, and infographic.** Four of the six types are variations of "a page." Ship
  `answer` (the flagship) and `brief` (which carries the print/A4 path and therefore answers the
  PDF question). Deck and infographic return in v0.2 as proof the ledger is reusable.
- **`sb package --public` quote-budget redaction.** The spec itself admits the default artifact is
  a private, noindexed reading document. Publication machinery before anyone has shipped a private
  artifact is premature. Keep the quote budget as a lint warn; cut the redaction pipeline.
- **Seven of the ten slash commands.** See correction 2.

### Change
- The user-facing vocabulary and the claim-authoring path (corrections 1 to 5 below).

## The five highest-leverage corrections

1. **Halve the artifact menu.** v0.1 ships `answer` and `brief`. This deletes M6, two-thirds of the
   templates, four playbooks, two ATs, and two commands, and it sharpens the pitch from "generates
   six formats" to "produces an answer you can check." Every cut type is a view over the same
   ledger, so nothing is architecturally lost by deferring them; deferring them is the proof the
   architecture works.

2. **One verb for users: `ask`.** The command surface should be `/sourcebook` (router and status)
   and `/sb-ask`. Per-artifact slash commands duplicate what `sb status` already does, and ten
   commands is a vocabulary nobody will learn. Also unify the naming seam: the user says *ask*, the
   system says *answer/plan/ground/compose*. Let "ask" name the whole loop end to end (`sb-ask` →
   `answer.html`) and keep the pipeline verbs internal to the skill.

3. **Fix the hottest agent path: `sb claim add --json '{...}'` is shell-quoting quicksand.** Claims
   contain verbatim quotes from sources, which contain apostrophes and quotation marks; the GROUND
   state writes twenty of these per artifact through single-quoted shell JSON. This is the most
   frequently executed command in the kit and the most likely to fail in an agent's hands. Accept
   `--stdin` and `--file`, and make the skill's documented form `sb claim add --file claim.json`
   (or heredoc to stdin). Same for adjudications.

4. **Delete the capability ceremony from the happy path.** `sb config set capabilities.web_fetch=agent`
   three times before the first source is friction with no payoff: any harness running this kit can
   fetch and read, and the script already degrades per-source via `needs_extraction`. Default
   `web_fetch=agent`, `image_gen=none`, `tts=none`, and let `sb config` exist only for overrides.
   The demo's step 1 should be `sb init`, step 2 `sb add`.

5. **Rebuild the demo around the tamper moment.** The UPI question is the right corpus, but the
   spec's runbook demos the pipeline, not the promise. The promise is "this artifact cannot lie,"
   and that is only felt when you watch it refuse. Script the sabotage into BRIEF.md: after the
   artifact passes, edit one digit in a claim's quote, run `sb verify`, and let the audience see
   exit 2 with `E-QUOTE-MISMATCH` and the claim id. That is the thirty seconds people will retell.

## Notes by review dimension

**Concept sharpness.** High at the core, blurred at the edges. "Portable kit that makes claim-cited
artifacts" is sharp. "Also decks, infographics, podcasts, license auditing, and public packaging"
is the sprawl the non-goals section promised to avoid. The corrections above restore the edge.

**Naming.** `sourcebook` is right: a sourcebook is a real object (a bound collection of primary
sources), and the name promises exactly what the ledger delivers. `sb` is a good CLI name. The mark
vocabulary is the naming highlight. Weak spots: `ask` vs `answer` (correction 2), and
`explainer` / `brief` / `infographic` have fuzzy boundaries that the type cut resolves.

**Portable agent ergonomics.** The best-in-class ideas are `sb find` (the agent never computes an
offset) and filesystem-derived state (survives compaction, crashes, and a different agent tomorrow).
The two real ergonomic hazards are the JSON-over-argv claim path (correction 3) and the mandated
reference-file reads, which are acceptable given the lean SKILL.md but should be counted: the hot
path for one answer reads SKILL.md + evidence.md + visual.md + answer.md. Keep it at those four.

**HTML over PDF: earned.** A citation in this design is a link, and links need a live document. The
superscript jumps to a ledger entry with a tier badge and a recheck URL; marks sit inline on the
sentence they qualify; the thing opens from `file://`, offline, forever, on a phone. A PDF flattens
the apparatus into footnotes and kills the recheck link. And the PDF question still has an answer:
`brief` carries `@page` rules, so print gives you the PDF for free. HTML is the medium; PDF is one
of its stylesheets. Say exactly that in the README.

**Taste alignment.** The lint registry is design-rules.md compiled to Python, and the agent-judged
half (category-reflex at two orders, no fake illustration, hero-metric ban, marks must vary to
carry information) matches the calibration file closely. One watch item: the slop rules hardcode
2026's saturated defaults; they are versioned like every other algorithm here, so treat the rule
registry as a dated snapshot to be revised, not eternal law. No change needed for v0.1.

**Overengineering.** Concentrated in breadth, not depth. The machinery that exists is disciplined
(2,200 LOC target, hand-rolled 90-line schema checker instead of a vendored validator, honest
linter). BM25 over a ten-source corpus is borderline but cheap and deterministic; keep it. The
cuts above remove roughly a third of the milestones without touching a single load-bearing idea.

## Public pitch

sourcebook turns a folder of links and files into a single HTML page you can actually trust. Drop
it into any coding agent (Claude Code, Codex, Cursor), ask a question, and get back a self-contained
artifact where every factual sentence is pinned to an exact quote in a source you gave it: verified
claims marked, disputed claims shown from both sides, dated claims stamped with when they were true
and where to recheck. The verification is not a model's opinion; it is a byte-for-byte string
comparison run by a small dependency-free script, so a made-up quote cannot ship, period. There is
no server, no account, no API key, and nothing to host: the output is one file that opens from disk,
works offline, prints to A4, and keeps working after every service you used to build it is gone.

## Demo concept: "Make it lie."

Three minutes, one question, one betrayal.

1. **Ask (60s).** `sb init --question "Can an Indian traveller pay by UPI in Malaysia right now?"`,
   add four sources (operator page, press release, trade article, traveller forum thread), and let
   the agent run the loop. Open `answer.html` from `file://` on a phone with wifi off. Click a
   superscript: it jumps to the ledger entry with the tier badge and quote. Point at the one
   sentence wearing `contested`: the artifact shows the signed-agreement claim and the
   not-on-the-live-list claim side by side, because the gate would not let it pick a side quietly.
2. **Tamper (60s).** "Now let's make it lie." Live-edit `claims.json`: change 2.9 million merchants
   to 3.9 million. Run `sb verify`. Exit 2, `E-QUOTE-MISMATCH clm_4b18…`, claim named, ship blocked.
   Undo, verify, green. One line to the audience: "The number in the page is the number in the
   source, or there is no page."
3. **Reuse (30s).** `sb plan --type brief`, compose, verify, hit print: the same ledger, now an A4
   one-pager with footnotes, no re-research. Close on the footer line: built with sourcebook,
   today's date, four sources.

The delight is not the generation, which every tool now has. It is watching the artifact refuse.
