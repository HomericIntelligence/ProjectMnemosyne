---
name: mojo-upstream-bug-filing-reproducibility-standard
description: "Use before filing any Mojo bug or feature request upstream against modular/modular. Enforces reproducibility standard: minimal reproducer, 100% deterministic on current pinned version, verified just-in-time. Prevents wasted effort from filing already-fixed or non-reproducible bugs."
category: debugging
date: 2026-04-11
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [mojo, upstream, bug-filing, reproducibility, modular, determinism, minimal-reproducer]
---

# Mojo Upstream Bug Filing: Reproducibility Standard

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-11 |
| **Objective** | Apply a strict reproducibility gate before filing upstream Mojo bugs against modular/modular |
| **Outcome** | Prevented filing a stale bug (FP16 SIMD) that had already been fixed in 0.26.3; saved Modular's triage time and avoided making the project look sloppy |
| **Verification** | verified-local — approach executed and validated in session |
| **Source** | ProjectOdyssey upstream bug classification session |

## When to Use

- About to file a Mojo bug report or feature request against `modular/modular`
- Writing a blog post or ADR claiming a Mojo feature is broken or unsupported
- Referencing an old ADR or issue that asserts a Mojo limitation
- Upgrading Mojo versions and want to know which old limitations still apply

## The Rule

Only file upstream if **ALL four** conditions are met:

| Condition | Gate |
| ----------- | ------ |
| Reproducer is ≤20 lines, zero external dependencies | Must be true |
| Error/crash happens on EVERY run (100% deterministic) | Must be true |
| Reproducer tested on the CURRENT pinned Mojo version (`pixi.toml`) | Must be true |
| Verified personally JUST BEFORE filing (not from memory or old docs) | Must be true |

If any condition fails → **do not file**. Mark as "non-deterministic" or "version-specific" internally.

## Verified Workflow

### Quick Reference

```bash
# Step 1: Read the current pinned Mojo version
grep "mojo" pixi.toml

# Step 2: Write minimal reproducer (≤20 lines, zero imports beyond stdlib)
cat > /tmp/repro_test.mojo << 'EOF'
# minimal reproducer here
EOF

# Step 3: Run 3 times — must fail ALL 3 to file
pixi run mojo run /tmp/repro_test.mojo
pixi run mojo run /tmp/repro_test.mojo
pixi run mojo run /tmp/repro_test.mojo

# Step 4: Check current docs before filing a feature request
# (the feature may already exist in the current version)
# https://docs.modular.com/mojo/manual/

# Step 5: Only then write blog post / issue template
```

### Step-by-Step Detail

**Step 1: Check current Mojo version**

```bash
grep "mojo" pixi.toml
# e.g. mojo = "==0.26.3"
```

Note the version. This is the authoritative version — not the version when the ADR was written,
not the version when the issue was filed.

**Step 2: Read the official docs for the type/API**

Before writing a reproducer for a "missing feature", check whether it's documented as supported:

- Mojo manual: <https://docs.modular.com/mojo/manual/>
- Stdlib reference: <https://docs.modular.com/mojo/stdlib/>
- CHANGELOG: <https://docs.modular.com/mojo/changelog>

If it's documented as supported → test it before claiming it's broken.

**Step 3: Write a minimal reproducer**

Rules for the reproducer:
- ≤20 lines of code
- Zero imports beyond Mojo stdlib
- No external data files, no network access
- Demonstrates the bug with a single assertion or crash
- Includes the expected vs actual behavior in a comment

**Step 4: Run the reproducer 3+ times**

```bash
for i in 1 2 3; do
  echo "Run $i:"
  pixi run mojo run /tmp/repro_test.mojo
done
```

Decision table:

| Outcome | Action |
| --------- | -------- |
| Fails all 3 runs | Proceed to file |
| Passes any run | Do NOT file — mark as non-deterministic |
| Passes all 3 runs | Do NOT file — bug is fixed in current version |

