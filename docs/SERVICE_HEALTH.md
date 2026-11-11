# Read-only local health checks

`service-health` is a universal CLI **diagnostic**, not a service manager or production health certification. It inspects only local Python, disk and known project metadata. It does not run application commands, collect credentials, send network requests, restart processes, clear caches or repair configuration.

```bash
python manage.py service-health --json
python manage.py service-health --component disk --min-free-mb 512 --dry-run --json
python manage.py service-health --component commands --json
```

When installed in isolated mode, use the reported entrypoint (for example `python tools/agent-cli-starter/manage.py service-health --json`).

## Checks and truthfulness

- **python**: running Python interpreter is version 3.10 or newer.
- **disk**: available space in the current project's filesystem is at least `--min-free-mb` (default 256 MiB).
- **workspace**: presence of root `AGENTS.md`, `.agents/rules/cli-standard.md`, and `.agents/skills/cli-tools/SKILL.md`. Does not read their contents, assert that an agent actually loaded them, or check permissions by writing a probe file.
- **commands**: expected built-in CLI commands are registered and no plugin discovery warnings occurred. Counts warnings without exposing their raw exception text.

You can select a check via `--component python|disk|workspace|commands`; default `all` checks all four. `--dry-run` states no-repair intent; **the command is always read-only**, with or without this flag.

The `checks` JSON object lists each observed result. If any selected check fails, the command exits **1** and returns `status: error`, `health_state: DEGRADED`, `error_code: HEALTH_CHECK_FAILED` and a generic recovery suggestion. If all selected checks pass, it exits **0** with `health_state: HEALTHY`. Here `HEALTHY` means *only that the specified shallow checks passed*. It is not evidence of working application features, secure production configuration, or absence of unobserved errors.

An invalid disk threshold raises typed `INVALID_DISK_THRESHOLD`. Neither that hint nor `HEALTH_CHECK_FAILED` authorizes automatic destructive remediation. Verify causes independently and follow project permissions.

## Limits

The framework imports its registered CLI plugins during command discovery. That is a trusted-code operation and **not a sandbox**. The health checker does not itself import user application modules, and its results avoid raw project file contents and absolute paths. A check of guidance files proves their presence only, not that any specific agent reads them.
