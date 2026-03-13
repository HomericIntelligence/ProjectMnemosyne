# Skill: CI Matrix continue-on-error Pattern

| Field | Value |
|-------|-------|
| Date | 2026-03-12 |
| Category | ci-cd |
| Outcome | Success |
| Project | ProjectOdyssey |

## Overview

When GitHub Actions matrix jobs need `continue-on-error` for specific entries (e.g., flaky JIT tests), use a matrix-level boolean field rather than hardcoding group names in the step. This avoids merge conflicts and keeps the workflow DRY.

## When to Use

- GitHub Actions workflow has a matrix strategy with some jobs that should be non-blocking
- Resolving merge conflicts between branches that modified `continue-on-error` logic differently
- Adding new test groups that may be flaky (JIT crashes, heap corruption, etc.)

## Verified Workflow

### Pattern: Matrix-level continue-on-error field

Add `continue-on-error: true` as a field on each matrix entry that should be non-blocking:

```yaml
strategy:
  matrix:
    test-group:
      - name: "Core Tensors"
        path: "tests/shared/core"
        pattern: "test_tensors*.mojo"
        # No continue-on-error field = blocking (defaults to false)

      - name: "Models"
        path: "tests/models"
        pattern: "test_*.mojo"
        continue-on-error: true  # Non-blocking due to JIT crashes
```

Then reference it in steps:

```yaml
steps:
  - name: Run tests
    continue-on-error: ${{ matrix.test-group.continue-on-error == true }}
    run: just test-group "${{ matrix.test-group.path }}" "${{ matrix.test-group.pattern }}"
```

### Why this is better than hardcoding names

The anti-pattern hardcodes group names in the step:

```yaml
# BAD - causes merge conflicts, hard to maintain
continue-on-error: ${{ matrix.test-group.name == 'Models' || matrix.test-group.name == 'Shared Infra' }}
```

Problems with hardcoded names:

1. Adding a new non-blocking group requires editing the step AND the matrix entry
2. Merge conflicts when two branches add different groups to the condition
3. The `||` chain grows unbounded and becomes unreadable

### Conflict resolution preference

When rebasing produces a conflict between these two approaches, **always keep the matrix-field approach** (the one using `matrix.test-group.continue-on-error == true`).

## Failed Attempts

### Hardcoded group name matching in continue-on-error

- **What happened**: A branch added `|| matrix.test-group.name == 'Models' || matrix.test-group.name == 'Shared Infra & Testing'` to the step-level `continue-on-error`
- **Why it failed**: Conflicted with main which had already migrated to the matrix-field pattern
- **Fix**: Resolved by keeping main's matrix-field approach, since the relevant matrix entries already had `continue-on-error: true` set

## Parameters

- `continue-on-error: true` on matrix entry = non-blocking job
- `== true` comparison required (not just `${{ matrix.test-group.continue-on-error }}`) because missing field returns empty string, not `false`
