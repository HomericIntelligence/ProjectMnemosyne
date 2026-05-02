---
name: debugging-silent-error-suppression-pola
description: "Fix functions that silently swallow errors and default to fallback behavior instead of propagating exceptions. Use when: (1) a function catches ValueError but falls back instead of re-raising, (2) symmetric functions (load/save) have inconsistent error handling, (3) POLA violations where callers get unexpected output formats."
category: debugging
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - error-handling
  - POLA
  - silent-failure
  - io-utils
  - hephaestus
---

# Fix Silent Error Suppression in Symmetric Functions

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Remove try/except fallback in `save_data()` that silently defaulted to JSON for unknown file extensions, making it consistent with `load_data()` which correctly raises `ValueError` |
| **Outcome** | Success — all 435 tests pass, PR #97 created |
| **Verification** | verified-local |
| **Project** | ProjectHephaestus, Issue #53, PR #97 |

## When to Use

- A function catches an exception and falls back to a default instead of propagating the error
- Symmetric functions (e.g., load/save, encode/decode, serialize/deserialize) have inconsistent error handling
- A caller passes an unsupported value and gets silently wrong output instead of an error
- POLA violation: `save_data(data, "file.csv")` creates a JSON file with `.csv` extension

## Verified Workflow

### Quick Reference

```bash
# 1. Identify the silent fallback pattern
grep -n "except ValueError" hephaestus/io/utils.py

# 2. Check if the symmetric function raises properly
grep -A2 "def load_data" hephaestus/io/utils.py  # should let ValueError propagate

# 3. Remove try/except, let exception propagate
# 4. Update docstring to document ValueError raise condition
# 5. Update tests: old test expected fallback, new test expects ValueError
# 6. Verify
pixi run pytest tests/unit/io/test_utils.py -v --no-cov
pixi run pytest tests/ -v --no-cov
```

### Detailed Steps

1. **Identify the anti-pattern**: Look for `try/except ValueError` blocks that catch format detection errors and fall back to a default format:
   ```python
   # BEFORE (anti-pattern)
   try:
       fmt = _detect_format(filepath, format_hint)
   except ValueError:
       fmt = "json"  # silent fallback
   ```

2. **Check the symmetric function**: Verify `load_data()` correctly lets the `ValueError` propagate — this confirms the inconsistency

3. **Remove the try/except**: Let the `ValueError` from `_detect_format()` propagate naturally:
   ```python
   # AFTER (correct)
   fmt = _detect_format(filepath, format_hint)
   ```

4. **Update the docstring**: Add `ValueError` to the Raises section documenting the new behavior:
   ```python
   Raises:
       ValueError: If format cannot be determined from the file extension
           and no format_hint is provided, or if format is unsafe and
           allow_unsafe_deserialization is False.
   ```

5. **Update tests**: Replace the test that expected silent fallback with one that expects `ValueError`:
   ```python
   # BEFORE
   def test_default_format_json(self, tmp_path):
       f = tmp_path / "out.dat"
       assert save_data({"x": 1}, f)  # silently creates JSON

   # AFTER
   def test_unknown_extension_raises(self, tmp_path):
       f = tmp_path / "out.dat"
       with pytest.raises(ValueError, match="Could not determine"):
           save_data({"x": 1}, f)
   ```

6. **Run full test suite** to ensure no other code depended on the silent fallback

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A — direct fix | The fix was straightforward (3 lines removed, docstring updated, test updated) | N/A | When the symmetric function already has the correct behavior, the fix is just removing the suppression code |

## Results & Parameters

### Files Modified

| File | Changes |
| ------ | --------- |
| `hephaestus/io/utils.py` | Removed try/except fallback (3 lines), updated docstring Raises section |
| `tests/unit/io/test_utils.py` | Replaced `test_default_format_json` with `test_unknown_extension_raises` |

### Test Results

```
435 passed, 0 failed
```

### Pattern: Identifying Silent Error Suppression

A function has a silent error suppression bug when ALL of these are true:
1. It catches an exception from a helper function
2. Instead of re-raising or wrapping the exception, it falls back to a default value
3. The fallback can produce silently wrong output (e.g., JSON file with `.csv` extension)
4. A symmetric function (load counterpart) correctly raises the same exception

### Detection Heuristic

```bash
# Find try/except blocks that catch and discard ValueError
grep -B1 -A2 "except ValueError" src/ --include="*.py" -rn | grep -v "raise"
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #53, PR #97 | Fixed `save_data()` silent JSON fallback, 435 tests pass |
