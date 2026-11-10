# Kilo Code compatibility

The starter is a Python control-plane with standard `AGENTS.md` instructions and Agent Skills. It does **not** depend on Kilo-specific APIs, configurations or model providers.

## Discovery

Kilo Code automatically loads a project's root `AGENTS.md` and discovers skills from `.agents/skills/<name>/SKILL.md`. The installer already supplies both. Start a new Kilo session (or reload its configuration) after installation.

Reference: [Kilo AGENTS.md](https://kilo.ai/docs/customize/agents-md), [Kilo Skills](https://kilo.ai/docs/customize/skills).

## Verified isolated smoke test

On November 10, 2026, we tested with the Kilo Code VS Code extension 7.8.27, its bundled CLI, Python 3.12 on Windows, and a disposable project directory:

1. The CLI's `debug skill` output included `cli-tools` and `continuous-skill-evolution`.
2. An agent invoked `python manage.py project-scan --json` and `python manage.py sys-info --json`. Both completed.
3. A second agent task used `dev-scaffold --command sandbox-audit`, `dev-validate`, `system-docgen`, and `sandbox-audit --json`. Each completed successfully.
4. Independent checks verified the new module, generated `SKILL.md` reference, and generated unittest. No throwaway `temp*.py` or `script_v*.py` files were found.

The generated `sandbox-audit` command was a **starter stub**, not a production auditor. This was an integration smoke test, **not** an A/B benchmark or proof of reduced token usage.

## Safety and behavior

- Instructions are guidance, not an enforcement layer. The Kilo model also used ordinary directory-listing shell commands during the scaffold task; CLI-first does not mean every shell operation is replaced.
- Kilo's noninteractive runner handles approvals differently from its interactive IDE. Test permissions on your actual version and do not rely on `--auto` as a sandbox. Use a disposable OS-isolated environment for autonomous runs; keep production actions approval-gated.
- Use `AGENTS.md` and `.agents/skills/` as the portable integration. Do not install duplicate Kilo-only rules or overwrite existing `kilo.jsonc` files solely to use this starter.
- The installer and scanner do not execute project-specific workflows or claim to make the coding model learn new weights. Persistent verified procedures are supplied as files for the model to consult.

## Manual smoke commands

In a disposable destination project, after installing the starter:

```bash
python manage.py sys-info --json
python manage.py project-scan --json
python manage.py dev-scaffold --command sandbox-audit --json
python manage.py dev-validate --file core/commands/sandbox_audit.py --json
python manage.py system-docgen --json
python manage.py sandbox-audit --json
```

If your existing project uses a foreign `manage.py`, substitute `agent_cli.py`. Never run scaffolding in a valuable codebase just to test discovery.
