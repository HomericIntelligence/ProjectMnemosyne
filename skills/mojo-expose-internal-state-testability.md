---
name: mojo-expose-internal-state-testability
description: "Refactor Mojo structs to expose internally-constructed state as fields for
  integration testing. Use when: (1) a struct creates metric/state objects internally in
  a method but never exposes them, (2) you need to verify internal state after calling a
  method, (3) adding raises to __init__ cascades to callers."
category: testing
date: 2026-03-25
version: 1.0.0
user-invocable: false
verification: verified-local
supersedes:
  - mojo-confusion-matrix-integration-tests.md
tags:
  - mojo
  - refactoring-for-testability
  - integration-testing
  - cascading-raises
---

# Expose Internal Struct State for Integration Testing

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Enable true integration tests where a struct method populates internal state that tests can inspect after the call |
| **Outcome** | Successfully exposed `ConfusionMatrix` on `ValidationLoop` struct; integration test verifies exact cell counts through the full `run()` path |
| **Verification** | verified-local |

Supersedes: `mojo-confusion-matrix-integration-tests.md` — that skill concluded "Use the
ValidationLoop smoke test only to verify no crash; test exact counts directly on
`ConfusionMatrix.update()`". This skill shows you *can* test exact counts through the full
integration path by promoting the internal object to a struct field.

## When to Use

- A struct method constructs an object internally (e.g., `var cm = ConfusionMatrix(...)` inside `validate()`) and the test needs to inspect that object after the method returns
- You want to test the integration path (struct → method → internal object) rather than testing the internal object in isolation
- A function creates state locally, updates it in a loop, and discards it — but tests need to verify those accumulated updates
- You need to refactor a free function to accept a caller-provided mutable reference instead of creating state internally

## Verified Workflow

### Quick Reference

```bash
# Pattern: Extract internal state to struct field
# 1. Add field to struct
# 2. Extract function impl to accept mut reference
# 3. Wrap original function for backwards compatibility
# 4. Update __init__ (may add `raises`)
# 5. Fix cascading callers
# 6. Test via struct field inspection
```

### Detailed Steps

1. **Identify the internal object** that needs exposure. Look for `var obj = SomeType(...)` created inside a method that's never returned or stored.

2. **Add the object as a struct field**:

    ```mojo
    struct ValidationLoop:
        var confusion_matrix: ConfusionMatrix
        """Populated during run() when compute_confusion=True."""
    ```

3. **Extract the method body** into a private function that accepts a mutable reference:

    ```mojo
    fn _validate_impl(
        ...
        mut confusion_matrix: ConfusionMatrix,  # Caller-provided
        ...
    ) raises -> Float64:
        # Original body, but uses the passed-in confusion_matrix
    ```

4. **Wrap the original function** for backwards compatibility (existing callers unaffected):

    ```mojo
    fn validate(...) raises -> Float64:
        var confusion_matrix = ConfusionMatrix(num_classes=num_classes)
        return _validate_impl(..., confusion_matrix, ...)
    ```

5. **Update the struct's method** to pass its field:

    ```mojo
    fn run(mut self, ...) raises -> Float64:
        self.confusion_matrix.reset()  # Reset each run
        var val_loss = _validate_impl(..., self.confusion_matrix, ...)
    ```

6. **Handle cascading `raises`**: If the field's `__init__` raises, the struct's `__init__` must also raise, which cascades to all callers:

    ```mojo
    # Before: fn __init__(out self, ...) :
    # After:  fn __init__(out self, ...) raises:
    ```

    Check all callers with: `grep -rn 'StructName(' --include='*.mojo'`

7. **Write the integration test** that inspects the struct field after calling the method:

    ```mojo
    fn test_integration() raises:
        var vloop = ValidationLoop(compute_confusion=True, num_classes=2)
        _ = vloop.run(identity_forward, simple_loss, loader, metrics)
        # Now inspect the field directly:
        var raw = vloop.confusion_matrix.normalize(mode="none")
        assert_equal_int(Int(raw._data.bitcast[Float64]()[0]), 1)  # TN
    ```

### Key Pattern: Identity Forward Function

Use an identity forward function to control predictions via crafted input logits:

```mojo
fn identity_forward(data: AnyTensor) raises -> AnyTensor:
    """Returns input unchanged — predictions = crafted logits."""
    return data
```

This lets you set up data as 2-column logits where argmax produces known class predictions.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Test ConfusionMatrix directly (bypass ValidationLoop) | Created ConfusionMatrix separately and called update() with known data | Tests the metric in isolation, not the integration path through ValidationLoop.run() | Isolated unit tests don't verify the wiring between struct method and internal metric |
| Inspect confusion matrix without struct changes | Tried to access confusion matrix after validate() call | validate() creates ConfusionMatrix locally and discards it — no way to inspect | Internal state must be promoted to a field or returned to be testable |
| Add field without adding `raises` to __init__ | Added ConfusionMatrix field but left __init__ as non-raising | ConfusionMatrix.__init__() raises, so the containing struct's __init__ must also raise | Mojo propagates `raises` requirements — always check if a field's constructor raises |

## Results & Parameters

### Files Modified

```text
shared/training/loops/validation_loop.mojo  — Add field, extract _validate_impl(), mut self on run()
shared/training/trainer.mojo                — Add raises to BaseTrainer.__init__ and factory functions
tests/shared/training/test_validation_loop.mojo — Add identity_forward + integration test
```

### Cascading raises checklist

When adding a `raises` field to a struct, update:

1. The struct's `__init__` → add `raises`
2. Any struct that *contains* this struct → add `raises` to its `__init__`
3. Factory functions that construct the struct → add `raises` to return type
4. Verify all callers are already in `raises` functions (grep for `StructName(`)

### Test fixture

```text
Data (logits):  [[1.0, 0.0], [0.0, 1.0], [0.0, 1.0], [1.0, 0.0]]
-> argmax:      [0, 1, 1, 0]
Labels:         [0, 1, 0, 1]

Expected confusion matrix (row=true, col=pred):
        pred=0  pred=1
true=0    1       1    (TN=1, FP=1)
true=1    1       1    (FN=1, TP=1)
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3185 | [notes.md](./skills/mojo-expose-internal-state-testability.notes.md) |
