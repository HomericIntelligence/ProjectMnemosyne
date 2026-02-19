# Manager Proxy Type Hints

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-15 |
| **Category** | architecture |
| **Objective** | Add explicit return type annotations to methods returning multiprocessing Manager proxy objects |
| **Outcome** | ✅ Successfully added `Any` type hint with comprehensive documentation |
| **Issue** | #641 |
| **PR** | #708 |

## When to Use This Skill

Use this skill when:

- ✅ Adding type hints to methods that return `Manager().Semaphore()`, `Manager().Queue()`, or other Manager proxy objects
- ✅ Encountering complex proxy types that are difficult to annotate precisely
- ✅ Need to improve type safety and IDE support for multiprocessing code
- ✅ Want to follow established codebase patterns for complex return types

**Triggers:**

- Type checker complains about implicit `Any` return types
- IDE cannot infer return type for Manager-created objects
- Code review requests explicit return type annotations
- Following up on type-safety improvements

## Verified Workflow

### 1. Identify the Return Type

```python
# Example method returning Manager proxy object
def _setup_workspace_and_semaphore(self):
    """Set up workspace manager and global semaphore."""
    manager = multiprocessing.Manager()
    return manager.Semaphore(value=self.config.parallel_subtests)
```

### 2. Add Any Import

```python
from typing import TYPE_CHECKING, Any
```

**Rationale**: Manager proxy objects have complex types that cannot be easily annotated. The `SyncManager` class is available but proxy types like `Semaphore()` created at runtime are difficult to represent accurately.

### 3. Add Return Type Annotation

```python
def _setup_workspace_and_semaphore(self) -> Any:
```

**Why `Any` instead of specific type?**

- Manager proxy objects are created dynamically
- The actual type is a proxy wrapper, not the raw `Semaphore` class
- `SyncManager.Semaphore` is not directly accessible as a type annotation
- Using `Any` is the pragmatic choice endorsed by existing codebase patterns

### 4. Enhance Docstring Documentation

```python
def _setup_workspace_and_semaphore(self) -> Any:
    """Set up workspace manager and global semaphore for parallel execution.

    Returns:
        Manager-created Semaphore for limiting concurrent agents across
        all tiers. Type annotation is Any due to complexity of Manager
        proxy types (returns multiprocessing.Manager().Semaphore()).

    """
```

**Key docstring elements:**

- Describe what the method actually returns (Manager-created Semaphore)
- Explain the purpose/usage context
- Document why `Any` is used (complexity of Manager proxy types)
- Show the actual return expression for clarity

### 5. Verify with Type Checker

```bash
# Run mypy via pre-commit hooks
pre-commit run mypy --all-files

# Expected: No new type errors
```

### 6. Test Runtime Behavior

```bash
# Verify type annotation is present
pixi run python -c "from scylla.e2e.runner import E2ERunner; import inspect; sig = inspect.signature(E2ERunner._setup_workspace_and_semaphore); print(f'Return annotation: {sig.return_annotation}')"

# Expected output: Return annotation: Any
```

## Failed Attempts

### ❌ Attempt 1: Using `SyncManager.Semaphore` Type

**What was tried:**

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multiprocessing.managers import SyncManager

def _setup_workspace_and_semaphore(self) -> SyncManager.Semaphore:
    ...
```

**Why it failed:**

- `SyncManager.Semaphore` is not a valid type annotation
- The actual return type is a proxy object, not the raw Semaphore class
- Mypy cannot resolve `SyncManager.Semaphore` as a type

**Error message:**

```
error: "Type[SyncManager]" has no attribute "Semaphore"
```

### ❌ Attempt 2: Using `multiprocessing.synchronize.Semaphore`

**What was tried:**

```python
from multiprocessing.synchronize import Semaphore

def _setup_workspace_and_semaphore(self) -> Semaphore:
    ...
```

**Why it failed:**

- This is the raw `Semaphore` class, not the Manager proxy type
- Manager returns a proxy wrapper, not the direct class
- Type mismatch between annotation and actual return type

### ❌ Attempt 3: Using Protocol or TypeVar

**What was tried:**

```python
from typing import Protocol

