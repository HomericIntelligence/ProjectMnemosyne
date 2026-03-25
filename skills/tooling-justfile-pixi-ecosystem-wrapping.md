---
name: tooling-justfile-pixi-ecosystem-wrapping
description: "Add justfile wrapping pixi tasks for ecosystem convention alignment. Use when: (1) a project uses pixi.toml but lacks a justfile, (2) cross-repo task invocation needs just scylla-* convention, (3) adding BATS tests to verify justfile-pixi sync."
category: tooling
date: 2026-03-25
version: "1.0.0"
user-invocable: false
tags:
  - justfile
  - pixi
  - ecosystem
  - bats
  - convention
---

# Justfile-Pixi Ecosystem Task Wrapping

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Add a justfile to a pixi-managed project so that cross-repo orchestration (e.g., Odysseus invoking `just scylla-*`) works via the HomericIntelligence ecosystem convention |
| **Outcome** | Successful — justfile created with 12 recipes, BATS sync test, all CI hooks passing |

## When to Use

- A project has `pixi.toml` tasks but no `justfile`
- Cross-repo orchestrators (e.g., Odysseus) need to invoke tasks via `just <project>-<task>`
- You need to verify justfile recipes stay in sync with pixi tasks
- Adding `just` as a conda-forge dev dependency in pixi.toml

## Verified Workflow

### Quick Reference

```bash
# 1. Add just as dev dependency in pixi.toml
# [feature.dev.dependencies]
# just = ">=1.25.0,<2"

# 2. Regenerate lock file
pixi install

# 3. Create justfile (see template below)

# 4. Verify
pixi run just --list

# 5. Run BATS sync test
pixi run test-shell
```

### Detailed Steps

1. **Add `just` to `pixi.toml`** under `[feature.dev.dependencies]` — it's a dev-only tool, not needed in CI lint or production environments.

2. **Run `pixi install`** to regenerate `pixi.lock`. Always commit the updated lock file.

3. **Create `justfile`** at project root with these conventions:
   - `default` recipe: `@just --list` (ecosystem standard)
   - Each recipe delegates to `pixi run <task>` (single source of truth stays in pixi.toml)
   - Add a comment above each recipe describing what it does
   - **Never use heredocs** in justfile recipes (known `just` pitfall — use `printf` instead)
   - For tasks without a pixi equivalent (e.g., `typecheck`), call the tool directly via `pixi run mypy ...`

4. **Justfile template**:
   ```just
   # Project task runner — delegates to pixi run
   # Ecosystem convention: justfile + pixi

   # List all available recipes
   default:
       @just --list

   # Run pytest
   test:
       pixi run test

   # Run ruff check
   lint:
       pixi run lint

   # Run ruff format
   format:
       pixi run format

   # Run mypy type checker
   typecheck:
       pixi run mypy scylla scripts tests

   # Run all pre-commit hooks
   pre-commit:
       pixi run pre-commit run --all-files
   ```

5. **Create BATS sync test** at `tests/shell/justfile/test_justfile.bats`:
   - Verify `justfile` exists at project root
   - Verify `just --list` succeeds
   - Verify expected recipes are present (test, lint, format, typecheck, etc.)
   - Regression guard: no heredocs in justfile (`grep -cE '<<\s*[A-Z_]'`)
   - **Sync test**: parse `[tasks]` from pixi.toml and verify each has a matching just recipe (skip utility-only tasks like `plan-issues`)

6. **Update project docs** (e.g., CLAUDE.md) with a Quick Start section showing justfile commands.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A — clean implementation | Direct pixi run delegation | Did not fail | Following the ecosystem convention from prior skills (flesh-out-scaffolded-repo, just-recipe-heredoc-fix) avoided all known pitfalls |

## Results & Parameters

### Pixi.toml Addition

```toml
[feature.dev.dependencies]
just = ">=1.25.0,<2"
```

### Recipe-to-Pixi Mapping

| Recipe | Delegates To | Notes |
|--------|-------------|-------|
| `default` | `@just --list` | Ecosystem standard |
| `test` | `pixi run test` | pytest |
| `test-shell` | `pixi run test-shell` | BATS tests |
| `lint` | `pixi run lint` | ruff check |
| `format` | `pixi run format` | ruff format |
| `typecheck` | `pixi run mypy scylla scripts tests` | No pixi task; calls mypy directly |
| `ci-build` | `pixi run ci-build` | Container build |
| `ci-lint` | `pixi run ci-lint` | CI lint in container |
| `ci-test` | `pixi run ci-test` | CI tests in container |
| `ci-all` | `pixi run ci-all` | Full CI suite |
| `audit` | `pixi run audit` | pip-audit scan |
| `pre-commit` | `pixi run pre-commit run --all-files` | All hooks |

### BATS Test Coverage

- 11 tests: existence, list, 7 recipe checks, no-heredoc guard, pixi sync test
- All pass in < 100ms total

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1506 — ecosystem convention alignment | PR #1550 |
