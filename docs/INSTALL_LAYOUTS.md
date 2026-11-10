# One universal installer, two non-conflicting layouts

The **same** Python CLI, verified procedural memory and acceptance checks work with any compatible coding agent. The layout is chosen according to the destination project, not according to Codex, Kilo or any model.

| Layout | Runtime | Root instructions |
| --- | --- | --- |
| `flat` | `manage.py` (fallback `agent_cli.py`) and `core/` | `AGENTS.md`, `.agents/` |
| `isolated` | `tools/agent-cli-starter/manage.py` and `tools/agent-cli-starter/core/` | `AGENTS.md`, `.agents/` |

`--layout auto` keeps existing flat/isolated deployments where they are. New targets with existing app markers (`manage.py`, `src/`, `core/`, `pyproject.toml`, `package.json`) use isolated runtime; otherwise flat.

## Django / existing project

From a reviewed source checkout, targeting the actual destination Git checkout (in a permitted branch):

```bash
python setup_starter_kit.py --target /path/to/django-project --layout auto --integrate-agents --dry-run --json
python setup_starter_kit.py --target /path/to/django-project --layout auto --integrate-agents --json
```

Inspect the dry-run. The Django application `manage.py`, its `src/`, `core/`, and tests are preserved. The installer returns the selected `entrypoint`; **from the destination project root**, invoke:

```bash
python tools/agent-cli-starter/manage.py sys-info --json
python tools/agent-cli-starter/manage.py project-scan --json
```

Do not call Django's `manage.py` in place of the CLI. A foreign pre-existing directory at `tools/agent-cli-starter/` blocks the isolated installation even with `--force`. The standalone Bash installer also detects isolated entrypoints.

## Meaningful outcomes

**PLANNED** means only `--dry-run` was done. **INSTALLED** requires successful file placement, a real CLI execution and unchanged foreign application sources. **AGENT_VERIFIED** requires observing the agent discover and use the installed rules/CLI in a new permitted task. A passing install is not proof that new feature behavior is correct; that requires independent acceptance.

Agent-specific configuration files are optional compatibility adapters, not separate runtimes. Reopen an agent session if project instructions are snapshotted at session start.