class SemaphoreLike(Protocol):
    def acquire(self) -> bool: ...
    def release(self) -> None: ...

def _setup_workspace_and_semaphore(self) -> SemaphoreLike:
    ...
```

**Why it failed:**

- Overly complex for a simple return type annotation
- Doesn't accurately represent the full Manager proxy interface
- Violates KISS principle - simpler solution exists (`Any`)

## Results & Parameters

### Changes Required

1. **Import statement (line 17)**:

   ```python
   from typing import TYPE_CHECKING, Any
   ```

2. **Method signature (line 263)**:

   ```python
   def _setup_workspace_and_semaphore(self) -> Any:
   ```

3. **Docstring (lines 264-270)**:

   ```python
   """Set up workspace manager and global semaphore for parallel execution.

   Returns:
       Manager-created Semaphore for limiting concurrent agents across
       all tiers. Type annotation is Any due to complexity of Manager
       proxy types (returns multiprocessing.Manager().Semaphore()).

   """
   ```

### Verification Commands

```bash
# Type checking
pre-commit run mypy --all-files

# Unit tests
pixi run python -m pytest tests/unit/e2e/test_checkpoint.py -v --no-cov

# Runtime verification
pixi run python -c "from scylla.e2e.runner import E2ERunner; import inspect; sig = inspect.signature(E2ERunner._setup_workspace_and_semaphore); print(f'Return annotation: {sig.return_annotation}')"
```

### Existing Patterns

This approach follows the established pattern in **`scylla/e2e/parallel_executor.py:170`**:

```python
def run_subtests_parallel(
    tier_id: TierID,
    subtests: list[SubtestConfig],
    tier_config: TierConfig,
    tier_result: TierResult,
    experiment_dir: Path,
    workspace_manager: WorkspaceManager,
    global_semaphore=None,  # Implicitly Any - same pattern
    ...
) -> None:
```

## Cross-References

- **Related skill**: `global-semaphore-parallelism` (debugging) - Documents usage patterns for Manager semaphores
- **Related skill**: `pydantic-model-dump` (debugging) - Reinforces explicit return type hints
- **Code location**: `scylla/e2e/runner.py:263` - Method implementation
- **Code location**: `scylla/e2e/parallel_executor.py:170` - Existing pattern reference

## Notes

### Type Annotation Philosophy

- **Precision vs. Pragmatism**: When exact type annotation is complex or impossible, `Any` with documentation is acceptable
- **Consistency**: Follow existing codebase patterns rather than introducing new approaches
- **Documentation**: Clear docstrings compensate for generic `Any` annotations
- **KISS Principle**: Don't overcomplicate type annotations with Protocols or complex generics when `Any` suffices

### Multiprocessing Type Challenges

Manager proxy objects are particularly challenging because:

1. They're created at runtime via factory methods
2. The proxy wrapper type is internal to multiprocessing
3. The public API doesn't expose concrete proxy types
4. TYPE_CHECKING imports can't access runtime-created types

### Future Improvements

If Python's type system evolves to better support Manager proxies, consider:

- `typing_extensions` updates for Manager proxy types
- PEP proposals for standardizing multiprocessing type hints
- Third-party stubs packages (e.g., `types-multiprocessing`)

For now, `Any` with comprehensive documentation is the recommended approach.

## Success Metrics

✅ **Type Safety**: Method now has explicit return type (was implicit `Any`, now explicit `Any`)
✅ **IDE Support**: IDEs can see the return type annotation
✅ **Documentation**: Docstring clearly explains what's returned and why `Any` is used
✅ **Consistency**: Follows existing codebase patterns
✅ **Maintainability**: Future developers understand the type annotation choice
✅ **No Regressions**: All tests pass, pre-commit hooks pass

## Team Knowledge

This skill captures the team's decision to use `Any` for Manager proxy types with comprehensive documentation. This is **not a workaround** but a **deliberate architectural choice** based on Python's type system limitations for dynamic proxy objects.

**Decision**: Explicit `Any` + clear docstring > Complex type gymnastics > Implicit `Any`
