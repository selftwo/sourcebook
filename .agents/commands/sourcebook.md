---
name: sourcebook
description: Router and status for a sourcebook workspace. Reports the derived state and the single next command.
---

Load the `sourcebook` skill.

Run `sb status`. Print the state, the source count, and the next command it names, then do
exactly that. If there is no workspace here, run `sb init --question "$ARGUMENTS"` first and
report where it was created.

If the state is BLOCKED, do not run the next command. Report the blockers and the failing
claims to the user, and ask how to proceed. When they have decided, clear it with
`sb unblock --reason "<what they decided>"` and continue from the state `sb status` then
reports.
