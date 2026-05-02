---
name: mojo-always-inline-worsens-jit-crashes
description: "Warning: @always_inline on large branching methods WORSENS Mojo JIT crashes. Use when: (1) considering @always_inline to fix bitcast crashes, (2) debugging libKGENCompilerRTShared.so crashes, (3) CI tests crash after adding @always_inline."
category: debugging
date: '2026-03-25'
version: "1.0.0"
user-invocable: false
tags:
  - mojo
  - always-inline
  - jit-crash
  - bitcast
  - regression
---

# @always_inline Worsens Mojo JIT Crashes

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Fix intermittent bitcast accessor crashes by adding @always_inline |
| **Outcome** | FAILED — @always_inline caused dramatically MORE crashes across ALL test groups |

## When to Use

- You are considering adding `@always_inline` to fix Mojo runtime crashes
- You added `@always_inline` and CI tests started crashing across multiple groups
- You see `libKGENCompilerRTShared.so` crashes that got WORSE after a code change
- A method has large if/elif dtype branching and you want to inline it

## Verified Workflow

### Quick Reference

```bash
# DO NOT add @always_inline to large branching methods
# Instead, keep them as regular functions

# BAD - causes more JIT crashes:
@always_inline
fn _get_float64(self, index: Int) -> Float64:
    if self._dtype == DType.float16: ...
    elif self._dtype == DType.bfloat16: ...
    elif self._dtype == DType.float32: ...
    elif self._dtype == DType.float64: ...
    else: ...  # integer fallback

# GOOD - works reliably:
fn _get_float64(self, index: Int) -> Float64:
    # same body, no @always_inline
```

### Detailed Steps

1. **Do NOT add @always_inline to methods with runtime dtype branching** — these have 5+ if/elif branches that expand massively when inlined into every call site

2. **@always_inline is safe for small parametric methods** — `load[dtype]`/`store[dtype]` work fine because they have NO branching (dtype is compile-time)

3. **The key difference:**
   - `load[dtype]` — 1 line body, compile-time dtype, safe to inline
   - `_get_float64` — 15+ line body, 5+ runtime branches, unsafe to inline

4. **If CI crashes get worse after a change**, check git diff for `@always_inline` additions

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| @always_inline on_get_float64 etc. | Added @always_inline to 7 runtime-dtype accessor methods to keep self alive during bitcast | Inlining large branching methods into every call site (hundreds of times in gradient checker) increases JIT compilation memory pressure, triggering MORE libKGENCompilerRTShared.so crashes | @always_inline is only safe for small, non-branching methods. Large methods with runtime if/elif should NOT be inlined. |
| Hypothesis: ASAP destruction | Assumed self was destroyed before bitcast write completed without @always_inline | The method frame already keeps self alive — the crash is from JIT memory pressure, not object lifetime | Don't assume the crash mechanism without evidence. The same crash signature can have different root causes. |

## Results & Parameters

### Before @always_inline (main branch)

| Test Group | Status |
|------------|--------|
| Models | PASSED |
| Autograd | PASSED |
| Core Utilities | PASSED |
| Core Gradient | PASSED |
| Core Layers | PASSED |
| Gradient Checking | FAILED (intermittent) |

### After @always_inline (PR #5099 first push)

| Test Group | Status |
|------------|--------|
| Models | FAILED (ALL crash) |
| Autograd | FAILED (4 crashes) |
| Core Utilities | FAILED |
| Core Gradient | FAILED |
| Core Layers | PASSED |
| Core Activations | FAILED (16/17 crash) |
| Gradient Checking | FAILED |

### Rule of thumb

| Method Characteristics | @always_inline Safe? |
|----------------------|---------------------|
| Small body (1-3 lines), compile-time params | Yes |
| Large body (10+ lines), runtime branching | NO |
| Called in tight loops (100+ times) | Risky — test thoroughly |
| Has 5+ if/elif branches | NO |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | shared/tensor/any_tensor.mojo | PR #5099 regression and revert |
