---
name: split-test-file-adr009
description: "Split a Mojo test file exceeding the ADR-009 fn test_ function limit into multiple smaller files. Use when: (1) a .mojo test file has >10 fn test_ functions causing CI heap corruption, (2) CI shows intermittent libKGENCompilerRTShared.so JIT faults."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | split-test-file-adr009 |
| **Category** | ci-cd |
| **Trigger** | Mojo test file exceeds ADR-009 limit of ≤10 fn test_ functions |
| **Outcome** | File split into N files of ≤8 tests each, CI workflow updated |

## When to Use

- A `.mojo` test file has more than 10 `fn test_` functions
- CI shows intermittent heap corruption: `libKGENCompilerRTShared.so` JIT fault
- ADR-009 compliance audit flags a file
- Non-deterministic CI failures in a test group correlating with test count

## Verified Workflow

1. **Count tests** in the offending file: `grep -c '^fn test_[a-z]' <file>`
2. **Plan split**: divide by logical section groupings (e.g. Core, Training, Data, Utils);
   target ≤8 per file
3. **Create N new files** (e.g. `test_foo_part1.mojo`, `test_foo_part2.mojo`,
   `test_foo_part3.mojo`)
4. **Add ADR-009 header** to each new file:

   ```text
   # ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
   # Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
   # high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
   ```

5. **Distribute tests** preserving all original test functions unchanged
6. **Add a `fn main()`** runner to each new file calling only its own tests
7. **Update CI workflow** pattern string to reference new filenames (remove old, add new)
8. **Delete original file**
9. **Run pre-commit hooks** and verify `validate_test_coverage.py` if present
10. **Commit, push, create PR**

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Grep with file_path param | Used `file_path` parameter in Grep tool | Grep tool uses `path` not `file_path` | Always use `path` parameter for Grep tool |
| Background commit without TaskOutput | Ran git commit as background task without capturing output | Output not immediately visible | Use TaskOutput tool to retrieve background task results |
| Using `grep "^fn test_"` to count tests | Counted comment lines matching the pattern | ADR-009 header comment can contain `fn test_` text | Use `^fn test_[a-z]` pattern instead |

## Results & Parameters

**ADR-009 limits**:

- Hard limit: ≤10 `fn test_` functions per file (heap corruption threshold)
- Recommended target: ≤8 (provides buffer)

**Split formula**: `ceil(total_tests / 8)` = number of files needed

**CI workflow update pattern** (space-separated filename list in pattern string):

```yaml
# Before:
pattern: "test_foo.mojo other_tests.mojo"
# After:
pattern: "test_foo_part1.mojo test_foo_part2.mojo test_foo_part3.mojo other_tests.mojo"
```

**Each split file structure**:

```text
"""
<module docstring with ADR-009 comment>
"""
from testing import assert_true

# Section tests (≤8 fn test_ functions)
fn test_xxx() raises: ...

fn main() raises:
    """Run this file's tests only."""
    test_xxx()
    ...
```

**Note**: If the CI glob already covers new files via pattern (e.g. `test_*.mojo`), no
workflow update is needed. Only update the workflow when the pattern lists explicit filenames.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3427, PR #4201 | [notes.md](../../references/notes.md) |
