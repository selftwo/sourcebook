# sourcebook — Iteration Backlog

This backlog extends sourcebook from a trustworthy research-to-artifact kit into a reusable
**personal content-engineering pipeline**: source-grounded interactive essays, experience atlases,
versioned takes, experiments, and small instruments that can improve through explicit snapshots.

It does **not** change the core architecture:

> **Source material is truth. The agent judges. Deterministic scripts verify. Code is expression.**

The implementation target remains static by default, self-contained, inspectable, portable between
coding agents, and useful without runtime AI.

## How to use this backlog

- Status vocabulary: `ready`, `blocked`, `spike`, `later`.
- Implement in dependency order unless a task is explicitly an independent spike.
- Every task that changes a contract must update `SPEC.md`, the relevant schema, the portable skill,
  and hermetic acceptance tests in the same commit.
- Every new artifact grammar must pass the existing evidence, contradiction, licensing, lint,
  packaging, and offline gates. A new grammar is not a shortcut around verification.
- Prefer one deep extension to the existing workspace contract over parallel bespoke pipelines.
- Keep reasoning in the agent playbooks and calculations in deterministic scripts.

## Product guardrails

1. **Interaction must earn its existence.** It must let a reader change an assumption, inspect
   evidence, navigate accumulated experience, encounter a counterfactual, or leave with an
   instrument. Otherwise use prose and a static visual.
2. **Progressive enhancement is mandatory.** Essential claims, evidence, and conclusions remain
   readable without JavaScript. Controls enhance a complete base document.
3. **Publish snapshots, not permanent services.** Personal takes, experiences, experiments, and
   tools are dated editions with visible provenance and version history.
4. **No invented experience.** Agents may organize supplied notes, photographs, measurements, and
   reflections; they may not manufacture first-person memories or observations.
5. **Private archive is not public corpus.** Public packages expose only an intentionally curated
   source packet, never local archive paths or private source material.
6. **Runtime AI is exceptional.** Codex, Claude Code, Hermes, or another agent may build the
   artifact. The shipped artifact does not call a model unless inference is the subject of the
   experience and the user explicitly enables it.
7. **One sourcebook, many grammars.** Essays, atlases, experiments, and tools remain views over
   compatible source, claim, plan, provenance, and package contracts.

---

## P0 — Define the extension contracts

### SB-23 — Model first-person evidence without weakening factual evidence

**Status:** ready

**Outcome:** sourcebook can distinguish externally checkable facts from supplied first-person
observations, remembered impressions, measured personal data, and authorial interpretation.

**Why:** a personal artifact may legitimately say “I recorded three meals” or “I remember this
street as quiet,” but neither statement should masquerade as institutional evidence. The current
`fact | interpretation | recommendation` vocabulary is not precise enough for this boundary.

**Likely files:**

- `SPEC.md`
- `schemas/claim.schema.json`
- `skills/sourcebook/reference/evidence.md`
- `scripts/sourcebook/ledger.py`
- `scripts/sourcebook/verify.py`
- `tests/cases/AT-23-first-person-evidence.py`

**Acceptance:**

- Add explicit claim/evidence semantics for at least `observed`, `remembered`, and `measured`
  first-person material without changing what earns `verified` for external facts.
- Require a supplied source span for first-person claims; “the user said it somewhere” is not an
  implicit citation.
- Render a visible reader-facing distinction between sourced fact, recorded observation, memory,
  and inference without proliferating decorative badges.
- A fabricated first-person claim with no supplied source fails closed.
- A personal source is Tier A only for the author’s own stated experience, not for external facts
  mentioned inside that source.

**Non-goal:** diagnosing the author, assigning objective truth to memory, or scoring emotional
confidence.

### SB-24 — Add private-to-public source packet curation

**Status:** ready

**Outcome:** a private workspace can produce a deliberately curated public evidence packet without
leaking private locators, people, photographs, notes, or archive structure.

**Likely files:**

- `SPEC.md`
- `schemas/source.schema.json`
- `schemas/manifest.schema.json`
- `scripts/sourcebook/package.py`
- `skills/sourcebook/reference/licensing.md`
- `skills/sourcebook/reference/evidence.md`
- `tests/cases/AT-24-public-source-packets.py`

**Acceptance:**

- Add an explicit publication state such as `private`, `public`, `redacted`, or `withheld` to source
  records or to a separate curation manifest.
- `sb package --public` includes only approved source records and assets.
- Public provenance keeps hashes and public canonical URLs while withholding local and private
  locators, including relative directory names.
- Redactions are visible as redactions; they cannot silently remove evidence needed by a rendered
  claim.
- Add negative fixtures for a private person’s name, local photo path, EXIF location, and raw note
  filename.

