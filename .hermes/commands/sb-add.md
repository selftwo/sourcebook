---
name: sb-add
description: Collect one or more sources into the workspace, with a judged tier and a written reason.
---

Load the `sourcebook` skill and `reference/evidence.md`.

For each locator in `$ARGUMENTS`: decide its tier by its position relative to the fact, not
by its brand, and write the reason before you run the command.

```
sb add <locator> --tier <A|B|C|D> --reason "<why this tier>"
```

Then `sb extract && sb chunk && sb index`, and report which sources reached `ready` and which
need you to read them yourself. Finish with `sb status`.
