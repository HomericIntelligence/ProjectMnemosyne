---
name: pixi-audit-task-alias
description: "TRIGGER CONDITIONS: When a project has pip-audit in a non-default pixi environment (e.g., lint) and developers want to run CVE scanning without specifying --environment flags. Use when adding developer convenience wrappers for environment-gated tools."
user-invocable: false
category: tooling
date: 2026-02-22
---

# pixi-audit-task-alias

Add a `pixi run audit` task alias that delegates to `pip-audit` in the `lint` environment, making CVE scanning available to developers without needing the `--environment lint` flag.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-22 |
| Objective | Allow `pixi run audit` from default dev environment without `--environment lint` |
| Outcome | Success — single-line change to `pixi.toml` [tasks] section |

## When to Use

- A project uses pixi with feature environments (e.g., `lint`, `ci`) and `pip-audit` is in a non-default environment
- Developers want to run security scanning via a simple alias without remembering environment flags
- Issue/PR requests exposing a tool from a secondary environment as a top-level task
- YAGNI/KISS applies: avoid bloating the default environment with security tooling when the lint environment already has it

## Verified Workflow

### 1. Confirm pip-audit is declared in the lint feature environment

```toml
# pixi.toml — verify this exists before adding alias
[feature.lint.pypi-dependencies]
pip-audit = ">=2.7"
```

### 2. Add the audit task alias to [tasks]

Add exactly one line to the top-level `[tasks]` section:

```toml
[tasks]
audit = "pixi run --environment lint pip-audit"
```

This invocation works from any environment (default `dev`, `lint`, etc.) because pixi evaluates the task command in a shell — the inner `pixi run --environment lint` spawns a subshell in the `lint` environment.

### 3. Verify the alias appears in task list

```bash
pixi task list
# Should include: audit
```

### 4. Verify lint environment installs cleanly

```bash
pixi install --environment lint
# Should succeed with pip-audit resolved
```

### 5. Run existing tests to confirm no regressions

```bash
pixi run python -m pytest tests/ -v
# All tests should pass
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Adding `pip-audit` to `[pypi-dependencies]` (default env) | Bloats the default dev environment with a security tool not needed at runtime or for tests; YAGNI violation | Use the `lint` environment task alias instead |
| Using `[feature.lint.tasks]` section for the alias | Would require `pixi run --environment lint audit` — same verbosity as the original problem | Top-level `[tasks]` alias gives maximum developer convenience |
| Nested pixi invocation concerns | Initial concern that `pixi run` inside a pixi task could cause recursion/issues | Pixi evaluates task commands in a shell; inner `pixi run --environment lint` works correctly |

## Results & Parameters

```toml
# pixi.toml — minimal change (1 line added to [tasks])
[tasks]
audit = "pixi run --environment lint pip-audit"

# pip-audit stays only in lint feature:
[feature.lint.pypi-dependencies]
pip-audit = ">=2.7"
```

**Developer usage:**
```bash
pixi run audit          # Run from any environment
pixi run audit --fix    # Pass pip-audit flags through
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #872, PR #976 | [notes.md](references/notes.md) |

## References

- Related skills: `enable-yaml-markdown-linting`, `pre-commit-maintenance`
- pixi documentation: https://prefix.dev/docs/pixi/reference/pixi_manifest#tasks
