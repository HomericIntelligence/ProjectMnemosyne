---
name: typing-callable-generic-return-preserve
description: "Use Callable[..., R] + TypeVar(R) instead of ParamSpec when a wrapper function interleaves keyword-only parameters between *args and **kwargs. ParamSpec violates PEP 612 in this case. Use when: (1) replacing object type-erased signatures with proper generics; (2) wrapping functions with complex parameter layouts (interleaved keyword-only params); (3) the wrapper needs to preserve the return type of the wrapped callable; (4) mypy requires full type coverage without # type: ignore comments."
category: architecture
date: 2026-06-05
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - typing
  - generic
  - callable
  - typevar
  - paramspec
  - pep-612
  - return-type-preservation
  - wrapper-pattern
  - mypy
---

# Typing: Preserve Generic Return Type with Callable[..., R]

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-05 |
| **Objective** | Replace type-erased `func: object, *args: object, **kwargs: object -> object` signatures with proper generic typing using `Callable[..., R] + TypeVar("R")` |
| **Outcome** | Successful type preservation for retry/circuit-breaker wrapper functions; zero `# type: ignore` comments; mypy verification-ci pass |
| **Verification** | verified-ci |

## When to Use

- Replacing `object` type-erased signatures (losing type information) with proper generics
- Wrapping a callable and preserving its return type transparently
- The wrapper function has **interleaved keyword-only parameters** between `*args` and `**kwargs` (violates PEP 612 for ParamSpec)
- You need `func: Callable[..., R]` to accept any callable and return type `R`
- All input parameters can be typed as `Any` (wrapper doesn't care about caller args, only return type)
- You want to remove `# type: ignore[arg-type]` and `[operator]` comments that hide real issues

## Pattern: When NOT to Use ParamSpec

**PEP 612 ParamSpec Limitation**: ParamSpec's `P.args` and `P.kwargs` must appear consecutively with no other parameters between them. This code violates that:

```python
# INVALID — ParamSpec with interleaved keyword-only parameter
def retry_with_backoff(
    func: Callable[P, R],
    *args: P.args,
    max_retries: int,  # <-- This violates PEP 612
    **kwargs: P.kwargs,
) -> R:
    ...
```

**Solution**: Use `Callable[..., R] + TypeVar("R")` instead:

```python
# VALID — Callable accepts any args, returns R
def retry_with_backoff(
    func: Callable[..., R],
    *args: Any,
    max_retries: int,  # <-- Interleaved param is fine now
    **kwargs: Any,
) -> R:
    ...
```

## Verified Workflow

### Quick Reference

```python
from collections.abc import Callable
from typing import Any, TypeVar

# Define generic return type variable
R = TypeVar("R")

# Wrapper function with Callable[..., R]
def retry_call(
    func: Callable[..., R],
    *args: Any,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    **kwargs: Any,
) -> R:
    """Retry a function with exponential backoff, preserving its return type.
    
    Args:
        func: Callable that returns type R
        *args: Positional arguments to pass to func
        max_retries: Number of retry attempts
        backoff_factor: Exponential backoff multiplier
        **kwargs: Keyword arguments to pass to func
    
    Returns:
        Result of calling func(*args, **kwargs) — type is preserved as R
    
    Raises:
        Exception: Re-raised from func after max_retries attempts
    """
    for attempt in range(max_retries):
        try:
            # Call the wrapped function with the provided arguments
            # Type checker knows this returns R
            return func(*args, **kwargs)
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            # exponential backoff logic here
```

### Detailed Steps

1. **Import the necessary types** at the module top:
   ```python
   from collections.abc import Callable  # Use collections.abc, not typing (preferred)
   from typing import Any, TypeVar
   ```

2. **Define a TypeVar for the return type**:
   ```python
   R = TypeVar("R")
   ```
   - Use a short, conventional name: `R` for return, `T` for general type, `P` for parameters
   - This variable can be reused across multiple wrapper functions in the same module

3. **Update the function signature** to use `Callable[..., R]`:
   ```python
   def my_wrapper(
       func: Callable[..., R],
       *args: Any,
       **keyword_only_params: Any,
       **kwargs: Any,
   ) -> R:
   ```
   - `Callable[..., R]` accepts any callable with any argument signature and return type `R`
   - `*args: Any` and `**kwargs: Any` accept any positional/keyword arguments
   - The return type is `R` — same as the wrapped callable

4. **Call the wrapped function and return its result**:
   ```python
   result = func(*args, **kwargs)
   return result  # Type: R (preserved from the input func)
   ```
   - No explicit type casting needed — the type checker infers `R` from the return

5. **Remove all `# type: ignore` comments** that were masking the old type-erased signature:
   - Old: `# type: ignore[arg-type]` (argument doesn't match Callable[[object], object])
   - Old: `# type: ignore[operator]` (can't multiply object by float)
   - These comments are no longer needed when signatures are correctly typed

6. **Verify with mypy**:
   ```bash
   pixi run mypy
   ```
   - Should pass with zero errors
   - If errors remain, they are real type issues, not masking from `object` types

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using ParamSpec with interleaved params | `def retry(func: Callable[P, R], *args: P.args, max_retries: int, **kwargs: P.kwargs) -> R:` | PEP 612 does not permit parameters between P.args and P.kwargs — violates the protocol for parameter specification variables | ParamSpec is designed for transparent parameter forwarding only. When you need to add wrapper-specific parameters (like max_retries), you must abandon parameter transparency and use Callable[..., R] instead |
| Using object-typed signature | `def retry(func: object, *args: object, **kwargs: object) -> object:` | Type information is completely erased; caller return types are unknown; mypy can't verify type safety; every call site needs `# type: ignore` | Type erasure defeats the purpose of static typing. Even broad types like Callable[..., R] preserve return-type semantics, enabling downstream type checking |
| Returning the result without typing | `return func(*args, **kwargs)  # type: ignore` | Hides the fact that the return type should be preserved; future refactors can't distinguish intentional type changes from oversight | Always type the return correctly. If mypy complains, the error is real (a legitimate type mismatch) and should be investigated, not masked |
| Using multiple TypeVars (R1, R2, ...) for different wrappers | Defined separate R1, R2, etc. in the same module | Unnecessary proliferation of TypeVars; makes code harder to follow; no additional type safety | One TypeVar R per module is sufficient. It can be reused across all wrapper functions because each function call creates a fresh binding of R to the specific wrapped callable's return type |

## Results & Parameters

### Complete Example: Subprocess Resilience Pattern

This is the pattern from ProjectHephaestus issue #757 (PR #956) — subprocess_resilience.py:

```python
from collections.abc import Callable
from typing import Any, TypeVar

R = TypeVar("R")

def resilient_call(
    func: Callable[..., R],
    *args: Any,
    max_retries: int = 3,
    retry_delay_ms: int = 100,
    backoff_factor: float = 2.0,
    **kwargs: Any,
) -> R:
    """Execute a callable with retry logic and exponential backoff.
    
    This wrapper preserves the return type of the wrapped callable, enabling
    transparent use in type-checked code.
    
    Args:
        func: Callable to execute and retry on failure
        *args: Positional arguments to pass to func
        max_retries: Maximum number of retry attempts (default 3)
        retry_delay_ms: Initial delay between retries in milliseconds (default 100)
        backoff_factor: Multiplier for delay after each retry (default 2.0)
        **kwargs: Keyword arguments to pass to func
    
    Returns:
        The return value of func(*args, **kwargs), with type R preserved.
        If all retries are exhausted, the last exception is re-raised.
    
    Raises:
        Exception: Re-raised after all retry attempts are exhausted
    """
    last_exception: Exception | None = None
    delay_ms = retry_delay_ms
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)  # Type: R
        except Exception as exc:
            last_exception = exc
            if attempt < max_retries - 1:
                time.sleep(delay_ms / 1000.0)
                delay_ms = int(delay_ms * backoff_factor)
    
    raise last_exception  # type: R (due to exhaustion)
```

### Type Verification Example

The following code type-checks cleanly with no `# type: ignore`:

```python
def expensive_computation(x: int, timeout_s: float) -> dict[str, float]:
    """Compute something expensive, may fail."""
    # ... implementation ...
    return {"result": 3.14}

# Call through wrapper — return type is preserved as dict[str, float]
result = resilient_call(
    expensive_computation,
    5,
    timeout_s=30.0,
    max_retries=3,
)

# Type checker knows result: dict[str, float]
value = result["result"]  # OK — no error, dict key is known
```

### Comparison: Before and After

**Before (type-erased with object):**
```python
def resilient_call(
    func: object,          # Type erased — loses all information
    *args: object,
    max_retries: int = 3,
    **kwargs: object,
) -> object:              # Return type is unknown
    # ... implementation ...
    return func(*args, **kwargs)  # type: ignore[misc]

# Caller code
result = resilient_call(expensive_computation, 5, timeout_s=30.0)
# result is object — type checker knows nothing
value = result["result"]  # type: ignore[index]  <-- Hidden error
```

**After (properly typed with Callable[..., R]):**
```python
from collections.abc import Callable
from typing import Any, TypeVar

R = TypeVar("R")

def resilient_call(
    func: Callable[..., R],  # Type-preserving
    *args: Any,
    max_retries: int = 3,
    **kwargs: Any,
) -> R:                      # Return type is preserved
    # ... implementation ...
    return func(*args, **kwargs)

# Caller code
result = resilient_call(expensive_computation, 5, timeout_s=30.0)
# result is dict[str, float] — type checker knows it
value = result["result"]  # OK — no type: ignore needed
```

### Related Pattern in the Codebase

The same pattern is already used in `hephaestus/resilience/circuit_breaker.py:129`:

```python
T = TypeVar("T")

def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Execute func and guard with circuit breaker.
    
    Args:
        func: Callable to execute
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func
    
    Returns:
        Return value of func, with type T preserved
    """
    # ... circuit breaker logic ...
    return func(*args, **kwargs)
```

This skill documents the design decision and explains when/why to use this pattern versus ParamSpec.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #757, PR #956 | hephaestus/resilience/subprocess_resilience.py: replaced type-erased `object` signature with `Callable[..., R] + TypeVar("R")` pattern. Full project mypy + 124 resilience/automation tests pass in CI. |
