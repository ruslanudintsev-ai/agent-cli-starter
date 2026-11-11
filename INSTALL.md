# Installation — Clone, Copy, Verify

Agent CLI Starter is a collection of **project-local files**, not a hosted service. Clone this repository and **copy the starter into the root of your own project** using the included installer. It renders the templates, preserves existing instructions, and checks the generated CLI.

**Requirements:** Git, Python 3.10 or later, and a destination project directory. No Python packages need to be installed.

## Step 1 — Clone the repository

In a terminal **outside** the destination project:

```bash
git clone https://github.com/ruslanudintsev-ai/agent-cli-starter.git
cd agent-cli-starter
```

Review the repository and its current commit before installing into an important project. For reproducible installations, use a reviewed full Git commit SHA as your checkout revision (`git checkout <reviewed-sha>`).

## Step 2 — Copy the starter into your project root

The **source** is the cloned `agent-cli-starter/` directory. The **destination** is your existing application's **root directory**, not `.agents/agent-cli-starter/` and not the starter repository itself.

**Linux, macOS, WSL, Git Bash:**

```bash
# Run from inside the cloned agent-cli-starter directory.
python3 setup_starter_kit.py --target ../your-project --layout auto --integrate-agents --dry-run --json
# Review the proposed created/overwritten/skipped files before applying.
python3 setup_starter_kit.py --target ../your-project --layout auto --integrate-agents --json
```

**Windows PowerShell:**

```powershell
# Run from inside the cloned agent-cli-starter directory.
python .\setup_starter_kit.py --target "C:\Projects\your-project" --layout auto --integrate-agents --dry-run --json
# Review the proposed file changes, then apply.
python .\setup_starter_kit.py --target "C:\Projects\your-project" --layout auto --integrate-agents --json
```

Replace the example destination path with your own project root. The installer **copies and configures the contents of `template/`**; it does not copy the starter's `README.md`, upstream Git history or upstream test suite into your application. Do **not** blindly copy the entire cloned repository or raw `template/` directory: source templates contain placeholders that the installer must render.

`--layout auto` is recommended: an otherwise empty project gets the CLI at the project root; an occupied Django/Node/other project gets the runtime under `tools/agent-cli-starter/`. In both cases, agent instructions and skills are copied to the **destination project root**. This avoids overwriting the application's own `manage.py` or `core/`.

For a **new empty project only**, add `--layout flat` to explicitly put `core/` and `manage.py` directly in the destination root. For an occupied project, keep `--layout auto`. Never use `--force` to resolve unknown collisions.

## Step 3 — Verify the copied files and run the CLI

Look at the JSON output. The key `entrypoint` specifies **exactly which file to run**. Examples of the destination layout:

**Flat layout (new empty project):**

```text
your-project/
├── AGENTS.md
├── .agents/
│   ├── rules/
│   └── skills/
├── .cursor/rules/
├── CLAUDE.md
├── AIDER_CONVENTIONS.md
├── manage.py
└── core/
    └── commands/
```

**Isolated runtime (existing application):**

```text
your-project/
├── AGENTS.md
├── .agents/
│   ├── rules/
│   └── skills/
├── manage.py                         # Application's own file (if present)
├── src/                              # Application code (if present)
└── tools/
    └── agent-cli-starter/
        ├── manage.py                 # Starter CLI
        └── core/
            └── commands/
```

From the destination project root, run **only the entrypoint returned by the installer**:

```bash
# Flat layout (entrypoint: manage.py)
python manage.py sys-info --json
python manage.py project-scan --json

# OR isolated layout (entrypoint: tools/agent-cli-starter/manage.py)
python tools/agent-cli-starter/manage.py sys-info --json
python tools/agent-cli-starter/manage.py project-scan --json
```

Verify that commands exit with code 0 and their JSON results report `status: "ok"`. Confirm that `AGENTS.md` and `.agents/skills/cli-tools/SKILL.md` exist in the destination root and point to the reported CLI entrypoint. Inspect the destination Git diff; follow its issue/branch/PR workflow.

## Step 4 — Start a new coding-agent session

Agents do not all auto-discover the same instruction files. `AGENTS.md`, `.agents/skills/`, `.cursor/rules/`, `CLAUDE.md`, and `AIDER_CONVENTIONS.md` offer references for different agent tools. Start a new session or reload instructions where your tool requires it. Test a safe command invocation in the new session before claiming the agent itself adopted the setup.

### Installation status

- **PLANNED** — only the `--dry-run` preview was run.
- **FILES_INSTALLED** — the installer copied/configured files; agent adoption is not yet proven.
- **INSTALLED** — file placement and CLI smoke commands were checked.
- **AGENT_VERIFIED** — a fresh agent session demonstrably reads the instructions and invokes the CLI.
- **BLOCKED** — unresolved collision, failed test or lack of permission.

### Existing instructions and updates

Existing `AGENTS.md` is **never overwritten**, including with `--force`; `--integrate-agents` adds an idempotent marked reference while preserving the project's rules. The installer preserves local procedural notes in `gotchas.md`, `recipes.md` and the feature backlog.

To update, pull the reviewed starter revision and repeat the same dry-run and apply procedure. Existing starter files are **not automatically overwritten**; review `skipped` and use `--force` only after a backup and review of starter-owned paths. The installer is not a sandbox; only use trusted project plugins and approved local/CI environments.

For technical details and alternate layouts, see [Universal setup for agents](AGENT_SETUP.md) and [Installation layouts](docs/INSTALL_LAYOUTS.md).
