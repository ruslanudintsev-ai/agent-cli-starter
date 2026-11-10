# Universal design: capabilities, boundaries and deliberate omissions

Agent CLI Starter can be installed in repositories using different languages and stacks because its **control plane** uses Python's standard library. It does not replace their build systems or automatically grant the agent knowledge of arbitrary project APIs. Extend it only with project-appropriate, tested commands.

| General pattern | Implementation | Boundary |
| --- | --- | --- |
| Command-first agent workflow | Rules, `AGENTS.md`, `CLAUDE.md`, Cursor rule, Aider conventions | Instructions do not guarantee agent compliance |
| Reusable tools | `BaseCommand`, safe error-isolated discovery, scaffold, AST validation | Imported Python remains fully privileged; review plugins |
| Context budgeting | Bounded JSON results, telemetry | Not a security or PII scrubber |
| Live tool reference | `system-docgen` creates `cli-tools/SKILL.md` | Never place hand-maintained lessons in generated reference |
| Procedural memory | Verified `gotchas.md`, manual `recipes.md`, self-improvement skill, feature backlog | Project-local and not automatically published upstream |
| Project adaptation | Read-only shallow `project-scan` | Proposed commands are not implemented or authorized |
| Checkpoints | Atomic and size-bounded local JSON, TTL and explicit expiry cleanup | Resume only after domain-specific validation; no auto-recovery |
| Runtime checks | Opt-in, warning-only `post_execution_assertions` hook | No universal browser, network, port, proxy or disk policy |
| Safe installation | Preview, pinning, rollback of installer-owned writes | Not a security sandbox and not crash-proof across power loss |

## Not universal / intentionally omitted

- Browser profile cleanup, proxy rotation, SERP collection, session hijacking, force-killing processes, arbitrary config mutation or production deployment must be separately designed, authorized and tested for the target project.
- Arbitrary `eval`/`exec` is **not** a sandbox. Capturing Python stdout or filtering built-ins cannot prevent filesystem or network side effects. It is not shipped in the general-purpose starter.
- Automatic quarantine that *moves or deletes* plugin source after an import error would modify user data. Existing discovery only skips a failed import and emits a bounded diagnostic.
- A TTL cache for live network/system-status checks risks stale decisions; no global semantic cache is enabled. A future opt-in cache must distinguish pure, deterministic data from volatile data.
- General rollback of application configuration cannot be correct without a project-specific transaction model. The installer rolls back only the files it changes; it does not offer arbitrary app-level rollback.

## Recommended improvement sequence

1. First run `project-scan` and read local instructions.
2. Reuse the existing CLI and its generated `SKILL.md`.
3. Make a tested new command only when a task demonstrates a repeatable need.
4. Store evidence-based project-specific findings in `gotchas.md` and tested multi-step workflows in `recipes.md`.
5. Use `CheckpointStore` for lengthy workflows only after designing safe resume checks for that workflow.
6. For serious failure detection, implement read-only assertions **inside the relevant project plugin**, return warnings, and require normal authorization for remediation.

Nothing in the universal starter copies personal documents, process lists or private infrastructure details to public repositories.
