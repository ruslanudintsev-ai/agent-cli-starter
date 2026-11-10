# Reviewed CLI recipes (project-local)

This file is manually maintained; `system-docgen` regenerates `SKILL.md` but never modifies `recipes.md`.
Record only **tested and reusable** workflows. Use synthetic or non-sensitive examples. Distinguish intended commands from implemented ones.

## Recipe template

### Purpose / applicable projects
- **Prerequisites:** Tool, versions, supported scope and required permissions.
- **Procedure:** Numbered, bounded `python __ENTRYPOINT__ <command> --json` invocations using existing commands.
- **Verification:** Observable test output / safe success criteria.
- **Failure recovery:** Reversible, approved steps first.
- **Last verified:** YYYY-MM-DD and generic environment.

Do not include secrets, private endpoints, users, logs, or raw outputs.
