---
trigger: always_on
description: Verified lessons, privacy-aware procedural memory and post-task audit
---

# Verified procedural learning — always on

The agent retains *operational knowledge*, not hidden thoughts or unfiltered logs. These instructions are **not** an automatic learning capability: agents must actually read and follow them.

## Start of task

1. Read `.agents/skills/cli-tools/SKILL.md` and `.agents/skills/cli-tools/gotchas.md` before choosing commands.
2. Check the CLI entrypoint, project policy and acceptance criteria; run read-only `project-scan` for unfamiliar repositories.
3. Treat every gotcha as *scoped evidence*, not an instruction to blindly rerun a fix in a different environment.

## Post-Task Audit (required before reporting completion)

1. **Verify results.** Review exit codes, tests and observable outcomes. Separate facts from hypotheses and state failed or untested conditions.
2. **Identify reusable lessons.** Record an issue only if it is repeatable or has a clearly verified cause/fix. For an unresolved incident, record it as an *open question* rather than a proven workaround.
3. **Record minimally.** Append a short entry to the private destination project's `gotchas.md` with date, scope, sanitized symptom, verified cause, recovery steps, validation evidence and limitations. Use the documented template in that file. Never paste raw logs, stack traces, credentials, cookies, personal data, internal infrastructure or secrets into shared upstream docs.
4. **Improve a tool when justified.** Follow `.agents/skills/self-improvement/SKILL.md`. Add tested workflow recipes to `cli-tools/recipes.md` and missing capabilities as *proposals* in `.agents/backlog/cli-features.md`; keep `SKILL.md` machine-generated. For a repeated operation, propose a reviewed persistent CLI command. Scaffold, validate and test it. Do not automatically execute destructive remediation just because an earlier run failed.
5. **Synchronize the reference.** If arguments or commands changed, run `python __ENTRYPOINT__ system-docgen --json` and check the generated SKILL.md. Run `dev-validate` and relevant tests for new commands.
6. **Close the loop.** Report what changed, what was tested and any limits. Recheck the recorded workaround when the stack/version changes; correct or retire stale notes.

## Privacy boundary

- A destination project's `gotchas.md` can contain sensitive operational context and is **not** automatically suitable for public GitHub.
- Upstream/public contributions must use generic examples and must be reviewed separately for private names, hosts, paths, credentials and identifying details.
- Do not claim the agent learned, fixed or verified something merely because it was written in the memory file.
