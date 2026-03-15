---
name: mojo-ci-failure-misdiagnosis
description: "Debugging Mojo CI failures misattributed to JIT crashes. Use when: CI tests fail with retry labels, all tests pass locally, or --Werror masks the real error."
category: debugging
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | CI test failures labeled as "Mojo JIT crash — ADR-009" were actually deterministic `--Werror` compile errors |
| **Root Cause** | `alias` keyword deprecated in Mojo 0.26.1; `--Werror` promotes deprecation warning to compile error |
| **Fix** | Replace `alias` with `comptime` in module-level constant declarations |
| **Impact** | Every test file transitively importing `extensor.mojo` failed to compile in CI |
| **Time to diagnose** | ~1 hour of controlled experiments before checking actual CI error output |

## When to Use

- CI tests fail and retry logic labels them as "likely Mojo JIT crash"
- Tests pass locally but fail in CI (especially when CI uses `--Werror`)
- `execution crashed` is assumed but never actually appears in CI logs
- Deprecation warnings exist in the codebase and CI uses `--Werror`

## Verified Workflow

### Quick Reference

1. **Read the actual CI error output** — don't trust retry labels
2. **Check if `--Werror` is in use** — deprecation warnings become errors
3. **Search for deprecated syntax** (`alias` → `comptime` in Mojo 0.26.1)
4. **Verify locally with `--Werror`** to reproduce the exact CI failure
5. **Fix the root cause** (syntax migration), not the symptom (retry logic)

### Step 1: Check CI Logs for Real Errors

```bash
gh run view <run-id> --log-failed 2>&1 | grep -E "error:|FAILED" | head -20
```

Look for **compile errors** (e.g., `'alias' is deprecated`) rather than `execution crashed`. The retry logic may mislabel compile errors as JIT crashes.

### Step 2: Reproduce Locally with CI Flags

```bash
# Match CI conditions exactly
pixi run mojo --Werror -I "$(pwd)" -I . tests/path/to/test.mojo
```

If this fails with a deprecation error, that's your root cause — not a JIT crash.

### Step 3: Find All Deprecated Syntax

```bash
grep -rn "^alias " --include="*.mojo" shared/ tests/
```

### Step 4: Fix and Verify

Replace deprecated syntax and confirm with `--Werror`:

```mojo
# Before (Mojo 0.26.1 deprecated)
alias MY_CONST: Int = 42

# After
comptime MY_CONST: Int = 42
```

### Step 5: Validate the Fix Isn't Environment-Specific

Run in Docker matching CI's GLIBC version to confirm:

```bash
docker exec <container> bash -c 'cd /workspace && pixi run mojo --Werror -I /workspace -I . tests/path/to/test.mojo'
```

**Important**: If Docker shares `.pixi/` via bind mount, `pixi install` inside Docker will corrupt the host env. Either use a separate volume or reinstall after.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Controlled experiment without `--Werror` | Ran heavy vs light import tests 30x locally | 0 crashes — the JIT crash hypothesis was untestable without `--Werror` | Always reproduce with exact CI flags first |
| Controlled experiment in Docker (GLIBC 2.35) | Ran same tests 30-100x in Docker matching CI env | Still 0 crashes — the crash wasn't GLIBC-dependent | Environment matching alone doesn't reproduce if the failure mode is wrong |
| ADR-009 reproduction (25 tests in one file) | Ran monolithic test file 50x locally and in Docker | 0 crashes — heap corruption also not reproducible | Historical bugs may already be fixed; verify before building workarounds |
| Searching CI logs for "execution crashed" | Searched 10+ recent CI runs | Zero instances found — the actual errors were compile failures | Read the logs before assuming the failure mode |
| Docker bind-mount pixi install | Ran `pixi install` inside Docker with shared `.pixi/` | Corrupted host Mojo installation (hardcoded paths) | Never share `.pixi/` between host and Docker; use separate volumes |

## Results & Parameters

### Environment

| Parameter | Local | Docker | CI |
|-----------|-------|--------|-----|
| GLIBC | 2.39 | 2.35 | 2.35 |
| Mojo | 0.26.1 | 0.26.1 | 0.26.1 |
| `--Werror` | No (default) | No (default) | Yes |
| Crash rate | 0% | 0% | 100% (compile error) |

### The Fix

```diff
- alias EXTENSOR_PRINT_THRESHOLD: Int = 1000
- alias EXTENSOR_PRINT_SHOW_ELEMENTS: Int = 3
+ comptime EXTENSOR_PRINT_THRESHOLD: Int = 1000
+ comptime EXTENSOR_PRINT_SHOW_ELEMENTS: Int = 3
```

**Files**: `shared/core/extensor.mojo:56-57`
**PR**: #4898

### Key Insight

The entire "JIT crash" narrative was built on a misdiagnosis. CI retry logic labeled deterministic compile errors as "likely Mojo JIT crash — ADR-009", which led to increasingly complex workarounds (targeted imports, file splitting, retry loops) when the actual fix was a 2-line syntax change. **Always read the actual error output before building workarounds.**