**Non-goal:** building an encrypted archive, sync service, or rights-management system.

### SB-25 — Specify an interaction manifest as a small, deep interface

**Status:** blocked by SB-23

**Outcome:** interactive behavior is planned and verified through one compact contract rather than
custom conventions per artifact.

**Likely files:**

- `SPEC.md`
- `schemas/plan.schema.json`
- `schemas/interaction.schema.json` (new)
- `scripts/sourcebook/verify.py`
- `skills/sourcebook/reference/visual.md`
- `tests/cases/AT-25-interaction-contract.py`

**Contract sketch:**

- purpose: `assumption | evidence | navigation | counterfactual | instrument`
- enhancement target and fallback element
- input controls and valid ranges
- output region and deterministic mapping
- claim ids affected by the interaction
- keyboard behavior
- reduced-motion behavior
- snapshot states required for visual review

**Acceptance:**

- Every interactive region declares one purpose from the allowlist.
- Each region has a complete static fallback containing its essential claim or outcome.
- Inputs have deterministic boundaries and named output regions.
- Claim wording cannot change to an uncited factual sentence in a client-side state.
- Missing keyboard, fallback, or reduced-motion behavior fails verification.
- The interface supports all planned grammars below without artifact-specific fields in the core.

**Non-goal:** inventing a component framework or serializing arbitrary application state.

---

## P1 — Add personal artifact grammars

### SB-26 — Interactive essay grammar

**Status:** blocked by SB-25

**Outcome:** sourcebook can produce an inspectable argument where readers manipulate assumptions and
see which claims, trade-offs, or conclusions change.

**Likely files:**

- `schemas/plan.schema.json`
- `templates/essay.html` (new)
- `skills/sourcebook/reference/essay.md` (new)
- `scripts/sourcebook/manifest.py`
- `scripts/sourcebook/verify.py`
- `tests/cases/AT-26-interactive-essay.py`

**Acceptance:**

- Add `essay` as an artifact type without weakening existing types.
- Base HTML presents the complete thesis, evidence, counterargument, and conclusion without JS.
- Interactive states expose assumptions or evidence; they do not merely animate sections.
- Every factual state is covered by claim ids already in the ledger.
- Direct links, print, 360px, keyboard, and reduced-motion paths work.
- Package at least three deterministic review states as screenshots or DOM snapshots.

### SB-27 — Experience atlas grammar

**Status:** blocked by SB-23, SB-24, SB-25

**Outcome:** sourcebook can render a dated experience from notes, photographs, places, times, and
reflections without turning it into an objective travel guide.

**Likely files:**

- `schemas/plan.schema.json`
- `schemas/experience.schema.json` (new)
- `templates/atlas.html` (new)
- `skills/sourcebook/reference/atlas.md` (new)
- `scripts/sourcebook/verify.py`
- `tests/cases/AT-27-experience-atlas.py`

**Acceptance:**

- Support temporal, geographic, thematic, and remembered ordering without requiring all four.
- Distinguish recorded itinerary from reconstructed memory and editorial sequence.
- Strip or explicitly approve precise location metadata before public packaging.
- Photographs retain credits, consent/privacy status, alt text, capture date when known, and asset
  hashes.
- A complete non-map reading path exists; geography cannot be the only navigation.
- Personal observations do not become recommendations about a whole place or culture without
  external evidence.

### SB-28 — Experiment notebook grammar

**Status:** blocked by SB-23, SB-25

**Outcome:** sourcebook can publish a personal or product experiment with a hypothesis, protocol,
observations, deviations, result, and next question.

**Likely files:**

- `schemas/experiment.schema.json` (new)
- `schemas/plan.schema.json`
- `templates/experiment.html` (new)
- `skills/sourcebook/reference/experiment.md` (new)
- `scripts/sourcebook/verify.py`
- `tests/cases/AT-28-experiment-notebook.py`

**Acceptance:**

- Require hypothesis, protocol, observation window, deviations, result, and limitations.
- Separate preregistered expectations from post-hoc interpretation.
- Never label a personal experiment as general evidence without external support.
- Permit interactive replay or parameter changes only when the mapping is deterministic and the
  original recorded result remains visible.
- Failed and inconclusive experiments are valid publishable states.

### SB-29 — Versioned take grammar

**Status:** blocked by SB-23

**Outcome:** sourcebook can publish a position with confidence, strongest support, strongest
objection, change conditions, and prior versions.

**Likely files:**

- `schemas/take.schema.json` (new)
- `schemas/plan.schema.json`
- `templates/take.html` (new)
- `skills/sourcebook/reference/take.md` (new)
- `scripts/sourcebook/package.py`
- `scripts/sourcebook/verify.py`
- `tests/cases/AT-29-versioned-take.py`

