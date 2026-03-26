---
name: tooling-justfile-pixi-ecosystem-wrapping
description: "Add justfile wrapping pixi tasks for ecosystem convention alignment. Use when: (1) a project uses pixi.toml but lacks a justfile, (2) Python library repo needs consistent CLI, (3) cross-repo task invocation needs just <project>-<task> convention, (4) adding BATS tests to verify justfile-pixi sync, (5) docs reference individual pixi run commands instead of just recipes."
category: tooling
date: 2026-03-25
version: "3.0.0"
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
| **Outcome** | Successful — verified on both CI-heavy (Scylla, 12 recipes) and library (Hephaestus, 9 recipes) repos |
| **Verification** | verified-local |
| **History** | [changelog](./tooling-justfile-pixi-ecosystem-wrapping.history) |

## When to Use

- A project has `pixi.toml` tasks but no `justfile`
- A Python library repo needs a consistent developer CLI (test, lint, format, typecheck, audit)
- Cross-repo orchestrators (e.g., Odysseus) need to invoke tasks via `just <project>-<task>`
- You need to verify justfile recipes stay in sync with pixi tasks
- Adding `just` as a conda-forge dev dependency in pixi.toml
- README.md and CLAUDE.md document individual `pixi run` commands instead of `just` recipes (DRY violation)

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
   - Use `*ARGS` forwarding for recipes where users commonly pass extra flags (test)
   - Use configurable variables at top of file (`src_dirs`, `test_dir`) to avoid path duplication
   - Include a `bootstrap` recipe for one-command setup and a `check` composite recipe for full CI

3. **Choose the right template** based on project type:

### Template A: Python Library Repo (e.g., Hephaestus)

```just
# ProjectName justfile
# One-command developer experience for the HomericIntelligence ecosystem

# Configurable paths
src_dirs := "<package> scripts tests"
test_dir := "tests/unit"

# List available recipes
default:
    @just --list

# === Setup ===

# Install dependencies and configure pre-commit hooks
bootstrap:
    pixi install
    pixi run pre-commit install

# === Test ===

# Run unit tests (pass extra args: just test -v, just test -k test_slugify)
test *ARGS:
    pixi run pytest {{ test_dir }} {{ ARGS }}

# === Code Quality ===

# Check code with ruff linter
lint:
    pixi run ruff check {{ src_dirs }}

# Format code with ruff formatter
format:
    pixi run ruff format {{ src_dirs }}

# Run mypy type checking
typecheck:
    pixi run mypy <package>/

# Run pre-commit hooks on all files
pre-commit:
    pixi run pre-commit run --all-files

# === Security ===

# Run pip-audit dependency audit
audit:
    pixi run --environment lint pip-audit

# === CI ===

# Run lint, typecheck, and tests (full CI check)
check:
    just lint
    just typecheck
    just test
```

Key decisions for library repos:
- **Configurable variables at top** (`src_dirs`, `test_dir`) avoid path duplication across recipes
- `bootstrap` combines `pixi install` + `pixi run pre-commit install` for one-command setup
- `test *ARGS` forwards to pytest with a default test directory (e.g., `just test -v`, `just test -k test_slugify`)
- `lint` and `format` use the `src_dirs` variable for consistent path targeting
- `typecheck` calls `pixi run mypy` directly since there's typically no pixi task for it
- `check` is a composite recipe that runs lint + typecheck + test for a single "is everything green?" command
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

5. **Update documentation** to reference `just` recipes instead of individual `pixi run` commands:
   - **README.md**: Replace "Getting Started with Pixi" with "Getting Started", use `just bootstrap`/`just test`/`just lint`/`just format` as primary commands, add a fallback note for `pixi run`
   - **CLAUDE.md**: Update Environment Setup, Common Commands, Testing Strategy, Pre-commit Hooks, and Troubleshooting sections to use `just` recipes
   - Add `justfile` to the directory structure listing in both files

6. **Verify** — run `just --list` to confirm no parse errors and all recipes show descriptions.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A — clean implementation (Scylla) | Direct pixi run delegation | Did not fail | Following the ecosystem convention from prior skills avoided all known pitfalls |
| N/A — clean implementation (Hephaestus v1) | Direct pixi run delegation with `*ARGS` | Did not fail | Pattern is now well-established; `*ARGS` forwarding works cleanly for test and lint |
| bootstrap in git worktree | `pixi run pre-commit install` in a worktree with `core.hooksPath` set | pre-commit refuses to install when `core.hooksPath` is set | `just bootstrap` works in normal clones; in worktrees with custom hook paths, pre-commit install may fail — this is a git config issue, not a justfile issue |

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
| `bootstrap` | `pixi install` + `pixi run pre-commit install` | One-command setup |
| `test *ARGS` | `pixi run pytest {{ test_dir }} {{ ARGS }}` | Forwards args to pytest |
| `lint` | `pixi run ruff check {{ src_dirs }}` | Uses configurable variable |
| `format` | `pixi run ruff format {{ src_dirs }}` | Uses configurable variable |
| `typecheck` | `pixi run mypy hephaestus/` | No pixi task; calls mypy directly |
| `audit` | `pixi run --environment lint pip-audit` | pip-audit in lint env |
| `pre-commit` | `pixi run pre-commit run --all-files` | All hooks |
| `check` | `just lint && just typecheck && just test` | Composite CI recipe |

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
| ProjectHephaestus | Issue #48 — bootstrap, check, variables, docs update | PR #77 |
| ProjectHephaestus | Issue #49 — combined justfile + src-layout atomic migration | PR #83 |
