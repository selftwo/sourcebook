---
name: sb-ledger
description: Render the citation apparatus in any of its forms, and re-inject it into the artifact.
---

Load the `sourcebook` skill.

```
sb ledger --json      # resolved ledger with ordinals
sb ledger --md        # markdown source list
sb ledger --sources   # grouped by source, with tier badges and tier reasons
sb ledger --html --out build/ledger.html
sb inject build/<artifact>.html --ledger build/ledger.html
```

Never hand-write a ledger entry. Re-running the command regenerates it, which is the only
reason drift between the prose and the ledger is impossible rather than merely discouraged.