**Acceptance:**

- Every edition has a stable id, date, parent edition when present, and a concise change note.
- Readers can see what changed without diffing raw JSON.
- The current position names at least one objection and an explicit condition that could change it.
- Superseded editions remain addressable in a snapshot package.
- A changed factual premise re-enters the ordinary contradiction and adjudication flow.

### SB-30 — Small instrument grammar

**Status:** blocked by SB-25

**Outcome:** sourcebook can publish a local-first calculator, composer, simulator, or decision aid as
the executable conclusion of an essay or sourcebook.

**Likely files:**

- `schemas/instrument.schema.json` (new)
- `schemas/plan.schema.json`
- `templates/instrument.html` (new)
- `skills/sourcebook/reference/instrument.md` (new)
- `scripts/sourcebook/verify.py`
- `tests/cases/AT-30-small-instrument.py`

**Acceptance:**

- Inputs, defaults, ranges, units, formula/version, and output interpretation are declared.
- The deterministic function has fixture tests independent of the DOM.
- The artifact explains limits and does not present a subjective weighting as an objective score.
- No network, account, telemetry, or model call is required for the default path.
- A printable/static explanation remains useful when controls are unavailable.

**Non-goal:** general-purpose app hosting or a plugin ecosystem.

---

## P2 — Make the outputs compound

### SB-31 — Snapshot, edition, and artifact-family manifests

**Status:** blocked by one completed P1 grammar

**Outcome:** an artifact can be revised deliberately and several formats can be derived from the
same accepted ledger without pretending they were independently researched.

**Likely files:**

- `schemas/edition.schema.json` (new)
- `schemas/manifest.schema.json`
- `scripts/sourcebook/package.py`
- `scripts/sourcebook/manifest.py`
- `tests/cases/AT-31-editions-and-families.py`

**Acceptance:**

- Record edition id, parent, creation date, source hashes, ledger hash, plan hash, and output hashes.
- Distinguish editorial revision, evidence revision, design revision, and correction.
- Derivative formats point to one artifact family and shared ledger snapshot.
- A correction cannot overwrite the package it corrects.
- The public package contains a human-readable edition history and machine-readable manifest.

### SB-32 — Add deterministic derived-media exports

**Status:** blocked by SB-31

**Outcome:** one verified artifact can produce bounded derivatives such as social cards, stills,
print views, or an optional video scene plan without rebuilding its research.

**Likely files:**

- `schemas/export.schema.json` (new)
- `scripts/sourcebook/package.py`
- `skills/sourcebook/reference/exports.md` (new)
- `tests/cases/AT-32-derived-exports.py`

**Acceptance:**

- Exports declare source artifact edition, claim ids used, dimensions/duration, and output hash.
- Static card/still copy cannot introduce new factual language absent from the ledger.
- Export generation may use an external browser or Remotion adapter, but gate-blocking verification
  remains standard-library and adapter-neutral.
- Missing optional render capability produces a plan, not a false success.
- Generated assets receive the same credit, labeling, and package checks as existing images.

**Non-goal:** shipping Remotion, Playwright, Chromium, or a video renderer as required dependencies.

### SB-33 — Add a reusable authoring brief for Codex and Claude Code

**Status:** ready; independent documentation task

**Outcome:** any coding agent receives a concise implementation contract for an artifact rather than
an open-ended “make this interactive” prompt.

**Likely files:**

- `skills/sourcebook/reference/authoring-brief.md` (new)
- `skills/sourcebook/SKILL.md`
- `commands/sb-ask.md`
- installer fixtures in `tests/cases/AT-20-install-portability.py`

**Acceptance:**

- Brief includes thesis, audience, source boundary, grammar, interaction purpose, static fallback,
  design tokens, accessibility, privacy, required review states, acceptance commands, and non-goals.
- Language is harness-neutral and contains no model-specific tool names.
- The brief states that the agent may implement and organize but may not invent evidence or personal
  experience.
- Runtime AI is off by default and must be justified separately.
- Updating the skill and re-running `make install` keeps checked-in adapters identical.

### SB-34 — Add post-publication review without mutable live content

**Status:** blocked by SB-31

**Outcome:** authors can capture reader feedback, corrections, and new evidence as inputs to the next
edition while published snapshots stay immutable.

**Likely files:**

- `schemas/review.schema.json` (new)
- `scripts/sourcebook/manifest.py`
- `skills/sourcebook/reference/revision.md` (new)
- `tests/cases/AT-34-post-publication-review.py`

**Acceptance:**

- Review records distinguish correction, new evidence, usability issue, accessibility issue, and
  editorial suggestion.
