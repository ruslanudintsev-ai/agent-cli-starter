# Agent CLI Starter — universal source repository guidance

This repository is the **shared source and installer**, not a destination project.

**Canonical instructions for all coding agents:** read [AGENT_SETUP.md](AGENT_SETUP.md), `README.md`, and `setup_starter_kit.py` before installing in another repository. Do not invent a nested `.agents/agent-cli-starter` layout or a new installer per agent. Identify the real destination root, respect its existing project rules and Git branch/PR workflow, and use the reviewed installer with `--dry-run` before applying.

If the destination has an `AGENTS.md`, preserve it and use `--integrate-agents` only after inspecting the resulting changes. Follow the documented cross-agent verification protocol: file placement and CLI execution are not proof of automatic instruction discovery or feature correctness.

Never copy destination-project secrets, personal files or private notes into this public repository. Do not claim a scaffold is fully implemented merely because AST or smoke tests pass. Model-specific instructions are optional compatibility notes, not the architecture.
