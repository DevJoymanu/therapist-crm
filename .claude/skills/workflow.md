# Workflow Rules

## Scope discipline — most important rule
Only change what was asked. Do not refactor, clean up, or "improve" surrounding code
unless explicitly asked to. If a bug fix is in `views/patients.py`, do not touch
`views/appointments.py` even if something looks improvable.

If a related file genuinely *needs* to change to complete the task, say so explicitly
before changing it — don't just change it silently.

## Before editing any file
Read the entire file first. Never edit a file that hasn't been fully read in the current
session. Missing something below the read window is a common cause of accidental breakage.

## Do not add unrequested things
- No extra error handling for scenarios that can't happen
- No refactoring of working code near the thing being changed
- No new abstractions or helper functions unless the task specifically requires them
- No comments explaining what the code does — only add a comment if the WHY is non-obvious

## Tests travel with the feature
When adding or changing a feature, tests for that feature are part of the same task.
See `testing.md` for the full testing rules.

## When something might break
If a change has risk of affecting other features, say so before making it. Give the user
the chance to decide. Don't silently make a risky change and hope it works.

## File changes should be minimal
A one-line bug fix should produce a one-line diff. Resist the urge to tidy nearby code.
Three similar lines is better than a premature abstraction.
