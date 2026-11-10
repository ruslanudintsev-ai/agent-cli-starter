# Environment gotchas and verified workarounds

Read before making changes; append only reproducible findings. Never store secrets.

## Starter-kit invariants

- `manage.py` may belong to Django or another tool. When occupied, this installer uses `agent_cli.py` and patches its generated rules accordingly.
- Keep `psutil` optional. System RAM detection has Python standard-library fallbacks.
- Prefer `pathlib.Path` over hard-coded platform-specific path separators.
- `--json` is accepted before or after the command name. Plugins return mappings and must not use `print()`.
- CLI output is trimmed: lists and mappings to 50 entries, individual strings to 5,000 characters, nesting to 12 levels and total JSON around 20,000 characters.
- Safe Discovery quarantines **import/configuration errors** only. It does not sandbox malicious plugin code.
- State files under `.cle_state/` should be written to a temporary sibling and atomically moved with `os.replace()`; coordinate concurrent writers if updates must be serialized.

## Verified incidents

Add entries in this format:

### YYYY-MM-DD — Area / symptom
- **Symptom:** What happened?
- **Cause:** What was confirmed?
- **Resolution:** Reproducible fix and verification command.
