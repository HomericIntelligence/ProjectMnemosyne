---
name: ci-catchall-pattern-timeout-fix
description: "Fix CI test group timeouts caused by catch-all glob patterns matching unintended files. Use when: (1) CI test group exceeds timeout, (2) test_*.mojo pattern matches too many files, (3) tests run in multiple CI groups."
category: ci-cd
date: '2026-03-25'
version: "1.0.0"
user-invocable: false
tags:
  - ci
  - timeout
  - test-patterns
  - comprehensive-tests
---

# CI Catch-All Pattern Timeout Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Fix deterministic CI timeout in Core Activations & Types test group |
| **Outcome** | Successful — replaced catch-all with explicit patterns, 247 files covered with 0 orphans and 0 duplicates |

## When to Use

- A CI test group is timing out when it previously worked
- A test group runs far more tests than expected
- Tests appear to run multiple times across different CI groups
- `validate_test_coverage.py` reports uncovered or duplicate test files
- After splitting test files per ADR-009, the CI pattern needs updating

## Verified Workflow

### Quick Reference

```bash
# 1. Identify the problem — check how many files a pattern matches
ls tests/shared/core/test_*.mojo | wc -l  # catch-all matches ALL files

# 2. List the intended files for the group
ls tests/shared/core/test_activation*.mojo tests/shared/core/test_dtype*.mojo

# 3. Verify coverage with Python
python3 -c "
import os, fnmatch
test_dir = 'tests/shared/core'
files = sorted(f for f in os.listdir(test_dir) if f.startswith('test_') and f.endswith('.mojo'))
patterns = 'test_activation*.mojo test_dtype*.mojo'.split()
matched = [f for f in files if any(fnmatch.fnmatch(f, p) for p in patterns)]
orphans = [f for f in files if not any(fnmatch.fnmatch(f, p) for p in patterns)]
print(f'Matched: {len(matched)}, Orphans: {len(orphans)}')
"

# 4. Run coverage validation
python3 scripts/validate_test_coverage.py
```

### Detailed Steps

1. **Identify the catch-all pattern** — Look in `.github/workflows/comprehensive-tests.yml` for patterns like `test_*.mojo` that match everything in a directory

2. **Count actual vs intended files** — A group named "Core Activations & Types" with `test_*.mojo` matched 250+ files instead of the 17 activation/dtype files it was meant to cover

3. **Check for overlapping groups** — When one group uses `test_*.mojo`, it catches files meant for other groups:
   - `test_gradient_checking_*.mojo` ran in 3 groups simultaneously
   - `test_backward_*.mojo` ran in 2 groups
   - `test_losses_*.mojo` ran in 2 groups

4. **Replace with explicit patterns** — List only the intended files or use targeted wildcards:
   ```yaml
   # BAD: catches everything
   pattern: "test_*.mojo"

   # GOOD: explicit file list
   pattern: "test_activation_funcs_part1.mojo test_activation_funcs_part2.mojo ..."

   # GOOD: targeted wildcards (if no overlap risk)
   pattern: "test_activation*.mojo test_dtype*.mojo"
   ```

5. **Audit for orphaned tests** — After replacing the catch-all, verify ALL test files are covered by exactly one group. Use `fnmatch` to simulate the CI pattern matching.

6. **Run `validate_test_coverage.py`** — This pre-commit hook catches orphaned files

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Catch-all pattern | Used `test_*.mojo` as a convenience to auto-include split files | Matched 250+ files instead of 17, causing 15-min timeout and triple execution of some tests | Never use `test_*.mojo` catch-all in a directory with multiple test groups — always use explicit patterns |
| ADR-009 split without CI update | Split test files into parts but kept the catch-all pattern | The catch-all absorbed the new split files, but also everything else | When splitting files per ADR-009, always update CI patterns to match the new filenames |

## Results & Parameters

### Pattern matching rules

The CI workflow `pattern` field uses **space-separated shell glob patterns** (NOT regex):
- `test_foo*.mojo` matches `test_foo.mojo`, `test_foo_bar.mojo`, `test_foo_part1.mojo`
- `test_backward_conv*.mojo` does NOT match `test_conv_backward.mojo` (prefix must match)
- Patterns are matched with Python `fnmatch.fnmatch()`

### Coverage verification script

```python
import os, fnmatch

test_dir = 'tests/shared/core'
all_files = sorted(f for f in os.listdir(test_dir)
                   if f.startswith('test_') and f.endswith('.mojo'))

groups = {
    'Core Tensors': 'test_tensors*.mojo test_arithmetic*.mojo ...',
    'Core Activations': 'test_activation*.mojo test_dtype*.mojo ...',
    # ... all groups
}

file_groups = {f: [] for f in all_files}
for name, patterns_str in groups.items():
    for f in all_files:
        if any(fnmatch.fnmatch(f, p) for p in patterns_str.split()):
            file_groups[f].append(name)

orphans = [f for f, gs in file_groups.items() if len(gs) == 0]
duplicates = [(f, gs) for f, gs in file_groups.items() if len(gs) > 1]
print(f'Orphans: {len(orphans)}, Duplicates: {len(duplicates)}')
```

### Expected outcome

- Core Activations & Types: ~17 files, completes in 2-3 minutes (was 15+ min timeout)
- Zero orphaned test files across all groups
- Zero duplicate test executions across groups

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | CI comprehensive-tests.yml | [notes](./skills/ci-catchall-pattern-timeout-fix.notes.md) |
