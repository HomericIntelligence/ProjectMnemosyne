---
name: mojo-ci-wildcard-pattern-coverage
description: "Determine if CI workflow test patterns need updating after adding/splitting Mojo test files. Use when: adding test_*.mojo files or splitting test files and unsure if CI auto-discovers the new files."
category: ci-cd
date: 2026-03-08
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | After splitting/adding test files, does CI need updating? |
| **Key insight** | Wildcard patterns auto-discover new files; explicit filename patterns do not |
| **Impact** | Prevents unnecessary CI workflow edits on test file splits |
| **Workflow** | `comprehensive-tests.yml` matrix `pattern` field |

## When to Use

1. You split a `test_*.mojo` file into `test_*_part1.mojo`, `test_*_part2.mojo`, etc.
2. You added new test files and need to verify CI will discover them
3. `validate_test_coverage.py` reports uncovered files after a split
4. An issue asks you to "update CI workflow to reference new filenames"

## Verified Workflow

### 1. Identify pattern type in the CI group

In `.github/workflows/comprehensive-tests.yml`, find the relevant test group:

```yaml
- name: "Data"
  path: "tests/shared/data"
  pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo ..."
  continue-on-error: true
```

### 2. Check: wildcard or explicit filenames?

**Wildcard pattern** (contains `*`):
```
test_*.mojo datasets/test_*.mojo transforms/test_*.mojo
```
→ **No CI update needed.** New `test_transforms_part1.mojo` is auto-discovered.

**Explicit filename pattern** (no `*`):
```
test_backward_linear.mojo test_backward_conv_pool.mojo test_backward_losses.mojo
```
→ **CI update required.** Add each new part file explicitly.

### 3. Verify with validate_test_coverage.py

```bash
python3 scripts/validate_test_coverage.py
```

If it reports uncovered files after a split → the pattern is explicit and needs updating.
If it passes → the wildcard pattern covers the new files automatically.

### 4. Example: wildcard group (Data)

Original pattern covers all `test_*.mojo` in `tests/shared/data/`:
```yaml
pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo transforms/test_*.mojo loaders/test_*.mojo formats/test_*.mojo"
```

After splitting `test_transforms.mojo` → `test_transforms_part1.mojo`, etc.:
- `test_transforms_part1.mojo` matches `test_*.mojo` ✅
- No CI change needed ✅

### 5. Example: explicit group (Core Gradient)

```yaml
pattern: "test_backward_linear.mojo test_backward_conv_pool.mojo test_backward_losses.mojo test_gradient_checking_basic.mojo ..."
```

After adding `test_backward_new.mojo`:
- NOT auto-discovered ❌
- Must add `test_backward_new.mojo` to the pattern ✅

### 6. Decision table

| Pattern contains `*`? | Action |
|-----------------------|--------|
| Yes (`test_*.mojo`) | No CI update needed |
| No (explicit names) | Add new filenames to pattern |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Wildcard groups | Data, Integration Tests, Models, Misc Tests, Shared Infra |
| Explicit groups | Core Gradient (split per ADR-009 with explicit names) |
| Coverage validator | `scripts/validate_test_coverage.py` — run before committing |
| Pre-commit hook | `Validate Test Coverage` — catches uncovered files automatically |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Editing Data group pattern | Added explicit part filenames to `test_*.mojo` pattern | Unnecessary — wildcard already matched new files | Check pattern type before editing CI YAML |
| Updating validate_test_coverage.py | Added new part filenames to excluded list | Wrong direction — files should be included, not excluded | validate_test_coverage.py exclusions are for files that should NOT be in CI |
| Assuming all groups need explicit names | Updated every test group after split | Most groups use wildcards and auto-discover | Read the pattern field before assuming work is needed |
