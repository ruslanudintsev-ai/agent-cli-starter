# Agent guidance snapshots — opt-in and one file at a time

The command `config-snapshot` protects a **reviewed, existing agent-instruction file** against accidental changes. It reuses the private `.cle_state/checkpoints/` directory and `CheckpointStore`; it is not a generic configuration backup, a sandbox or a production rollback tool.

It supports only `AGENTS.md`, `CLAUDE.md`, `AIDER_CONVENTIONS.md`, individual `.agents/rules/*.md` files and individual `.cursor/rules/*.mdc` files. It refuses symlink components, hard-linked or non-regular files, path traversal, absent targets, and files over **48 KiB**. Never snapshot credentials, `.env`, application source, databases, or unreviewed configuration. Storage contains base64-encoded file content **without encryption**; keep the `.cle_state/` directory private and Git-ignored. Snapshots expire after seven days.

## Workflow

From the destination project root, use the exact installed CLI entrypoint:

```bash
# Listing is read-only and never shows file contents.
python manage.py config-snapshot --action list --json

# Explicitly create a private snapshot of an allowed guidance file.
python manage.py config-snapshot --action create --file AGENTS.md --json

# Preview only. Use the exact snapshot_id returned above.
python manage.py config-snapshot --action restore --id cfg-REPLACE_WITH_ID --json

# After a human reviews and authorizes the restore, pass the confirmation_sha256
# from the CURRENT preview, not from an old run.
python manage.py config-snapshot --action restore --id cfg-REPLACE_WITH_ID \
    --apply --confirm REVIEWED_CURRENT_CONFIRMATION_SHA256 --json
```

On Windows PowerShell, put the last command on one line rather than using a Bash line continuation.

`restore` without `--apply` reports `PREVIEW_ONLY`, `would_change`, `current_sha256`, `snapshot_sha256` and a confirmation digest, **without changing any project file**. Restore with `--apply` checks that the confirmation matches the current file state and then atomically replaces the one allowed file. When successful it returns `RESTORED`, plus `undo_snapshot_id` containing the exact pre-restore bytes. Undo is **another separate preview and explicit restore**, not an automatic rollback.

If the file changed after preview, the supplied confirmation no longer matches and the action fails with `STALE_RESTORE_PLAN`. Malformed, expired or corrupted snapshots fail rather than silently restoring anything. The tool refuses to restore a deleted target and never creates a new project file during a restore.

## Scope and limitations

- **One file per snapshot and restore.** There is no multi-file transaction or background process.
- The confirmation hash is an *observed-state check*, **not** an access-control credential or approval. A cooperating agent must obtain normal project permission for file modifications.
- File content is not sent to stdout. Metadata and SHA-256 are emitted; keep the private backing store protected.
- Restoration preserves the existing file mode and uses an atomic `os.replace` in the same directory. An ordinary concurrent writer could still race after the final check; there is no cross-process OS lock covering unrelated editors.
- Snapshots have a seven-day TTL. The existing `checkpoints` command may explicitly prune expired entries. A forced crash or disk failure cannot be promised safe.
- The installed CLI imports trusted plugin modules while discovering commands; it is **not** a safe environment for untrusted Python.
- This feature does not prove that the restored instructions are correct or that an agent adopted them. Check content and agent behavior independently.

For Django/isolated layouts replace `python manage.py` with `python tools/agent-cli-starter/manage.py`, using the exact `entrypoint` from the installer.
