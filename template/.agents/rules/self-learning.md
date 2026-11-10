---
trigger: always_on
description: Post-task audit, lessons learned and automated CLI documentation
---

# Self-learning procedure — always on

## Before a task

Read `.agents/skills/cli-tools/gotchas.md` and the relevant commands in `.agents/skills/cli-tools/SKILL.md`. For a newly encountered project, also follow `.agents/rules/agent-onboarding.md` and use read-only `project-scan` to identify the stack. Identify project-specific limits and the correct entrypoint.

## After each task (Post-Task Audit)

1. Check the actual command outputs and exit codes. Did the task meet the acceptance criteria? Record unmet criteria clearly.
2. If an environment-specific issue occurred, investigate the cause before editing files, terminating processes or attempting recovery. Prefer a reviewed, reusable fix over an impulsive one-off workaround. Append a short, reproducible entry to `gotchas.md`: **symptom**, **root cause**, **verified workaround**, **date/scope**. Do not record credentials, tokens, personal data, internal hostnames, proxy settings, or unverified guesses. Do not transfer private destination-project gotchas into public upstream repositories.
3. If command modules or arguments changed, run `python __ENTRYPOINT__ system-docgen --json` and include the generated SKILL.md in the same change.
4. Validate every new command with `python __ENTRYPOINT__ dev-validate --file core/commands/<name>.py --json` and run its tests.
5. Ensure no throwaway code or unexpected generated files remain. Report what was tested and what remains uncertain.

This procedure is a documented expectation for agents; it does not autonomously change a model's behavior or guarantee its memory is consulted.
