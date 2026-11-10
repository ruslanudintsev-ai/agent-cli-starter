# Reliability Core: verifiable acceptance, not green-looking scaffolds

This document specifies the **minimum** common contract. It is intentionally project-agnostic and is not a claim of autonomous learning or a formal security sandbox.

## What failed in the first agent smoke test

An agent generated a new CLI command; its generic smoke test, AST lint and JSON status check passed. Yet the generated command did not implement the requested domain behavior. A passing smoke test proves only that the shell, dispatcher and template work; it does not prove the feature works. This is **false success**.

## Acceptance contract (proposed interface)

Before implementing a feature, define externally observable criteria, preferably in an independently reviewed task specification:

- `task_id` and immutable `criteria_version`
- `criterion_id`, domain intent, preconditions and *oracle* (how the outcome can be checked)
- positive fixture, expected success outcome
- negative/counterexample fixture, expected detection or rejection
- verifier identifier and reference to the tested code revision
- observed outcome, evidence reference, verifier timestamp and final status

States: `SCAFFOLDED`, `IMPLEMENTED`, `VERIFIED`, `FAILED`, `BLOCKED/UNVERIFIED`. **VERIFIED requires all mandatory criteria to pass in a separate check**. Neither a 0 exit code nor a source hash proves semantic correctness. A high-risk verification environment needs explicit authorization, isolation and review.

### Shipped phase 1 (v1.4)

`dev-scaffold` creates a syntactically valid, **unimplemented** command returning a `NOT_IMPLEMENTED` error, with two failing `unittest` acceptance placeholders (positive and negative behavior). It labels its own output `SCAFFOLDED / UNVERIFIED`. The `dev-validate` structural check notices the unchanged marker and reports a failure; even after removing that marker, its `behavior_verified` field remains `false` because static analysis is not an independent behavioral test.

Agents must replace the placeholders with **meaningful fixtures** and prove the real task. `.agents/rules/self-learning.md` requires Grounding Proof and honest status. The core cannot force an external agent to follow its prose or prevent it from editing tests: it is a first step to closing the false-success gap.

### Shipped phase 2: pinned positive/negative CLI acceptance runner

`verify-acceptance` reads a JSON manifest that names a trusted CLI command, its project-local module, positive and negative arguments, expected exit codes, and **at least one functional JSON assertion beyond `status` per case**. A SHA-256 pinned by the reviewer protects the exact manifest bytes; listed fixture files also have pinned SHA-256 digests. The runner uses `subprocess.run` with a bounded timeout, direct Python argv (never a shell), stripped-down environment and no raw logs in its report. It hashes the source file before/after execution to detect changed code during verification.

Only `--execute` authorizes running the trusted destination code. Without it the result is `UNVERIFIED`, with mismatched pins or invalid criteria it is `BLOCKED`, with failed behavior it is `FAILED`, and with **all explicitly described cases** satisfied it is `VERIFIED`. This status is scoped to the manifest and code revision, not a claim that all unspecified business requirements are satisfied.

**Critical boundary:** the runner is not a sandbox. Python imports project command modules and test code may have side effects. The calling agent could fabricate favorable tests or recompute a changed digest; genuine independence requires the reviewer to keep the manifest, pin and fixtures outside the implementing agent's control. The test environment must be trusted and isolated according to project risk. This is a CLI-verification adapter to the universal reliability contract, not a model-specific implementation or a general-purpose remote shell.

### Not yet shipped

A platform-enforced separation of author and verifier, signed/locked or separate-runner oracles, reproducible multi-project false-success benchmarks and semantic correctness outside the stated cases are **future work**. A SHA-256 argument provided by the same agent is NOT an independently approved oracle. Do not advertise those as existing.

## Reporting, privacy, memory

Report which criterion each sanitized observation supports. For example, a reproducible test name plus pass/fail and a CI reference is better than dumping raw stdout. Avoid publishing project hostnames, credentials, profile state, account details, full paths or personal debugging notes. Record validated lessons in project-local gotchas/recipes, not in generated `SKILL.md`; mark hypotheses and stale advice explicitly. A hash proves the artifact revision only, not the feature's behavior.

The universal starter offers the control plane. Domain-specific oracles and negative fixtures belong to the destination project.
