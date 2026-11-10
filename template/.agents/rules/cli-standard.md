---
trigger: always_on
description: Reusable command-first workflow; prohibit throwaway root scripts
---

# CLI standard — always on

1. First read `.agents/skills/cli-tools/SKILL.md` , `.agents/skills/cli-tools/gotchas.md`, and `.agents/rules/agent-onboarding.md`, and `.agents/rules/command-authoring.md`.
2. Do not create temporary, ad-hoc project scripts (`temp.py`, `script_v1.py`, `debug_once.py`, etc.) in the repository root or elsewhere just to complete an operation. Temporary **data** and test fixtures are different from throwaway executable scripts.
3. Run project operations through `python __ENTRYPOINT__ <command> --json`. Examples: `python __ENTRYPOINT__ sys-info --json` and `python __ENTRYPOINT__ dev-validate --file core/commands/example.py --json`.
4. If a reusable command is missing, first run `python __ENTRYPOINT__ dev-scaffold --command your-command --json`; implement its persistent command module under `core/commands/` and add a test.
5. Every command must subclass `BaseCommand`, return a mapping, use `argparse` for its arguments, and avoid direct `print()` calls. The dispatcher owns output formatting and output limits.
6. Never dump secrets, large files or unrestricted logs into a model context. Filter, summarize, paginate, or return bounded JSON. `--json` does not make sensitive output safe by itself.
7. Do not execute downloaded scripts, mutate production or remove files without the normal approval and safety checks for the project. These rules govern workflow, not user authority.

8. For repeated improvements use `.agents/skills/self-improvement/SKILL.md`; store verified manual recipes in `cli-tools/recipes.md` and unbuilt proposals in `.agents/backlog/cli-features.md`. Never treat a backlog item as an available command.
