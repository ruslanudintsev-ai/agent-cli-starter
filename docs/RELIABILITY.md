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

### Not yet shipped

A fully independent verification harness, durable pre-approved acceptance manifests, signed/locked or separate-runner oracles, versioned evidence references and reproducible false-success benchmark suites are **future work**. Do not advertise those as existing.

## Reporting, privacy, memory

Report which criterion each sanitized observation supports. For example, a reproducible test name plus pass/fail and a CI reference is better than dumping raw stdout. Avoid publishing project hostnames, credentials, profile state, account details, full paths or personal debugging notes. Record validated lessons in project-local gotchas/recipes, not in generated `SKILL.md`; mark hypotheses and stale advice explicitly. A hash proves the artifact revision only, not the feature's behavior.

The universal starter offers the control plane. Domain-specific oracles and negative fixtures belong to the destination project.
