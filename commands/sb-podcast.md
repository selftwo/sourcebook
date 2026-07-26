---
name: sb-podcast
description: Write a two-host podcast script with a parallel citation track, plus a provider-agnostic TTS plan.
---

Load the `sourcebook` skill and `reference/podcast.md`.

Two stages, in order. First write the whole outline (segments with name, description, and
size). Then write the transcript segment by segment, with the running transcript as context.

Every line is typed `factual`, `opinion`, `banter`, or `transition`. Every `factual` line
carries at least one active claim id. Write `build/podcast.script.json`, then:

```
sb tts-plan
sb verify --podcast
```

Audio is optional and its absence fails no gate. Do not smuggle a fact into an opinion line
to avoid citing it.
