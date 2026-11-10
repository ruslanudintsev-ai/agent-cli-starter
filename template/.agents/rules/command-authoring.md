---
trigger: always_on
description: Reusable command development contract, validation and safety gate
---

# Command authoring — universal rules

1. Never substitute a disposable `temp.py`, `script_v2.py` or shell file for a reusable project operation. Prefer an existing documented command; otherwise consider `python __ENTRYPOINT__ dev-scaffold --command <kebab-name> --json`.
2. Locate new Python commands in `core/commands/<snake_name>.py`. Declare one concrete subclass of `BaseCommand`, set a unique kebab-case `name` and `description`, and implement `configure_parser(parser)` and `run(args)`.
3. `run(args)` MUST return a mapping with `status: ok` or `status: error`; never directly `print()` or return unbounded raw data. The dispatcher owns JSON serialization, budgets and telemetry.
4. Make arguments explicit. Nontrivial/dangerous actions require an independently reviewed plan, a dry-run path, clear confirmation/authorization and a test. **Do not** silently introduce destructive commands, remote execution, eval/exec, background processes or secret collection.
5. Specify behavior and an independent observable acceptance oracle before implementation. `dev-scaffold` deliberately generates SCAFFOLDED code with error `NOT_IMPLEMENTED` and two failing test placeholders (positive case and negative/counterexample). Replace both with meaningful, reproducible fixtures and assertions before claiming VERIFIED. Run `dev-validate`, focused acceptance tests and `system-docgen`; AST validity is NOT functional proof. For changes to tests/oracle require separate review.
6. Check `.agents/skills/cli-tools/recipes.md` for reviewed workflows, `gotchas.md` for verified environment restrictions, and `.agents/backlog/cli-features.md` for prospective commands.
7. Command discovery is **exception isolation, not a permission boundary or sandbox**. New modules are imported and can execute top-level Python. Review all contributed code before importing it.
8. A plugin that checks runtime invariants may override `post_execution_assertions`, returning bounded generic warnings. It must not mutate state, inspect unrelated processes or disclose secrets. Never assume a default global invariant applies to every project.

These are instructions for cooperating agents, not a hard enforcement or a substitute for project-specific safety rules.
