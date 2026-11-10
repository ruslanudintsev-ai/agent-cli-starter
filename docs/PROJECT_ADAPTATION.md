# Project adaptation loop

This document describes the public, portable workflow behind the `project-scan` command and first-use onboarding rule. No private repository metadata or environment-specific settings are required.

## 1. Discover, don't guess

Run `python manage.py project-scan --json` (or `python agent_cli.py ...` when a project already owns `manage.py`). The scanner examines **only** common, top-level marker files and limited manifest text. It does not import project code, invoke package managers, enumerate environment variables, read `.env` files, connect to services or traverse private directories.

A sample result might contain `detected_stack: ["django", "python", "node"]`, `evidence: ["package.json", "pyproject.toml"]`, and `recommended_commands: ["django-check", "frontend-build", "python-test", "routes-list"]`.

Recommendations are speculative **names of possible future commands** and do not imply an implementation. `recommendations_installed` is `false`.

## 2. Adapt to a real task

Choose at most one or two recurring capabilities justified by the current task. Scaffold with `dev-scaffold`, implement using existing project APIs, and add automated tests. Before the first side effect, review inputs, scopes, dry-run behavior and recovery options. Preserve existing commands and naming conventions.

Use `dev-validate` as a focused static check, not as a security gate; it cannot establish correctness or safety. Run appropriate integration tests and record actual outcomes.

## 3. Learn from evidence

After a task, check acceptance criteria. For a repeated failure, identify the confirmed root cause and fix it at the appropriate level. Write a minimal and privacy-safe gotcha if it will help future sessions. Do not automatically create a generic "cleanup" command or kill processes just because a test failed.

If CLI arguments changed, regenerate `.agents/skills/cli-tools/SKILL.md`. The generated reference documents *registered* commands; user-suggested commands are not documented as implemented until they actually exist.

## 4. Privacy and scope

Public starter-kit documentation contains no personal notes, project-specific URLs, internal hostnames, credentials, proxy configuration, private paths or environment dumps. Keep operational details in the private destination project and never copy them into this public upstream repository.

The starter is opt-in and may be combined with repository-specific project instructions. It does not automatically adapt project code, run tests, or enforce the instructions on a third-party agent.
