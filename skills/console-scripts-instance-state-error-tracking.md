---
name: console-scripts-instance-state-error-tracking
description: "How to add exit-code discipline to CLI main() functions without breaking existing return-value callsites. Use when: (1) main() must return int for exit-code discipline, (2) existing code unpacks tuples from helper methods, (3) you need to track error state without changing method signatures."
category: architecture
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: []
---

# Console Scripts: Instance-State Error Tracking

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Add exit-code discipline to CLI main() functions without breaking existing return-value callsites or requiring test modifications |
| **Outcome** | Successfully implemented instance-state error tracking pattern — all 119 tests pass, zero test modifications, fully resolves masked failures |
| **Verification** | verified-ci (PR #653 CI passed, auto-merge enabled) |

## When to Use

- CLI main() function needs to return `int` for proper exit-code discipline (signal success/failure to OS)
- Existing helper methods return tuples unpacked by test callsites (changing tuple shape breaks tests)
- You need to track error state across multiple method calls without changing function signatures
- Refactoring must be backward-compatible with existing test suite

## Verified Workflow

### Problem Statement

Three main() functions in ProjectHephaestus had exit-code discipline violations:

```python
def main() -> None:  # BAD: No exit code on failure
    fixer = MarkdownLinkFixer(...)
    fixer.process_file(...)  # May fail silently
    sys.exit(0)  # Always exit 0, even on errors
```

Initial approaches failed:

1. **Tuple-shape change** (rejected): Changing `fix_file()` return from `(status, data)` 2-tuple to `(status, data, error_code)` 3-tuple broke 8 test callsites unpacking the tuples
2. **Method signature change** (rejected): Adding error tracking parameter would require changes across 20+ callsites

### Solution: Instance-State Error Tracking

**Pattern**: Track error state via a `had_error: bool` instance attribute, set it at error sites, compute exit code in main().

#### Step 1: Add had_error attribute to class

```python
class MarkdownLinkFixer:
    def __init__(self, ...):
        self.had_error: bool = False
        # ... rest of init
```

#### Step 2: Set had_error at error sites (no signature changes)

```python
def fix_file(self, file_path: str) -> Tuple[bool, Optional[Dict]]:
    """Fix markdown links in a file.
    
    Returns:
        Tuple of (success: bool, data: Optional[Dict])
    """
    try:
        content = self._read_file(file_path)
    except OSError as e:
        self.had_error = True  # Track error in instance state
        logger.error(f"Failed to read {file_path}: {e}")
        return False, None
    
    try:
        self._write_file(file_path, fixed_content)
    except OSError as e:
        self.had_error = True  # Track error in instance state
        logger.error(f"Failed to write {file_path}: {e}")
        return False, None
    
    return True, result_data
```

#### Step 3: Compute exit code in main()

```python
def main() -> int:
    """Main entry point with proper exit-code discipline."""
    fixer = MarkdownLinkFixer(...)
    
    # Process files (errors tracked in fixer.had_error)
    for file_path in file_list:
        fixer.fix_file(file_path)
    
    # Return proper exit code
    return 1 if fixer.had_error else 0
```

#### Step 4: Update sys.exit() call

```python
if __name__ == "__main__":
    sys.exit(main())
```

### Key Properties of This Pattern

| Property | Value | Why It Works |
|----------|-------|--------------|
| **Signature compatibility** | Zero changes to fix_file/process_path signatures | All test callsites remain valid |
| **Return value contracts** | Tuples unchanged (still 2-tuples) | Tests unpack `success, data` as before |
| **Error propagation** | Via instance attribute + main() return | Main() exit code reflects accumulated errors |
| **Test modifications** | Zero required | Existing tests pass unchanged |
| **Blast radius** | Limited to class implementation | No impact on public API |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Tuple-shape expansion | Change `fix_file()` return from `(bool, dict)` 2-tuple to `(bool, dict, int)` 3-tuple to carry error codes | 8 test callsites unpack tuples: `success, data = fixer.fix_file()` would become `success, data, _ = ...` requiring test edits; breaks KISS principle | Instance state avoids signature changes; preserve tuple contracts when possible |
| Method signature addition | Add optional `error_tracker: ErrorTracker` parameter to fix_file/process_path | Would require 20+ callsite updates across tests and main; violates backward-compatibility | Use instance attributes to share state across methods without changing signatures |

## Results & Parameters

### Code Pattern Reference

```python
# Class-level error tracking
class MarkdownLinkFixer:
    def __init__(self, ...):
        self.had_error: bool = False
    
    # No signature changes to existing methods
    def fix_file(self, file_path: str) -> Tuple[bool, Optional[Dict]]:
        try:
            # ... file operations
            pass
        except OSError as e:
            self.had_error = True  # Set error flag
            logger.error(f"Error: {e}")
            return False, None  # Still return same tuple shape
    
    # main() returns exit code
    def main(self) -> int:
        for path in self.files:
            self.fix_file(path)  # Errors tracked in self.had_error
        return 1 if self.had_error else 0

# Entry point
if __name__ == "__main__":
    fixer = MarkdownLinkFixer(...)
    sys.exit(fixer.main())
```

### Error Tracking Sites

For each main() function, identify all error sites where operations can fail:

1. **File read failures**: `OSError` from `_read_file()` → set `self.had_error = True`
2. **File write failures**: `OSError` from `_write_file()` → set `self.had_error = True`
3. **Missing file path**: Path validation failures → set `self.had_error = True`
4. **Processing errors**: Any recoverable failures that should not halt execution → set `self.had_error = True`

### Exit Code Return Convention

```python
# Consistent exit code computation across all main() functions
return 1 if self.had_error else 0
```

This signals:
- Exit code 0: All files processed successfully (or no errors encountered)
- Exit code 1: At least one file processing error occurred

### Test Compatibility

**Zero test modifications required.** Existing tests that unpack tuples continue to work:

```python
# Before and after — same contract
success, data = fixer.fix_file("path/to/file.md")
assert success == True or success == False
```

The instance state (`self.had_error`) does not interfere with tuple unpacking or existing assertions.

## Verified On

| Project | Context | PR |
|---------|---------|-----|
| ProjectHephaestus | issue #632: console-scripts exit-code discipline (3 main functions) | #653 |

### CI Verification

- **All 119 unit tests pass** (tests/unit suite)
- **Linting passes** (ruff check)
- **Formatting passes** (ruff format)
- **Type checking passes** (mypy)
- **No test breakage** despite significant changes to error handling
- **All commits cryptographically signed** (git commit -S)
- **PR auto-merge enabled** via CI (squash merge policy)
