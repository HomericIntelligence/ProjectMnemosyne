---
name: console-scripts-exit-code-discipline
description: "Enforce exit-code discipline for Python console-script main() functions using instance state for error tracking. Use when: (1) a console-script main() exits 0 unconditionally despite errors, (2) updating error signaling for methods with existing tuple-return callers, (3) preventing pre-commit pipelines from masking failures."
category: architecture
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [python, console-scripts, exit-codes, error-tracking, tuple-contracts, architecture]
---

# Console Scripts Exit-Code Discipline

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Enforce proper exit-code signaling in Python console-script main() functions without breaking tuple-return contracts on existing callsites |
| **Outcome** | Successfully applied pattern to 3 console scripts; all 119 unit tests pass; pre-commit pipelines now catch real failures |
| **Verification** | verified-ci (all 119 tests pass in CI; commits signed and PR auto-merged) |

## When to Use

- A console-script `main()` calls `sys.exit(0)` unconditionally, masking read/write errors
- Updating error signaling for methods that existing callers unpack as tuples (changing tuple shape breaks all callsites)
- Pre-commit pipelines are failing silently because scripts exit 0 despite errors
- A utility class has multiple public methods returning tuples, and you need to track cumulative errors without changing signatures
- Normalizing exit-code behavior across multiple console scripts in a package

## Verified Workflow

### Quick Reference

**The pattern**: When a class's public methods return tuples that callers unpack, use instance state (`self.had_error: bool`) to track failures instead of modifying the tuple shape.

```python
# In __init__:
def __init__(self):
    self.had_error = False

# At error sites (catch exceptions, set flag):
except OSError as e:
    self.had_error = True
    # Continue processing, don't raise

# In main(), compute exit code from flag and return it:
def main(self) -> int:
    # ... do work that may set self.had_error = True ...
    exit_code = 1 if self.had_error else 0
    return exit_code

# In the entrypoint (console_script):
if __name__ == "__main__":
    sys.exit(main())
```

### Detailed Steps

**Step 1: Identify methods with tuple-return callers**

Search for existing callers that unpack the return value as a tuple:

```bash
# Find the method signature (e.g., fix_file())
grep -n "def fix_file" hephaestus/markdown/fixer.py

# Find all unpacking callsites
grep -rn "fix_file.*=" tests/ | grep -v "==" | head -5
# Look for patterns like: (result, count) = obj.fix_file(...)
```

**Step 2: Add instance state in `__init__`**

```python
class MyProcessor:
    def __init__(self):
        # ... other init ...
        self.had_error: bool = False
```

**Step 3: Set the flag at every error site**

Identify all places where the method should signal failure:

```python
def process_path(self, path: str):
    try:
        with open(path) as f:
            # ... process ...
    except OSError as e:
        self.had_error = True
        logger.error(f"Failed to read {path}: {e}")
        # DO NOT raise — let main() decide exit code
        return  # or return existing tuple
```

**Step 4: Compute exit code in main() and return it**

Change `main()` from `-> None` to `-> int`:

```python
def main(self) -> int:
    # ... do work; errors set self.had_error = True ...
    exit_code = 1 if self.had_error else 0
    return exit_code
```

**Step 5: Update the entrypoint to sys.exit(main())**

Change from:

```python
if __name__ == "__main__":
    main()
    sys.exit(0)  # unconditional — masks errors
```

To:

```python
if __name__ == "__main__":
    sys.exit(main())
```

And update `[project.scripts]` in pyproject.toml:

```toml
[project.scripts]
my-tool = "my_module:main"
```

**Step 6: Test the exit codes**

Write integration tests that verify exit behavior:

