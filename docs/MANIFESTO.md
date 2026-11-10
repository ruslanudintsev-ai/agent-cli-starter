# Agent Engineering Manifesto

> A coding agent should build and reuse reliable tools, not repeatedly improvise throwaway automation.

## The problems

**Context sprawl.** Raw HTML, lengthy logs and database dumps can crowd out the original task. A helpful CLI produces concise, bounded, machine-readable summaries and offers explicit filters when detail is needed.

**The disposable-script trap.** A sequence of `temp.py`, `script_v2.py` and `fix_final.py` files creates untested, hard-to-maintain logic. Recurring operations deserve named, tested commands with stable parameters and contracts.

**Repeated environment mistakes.** Many agents start new sessions without the previous session's operating knowledge. Reproducible lessons in versioned documentation can reduce repeat failures when agents actually read and follow them.

## Four engineering principles

1. **Protect attention.** Use output budgeting (50 items, 5,000 characters per string, plus an overall response limit) and return honest truncation notices. Protect secrets separately: short output is not automatically safe output.
2. **Make useful operations durable.** Prefer a `BaseCommand` module, argparse parameters and unit tests over a disposable root-level script. Not every one-off action needs a new module; use established project tooling when appropriate.
3. **Maintain verified operational memory.** A `gotchas.md` entry should describe the symptom, confirmed cause, reproducible fix and validation. Do not preserve guesses, credentials or personal/project-private infrastructure in public docs.
4. **Evolve deliberately.** `dev-scaffold` creates a skeleton; `dev-validate` checks a limited set of AST constraints; tests establish behavior; `system-docgen` updates the CLI reference. The agent must inspect, implement and verify the change.

## The operating loop

```text
Human task
  -> read project instructions, skill and verified gotchas
  -> project-scan (read-only discovery when new to the project)
  -> existing reusable CLI command (bounded JSON)
  -> evidence-based results and tests
  -> post-task audit
       -> verified failure? update safe gotchas
       -> reusable missing tool? scaffold, implement, validate, test
       -> command interface changed? regenerate SKILL.md
```

## Autonomy with boundaries

Autonomy is not carte blanche. The agent should preserve user authority, existing project rules, data confidentiality and rollback options. No uncontrolled process killing, secret dumping, production mutations, remote-code execution or unreviewed destructive cleanup. Safe Discovery isolates import failures; it is **not** a malicious-code sandbox.

## Outcome

The objective is lower operational friction and more repeatable project work, not a promised token-saving percentage, execution speed or error-free model memory. An agent is only as dependable as the commands it executes and the evidence it checks.
