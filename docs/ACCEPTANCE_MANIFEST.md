# Pinned acceptance manifest example

This is a generic, **illustrative** contract for a CLI command named `audit-demo`, not a built-in auditor. Save JSON below as an independently reviewed file; keep the reference hash and fixtures under reviewer control.

```json
{
  "schema_version": 1,
  "task_id": "audit_demo",
  "criteria_version": "v1",
  "command": "audit-demo",
  "source": "core/commands/audit_demo.py",
  "fixtures": {
    "healthy": {"path": "fixtures/healthy.json", "sha256": "<64 hex of fixture bytes>"},
    "broken": {"path": "fixtures/broken.json", "sha256": "<64 hex of fixture bytes>"}
  },
  "cases": [
    {
      "id": "healthy",
      "kind": "positive",
      "argv": ["audit-demo", "--fixture", "fixtures/healthy.json"],
      "expected_exit": 0,
      "expected_result": {"status": "ok", "finding_count": 0}
    },
    {
      "id": "broken",
      "kind": "negative",
      "argv": ["audit-demo", "--fixture", "fixtures/broken.json"],
      "expected_exit": 1,
      "expected_result": {"status": "error", "error_code": "DEFECT_DETECTED", "finding_count": 1}
    }
  ]
}
```

Values are exact. The CLI will execute `python <entrypoint> <argv...> --json` in the project root. If a defect is ignored or test data changed, verification fails. The CLI does not execute bare manifest shell commands.

Run after an external reviewer has frozen the manifest and its hash:

```bash
python manage.py verify-acceptance --manifest /reviewed/acceptance.json --sha256 <reviewer-trusted-64-hex> --execute --json
```

In a target project where the starter picked `agent_cli.py`, use that entrypoint instead. Do not run untrusted project plugins or tests on a privileged machine.

The `VERIFIED` state says only that the named, frozen cases matched the outputs at that point. The verifier and acceptance contract remain vulnerable to someone who controls the implementation **and** can replace the reviewed manifest/digest. There is no cryptographic signature, capability isolation or sandbox in this version.
