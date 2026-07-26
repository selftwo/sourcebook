# Playbook: `podcast`

Outline, then transcript, with a parallel citation track.
`build/podcast.script.json`, `.md`, and `.ttsplan.json`.

## Two stages, in order

1. **Outline.** N segments, each with a name, a description, and a size
   (`short` | `medium` | `long`). Write the whole outline before any dialogue.
2. **Transcript.** Per segment, in order, with the running transcript as context so the
   conversation does not restate itself.

## The citation track

Every line is typed. This is the whole point:

```json
{ "n": 14, "speaker": "Ana", "text": "The operator's own page still uses future tense.",
  "claims": ["clm_bb22..."], "kind": "factual" }
{ "n": 15, "speaker": "Ravi", "text": "So plan as if it does not work.",
  "claims": [], "kind": "opinion" }
```

`kind` is `factual`, `opinion`, `banter`, or `transition`. `sb verify --podcast` requires
every `factual` line to carry at least one active, verifying claim id. The boundary between
what the sources support and what the hosts are riffing on is therefore machine-checkable,
which no other podcast format gives you.

Write the banter as banter. Do not smuggle a fact into an opinion line to avoid citing it.

## Audio hooks, not audio

```
sb tts-plan
```

emits `build/podcast.ttsplan.json` (one segment per line, deterministic pauses: 320ms on a
speaker change, 180ms sentence-final within a speaker, 600ms at a segment boundary) plus
`build/audio/concat.txt` in ffmpeg concat-demuxer format.

sourcebook implements no adapter. Two shapes that work:

**Local CLI loop.** For each segment, call your local synthesizer with the segment text and
the speaker's voice hint, write to `segments[].out`, then
`ffmpeg -f concat -safe 0 -i build/audio/concat.txt -c copy build/audio/episode.wav`.

**API loop.** Same, but the per-segment call is an HTTP request, and you insert silence of
`pause_after_ms` between segments before concatenating.

A missing `build/audio/` never fails a gate. The script, the citation track, and the plan are
the deliverable.

## Optionally, a transcript page

`sb template podcast` gives a readable HTML transcript with the citation track visible and
the ledger injected, for people who would rather read it.