```python
def test_main_exits_zero_on_success(tmp_path):
    """Verify exit code 0 for successful processing."""
    processor = Processor()
    exit_code = processor.main()
    assert exit_code == 0

def test_main_exits_nonzero_on_error(tmp_path):
    """Verify exit code 1 when errors occur."""
    processor = Processor()
    # Create condition that triggers error
    exit_code = processor.main()
    assert exit_code == 1
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Change tuple shape to include error flag | Modify `fix_file()` to return 3-tuple: `(was_modified: bool, num_errors: int, had_error: bool)` | Breaks 8+ existing test callsites that unpack 2-tuples; forces edits to all callers (pure churn) | Don't modify public method signatures to track internal state; use instance attributes instead |
| Use exception chain for error tracking | Catch errors, append to list, re-raise at end | Makes main() harder to invoke from tests; forces try/except at every callsite; error propagation obscures which phase failed | Use instance flags for cumulative error tracking; main() consumes and decides exit code |
| Create a new wrapper class just for exit code | Separate `Processor` (returns tuples) from `ProcessorCLI` (returns int) | Doubles the class count; duplicates all process methods; maintenance burden | Instance state is simpler; one class, two calling contexts (test unpacks tuples, main() unpacks exit code) |
| Use sentinel return value instead of exception | Return `None` on error instead of raising | Silent failure; callers don't know if processing succeeded; no exception traceback for debugging | Use exception + instance flag combination: catch at error site, set flag, log + continue |
| Store exit code only in main(), not in instance state | Compute `had_error` locally at the end of main() | Can't detect errors that occur outside main() call (e.g., __init__); if main() is called multiple times, state is lost | Instance flag persists across the object lifecycle; main() merely consumes and returns it |
| Restore sys.exit(0) in entrypoint after setting return value | Return exit code from main() but also call sys.exit(0) | Unconditional exit masks the computed code; exit code is never visible to parent process | Return from main(), let the entrypoint `sys.exit()` consume it; one decision point only |

## Results & Parameters

### Files modified (ProjectHephaestus issue #632)

**1. hephaestus/markdown/fixer.py**

```python
# Line 43: add instance state
class Fixer:
    def __init__(self):
        self.had_error: bool = False  # ← new

# Lines 59, 99, 437: set flag at error sites
except OSError:
    self.had_error = True  # ← new at each site
    # continue processing

# Lines 492–516: compute exit code
def main(self) -> int:
    # ... do processing (may set self.had_error = True) ...
    exit_code = 1 if self.had_error else 0
    return exit_code  # ← return instead of sys.exit(0)
```

**2. hephaestus/system/info.py**

```python
# Changed signature
def main(self) -> int:  # was -> None
    # ... do work ...
    return 0  # was implicit None
```

**3. hephaestus/datasets/downloader.py**

```python
# Changed exit behavior
return exit_code  # was sys.exit(exit_code)
```

**4. All three: normalized entrypoint**

```python
if __name__ == "__main__":
    sys.exit(main())  # was main(); sys.exit(0)
```

### Test coverage

- 119 unit tests pass (all 3 modules tested)
- No changes to existing test callsites (tuple contracts preserved)
- Integration tests verify exit codes: `test_main_exits_zero_on_success()`, `test_main_exits_nonzero_on_*`

### Exit code outcomes

| Scenario | Before | After |
|----------|--------|-------|
| Read OSError on input | exit 0 | exit 1 |
| Write OSError on output | exit 0 | exit 1 |
| All processing succeeds | exit 0 | exit 0 |
| Multiple errors occur | exit 0 | exit 1 (first error sets flag) |

### Key architectural insight

**Instance state vs. tuple shape**: Instance attributes (`self.had_error`) capture *cumulative state* across multiple method calls without breaking *public contracts* (tuple shapes callers unpack). This pattern generalizes to any class with:
- Public methods returning fixed-shape tuples
- Callers that unpack those tuples
- Need to signal cumulative success/failure

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #632 — PR #650 | Enforced exit-code discipline on 3 console-script main() functions. Modified fixer.py (instance state), info.py (signature change), downloader.py (return instead of sys.exit). All 119 tests pass; CI green; PR auto-merged. |
