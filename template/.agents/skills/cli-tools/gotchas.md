# Verified environment gotchas (project-local procedural memory)

Read before a task; update only when you can reproduce or verify the evidence. This file is **project-scoped**, not a public incident report. Never store secrets, personal information, private hostnames, internal endpoints or entire logs. Do not copy project-specific notes into the public starter repository.

## Known starter constraints

- If another application owns `manage.py`, the installer uses `agent_cli.py`. Neither foreign entrypoint may be overwritten, even with `--force`.
- Use `--dry-run` to inspect installation changes first. Existing files are preserved unless `--force`; failed installation or doc generation attempts to restore all files the installer changed.
- To install a reviewed source revision, pass `--ref <40-character-commit-SHA>` and use a bootstrap URL for that same commit. The default `main` can change.
- `psutil` is optional and physical RAM diagnostics use platform-specific standard-library fallbacks.
- `--json` works before or after the command name. Plugins must return mappings, not print directly.
- Output is limited to 50 list/map items, 5,000 characters per string, depth 12 and ~20,000 total JSON characters.
- Safe Discovery only isolates plugin load/configuration failures, **not malicious plugin behavior**.
- Atomic replacement (`os.replace`) protects against partial file writes, but multi-writer state still requires coordination.

## Incident entry template

### YYYY-MM-DD — Component / short symptom
- **Scope:** OS, tool and version (generic; omit identifying paths/hostnames).
- **Observed symptom:** Minimal sanitized error text or observable outcome.
- **Cause:** Verified root cause, or explicitly *unknown*.
- **Recovery:** Non-destructive steps first; mention required approval for any destructive action.
- **Validation:** Test/command that reproduced and verified the recovery, including pass/fail.
- **Limitation / recheck:** Conditions under which the note may no longer apply.

Do not add imagined examples as if they were real incidents. Remove or correct stale assertions when new evidence invalidates them.
