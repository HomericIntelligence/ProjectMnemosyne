---
name: tooling-justfile-pixi-ecosystem-wrapping
description: "Add justfile wrapping pixi tasks for ecosystem convention alignment. Use when: (1) a project uses pixi.toml but lacks a justfile, (2) Python library repo needs consistent CLI, (3) cross-repo task invocation needs just <project>-<task> convention, (4) adding BATS tests to verify justfile-pixi sync."
category: tooling
date: 2026-03-25
version: "2.0.0"
user-invocable: false
verification: verified-local
history: tooling-justfile-pixi-ecosystem-wrapping.history
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
| **Objective** | Add a justfile to a pixi-managed project so that cross-repo orchestration and developer CLI is consistent via the HomericIntelligence ecosystem convention |
| **Outcome** | Successful — verified on both CI-heavy (Scylla, 12 recipes) and library (Hephaestus, 7 recipes) repos |
| **Verification** | verified-local |
| **History** | [changelog](./tooling-justfile-pixi-ecosystem-wrapping.history) |

## When to Use

- A project has `pixi.toml` tasks but no `justfile`
- A Python library repo needs a consistent developer CLI (test, lint, format, typecheck, audit)
- Cross-repo orchestrators (e.g., Odysseus) need to invoke tasks via `just <project>-<task>`
- You need to verify justfile recipes stay in sync with pixi tasks
- Adding `just` as a conda-forge dev dependency in pixi.toml

## Verified Workflow

### Quick Reference

```bash
# 1. (Optional) Add just as dev dependency in pixi.toml
# [feature.dev.dependencies]
# just = ">=1.25.0,<2"

# 2. Create justfile (see templates below)

# 3. Verify
just --list

# 4. (Optional) Run BATS sync test if available
pixi run test-shell
```

### Detailed Steps

1. **Decide if `just` needs to be a pixi dependency.** If `just` is already installed system-wide or via another mechanism, skip adding it to pixi.toml. For repos where `just` is the only way to discover it, add it under `[feature.dev.dependencies]`.

2. **Create `justfile`** at project root with these conventions:
   - `default` recipe: `@just --list` (ecosystem standard)
   - Each recipe delegates to `pixi run <task>` (single source of truth stays in pixi.toml)
   - Add a comment above each recipe describing what it does
   - **Never use heredocs** in justfile recipes (known `just` pitfall — use `printf` instead)
   - For tasks without a pixi equivalent (e.g., `typecheck`), call the tool directly via `pixi run mypy ...`
   - Use `*ARGS` forwarding for recipes where users commonly pass extra flags (test, lint)

3. **Choose the right template** based on project type:

### Template A: Python Library Repo (e.g., Hephaestus)

```just
# ProjectName task runner
# Convention: justfile delegates to pixi tasks

default:
    @just --list

# === Test ===

# Run tests (accepts optional args, e.g. `just test tests/unit/`)
test *ARGS:
    pixi run pytest {{ ARGS }}

# === Code Quality ===

# Run linter
lint *ARGS:
    pixi run lint {{ ARGS }}

# Run formatter
format:
    pixi run format

# Run type checker
typecheck:
    pixi run mypy <package>/

# === Security ===

# Run dependency audit
audit:
    pixi run audit

# === Checks ===

# Run pre-commit hooks on all files
pre-commit:
    pixi run pre-commit run --all-files
```

Key decisions for library repos:
- `test *ARGS` forwards to pytest (e.g., `just test tests/unit/ -v`)
- `lint *ARGS` forwards to ruff check (e.g., `just lint --fix`)
- `format` has no args — ruff format targets are fixed in pixi.toml
- `typecheck` calls `pixi run mypy` directly since there's typically no pixi task for it
- No CI recipes needed — CI runs pixi tasks directly

### Template B: CI-Heavy Repo (e.g., Scylla)

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

# Run CI build
ci-build:
    pixi run ci-build

# Run CI lint
ci-lint:
    pixi run ci-lint

# Run CI tests
ci-test:
    pixi run ci-test

# Run full CI suite
ci-all:
    pixi run ci-all

# Run dependency audit
audit:
    pixi run audit

# Run BATS shell tests
test-shell:
    pixi run test-shell
```

4. **(Optional) Create BATS sync test** at `tests/shell/justfile/test_justfile.bats`:
   - Verify `justfile` exists at project root
   - Verify `just --list` succeeds
   - Verify expected recipes are present
   - Regression guard: no heredocs in justfile (`grep -cE '<<\s*[A-Z_]'`)
   - **Sync test**: parse `[tasks]` from `pixi.toml` and verify each has a matching just recipe

5. **Verify** — run `just --list` to confirm no parse errors and all recipes show descriptions.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A — clean implementation (Scylla) | Direct pixi run delegation | Did not fail | Following the ecosystem convention from prior skills avoided all known pitfalls |
| N/A — clean implementation (Hephaestus) | Direct pixi run delegation with `*ARGS` | Did not fail | Pattern is now well-established; `*ARGS` forwarding works cleanly for test and lint |

## Results & Parameters

### Pixi.toml Addition (optional)

```toml
[feature.dev.dependencies]
just = ">=1.25.0,<2"
```

### Recipe-to-Pixi Mapping (Library Repo — Hephaestus)

| Recipe | Delegates To | Notes |
|--------|-------------|-------|
| `default` | `@just --list` | Ecosystem standard |
| `test *ARGS` | `pixi run pytest {{ ARGS }}` | Forwards args to pytest |
| `lint *ARGS` | `pixi run lint {{ ARGS }}` | Forwards args to ruff check |
| `format` | `pixi run format` | ruff format |
| `typecheck` | `pixi run mypy hephaestus/` | No pixi task; calls mypy directly |
| `audit` | `pixi run audit` | pip-audit scan |
| `pre-commit` | `pixi run pre-commit run --all-files` | All hooks |

### Recipe-to-Pixi Mapping (CI-Heavy Repo — Scylla)

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

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1506 — ecosystem convention alignment | PR #1550 |
| ProjectHephaestus | Issue #35 — add justfile for ecosystem convention | PR #72 |
