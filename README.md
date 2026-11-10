# Agent CLI Starter

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen)](template/core/commands/base.py)
[![CI](https://github.com/ruslanudintsev-ai/agent-cli-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/ruslanudintsev-ai/agent-cli-starter/actions/workflows/ci.yml)

**Zero-dependency, cross-platform project command scaffold for coding agents** — Antigravity, Cursor, Claude Code, Kilo Code, Aider and tools that support project instruction files.

Instead of writing `temp.py`, `script_v1.py` and dumping unlimited logs into a model context, agents can extend a reusable Python CLI with explicit parameters, bounded JSON results, tests, and persistent operational notes.

## Quick install

Open a terminal in the **target project directory** (not this starter repository).

Linux, macOS, WSL, Git Bash:

```bash
curl -fsSL https://raw.githubusercontent.com/ruslanudintsev-ai/agent-cli-starter/main/install.sh | bash
```

Windows PowerShell, with Python 3.10+ installed:

```powershell
python -c "import urllib.request; exec(compile(urllib.request.urlopen('https://raw.githubusercontent.com/ruslanudintsev-ai/agent-cli-starter/main/setup_starter_kit.py').read(), '<installer>', 'exec'))" 
```

**PowerShell note:** the remote installer is loaded in the current process and writes the project files to the current directory. To inspect it first, download `setup_starter_kit.py` and run `python setup_starter_kit.py` directly. Executing scripts over HTTPS means trusting the remote code; for sensitive projects, inspect and pin a reviewed release commit.

From a cloned checkout (offline, local template):

```bash
python setup_starter_kit.py --target /path/to/project
```

## Safer install and update (v1.2)

**Inspect first, without writing anything:**

```bash
python setup_starter_kit.py --target /path/to/project --dry-run --json
```

Or via the shell installer (in the target project directory):

```bash
curl -fsSL https://raw.githubusercontent.com/ruslanudintsev-ai/agent-cli-starter/main/install.sh | bash -s -- --dry-run --json
```

**Pin every downloaded component to a reviewed commit:** replace `FULL_40_CHARACTER_COMMIT_SHA` below with the verified 40-character SHA of a reviewed GitHub commit (not a tag or branch):

```bash
curl -fsSL https://raw.githubusercontent.com/ruslanudintsev-ai/agent-cli-starter/FULL_40_CHARACTER_COMMIT_SHA/install.sh | bash -s -- --ref FULL_40_CHARACTER_COMMIT_SHA
```

The shell installer obtains its Python installer from the same SHA; that installer downloads template files from the same SHA. The quick-install `main` URL is convenient but mutable. Verify/trust upstream code before executing a network script. `--ref` does not provide independent signature verification.

The Python installer supports `--force` to replace starter-owned files, `--dry-run` for a non-writing plan, and `--ref` for a commit SHA. Never replace foreign entrypoints. Installation attempts to roll back **its own file writes** if a step fails, including failed documentation generation, but it cannot reverse side effects from arbitrary third-party plugins imported by the target CLI, or recover from power loss/forced termination at every point. Back up valuable projects before `--force`.

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
python -m unittest discover -s tests -v
```

If the project already has a **foreign** `manage.py` (including Django), the starter creates **`agent_cli.py`** instead and patches generated instructions. Existing files are not overwritten without `--force`; even `--force` never replaces a foreign `manage.py`.

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

## Philosophy and adaptation

- [Engineering manifesto](docs/MANIFESTO.md) — bounded context, durable commands, verified procedural memory and responsible autonomy.
- [Project adaptation loop](docs/PROJECT_ADAPTATION.md) — read-only project discovery, opt-in tool expansion and privacy boundaries.
- [Universality and safety boundaries](docs/UNIVERSALITY.md) — implemented controls versus deliberately omitted project-specific features.
- [Roadmap](docs/ROADMAP.md) — shipped behavior versus ideas that still need implementation.
- [Procedural memory protocol](docs/PROCEDURAL_MEMORY.md) — verified lessons, review scope, privacy and limits.
- [Reliability Core](docs/RELIABILITY.md) — scaffold is not success; failing acceptance placeholders and Grounding Proof.

The template includes a first-use `.agents/rules/agent-onboarding.md` instruction. In a new project run `project-scan`, inspect the output and implement only the commands justified by an actual task. The scanner is shallow, deliberately avoids `.env` and private directories, and never runs user code.

## Integration with agents

- **Antigravity / agents supporting `.agents/`** — three `always_on` rules under `.agents/rules/`.
- **Cursor** — `.cursor/rules/agent-cli.mdc` includes an `alwaysApply` reference to the rules.
- **Claude Code** — `CLAUDE.md` references the CLI and operational notes.
- **Kilo Code** — automatically discovers root `AGENTS.md` and the project `.agents/skills/` directory. See [tested Kilo integration](docs/KILO_CODE.md); no platform-specific code is installed.
- **AGENTS.md readers** — `AGENTS.md` introduces the same conventions.
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