**Step 5: Gate before writing the issue template**

Only after all 3 runs fail consistently:
1. Write the issue template with version attribution
2. Note which Mojo version introduced the regression (if known)
3. File against `modular/modular`

## Bug Classification Reference

The following table documents how bugs were classified in the session that produced this skill:

| Bug | Deterministic? | Filed? | Reason |
| ----- | --------------- | -------- | -------- |
| ASAN + Python FFI dlsym abort | YES (5-line repro, every run) | YES (template) | 100% deterministic on 0.26.3 |
| FP16 SIMD limitation | N/A — resolved | NO | Feature works in 0.26.3; was 0.26.1-only |
| JIT volume crash | NO (~40-60% CI only) | NO | Non-deterministic; never reproduces locally |
| JIT fortify abort | NO (CI-only) | NO | Never reproduces locally |
| Bitcast UAF | YES | Already filed | modular/modular#6187, closed |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Write blog post before verifying | Wrote full blog post claiming FP16 SIMD was broken in Mojo | Had to retract when verification showed FP16 SIMD worked in 0.26.3 | Always verify FIRST, write SECOND — never document a bug without running a reproducer |
| Trust old ADRs without re-testing | Cited ADR-010 which stated FP16 SIMD was unsupported (written for 0.26.1) | Project had upgraded to 0.26.3 where the feature was fixed; ADR was stale | ADRs document a version snapshot; always re-test the claim before citing them |
| File from memory | Recalled a crash from testing, began drafting upstream issue without re-running | The bug may have been fixed or the memory may be wrong | Run the reproducer just-in-time, every time — never file from memory |
| Assume CI-only failure = upstream Mojo bug | JIT fortify abort appeared in CI but never locally; drafted upstream issue | CI environment differences (resource limits, cgroup, timing) caused the failure, not Mojo itself | Not an upstream Mojo bug unless it reproduces locally with a minimal script |
| File non-deterministic crash | JIT volume crash ~40-60% CI hit rate; began writing issue template | Non-deterministic failures are environment/timing issues, not clean Mojo bugs | 100% determinism is a hard requirement; flaky reproducers waste maintainer time |

## Version Attribution Format

When a bug IS filed, include version history in the issue:

```text
**First observed**: Mojo 0.26.1
**Verified broken in**: Mojo 0.26.3 (current pinned version)
**Confirmed fixed in**: N/A (not fixed as of filing)
```

When updating an ADR or blog post after re-testing:

```text
> **Update 2026-04-11**: Re-tested on Mojo 0.26.3 — this limitation no longer applies.
> The original finding was specific to Mojo 0.26.1.
```

## Results & Parameters

### Determinism Test Threshold

| Hit Rate | Decision |
| ---------- | ---------- |
| 100% (3/3, 5/5, 10/10) | File upstream |
| 80-99% (fails most runs) | Investigate environment; do not file yet |
| <80% or CI-only | Do not file — mark as flaky/environment-specific |

### Minimal Reproducer Size Limit

- **Hard limit**: 20 lines (not counting blank lines and comments)
- **Rationale**: Larger reproducers introduce too many variables; the bug may be in your code, not Mojo
- **If you can't reduce below 20 lines**: The root cause may not be a Mojo bug

### Version Check Command

```bash
# Always run this before filing
grep -E "^mojo\s*=" pixi.toml
# Output example: mojo = "==0.26.3"
```

## Verified On

| Project | Context | Outcome |
| --------- | --------- | --------- |
| ProjectOdyssey | FP16 SIMD upstream bug classification | Correctly suppressed filing — feature works in 0.26.3 |
| ProjectOdyssey | ASAN + Python FFI dlsym abort | Correctly filed — 100% deterministic 5-line repro |
| ProjectOdyssey | JIT volume crash + fortify abort | Correctly suppressed filing — non-deterministic / CI-only |
