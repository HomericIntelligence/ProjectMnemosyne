# Session Notes: mojo-python-interop-placeholder-replacement

## Session Context

- **Date**: 2026-03-07
- **Repository**: HomericIntelligence/ProjectOdyssey
- **Issue**: #3283 — Replace file_io.mojo placeholder remove_file() with real implementation
- **Branch**: 3283-auto-impl
- **PR**: #3874

## Problem

`shared/utils/file_io.mojo:671` contained a `remove_safely()` function that:
- Checked `file_exists()` (real check)
- Returned `True` unconditionally without deleting anything
- Had a NOTE comment: "Mojo v0.26.1 doesn't have os.remove() or file system operations"
- Called itself a "placeholder"

This was a silent correctness bug: callers (e.g. checkpoint cleanup) believed files were
removed when they were not.

## Root Cause

Mojo v0.26.1 stdlib lacks `os.remove()` and other filesystem mutation operations.
The same file already used `Python.import_module("os").rename()` in `safe_write_file()`
for the same reason — there was a clear pattern to follow.

## Files Changed

- `shared/utils/file_io.mojo:662-679` — replaced placeholder with Python interop
- `tests/shared/utils/test_io.mojo:233-253` — replaced TODO stub with real test

## Verification

Pre-commit passed locally:
```
Mojo Format..............................................................Passed
Check for deprecated List[Type](args) syntax.............................Passed
Validate Test Coverage...................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check for Large Files....................................................Passed
Fix Mixed Line Endings...................................................Passed
```

Mojo tests could NOT run locally due to GLIBC version mismatch (host: 2.31, required: 2.32+).
CI is the authoritative test runner.

## Implementation

```mojo
fn remove_safely(filepath: String) -> Bool:
    """Remove file using Python os.remove() interop."""
    if not file_exists(filepath):
        return False
    try:
        var python = Python.import_module("os")
        python.remove(filepath)
        return True
    except:
        return False
```

## Test

```mojo
fn test_safe_remove() raises:
    from shared.utils.file_io import remove_safely, safe_write_file, file_exists
    var test_path = "/tmp/test_remove_safely_3283.txt"
    var written = safe_write_file(test_path, "test content")
    assert_true(written)
    assert_true(file_exists(test_path))
    var removed = remove_safely(test_path)
    assert_true(removed)
    assert_false(file_exists(test_path))
    var removed_again = remove_safely(test_path)
    assert_false(removed_again)
    print("PASS: test_safe_remove")
```