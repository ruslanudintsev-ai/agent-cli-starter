# Structured command errors

Agent CLI Starter uses a **single bounded JSON envelope** for every installed CLI command. A non-zero command exit code is a failure and must never be presented as completion.

## Expected failures: `CommandError`

Raise an explicit, actionable error from a trusted project command rather than relying on an uncontrolled exception string:

```python
from core.commands.base import BaseCommand, CommandError

# Inside run(args):
if not target.exists():
    raise CommandError(
        "The target directory does not exist.",
        error_code="INVALID_TARGET_DIRECTORY",
        suggested_fix="Choose an existing directory and rerun with --target.",
        details={"argument": "--target"},  # Optional, sanitized metadata only
    )
```

The dispatcher emits exactly one JSON document and exits with code **1**:

```json
{
  "command": "your-command",
  "result": {
    "status": "error",
    "error_code": "INVALID_TARGET_DIRECTORY",
    "message": "The target directory does not exist.",
    "suggested_fix": "Choose an existing directory and rerun with --target.",
    "details": {"argument": "--target"}
  },
  "_telemetry": {"duration_ms": 0.0, "process_rss_mb": null}
}
```

Telemetry values vary. `error_code` is a stable, uppercase identifier matching `[A-Z][A-Z0-9_]{2,63}`. It is intended for *routing*, not as proof that a retry is safe.

## Existing commands and unexpected exceptions

- Commands returning `{"status": "error", ...}` retain all their existing fields and exit code **1**. If `error_code`, `message` or `suggested_fix` were omitted, the dispatcher adds **generic** recovery fields. That fallback is not a diagnosis and must not be treated as a verified fix.
- The `project-scan --root` invalid-directory path demonstrates a concrete `INVALID_PROJECT_ROOT` error with a specific next step.
- Unexpected exceptions return `UNEXPECTED_ERROR`, `error_type` and a **generic** recommendation. The raw exception message and traceback are not emitted, because they could contain confidential paths, credentials or private data. Inspect trusted local debugging evidence instead.
- Success payloads stay unchanged. Error payloads and intentionally provided details are subject to the existing bounded-output limits.

## Safety and learning contract

A structured error is a diagnostic hint, **not authority to perform remediation**. The agent must not auto-run destructive or privileged fixes. It should reproduce the observed failure, verify the proposed correction against project requirements, and record a project-local gotcha only with evidence. The caller must never blindly execute shell commands constructed from `suggested_fix`.

Do not place raw tokens, cookies, sensitive file paths or user data in `CommandError` messages, suggestions or details. The dispatcher bounds length but **cannot identify and redact arbitrary secrets from intentionally supplied data**.

This contract is independent of model/provider and installation layout. It does not train model weights, bypass any permission requirements or certify that a command's underlying behavior is correct.