- A review never mutates claims or published HTML automatically.
- Accepted factual corrections enter a new grounding/adjudication cycle.
- Rejected suggestions retain a brief reason without entering public provenance by default.
- The next edition links to the review ids it resolved.

---

## P3 — Prove the system with one complete season

### SB-35 — Ship an executable-authorship demo

**Status:** blocked by SB-26, SB-30, SB-31

**Outcome:** a synthetic, redistributable demo proves an interactive essay can end in a small
instrument and produce a versioned, verified package.

**Candidate thesis:** “More interfaces can reduce capability by increasing setup, checking,
switching, correction, and maintenance costs.”

**Likely files:**

- `examples/executable-authorship/` (new)
- synthetic local sources under that example
- one essay artifact
- one embedded or linked instrument
- edition and provenance manifests
- a build runbook

**Acceptance:**

- All sources are synthetic or clearly licensed for redistribution.
- The essay contains one assumption control, one evidence-inspection interaction, one explicit
  counterargument, and one useful instrument.
- It reads completely with JS disabled and passes every existing and new gate.
- `make executable-authorship-demo` rebuilds it offline.
- `make executable-authorship-tamper` demonstrates refusal for an uncited interactive state and a
  changed instrument formula.

### SB-36 — Ship an experience-to-take-to-tool demo family

**Status:** blocked by SB-27, SB-28, SB-29, SB-30, SB-31

**Outcome:** one synthetic source packet moves through the complete creative loop:

`experience → observation → take → experiment → instrument → deeper essay`

**Acceptance:**

- Every output has a genuinely different grammar, not a reskinned page.
- Shared factual claims resolve to one ledger snapshot.
- First-person, memory, measured, inferred, and externally sourced material remain visibly distinct.
- Public packaging proves private-source exclusion.
- The hub is a light static index; sourcebook does not become a CMS.

---

## Cross-cutting verification tasks

These can be implemented with the first grammar that needs them and then reused.

### SB-37 — Interactive-state claim verification

**Status:** blocked by SB-25

- Enumerate declared deterministic states or boundary combinations.
- Verify every factual output state maps to active claim ids.
- Fail if client-side code contains alternate factual copy not represented in the plan/ledger.
- Add a deliberate tamper fixture.

### SB-38 — Static-fallback and control semantics audit

**Status:** blocked by SB-25

- Essential content visible before enhancement.
- Script-only controls hidden until enhancement succeeds.
- Controls have labels, visible focus, keyboard operation, valid ARIA semantics, and touch targets.
- Reduced-motion behavior preserves information.
- Verify at 360px and at the tallest/longest state.

### SB-39 — Formula and transformation provenance

**Status:** blocked by SB-30 or SB-32

- Hash deterministic formulas/transforms used by instruments and exports.
- Record units, rounding, defaults, and version.
- Fixture-test boundaries, invalid inputs, and one representative result.
- A changed transform without an edition bump fails packaging.

### SB-40 — Personal-content privacy audit

**Status:** blocked by SB-24

- Detect public packages containing local paths, precise coordinates, unapproved EXIF, private
  source titles, withheld people, or uncredited photographs.
- Treat findings as ship-blocking, not warnings.
- Keep the detector narrow and deterministic; ambiguous consent remains an agent/user decision.

---

## Intentionally not planned

- A hosted CMS, collaborative editor, account system, or sync service.
- Automatic life logging, inbox surveillance, or background collection.
- A vector database or semantic-search service.
- A generic React/Astro component framework inside sourcebook.
- Runtime personalization powered by an LLM.
- Automatically publishing agent-generated memories, takes, or conclusions.
- Engagement analytics as a quality measure.
- Turning every sourcebook into an interactive artifact.

## Suggested implementation order

1. SB-23 first-person evidence.
2. SB-24 private/public curation.
3. SB-25 interaction manifest.
4. SB-26 interactive essay and SB-30 small instrument as the first vertical slice.
5. SB-31 editions, then SB-35 executable-authorship demo.
6. SB-27/SB-28/SB-29 only after the first slice demonstrates that the shared contracts are deep
   enough to avoid parallel pipelines.
7. SB-32/SB-34 and the complete demo family after two grammars reuse the same seams.

This order tests the central bet early: sourcebook should gain new expressive forms while preserving
one trustworthy evidence and packaging substrate.

## Origin of this backlog

The backlog adapts the “content is code” thesis from Matt Palmer’s talk for personal publishing:

- [Content Is Code — Matt Palmer, Conductor](https://www.youtube.com/watch?v=yv6xovSsB1U)

The talk motivates cheap code, structure, and conscientiousness. The task definitions above are an
editorial and architectural extension for sourcebook, not claims made by the speaker.
