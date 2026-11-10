# Engineering roadmap

This public roadmap separates existing behavior from prospective improvements.

## Available now

- Cross-platform zero-dependency installer with `manage.py` conflict handling.
- Safe command discovery (exception isolation, not untrusted-code sandboxing).
- Bounded JSON output and optional memory telemetry.
- CLI scaffolding, AST checks, documentation generation and integration tests.
- Read-only shallow project stack discovery and human-guided onboarding.
- Versionable procedural notes, with a privacy-first Post-Task Audit.

## Candidates, not shipped features

- A project-local, opt-in command catalog with reviewed, stack-specific implementations.
- Atomic state writes (`os.replace`) and locking where multi-writer coordination is needed.
- Structured checkpoint expiry and safe recovery contracts for long-running tasks.
- More stringent source-inspection checks and opt-in policy validation.
- Packaging/release pinning and integrity verification for downloaded installer assets.
- Cross-platform integration tests for unusual encodings, filesystem permissions and paths.

**Scope:** No browser-session management, proxy rotation, broad process termination, filesystem deletion, or production repair is part of the universal starter. Those require a separate, explicitly authorized project-specific implementation.
