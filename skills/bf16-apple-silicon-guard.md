---
name: bf16-apple-silicon-guard
description: 'Add runtime guards to dtype/precision factory methods that raise descriptive
  errors on unsupported hardware. Use when: adding Apple Silicon BF16 restrictions
  in Mojo, converting silent dtype misuse into loud runtime errors, or making precision
  checks testable without target hardware.'
category: architecture
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | `PrecisionConfig.bf16()` silently used `DType.bfloat16` on Apple Silicon where it is unsupported, causing runtime failures with no diagnostic message |
| **Solution** | Extract the platform check into a testable helper, add `raises` to the factory method signature, and call `is_apple_silicon()` from `sys.info` |
| **Language** | Mojo v0.26.1+ |
| **Files Changed** | `shared/training/precision_config.mojo`, new `tests/shared/training/test_bf16_apple_silicon_guard.mojo` |
| **Issue** | #3203 (follow-up to #3088) |

## When to Use

- Adding a hardware restriction to a Mojo dtype or precision factory method
- Converting a "silently wrong" dtype usage into a loud, helpful error
- Need to test a platform guard in CI (Linux) without the restricted hardware (Apple Silicon)
- Any time `sys.info.is_apple_silicon()` (or similar platform check) should block a code path

## Verified Workflow

### 1. Confirm the stdlib API exists

Check the Mojo stdlib package binary for the symbol before writing code:

```bash
strings .pixi/envs/default/lib/mojo/std.mojopkg | grep -i "is_apple"
# → is_apple_silicon(), is_apple_m1(), is_apple_m2(), ...
```

The `is_apple_silicon()` function is available in `sys.info`.

### 2. Extract a testable helper function

Place the guard logic in a module-level function that accepts `is_apple: Bool`.
This decouples the platform detection from the guard logic, allowing CI (Linux)
to exercise the error path by passing `True` without Apple Silicon hardware.

```mojo
fn _check_bf16_platform_support(is_apple: Bool) raises:
    """Raise an error if the platform does not support BF16.

    Args:
        is_apple: True if running on Apple Silicon hardware.

    Raises:
        Error: If is_apple is True, since bfloat16 is unsupported on Apple Silicon.
    """
    if is_apple:
        raise Error(
            "BF16 (bfloat16) is not supported on Apple Silicon."
            " Use PrecisionConfig.fp16() instead."
        )
```

### 3. Add the import and call the helper in the factory method

```mojo
from sys.info import is_apple_silicon

# In PrecisionConfig:
@staticmethod
fn bf16(initial_scale: Float32 = 65536.0) raises -> PrecisionConfig:
    """...
    Raises:
        Error: If called on Apple Silicon where bfloat16 is unsupported.
    """
    _check_bf16_platform_support(is_apple_silicon())
    return PrecisionConfig(
        mode=PrecisionMode.BF16,
        compute_dtype=bfloat16_dtype,
        ...
    )
```

Key change: `-> PrecisionConfig` becomes `raises -> PrecisionConfig`.

### 4. Audit callers for `raises` propagation

```bash
grep -rn "\.bf16()" --include="*.mojo" .
```

All callers must either already have `raises` in their signature or be updated.
In this case all existing callers (`test_precision_config.mojo`,
`test_multi_precision_training.mojo`, `test_precision_checkpoint.mojo`,
`from_string()` in the same file) already propagated `raises` — no further changes needed.

### 5. Write tests that exercise the error path on CI

```mojo
fn test_check_bf16_platform_support_raises_on_apple() raises:
    var caught = False
    try:
        _check_bf16_platform_support(True)  # simulate Apple Silicon
    except e:
        caught = True
        var msg = String(e)
        if "Apple Silicon" not in msg:
            raise Error("Expected 'Apple Silicon' in message, got: " + msg)
    if not caught:
        raise Error("Should have raised")

fn test_bf16_succeeds_on_non_apple_silicon() raises:
    # On Linux CI, is_apple_silicon() returns False — guard should not fire
    var config = PrecisionConfig.bf16()
    if config.compute_dtype != DType.bfloat16:
        raise Error("BF16 config should use bfloat16 compute dtype")
```

### 6. Verify pre-commit passes

```bash
pixi run pre-commit run --files shared/training/precision_config.mojo \
    tests/shared/training/test_bf16_apple_silicon_guard.mojo
# All hooks: Passed
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fallback to FP16 silently | Return `PrecisionConfig.fp16()` when `is_apple_silicon()` | Changes semantics without warning; callers expect BF16 mode but get FP16 | Fail loudly instead — let the caller decide to use FP16 explicitly |
| Compile-time `@parameter` guard | Use `@parameter if is_apple_silicon()` to block at compile time | `is_apple_silicon()` is a runtime function, not a compile-time parameter in v0.26.1 | Use runtime `raises` pattern; compile-time guard requires a different API |
| Inline the guard in `bf16()` directly | Put the `if is_apple_silicon(): raise Error(...)` directly inside `bf16()` without a helper | Cannot test the error path on Linux CI — `is_apple_silicon()` always returns `False` | Extract into a helper that accepts `is_apple: Bool` to enable injection in tests |
| Check Docker image | Run `mojo -c "from sys.info import is_apple_silicon; ..."` via Docker | Docker image pull was denied (access restricted) | Use `strings` on the `.mojopkg` binary to confirm API availability instead |

## Results & Parameters

### Confirmed: `is_apple_silicon()` is in `sys.info`

```bash
strings .pixi/envs/default/lib/mojo/std.mojopkg | grep -i "is_apple"
# is_apple_gpu
# is_apple_m1()
# is_apple_m2()
# is_apple_m3()
# is_apple_m4()
# is_apple_silicon()
```

### Error message template

```
"BF16 (bfloat16) is not supported on Apple Silicon. Use PrecisionConfig.fp16() instead."
```

The message must:
- Name the dtype (`BF16`/`bfloat16`)
- Name the platform (`Apple Silicon`)
- Suggest the alternative (`PrecisionConfig.fp16()`)

### Pattern for testable platform guards

```mojo
# Module-level helper (testable via injection)
fn _check_<dtype>_platform_support(is_restricted: Bool) raises:
    if is_restricted:
        raise Error("<dtype> is not supported on <platform>. Use <alternative> instead.")

# Factory method calls helper with real platform check
@staticmethod
fn <dtype>(args) raises -> PrecisionConfig:
    _check_<dtype>_platform_support(is_<platform>())
    return PrecisionConfig(...)
```

### Signature change pattern

```mojo
# Before:
fn bf16(initial_scale: Float32 = 65536.0) -> PrecisionConfig:

# After:
fn bf16(initial_scale: Float32 = 65536.0) raises -> PrecisionConfig:
```

All callers of `bf16()` must propagate `raises` — audit with grep before changing.
