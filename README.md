# Agent CLI Starter

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen)](template/core/commands/base.py)
[![CI](https://github.com/ruslanudintsev-ai/agent-cli-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/ruslanudintsev-ai/agent-cli-starter/actions/workflows/ci.yml)

**Zero-dependency, cross-platform project command scaffold for coding agents** — Antigravity, Cursor, Claude Code, Aider and tools that support project instruction files.

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

## Usage

```bash
python manage.py sys-info --json
python manage.py project-scan --json
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
| Project Adaptation | `project-scan` detects common top-level stack markers without running project code or exposing manifest content. It proposes command names for deliberate implementation; it does **not** install or execute them. |
| Scaffold/Validation | `dev-scaffold` creates a persistent command and `unittest`; `dev-validate` checks AST for direct `print()` and inheritance. It is a linting aid, not a complete code safety proof. |
| Procedural Memory | `gotchas.md` stores verified environment findings. `self-learning.md` establishes a Post-Task Audit and doc update ritual; agents must actually follow it. |

## Philosophy and adaptation

- [Engineering manifesto](docs/MANIFESTO.md) — bounded context, durable commands, verified procedural memory and responsible autonomy.
- [Project adaptation loop](docs/PROJECT_ADAPTATION.md) — read-only project discovery, opt-in tool expansion and privacy boundaries.
- [Roadmap](docs/ROADMAP.md) — shipped behavior versus ideas that still need implementation.

The template includes a first-use `.agents/rules/agent-onboarding.md` instruction. In a new project run `project-scan`, inspect the output and implement only the commands justified by an actual task. The scanner is shallow, deliberately avoids `.env` and private directories, and never runs user code.

## Integration with agents

- **Antigravity / agents supporting `.agents/`** — three `always_on` rules under `.agents/rules/`.
- **Cursor** — `.cursor/rules/agent-cli.mdc` includes an `alwaysApply` reference to the rules.
- **Claude Code** — `CLAUDE.md` references the CLI and operational notes.
- **AGENTS.md readers** — `AGENTS.md` introduces the same conventions.
- **Aider** — launch with `aider --read AIDER_CONVENTIONS.md` to inject conventions. Aider won't automatically read that file just because it exists.

Some agents and versions do not auto-load every instruction format. Check your tool's current behavior; these are instructions, not a hard enforcement boundary.

## Privacy policy for upstream contributions

This repository contains only generic, publication-safe source, instructions and examples. Do not commit raw personal planning documents, private project paths, hostnames, credentials, tokens, proxy configuration, internal incident logs, `.env` content or sensitive operational data from a destination project. Review changes before publishing. Project-specific lessons belong in the **private destination project**, not this public starter.

## Installer guarantees and limits

- Uses only Python standard-library modules; `psutil` is optional.
- From a checkout it uses local `template/`; from a downloaded standalone installer it fetches template files from this repository over HTTPS.
- Pre-fetches all source files before changing any project file.
- Skips existing files without `--force` and idempotently appends `.cle_state/`, `.cle_cache/` and `__pycache__/` to `.gitignore`.
- Generates `SKILL.md` immediately; on later installs, when an existing `SKILL.md` is preserved, runs doc generation in dry-run mode instead of overwriting it.
- **Heads-up:** in a project that already uses `core/commands`, non-overwrite mode may leave collisions. Review `skipped` in the installer JSON, and resolve manually before relying on the CLI. Take backups before using `--force`.
- The CLI's plugin import error isolation does **not** prevent filesystem/network side effects from untrusted plugins. Only install trusted code.

## Developing commands

Create a persistent command with `dev-scaffold`, implement `run()` to return a JSON-compatible dictionary, add tests, run `dev-validate`, and regenerate docs. The generated `SKILL.md` is versionable. Append only **verified** incident details to `gotchas.md` and never include secrets.

## Testing

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the tests on Ubuntu and Windows for Python 3.10, 3.11 and 3.12. No `pip install` step is required.

## License

[MIT](LICENSE).
