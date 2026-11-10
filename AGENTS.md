# Agent CLI Starter — source repository guidance

This is a reusable **installer source**, not a target project. If a user asks to install this framework into another project, first identify the target checkout root; do not create a nested `.agents/agent-cli-starter` folder. Preserve the target project's own rules, CI flow, branches and files.

Read `README.md`, `docs/CODEX.md` and `setup_starter_kit.py`. The installer already places `AGENTS.md`, `.agents/rules/`, `.agents/skills/` and the CLI at the destination root. Preview with `--target <project-root> --integrate-agents --dry-run --json` from a reviewed checkout, then apply on a permitted branch and run real smoke commands. Report observed evidence, not assumed installation.

If the target already has `AGENTS.md`, do not replace it: the explicit `--integrate-agents` option appends a reviewable managed reference. Do not modify `AGENTS.override.md` automatically. Respect project Git workflow rules; a PR may be needed, but do not mistake planning a PR for completing the user's requested work.

Never leak destination project secrets, private notes, absolute paths or account details into this public upstream repository. Tests and documentation should remain project-agnostic. Do not claim a scaffold passes behavioral acceptance without real positive and negative cases.
