---
name: ci-zero-discovery-guard
description: 'Fix silent CI false-passes caused by zero test files discovered. Use
  when: (1) just test-group exits 0 on empty glob matches, (2) a CI matrix entry uses
  parent-path + subdirectory glob patterns, (3) splitting merged CI matrix entries
  to prevent undetected directory renames.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# CI Zero-Discovery Guard

Prevent silent CI false-passes when test file discovery returns zero results in `just test-group`.

## Overview

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-03-07 | Fix #3356: merged `Autograd & Benchmarking` CI entry silently passes with 0 tests if subdirectory is renamed | Two-part fix: exit guard in justfile + split CI matrix entry |

## When to Use

- `just test-group` exits 0 even though no test files were found (silent pass)
- A CI matrix entry uses a parent directory as `path:` with `subdir/test_*.mojo` patterns, instead of pointing directly to the subdirectory
- A directory containing tests is renamed or moved and CI still shows green
- You want to split a merged CI matrix entry back into separate entries for safety

## Verified Workflow

### Step 1: Add zero-discovery guard to `just test-group`

In `justfile`, find the empty-file check in the `test-group` recipe and change it from silent exit 0 to a loud exit 1:

```bash
# BEFORE (silent false-pass):
if [ -z "$test_files" ]; then
    echo "⚠️  No test files found"
    exit 0
fi

# AFTER (loud failure):
if [ -z "$test_files" ]; then
    echo "❌ ERROR: No test files found in {{path}} matching {{pattern}}"
    echo "   This usually means the directory is empty or was renamed."
    echo "   Fix: update the test group path/pattern in comprehensive-tests.yml"
    exit 1
fi
```

### Step 2: Split merged CI matrix entry into separate entries

In `.github/workflows/comprehensive-tests.yml`, replace any merged entry that uses a parent path with individual entries per subdirectory:

```yaml
# BEFORE (merged parent-path — silent false-pass risk):
- name: "Autograd & Benchmarking"
  path: "tests/shared"
  pattern: "autograd/test_*.mojo benchmarking/test_*.mojo"

# AFTER (separate entries — each fails loudly if empty):
# Kept as separate entries (not merged under tests/shared parent path)
# to avoid silent pass-with-0-tests if a subdirectory is empty/renamed.
# See: https://github.com/homericintelligence/projectodyssey/issues/3356
- name: "Autograd"
  path: "tests/shared/autograd"
  pattern: "test_*.mojo"
- name: "Benchmarking"
  path: "tests/shared/benchmarking"
  pattern: "test_*.mojo"
```

### Step 3: Verify `continue-on-error` references still match

If the workflow has a `continue-on-error` condition referencing a test group by name, ensure it still matches after a rename:

```yaml
# This already correctly references "Benchmarking" by name — no change needed
continue-on-error: ${{ matrix.test-group.name == 'Integration Tests' || matrix.test-group.name == 'Core Tensors' || matrix.test-group.name == 'Benchmarking' }}
```

### Step 4: Verify locally

```bash
# Should find files and pass:
just test-group tests/shared/autograd "test_*.mojo"
just test-group tests/shared/benchmarking "test_*.mojo"

# Should fail with error message:
just test-group tests/shared/nonexistent "test_*.mojo"
# Expected: exit 1, prints "❌ ERROR: No test files found..."
```

### Step 5: Run pre-commit and push

```bash
just pre-commit-all
git add justfile .github/workflows/comprehensive-tests.yml
git commit -m "fix(ci): split merged test group and add zero-discovery guard"
gh pr create --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| No attempts failed | Both fixes were applied directly based on issue plan | N/A | Reading the issue comments/plan first gives all necessary context |
| Checked if `continue-on-error` needed updating | Searched for `Benchmarking` reference in workflow | The existing condition already referenced `'Benchmarking'` by name, which matches the new standalone entry | Always verify downstream references when renaming matrix entries |

## Results & Parameters

**Root cause**: `just test-group` used `exit 0` when the glob expanded to no files. A CI matrix entry with `path: tests/shared` and `pattern: autograd/test_*.mojo` would silently pass if `tests/shared/autograd/` was empty or renamed.

**Fix summary**:

- `justfile`: `exit 0` → `exit 1` with descriptive error on zero test discovery
- `comprehensive-tests.yml`: Split `"Autograd & Benchmarking"` (parent path) into `"Autograd"` + `"Benchmarking"` (specific paths)

**Pattern to watch for**: Any CI matrix entry where `path:` is a parent directory and `pattern:` contains `/` (subdirectory traversal). These are candidates for silent false-passes.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3356, PR #3996 | [notes.md](../../references/notes.md) |
