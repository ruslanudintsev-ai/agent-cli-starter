# Agent CLI Starter — universal agent installation contract

This is the **canonical instruction for any coding agent** that is asked to install Agent CLI Starter in another repository. Begin with [INSTALL.md](INSTALL.md): **clone the starter repository, then copy/configure its template files into the destination project root using the included local installer**. The system has **one installer, one set of project skills, one CLI and one verification protocol**. It does not depend on any model/provider or a specific coding-agent product.

## Interpret the request

"Install this in the project" means **integrate the starter into the actual destination project root**, not create a nested `.agents/agent-cli-starter` folder, not clone this entire starter into the destination, and not stop after drafting an installation plan. If the destination repository is not identifiable, discover it from the active checkout; if multiple candidate projects remain ambiguous, ask for the actual target rather than guessing.

Read the destination project's current instructions and Git workflow **before writing**. Installation must respect existing project rules, branches, PRs and production safety. Never claim installation was completed when it was only planned.

## One deterministic workflow

1. **Discover.** Identify the trusted source revision and the destination checkout root. Inspect the destination `AGENTS.md`, existing `.agents/` content, `manage.py`, `agent_cli.py`, `core/`, `.gitignore`, and any instruction overrides that your agent actually uses. If the project already includes this CLI, do not install another copy.
2. **Clone and inspect.** Run `git clone https://github.com/ruslanudintsev-ai/agent-cli-starter.git` outside the destination project, then `cd agent-cli-starter`. Review the source and ideally pin a known commit. **Do not copy the entire upstream repository** into the destination: the installer uses the contents of `template/`, renders placeholders and preserves application-owned files. Do not execute uninspected remote scripts.
3. **Plan without writing.** The common installer chooses `--layout auto`: for an occupied project it places the runtime in `tools/agent-cli-starter/` while keeping rules and skills in the project root. From the *starter source checkout*, run:

   ```bash
   python setup_starter_kit.py --target /path/to/destination --layout auto --integrate-agents --dry-run --json
   ```

   Inspect `layout`, `entrypoint`, `commands_dir`, `planned_created`, `planned_overwritten`, `skipped`, `guidance_state`, `codex_override_present`. This last field reports one known override filename; other agents may have additional precedence rules. Reject unsafe collisions instead of making assumptions. Existing `AGENTS.md` is preserved by default and `--integrate-agents` only adds a reviewable, idempotent reference.
4. **Apply in the permitted worktree.** If the preview is acceptable and the destination repository's workflow permits it, run the same command **without** `--dry-run`:

   ```bash
   python setup_starter_kit.py --target /path/to/destination --layout auto --integrate-agents --json
   ```

   Never use `--force` to solve unknown project collisions, and never change production or other repositories as a side effect.
5. **Verify the installation.** Enter the destination root and run the CLI the installer actually reported (usually `manage.py`, otherwise `agent_cli.py`):

   ```bash
   python <entrypoint-from-installer> sys-info --json
   python <entrypoint-from-installer> project-scan --json
   ```

   For Django, the reported entrypoint may be `tools/agent-cli-starter/manage.py`; never call the application's own `manage.py` by mistake. Check both exit codes and observed JSON `result.status`. Confirm the project instructions actually reference the entrypoint; confirm the generated `.agents/skills/cli-tools/SKILL.md` and `.agents/skills/self-improvement/SKILL.md` exist. Review the diff and open a PR if the destination requires it.
6. **Verify actual agent adoption separately.** Start a new agent session when its instruction snapshot is not refreshed automatically. Confirm **on a permitted non-destructive task** that the agent reads the intended instructions and calls an installed CLI command. Merely having files on disk does *not* prove the agent followed them.

**State your outcome precisely:** `PLANNED` (dry-run only), `INSTALLED` (files placed and CLI smoke tested), `AGENT_VERIFIED` (agent discovery and real usage observed), or `BLOCKED` (specific reason). Neither `INSTALLED` nor `AGENT_VERIFIED` proves that a new domain feature works; that needs independent behavioral acceptance under [Reliability Core](docs/RELIABILITY.md).

## One behavioral contract

- The CLI uses `BaseCommand`, bounded JSON and standard `argparse`; do not create throwaway root scripts instead of implementing justified reusable commands.
- Generated commands start `SCAFFOLDED / UNVERIFIED`. Do not equate file creation, syntax checks or `status: ok` with fulfilling the task.
- For real features, require independently observable positive and negative acceptance cases and sanitized evidence before reporting `VERIFIED`.
- Project-local `gotchas.md` and recipes are scoped, verified procedural memory, not facts to copy into the public upstream.
- Respect project permissions. Agent instruction text is **guidance, not a security boundary**.

## Agent adapters are optional discovery surfaces

The canonical contract is this file, the Python installer, and the installed project content. Different agents expose different ways to read the **same** content:

- `AGENTS.md` readers: project root `AGENTS.md` links to the shared rules and CLI.
- Agent Skills readers: project `.agents/skills/*/SKILL.md`.
- Cursor-like agents: thin references in `.cursor/rules/`.
- Claude Code readers: `CLAUDE.md` links to the same contract.
- Aider-style tools: explicitly load `AIDER_CONVENTIONS.md` where supported.

No file format is auto-discovered by **every** current or future agent. If an agent does not support these files, supply this canonical guide as part of its project instructions or tool configuration. Do not create a new implementation of the runtime per vendor.

Compatibility notes and empirical tests belong in [Codex](docs/CODEX.md) and [Kilo Code](docs/KILO_CODE.md), **not** in the universal install algorithm.
