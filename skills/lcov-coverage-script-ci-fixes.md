---
name: lcov-coverage-script-ci-fixes
description: "Fix generate_coverage.sh scripts failing in CI with lcov/geninfo. Use when: (1) coverage script fails with wrong paths after BUILD_DIR is a relative path, (2) cmake source dir is wrong after cd into build dir, (3) lcov fails with gcov version mismatch error on Ubuntu 24.04 with Clang, (4) geninfo fails with 'unable to create link .gcda' when multiple test targets share source files."
category: ci-cd
date: 2026-04-24
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - lcov
  - gcov
  - geninfo
  - coverage
  - ci-cd
  - clang
  - ubuntu
  - bash
  - generate_coverage
---

# lcov Coverage Script CI Fixes (4 Sequential Bugs)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-24 |
| **Objective** | Fix `generate_coverage.sh` failing in CI with multiple sequential independent bugs, each masked until the previous was fixed |
| **Outcome** | Success — all 4 bugs fixed; coverage script ran to completion on ProjectKeystone PR #340 |
| **Verification** | verified-ci |
| **History** | N/A (initial version) |

## When to Use

- `generate_coverage.sh` (or similar lcov coverage script) fails in CI but not always locally
- CI passes `BUILD_DIR` as a relative path (e.g., `build/x86.coverage.debug`)
- Script does `cd "$BUILD_DIR"` then uses paths derived from `$BUILD_DIR`
- lcov produces version mismatch errors: `"ERROR: GCOV version mismatch"` or similar
- geninfo errors: `"unable to create link <file>.gcda: No such file or directory"`
- Running on Ubuntu 24.04 with Clang 18 (`--coverage` instrumentation) + lcov 2.0
- Multiple test targets compile the same source file (e.g., shared utility sources across unit test suites)

## Verified Workflow

### Quick Reference

```bash
# Bug 1: Canonicalize BUILD_DIR to absolute path early
_raw_build="${BUILD_DIR:-$PROJECT_ROOT/build/coverage}"
if [[ "$_raw_build" = /* ]]; then
  BUILD_DIR="$_raw_build"
else
  BUILD_DIR="$PROJECT_ROOT/$_raw_build"
fi
unset _raw_build

# Bug 2: Use PROJECT_ROOT explicitly for cmake source directory
cmake -DENABLE_COVERAGE=ON -DCMAKE_BUILD_TYPE=Debug ... "$PROJECT_ROOT"
# NOT:  cmake ... ..   (broken after cd "$BUILD_DIR")

# Bugs 3+4: Extended --ignore-errors for lcov capture
lcov --capture \
  --directory . \
  --output-file "$COVERAGE_INFO" \
  --ignore-errors negative,mismatch,version,gcov
```

### Detailed Steps

#### Bug 1 — Relative BUILD_DIR Breaks All Paths After `cd`

**Symptom**: Script does `cd "$BUILD_DIR"` then references `$COVERAGE_DIR` (which is set as `$BUILD_DIR/reports/coverage`). If `BUILD_DIR=build/x86.coverage.debug` (relative), after `cd` all derived paths are wrong.

**Fix** — Canonicalize BUILD_DIR to absolute immediately after receiving it:

```bash
# At the top of the script, after PROJECT_ROOT is set:
_raw_build="${BUILD_DIR:-$PROJECT_ROOT/build/coverage}"
if [[ "$_raw_build" = /* ]]; then
  BUILD_DIR="$_raw_build"
else
  BUILD_DIR="$PROJECT_ROOT/$_raw_build"
fi
unset _raw_build

# Now safe to derive other paths
COVERAGE_DIR="$BUILD_DIR/reports/coverage"
COVERAGE_INFO="$COVERAGE_DIR/coverage.info"
```

**Why**: `cd "$BUILD_DIR"` resolves relative to whatever the current directory is at invocation time — which varies in CI. All subsequent `$COVERAGE_DIR` references then point to nonsensical paths.

#### Bug 2 — Wrong cmake Source Directory After `cd`

**Symptom**: Script does `cd "$BUILD_DIR"` then calls `cmake ... ..`. The `..` goes to the parent of `$BUILD_DIR`, not `$PROJECT_ROOT`.

