---
name: ci-cd-justfile-build-validation-gaps
description: "Fix justfile build recipes that silently skip library validation. Use when: (1) just build excludes important directories, (2) CI build recipes are empty/no-ops, (3) mojo build vs mojo package confusion."
category: ci-cd
date: "2026-03-25"
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - justfile
  - mojo
  - build-validation
  - ci
  - mojo-package
---

# Justfile Build Validation Gaps

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Fix justfile build recipes that exclude shared/ library from compilation, leaving CI with no compile-time validation of the core ML framework |
| **Outcome** | Successful — ci-build recipe filled in, check recipe added, CI workflows consolidated |
| **Verification** | verified-precommit |

## When to Use

- A `just build` recipe uses `find -not -path` to exclude important source directories
- A CI build recipe exists but has zero commands (silent no-op)
- You need to validate Mojo library code but `mojo build` requires `fn main()` entry points
- Build and package steps are duplicated across justfile recipes and CI workflow YAML files
- Developers have no fast command to type-check library code without running tests

## Verified Workflow

> **Note:** Pre-commit hooks pass. CI validation pending on PR merge.

### Quick Reference

```bash
# Type-check shared library (no artifacts produced)
NATIVE=1 just check

# Full CI build validation (entry points + library packaging)
NATIVE=1 just ci-build

# Full validation including tests
NATIVE=1 just validate
```

### Detailed Steps

1. **Identify the gap**: `_build-inner` uses `find -not -path "./shared/*"` because `mojo build` requires `fn main()`. Library modules have no main — they must be validated with `mojo package` instead.

2. **Fill empty `ci-build` recipe** to run both entry-point compilation and library packaging:
   ```just
   ci-build:
       @echo "Running CI build validation..."
       @just build ci
       @just package ci
       @echo "✅ CI build validation complete"
   ```

3. **Add `just check` recipe** for fast developer feedback on library code:
   ```just
   check:
       @just _run "just _check-inner"

   [private]
   _check-inner:
       #!/usr/bin/env bash
       set -euo pipefail
       REPO_ROOT="$(pwd)"
       OUT=$(mktemp -d)
       trap "rm -rf $OUT" EXIT
       pixi run mojo package --Werror -I "$REPO_ROOT" shared -o "$OUT/shared.mojopkg"
   ```
   Key: uses `mktemp -d` + trap to compile without leaving artifacts.

4. **Update `validate` recipe** to delegate to `ci-build` instead of calling `build` and `package` separately — single source of truth.

5. **Consolidate CI workflows** to use `NATIVE=1 just ci-build` instead of inline `mojo package` commands. This eliminates duplication between `build-validation.yml` and `comprehensive-tests.yml`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Include shared/ in `_build-inner` find | Adding shared/ .mojo files to the `mojo build` loop | `mojo build` requires `fn main()` — library modules don't have one, so compilation fails | Library code must be validated with `mojo package`, not `mojo build` |
| Add `mojo build --check` flag | Use a hypothetical check-only mode | Flag doesn't exist in Mojo 0.26.1 | Must use `mojo package` to temp dir as a workaround for type-checking |
| Keep separate build+package in validate | Calling `just build` then `just package` independently | Duplication — same logic in validate, ci-build, and CI YAML files | Consolidate into `ci-build` and have everything delegate to it |

## Results & Parameters

### justfile changes

```just
# ci-build: validates entry points AND shared library
ci-build:
    @just build ci
    @just package ci

# check: fast library type-check (no artifacts)
check:
    @just _run "just _check-inner"

# validate: delegates to ci-build (single source of truth)
validate:
    @just ci-build
    @just test-mojo
```

### CI workflow pattern

```yaml
# Replace inline mojo package commands with:
- name: Build and validate
  run: NATIVE=1 just ci-build
```

### Key insight: mojo build vs mojo package

| Command | Input | Requires main()? | Output |
|---------|-------|-------------------|--------|
| `mojo build` | Single .mojo file | Yes | Binary executable |
| `mojo package` | Directory (package) | No | .mojopkg library |

Use `mojo package` for library validation, `mojo build` only for entry points.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5121, Issue #4914 | Fixed empty ci-build, added check recipe, consolidated CI workflows |
