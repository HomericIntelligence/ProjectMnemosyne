# Fix Mojo CI Compilation Errors

| Field | Value |
|-------|-------|
| Date | 2026-03-12 |
| Objective | Fix CI failures caused by wrong import paths, mypy version target, and incompatible assert calls |
| Outcome | Success — 4 fixes applied, PR created with auto-merge |
| Project | ProjectOdyssey |
| PR | #4497 |

## When to Use

- CI fails with Mojo import errors (`activation_ops`, `batch_norm` not found)
- mypy fails on `X | Y` union syntax in Python scripts
- `assert_equal` fails to compile for `DType` comparisons in Mojo tests

## Verified Workflow

### 1. Identify the real errors

Separate pre-existing/non-blocking failures (JIT crashes, link checker) from real compilation errors. Focus only on errors that block CI.

### 2. Common fix patterns

| Error Type | Root Cause | Fix |
|------------|-----------|-----|
| mypy `X \| Y` unsupported | `python_version` in `mypy.ini` too low | Bump to match runtime (e.g., 3.12) |
| Mojo import not found | Module was renamed/moved | Check actual module path in `shared/` package `__init__.mojo` files |
| `assert_equal` won't compile | Type doesn't implement required trait for `assert_equal` | Use `assert_true(a == b, msg)` instead |

### 3. Verify before committing

```bash
# Python type checking
pixi run mypy scripts/

# Mojo compilation (not full test run — just verify it compiles)
pixi run mojo build <test_file>.mojo
```

### 4. Always use PR workflow

Even for CI fix commits — never push directly to main.

## Failed Attempts

None in this session. The fixes were straightforward once the correct module paths were identified.

## Key Insight: Mojo Module Renames

When `shared/core/` modules are reorganized:

- `activation_ops` → `activation`
- `batch_norm` → `normalization`

Check the actual `__init__.mojo` re-exports to find where symbols live now. The test files often lag behind refactors.

## Results & Parameters

```ini
# mypy.ini — before
python_version = 3.9

# mypy.ini — after
python_version = 3.12
```

```mojo
# DType assert fix
# Before (won't compile):
assert_equal(dtype, DType.float32)

# After:
assert_true(dtype == DType.float32, "dtype should be float32")
```
