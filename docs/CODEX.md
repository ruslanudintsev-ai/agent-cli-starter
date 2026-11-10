# Codex compatibility notes

**Canonical for every agent:** [Universal agent setup](../AGENT_SETUP.md). This page records Codex-specific instruction discovery and caveats only; it is not a separate installation protocol.

## What Codex detects

- Codex reads project-root `AGENTS.md` and parent instructions before starting work. An existing `AGENTS.override.md` takes precedence at the same level.
- Codex also discovers repository skills from `.agents/skills/<skill-name>/SKILL.md`.
- Arbitrary Markdown under `.agents/rules/` is **not** guaranteed to be automatically loaded by Codex. `AGENTS.md` explicitly points to project rules and the CLI.
- Newly installed instructions may require a **new Codex session** to be included.

Official references: [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) and [Skills](https://learn.chatgpt.com/docs/build-skills).

## Installation

Follow the same [universal install and verification steps](../AGENT_SETUP.md) as every other coding agent. Django-like occupied roots select `tools/agent-cli-starter/` using `--layout auto`; project-owned `manage.py` is preserved. Review destination Git/PR rules, use the existing Python installer with `--target` and `--integrate-agents`, perform dry-run first, and verify actual CLI execution. This page adds no Codex-only installer, command or runtime.

### Existing AGENTS.md

Without `--integrate-agents`, the installer leaves an existing file byte-for-byte untouched, **even with `--force`**. This may leave Codex unaware of the new CLI despite its being installed.

With `--integrate-agents`, the installer appends one idempotent, clearly marked section to the existing root file. It preserves the existing content, refuses malformed markers and retains its line endings. Preview this modification using `--dry-run`; do not use `--force` just to inject instructions.

If `AGENTS.override.md` is present, the installer warns but does not edit it. Codex may prioritize the override: adapt it manually within the destination repository's review process.

### Honest status

A created file or a passing `sys-info` smoke test does **not** prove the agent follows all rules or that the target project behaves correctly. For new commands, a scaffold must remain `SCAFFOLDED / UNVERIFIED` until actual positive and negative behavioral acceptance tests pass.
