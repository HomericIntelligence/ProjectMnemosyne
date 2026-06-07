# typing-callable-generic-return-preserve — Session Notes

## Issue Context

**ProjectHephaestus Issue #757**: Replace type-erased `func: object, *args: object, **kwargs: object -> object` signature in `subprocess_resilience.py` with proper generic typing.

**PR #956**: Merged fix with full mypy + test suite verification.

## Implementation Journey

### Initial Attempt: ParamSpec

The first approach tried ParamSpec (PEP 612):

```python
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def resilient_call(
    func: Callable[P, R],
    *args: P.args,
    max_retries: int,  # <-- PROBLEM: Interleaved parameter
    **kwargs: P.kwargs,
) -> R:
    ...
```

**Why this failed**: PEP 612 explicitly requires that `P.args` and `P.kwargs` appear consecutively with no other parameters between them. The `max_retries` parameter violates this constraint.

From PEP 612:
> "The ParamSpec is designed for parameter forwarding. A ParamSpec object represents the positional and keyword arguments of the function signature from which it is instantiated. The semantics of P.args and P.kwargs requires that they be used together in sequence."

### Solution: Callable[..., R] + TypeVar

Switch to using `Callable[..., R]`:

```python
from collections.abc import Callable
from typing import Any, TypeVar

R = TypeVar("R")

def resilient_call(
    func: Callable[..., R],
    *args: Any,
    max_retries: int,  # <-- OK: No constraint on interleaving
    **kwargs: Any,
) -> R:
    return func(*args, **kwargs)
```

**Why this works**:
- `Callable[..., R]` accepts any callable with any argument signature
- `...` (Ellipsis) means "any arguments"
- `R` is the return type, which is preserved
- There's no constraint on where we place other parameters

### Code Changes in ProjectHephaestus

**File: hephaestus/resilience/subprocess_resilience.py**

1. Added imports:
   ```python
   from collections.abc import Callable
   from typing import Any, TypeVar
   ```

2. Added TypeVar:
   ```python
   R = TypeVar("R")
   ```

3. Updated function signature (circa line 80):
   ```python
   # Before:
   def resilient_call(
       func: object,
       *args: object,
       max_retries: int = 3,
       **kwargs: object,
   ) -> object:

   # After:
   def resilient_call(
       func: Callable[..., R],
       *args: Any,
       max_retries: int = 3,
       **kwargs: Any,
   ) -> R:
   ```

4. Removed type ignore comments:
   - Deleted `# type: ignore[arg-type]` from line ~85
   - Deleted `# type: ignore[operator]` from line ~92
   - Deleted `# type: ignore[attr-defined]` from caller site (loop_runner.py:643)

5. Simplified closure by inlining `func(*args, **kwargs)` directly (no wrapper assignment needed)

### Verification

**Local verification (pre-commit):**
```bash
pixi run ruff check hephaestus/resilience/subprocess_resilience.py
pixi run ruff format hephaestus/resilience/subprocess_resilience.py
pixi run mypy
```

**CI verification (verified-ci level):**
```bash
pixi run pytest tests/unit/resilience/test_subprocess_resilience.py tests/unit/automation/test_github_api.py -v
# 124 tests pass
```

**Final status:**
- No `# type: ignore` comments remain
- No `object` typing remains on the function signature
- Full mypy coverage with zero errors
- All downstream callers type-check cleanly

### Design Decision: Why This Pattern?

This pattern is already used in the same codebase:

**hephaestus/resilience/circuit_breaker.py:129**
```python
T = TypeVar("T")

def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Execute func and guard with circuit breaker."""
    # ... circuit breaker logic ...
    return func(*args, **kwargs)
```

The learning codifies this decision: **Use `Callable[..., R]` when you need to wrap a callable with wrapper-specific parameters that would violate ParamSpec constraints.**

### Metrics

- **Lines changed**: ~8 (mostly import additions)
- **Type ignore comments removed**: 3
- **Tests passing**: 124
- **Mypy errors eliminated**: 1 (was `object` → `R`)
- **Verification level**: verified-ci (full project CI)

### Related Skills/Patterns

- `resilience-circuit-breaker-error-translation`: Different problem (error mapping, not typing)
- `python-type-system-and-api-alignment`: Related (general typing patterns) but this is more specific to the Callable+TypeVar pattern

## Callsites Using resilient_call

After the fix, these callers type-check cleanly:

1. **test_subprocess_resilience.py**: Mock testing
2. **loop_runner.py**: Real subprocess execution with resilience
   - Was: `# type: ignore[attr-defined]` on line 643
   - Now: Type-checks cleanly, return type is preserved

## Future Considerations

This pattern should be applied to any wrapper function that:
1. Takes a callable and needs to preserve its return type
2. Has wrapper-specific parameters (disqualifying ParamSpec)
3. Currently uses `object` or untyped function parameters

Search keywords for finding similar patterns:
- `Callable[[` (looking for callable parameters)
- `# type: ignore` (looking for type masking)
- `-> object` (type-erased returns)
