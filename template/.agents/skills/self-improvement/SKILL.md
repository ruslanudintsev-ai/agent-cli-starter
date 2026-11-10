---
name: continuous-skill-evolution
description: Evidence-driven improvement of persistent CLI commands and project-local agent procedures
---

# Continuous skill evolution

Use this skill after an unusual task, a repeatable failure or discovery of a reusable workflow. It **does not** change model weights or grant permission to alter production systems.

## Before starting

1. Read the project's `AGENTS.md`/equivalent instructions, `.agents/skills/cli-tools/SKILL.md`, `gotchas.md`, `recipes.md` and `.agents/backlog/cli-features.md`.
2. Reuse a supported CLI command when possible. Treat suggested but unimplemented commands as proposals.
3. Validate the task scope. Avoid collecting private paths, tokens or unfiltered logs; do not upload project memory upstream.

## After the task — evidence-first loop

1. **Observe.** Note exactly what ran, the outcome, failed checks and any specific reproducible error.
2. **Verify.** Run a focused check. If the root cause is uncertain, mark it *unverified*; never invent a fix.
3. **Classify.** Choose only the useful destination:
   - Verified, environment-scoped fact → `cli-tools/gotchas.md` using its incident template.
   - Reusable, tested multi-step workflow → `cli-tools/recipes.md` (manually maintained, never overwritten by docgen).
   - Missing repeatable capability → `.agents/backlog/cli-features.md` with expected behavior, safety and tests.
   - New approved command → `dev-scaffold` → implement → `dev-validate` → tests → `system-docgen`.
4. **Clean up.** Remove stale or superseded **notes**, not unexplained files or other agents' work. Revalidate older findings after major OS, framework or project changes.
5. **Report.** Specify which behavior was genuinely implemented and tested, which ideas remain proposals, and what was added to the procedural memory.

## Guardrails

- Never write incidents into generated `cli-tools/SKILL.md`: `system-docgen` regenerates that file.
- Never auto-execute stored fixes, run arbitrary code, kill processes, change credentials, or publish private artifacts just because a note recommends it.
- Never copy the destination project's notes into the public starter repository. Upstream reusable techniques require independent sanitization and review.
- Avoid note inflation: prefer concise verified information over unbounded traces or repeated speculative hypotheses.
