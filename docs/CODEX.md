# Codex integration (and other agents supporting AGENTS.md)

This repository is the **installer source**. It should not be copied wholesale into the destination project's `.agents/` directory. The destination must be the actual project checkout root (normally the Git root).

## What Codex detects

- Codex reads project-root `AGENTS.md` and parent instructions before starting work. An existing `AGENTS.override.md` takes precedence at the same level.
- Codex also discovers repository skills from `.agents/skills/<skill-name>/SKILL.md`.
- Arbitrary Markdown under `.agents/rules/` is **not** guaranteed to be automatically loaded by Codex. `AGENTS.md` explicitly points to project rules and the CLI.
- Newly installed instructions may require a **new Codex session** to be included.

Official references: [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) and [Skills](https://learn.chatgpt.com/docs/build-skills).

## Installation in a real project

1. Determine the destination repository root from the current checkout. Respect that project's branch/PR policy; never work inside a temporary CI runner checkout.
2. Obtain a **reviewed** checkout of this starter and record its exact commit SHA. Do not execute an unreviewed remote installation script.
3. From the starter checkout, preview:

   ```bash
   python setup_starter_kit.py --target /absolute/path/to/project --integrate-agents --dry-run --json
   ```

4. Check `planned_created`, `planned_overwritten`, `skipped`, `entrypoint`, `guidance_state` and `codex_override_present`. Confirm the CLI will not conflict with the target's own `core/`, `manage.py`, or project documentation. Stop and handle collisions rather than claiming success.
5. If approved in the target's branch, apply the **same reviewed checkout**:

   ```bash
   python setup_starter_kit.py --target /absolute/path/to/project --integrate-agents --json
   ```

6. Inside the target project run `python manage.py sys-info --json` and `python manage.py project-scan --json`. If the installer reported `entrypoint: agent_cli.py`, use `agent_cli.py` instead.
7. Verify the root `AGENTS.md` references the CLI and the two skills exist: `.agents/skills/cli-tools/SKILL.md` and `.agents/skills/self-improvement/SKILL.md`. Start a **new Codex session** for instruction discovery and, in a permitted task, verify it really invokes the CLI.
8. Review the diff and open a PR if the project requires it. Installation is only `VERIFIED` after both file placement and real CLI execution are checked.

### Existing AGENTS.md

Without `--integrate-agents`, the installer leaves an existing file byte-for-byte untouched, **even with `--force`**. This may leave Codex unaware of the new CLI despite its being installed.

With `--integrate-agents`, the installer appends one idempotent, clearly marked section to the existing root file. It preserves the existing content, refuses malformed markers and retains its line endings. Preview this modification using `--dry-run`; do not use `--force` just to inject instructions.

If `AGENTS.override.md` is present, the installer warns but does not edit it. Codex may prioritize the override: adapt it manually within the destination repository's review process.

### Honest status

A created file or a passing `sys-info` smoke test does **not** prove the agent follows all rules or that the target project behaves correctly. For new commands, a scaffold must remain `SCAFFOLDED / UNVERIFIED` until actual positive and negative behavioral acceptance tests pass.
