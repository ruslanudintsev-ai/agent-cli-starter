# Procedural memory without private-data leakage

The CLI starter helps autonomous coding assistants keep **verified reusable engineering lessons** between sessions. It does not change model weights, provide hidden persistent reasoning, or guarantee any particular assistant loads the files automatically.

## Separate knowledge surfaces

- `.agents/skills/cli-tools/SKILL.md` is a generated *interface reference*: which CLI commands exist and how their `argparse` options work. Regenerate it with `system-docgen` after code changes. Do not manually append incidents here; generation replaces it.
- `.agents/skills/cli-tools/gotchas.md` holds *project-local operational evidence*: reproductions, validated workarounds, relevant environment constraints and dates. The assistant must review its relevance before using an old note.
- `.agents/skills/cli-tools/recipes.md` is a *manually maintained*, tested project workflow collection. Docgen never overwrites it.
- `.agents/backlog/cli-features.md` is a collection of **proposals** for missing commands, not installed features.
- `.agents/skills/self-improvement/SKILL.md` guides verification and proper classification of reusable knowledge; it is not a background autonomous agent.

## Evidence-first learning loop

1. **Observe.** Capture the smallest useful evidence from a command, test or environment observation. Prefer a bounded JSON result over pasting raw terminal output.
2. **Explain.** Distinguish confirmed root causes from hypotheses. An issue that has not been reproduced is an open question.
3. **Fix safely.** Prefer a reversible change or reviewable CLI command with explicit parameters; destructive remediation requires ordinary project approval.
4. **Verify.** Run a focused test and note the observable result. Without verification, do not label an intervention successful.
5. **Record.** Add a sanitized, scoped gotcha with date, symptom, root cause (or unknown), recovery, validation and limits.
6. **Reuse judiciously.** At the next task, check whether the OS, dependency versions and circumstances still match. Amend stale knowledge rather than repeating obsolete advice.

## Privacy and upstream boundary

Memory created inside a target project may expose its infrastructure, users or business logic. **Never automatically synchronize it to the public starter.** Public upstream documentation should contain only generic, independently reviewed methods or synthetic examples. Do not place tokens, `.env` contents, private file paths, logs with identifiers, internal hostnames, session data or raw project notes in public commits.

## Limitations

This is a workflow contract, not an automated incident-recovery service. The framework supplies agent instructions and a place for evidence, but cannot enforce that arbitrary models follow instructions. Do not treat a documented command recommendation as a command that is already implemented or authorized to run.

## Upgrade safety

The installer deliberately skips pre-existing project-local `gotchas.md`, `recipes.md` and `.agents/backlog/cli-features.md` even under `--force`. These files are operational knowledge, not distributable program code. Updating the template must not erase previously verified local lessons.