Example: If `BUILD_DIR=/home/runner/work/repo/build/x86.coverage.debug`, then `..` → `/home/runner/work/repo/build/` (the build parent, not the project root).

**Fix** — Always use `"$PROJECT_ROOT"` explicitly:

```bash
cmake -DENABLE_COVERAGE=ON \
      -DCMAKE_BUILD_TYPE=Debug \
      -G Ninja \
      "$PROJECT_ROOT"    # NOT ".." — that resolves to BUILD_DIR parent
```

#### Bug 3 — gcov Version Mismatch (Clang + Ubuntu 24.04)

**Symptom**: lcov `--capture` fails with a version mismatch error. Clang's `--coverage` generates gcov data in format `4.8*`, but Ubuntu 24.04's system gcov reports version `B33*`. lcov 2.0 treats this as a fatal error.

**Fix** — Add `version` to `--ignore-errors`:

```bash
lcov --capture \
  --directory . \
  --output-file "$COVERAGE_INFO" \
  --ignore-errors negative,mismatch,version
```

**Environment**: Ubuntu 24.04, lcov 2.0-4ubuntu2, Clang 18.1.3.

#### Bug 4 — gcda Symlink Collision (Multiple Targets, Shared Sources)

**Symptom**: When multiple test targets compile the same source file (e.g., `test_nats_status.cpp` appears in both `monitoring_unit_tests` and `unit_tests`), geninfo tries to create a `.gcda` symlink that already exists from the other target:

```
geninfo: ERROR: unable to create link test_nats_status.cpp.gcda: No such file or directory!
    (use "geninfo --ignore-errors gcov ..." to bypass this error)
```

**Fix** — Add `gcov` to `--ignore-errors`:

```bash
lcov --capture \
  --directory . \
  --output-file "$COVERAGE_INFO" \
  --ignore-errors negative,mismatch,version,gcov
```

**Root cause**: geninfo uses symlinks to map `.gcda` files to source filenames. When the same source basename appears in multiple targets, the second attempt to create the symlink fails because it already exists.

### Complete Fixed lcov Capture Command

```bash
lcov --capture \
  --directory . \
  --output-file "$COVERAGE_INFO" \
  --ignore-errors negative,mismatch,version,gcov
```

All 4 bugs must be fixed together — each one masks the next in CI.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Relative BUILD_DIR | `BUILD_DIR=build/x86.coverage.debug` passed from CI; used directly without canonicalization | After `cd "$BUILD_DIR"`, all derived paths (`$COVERAGE_DIR`, `$COVERAGE_INFO`) were wrong | Always canonicalize BUILD_DIR to absolute path at script startup before any `cd` |
| Using `..` as cmake source | `cd "$BUILD_DIR" && cmake ... ..` | `..` resolves to parent of BUILD_DIR, not PROJECT_ROOT | Use `"$PROJECT_ROOT"` explicitly as cmake source directory |
| `--ignore-errors negative,mismatch` only | Added mismatch to suppress gcov format error | gcov version string `B33*` vs `4.8*` still fatal with lcov 2.0 | Add `version` to the ignore-errors list |
| `--ignore-errors negative,mismatch,version` | Fixed version mismatch, coverage ran further | Multiple test targets sharing source filenames caused gcda symlink collision in geninfo | Add `gcov` to the ignore-errors list to bypass symlink creation failures |

## Results & Parameters

**Environment verified on:**

| Component | Version |
| ----------- | --------- |
| OS | Ubuntu 24.04 |
| lcov | 2.0-4ubuntu2 |
| Clang | 18.1.3 |
| gcov format (Clang) | 4.8* |
| gcov format (system) | B33* |

**Final working lcov capture invocation:**

```bash
lcov --capture \
  --directory . \
  --output-file "$COVERAGE_INFO" \
  --ignore-errors negative,mismatch,version,gcov
```

**Diagnostic order** — fix bugs in this sequence since each masks the next:
1. Check BUILD_DIR canonicalization (absolute vs relative)
2. Check cmake source argument (`"$PROJECT_ROOT"` not `..`)
3. Check for gcov version mismatch in lcov stderr
4. Check for geninfo symlink collision in lcov stderr

**Project ROOT detection** (standard pattern):

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectKeystone | PR #340 Code Coverage CI — verified-ci 2026-04-24 | All 4 bugs fixed sequentially; coverage script ran to completion |
