---
trigger: always_on
description: Read-only stack discovery and deliberate CLI adaptation on first project use
---

# First-time project onboarding

When entering a new project, or when its stack materially changes:

1. Read the existing project instructions before acting. **Never replace established conventions or safety controls.**
2. Run `python __ENTRYPOINT__ project-scan --json` for a shallow, read-only overview.
3. Inspect its `detected_stack`, `evidence`, and `recommended_commands` fields. Recommendations are **ideas**, not installed commands or authorization to make changes.
4. Pick at most one or two commands that are relevant to the current user task. If a reusable command is truly needed, run `python __ENTRYPOINT__ dev-scaffold --command <name> --json`; implement it using safe project-specific APIs and tests.
5. Validate with `python __ENTRYPOINT__ dev-validate --file core/commands/<name>.py --json`, run the project's tests, then `python __ENTRYPOINT__ system-docgen --json`.
6. Record only **verified and non-sensitive** general constraints in `gotchas.md`. Never record secret values, tokens, identifiable user information, private hosts, or complete environment dumps.
7. Obtain normal authorization before side effects, destructive operations, production access, process termination, or network calls. Never automatically run suggested commands or generate dozens of unused modules.

This workflow is a set of instructions; it does not automatically enforce agent behavior.

8. If a task genuinely needs restartable progress, use project-local `core.state.CheckpointStore` with explicit expiry, validation on resume and project-specific privacy checks. No default automatic resume or recovery is provided.
