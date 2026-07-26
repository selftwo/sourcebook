---
name: sb-verify
description: Run the ship gate and report exactly what is blocking.
---

Load the `sourcebook` skill.

```
sb verify
sb lint build/<artifact>.html
```

Paste the gate output verbatim. For each finding, name the error code, the subject, and the
one change that fixes it.

If `revise_count` has reached 3, stop. Report the blocking claims and error codes to the user
and ask how to proceed. Do not loosen a claim, drop a contested side, or weaken a confidence
level to make a gate pass.

Once the user has decided what changes, clear the block with
`sb unblock --reason "<what the user decided>"`, make the change they asked for, and run
`sb verify` again. `sb unblock` waives no gate; it only resets the loop counter.
