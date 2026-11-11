# Agent CLI Starter

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen)](template/core/commands/base.py)
[![CI](https://github.com/ruslanudintsev-ai/agent-cli-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/ruslanudintsev-ai/agent-cli-starter/actions/workflows/ci.yml)

**Zero-dependency, cross-platform project command scaffold for coding agents** — Antigravity, Cursor, Claude Code, Kilo Code, Aider and tools that support project instruction files.

Instead of writing `temp.py`, `script_v1.py` and dumping unlimited logs into a model context, agents can extend a reusable Python CLI with explicit parameters, bounded JSON results, tests, and persistent operational notes.

## Install — clone and copy into your project

**Start here: [Installation — Clone, Copy, Verify](INSTALL.md).** This is the primary installation guide for all coding agents and operating systems.

```bash
git clone https://github.com/ruslanudintsev-ai/agent-cli-starter.git
cd agent-cli-starter

# Preview the files to be copied into the destination project root.
python setup_starter_kit.py --target ../your-project --layout auto --integrate-agents --dry-run --json

# Copy and configure the starter files, without copying the starter Git repository.
python setup_starter_kit.py --target ../your-project --layout auto --integrate-agents --json
```

Replace `../your-project` with the actual destination root. The command uses the cloned repository's **`template/` files** and installs `AGENTS.md`, `.agents/`, and the CLI into the destination project layout. For an empty project, the CLI can be installed directly at its root; for an occupied project, `--layout auto` isolates the runtime in `tools/agent-cli-starter/` to preserve existing application files.

The installer reports the precise `entrypoint`. From the destination project root, verify the CLI with `python <entrypoint> sys-info --json` and `python <entrypoint> project-scan --json`, then restart/reload your coding agent if required. **Do not simply copy the raw `template/` files**: their placeholders must be rendered first. No `pip install` step is needed.

The [universal agent setup contract](AGENT_SETUP.md) explains agent discovery, acceptance evidence and the destination repository's branch/PR workflow. Existing project instructions remain authoritative.

## Universal installation layout

The **same Python installer and CLI contract** work with every supported coding agent.

| Layout | Runtime location | Use |
| --- | --- | --- |
| `--layout auto` (default) | Flat for new empty projects; isolated for occupied roots | Recommended; preserves existing installations |
| `--layout isolated` | `tools/agent-cli-starter/manage.py` | Django, monorepos, projects with their own `core/`, `src/` or `manage.py` |
| `--layout flat` | `manage.py` or `agent_cli.py` | Legacy compatibility where root layout is acceptable |

**Only the runtime is isolated.** Project-root `AGENTS.md` and `.agents/` remain discoverable. For an existing project, install from a reviewed starter checkout:

```bash
python setup_starter_kit.py --target /path/to/project --layout auto --integrate-agents --dry-run --json
python setup_starter_kit.py --target /path/to/project --layout auto --integrate-agents --json
```

Inspect the returned `layout`, `entrypoint`, `commands_dir`, `planned_created`, `planned_overwritten` and `skipped`. The chosen CLI is launched from the **destination project root**. On an isolated Django-like project:

```bash
python tools/agent-cli-starter/manage.py sys-info --json
python tools/agent-cli-starter/manage.py project-scan --json
```

The application's own `manage.py`, `src/`, `core/` and tests remain untouched. An unrelated existing `tools/agent-cli-starter/` tree is an installation error even with `--force`. Read the [universal layout contract](docs/INSTALL_LAYOUTS.md).

## Additional installation options

The **recommended method is to clone the repository and use its local installer**, as shown in [INSTALL.md](INSTALL.md). This allows source review and avoids executing a remotely downloaded script.

The installer also supports `--layout flat` for a brand-new, otherwise empty project and `--layout isolated` for explicitly namespaced runtime files. Use `--dry-run --json` first, and inspect `created`, `skipped`, and `planned_overwritten` before changing an existing codebase.

To update a previous installation, review the upstream changes, make a destination-project backup, and rerun the same installer. Files belonging to the project, including existing `AGENTS.md`, are preserved by default. `--force` should be limited to reviewed starter-owned files; it is not a solution to unknown path conflicts.

## Usage

```bash
python manage.py sys-info --json
python manage.py project-scan --json
python manage.py checkpoints --json
python manage.py checkpoints --action prune --json  # preview only
python manage.py --json sys-info --details
python manage.py dev-scaffold --command cache-clear --json
python manage.py dev-validate --file core/commands/cache_clear.py --json
python manage.py system-docgen --json
python manage.py verify-acceptance --manifest acceptance.json --sha256 REVIEWED_64_HEX_SHA256 --execute --json
python -m unittest discover -s tests -v
```

For explicit `--layout flat`, a foreign `manage.py` triggers the legacy `agent_cli.py` fallback. With the default `--layout auto`, such a project uses `tools/agent-cli-starter/manage.py` instead. Existing files are not overwritten without `--force`; even `--force` never replaces a foreign `manage.py`.

```bash
python agent_cli.py sys-info --json
```

## How it works

| Component | Contract |
| --- | --- |
| `BaseCommand` | Every plugin subclasses the base, declares its `argparse` options and returns a mapping. The dispatcher formats exactly one JSON response. |
| Output Budgeting | Maximum 50 list items or mapping keys, 5,000 characters per string, 12 nesting levels, and about 20,000 JSON characters overall. Suppresses stray plugin stdout and reports truncation. |
| Safe Discovery | Imports every `core/commands/*.py` module independently. Broken imports, class constructors, or argument registration are reported as warnings while healthy commands continue. **Not a sandbox** for untrusted code. |
| Telemetry | Duration is always included; process RSS is included only when optional `psutil` happens to be installed. Physical RAM uses standard-library OS fallbacks. |
| Doc Sync | `system-docgen` inspects registered `argparse` subparsers and generates `SKILL.md` including argument tables. |
| Optional Assertions | Plugins may return bounded, read-only `post_execution_assertions` warnings. No global system checks run by default. |
| Checkpoints | Project-local bounded atomic JSON with TTL and cooperative locks; `checkpoints` lists metadata or explicitly prunes expired entries. |
| Project Adaptation | `project-scan` detects common top-level stack markers without running project code or exposing manifest content. It proposes command names for deliberate implementation; it does **not** install or execute them. |
| Scaffold/Validation | `dev-scaffold` creates a persistent command and `unittest`; `dev-validate` checks AST for direct `print()` and inheritance. It is a linting aid, not a complete code safety proof. |
| Procedural Memory | `gotchas.md` stores verified environment findings. `self-learning.md` establishes a Post-Task Audit and doc update ritual; agents must actually follow it. |
| Acceptance Verification | `verify-acceptance` runs a reviewer-pinned manifest of positive and negative CLI scenarios with pinned fixture hashes. Opt-in execution; no shell commands or raw subprocess logs in the result. Not a sandbox or full proof of semantics. |

## Philosophy and adaptation

- [Engineering manifesto](docs/MANIFESTO.md) — bounded context, durable commands, verified procedural memory and responsible autonomy.
- [Project adaptation loop](docs/PROJECT_ADAPTATION.md) — read-only project discovery, opt-in tool expansion and privacy boundaries.
- [Universality and safety boundaries](docs/UNIVERSALITY.md) — implemented controls versus deliberately omitted project-specific features.
- [Roadmap](docs/ROADMAP.md) — shipped behavior versus ideas that still need implementation.
- [Procedural memory protocol](docs/PROCEDURAL_MEMORY.md) — verified lessons, review scope, privacy and limits.
- [Reliability Core](docs/RELIABILITY.md) — scaffold is not success; failing acceptance placeholders and Grounding Proof.

The template includes a first-use `.agents/rules/agent-onboarding.md` instruction. In a new project run `project-scan`, inspect the output and implement only the commands justified by an actual task. The scanner is shallow, deliberately avoids `.env` and private directories, and never runs user code.

## Integration with agents

The portable interface is the shared [agent setup contract](AGENT_SETUP.md), `AGENTS.md` and `.agents/skills/`; the following files only tell different agents where to find the **same** CLI and rules. There is no separate runtime per model or vendor.


- **Antigravity / agents supporting `.agents/`** — three `always_on` rules under `.agents/rules/`.
- **Cursor** — `.cursor/rules/agent-cli.mdc` includes an `alwaysApply` reference to the rules.
- **Claude Code** — `CLAUDE.md` references the CLI and operational notes.
- **Kilo Code** — automatically discovers root `AGENTS.md` and the project `.agents/skills/` directory. See [tested Kilo integration](docs/KILO_CODE.md); no platform-specific code is installed.
- **Codex / AGENTS.md readers** — project-root `AGENTS.md` introduces the same conventions; repo-local skills are under `.agents/skills/`. An existing project's instructions are preserved by default.
- **Aider** — launch with `aider --read AIDER_CONVENTIONS.md` to inject conventions. Aider won't automatically read that file just because it exists.

Some agents and versions do not auto-load every instruction format. Check your tool's current behavior; these are instructions, not a hard enforcement boundary.

## Privacy policy for upstream contributions

This repository contains only generic, publication-safe source, instructions and examples. Do not commit raw personal planning documents, private project paths, hostnames, credentials, tokens, proxy configuration, internal incident logs, `.env` content or sensitive operational data from a destination project. Review changes before publishing. Project-specific lessons belong in the **private destination project**, not this public starter.

## Installer guarantees and limits

- Uses only Python standard-library modules; `psutil` is optional.
- From a checkout it uses local `template/`; from a downloaded standalone installer it fetches template files from this repository over HTTPS.
- Pre-fetches all source files and validates target paths before changing project files; refuses symlink destinations.
- `--dry-run` lists planned creates, overwrites and skips without touching the destination.
- `--ref <full-Git-commit-SHA>` pins fetched installer/templates; the default `main` is mutable.
- A normal installation snapshots files it will change and restores them on an observed failure. Rollback does not cover third-party side effects, abrupt termination or a changed target from another concurrent process.
- Selects a non-conflicting flat or isolated runtime with `--layout auto`; returns the exact CLI entrypoint.
- Skips existing files without `--force` and idempotently appends `.cle_state/`, `.cle_cache/` and `__pycache__/` to `.gitignore`.
- Generates `SKILL.md` immediately; on later installs, when an existing `SKILL.md` is preserved, runs doc generation in dry-run mode instead of overwriting it.
- **Heads-up:** in a project that already uses `core/commands`, non-overwrite mode may leave collisions. Review `skipped` in the installer JSON, and resolve manually before relying on the CLI. Take backups before using `--force`; this is not a fully isolated plugin sandbox.
- The CLI's plugin import error isolation does **not** prevent filesystem/network side effects from untrusted plugins. Only install trusted code.

## Developing commands

Create a persistent command with `dev-scaffold`, implement `run()` to return a JSON-compatible dictionary, add tests, run `dev-validate`, and regenerate docs. The generated `SKILL.md` is versionable. Append only **verified** and scoped incident details to `gotchas.md` and never include secrets; see [Procedural memory](docs/PROCEDURAL_MEMORY.md).

## Testing

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the tests on Ubuntu and Windows for Python 3.10, 3.11 and 3.12. No `pip install` step is required.

## License

[MIT](LICENSE).

## Self-improvement without leaking project context

The template includes a persistent command-authoring rule, a `self-improvement` skill, a manually maintained `cli-tools/recipes.md` and a project-local `.agents/backlog/cli-features.md`. Agents can suggest durable improvements and record only tested workflows. `system-docgen` changes the generated command reference, not personal notes. Existing `gotchas.md`, `recipes.md` and `.agents/backlog/cli-features.md` are preserved even when upgrading with installer `--force`. No automated background agent or model-weight training is implied.

Long-running project commands can optionally use `from core.state import CheckpointStore` for private, TTL-limited checkpoints; the CLI provides metadata-only listing and a read-only expiry preview by default. Restore/resume logic is never automatic; each command must validate its own state and request appropriate authorization.

For stack-specific health checks, a plugin can override `BaseCommand.post_execution_assertions()` to return bounded **warnings**, never to change running systems. No project-specific processes or services are inspected by default.
