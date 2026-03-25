---
name: ci-group-split-glob-patterns
description: "Split oversized CI test groups using glob patterns (not explicit filenames) for maintainability. Use when: (1) a CI matrix group has 30+ files causing long jobs and poor failure isolation, (2) splitting per ADR-009 but wanting auto-discovery of future split files."
category: ci-cd
date: 2026-03-25
version: 1.0.0
user-invocable: false
verification: verified-precommit
supersedes:
  - adr009-ci-group-split.md
tags:
  - ci-cd
  - adr-009
  - test-splitting
  - glob-patterns
  - comprehensive-tests
---

# Split CI Test Groups Using Glob Patterns

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Split a 91-file CI test group into 4 domain-focused sub-groups using glob patterns |
| **Outcome** | Successful: validate_test_coverage.py exits 0, pre-commit passes, PR created |
| **Verification** | verified-precommit |

Supersedes: `adr009-ci-group-split.md` — that skill recommended explicit filenames for each
sub-group, but glob patterns are shorter, auto-include future split files, and are already
used by existing groups (Core Tensors, Core Loss, Core Gradient). The justfile `_test-group-inner`
recipe (line ~588) explicitly supports glob expansion.

## When to Use

- A CI matrix group has 30+ test files and needs splitting per ADR-009
- You want sub-groups that auto-discover new `_partN.mojo` files without manual updates
- The test files in the group naturally cluster by filename prefix (e.g., `test_extensor_*`, `test_conv*`)
- The existing group already uses glob patterns in its `pattern:` field

**Anti-trigger**: If the group spans multiple subdirectories (different `path:` values needed),
use `split-ci-data-subgroups.md` instead.

## Verified Workflow

> **Note:** Verified at pre-commit level (formatting, linting, coverage validation). CI validation pending.

### Quick Reference

```bash
# 1. Count actual files per glob pattern
TEST_PATH="tests/shared/core"
for p in "test_extensor_*.mojo" "test_conv*.mojo"; do
  echo "$p: $(ls $TEST_PATH/$p 2>/dev/null | wc -l) files"
done

# 2. After editing, validate
python3 scripts/validate_test_coverage.py

# 3. Check for stale patterns
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from validate_test_coverage import parse_ci_matrix, check_stale_patterns
from pathlib import Path
root = Path('.')
groups = parse_ci_matrix(root / '.github/workflows/comprehensive-tests.yml')
stale = check_stale_patterns(groups, root)
print('Stale:' if stale else 'No stale patterns')
for s in stale: print(f'  {s}')
"
```

### Detailed Steps

1. **Expand current group to count actual files** — glob patterns hide the true file count.
   Use a shell loop to expand each pattern and count:

   ```bash
   TEST_PATH="tests/shared/core"
   PATTERNS="test_utilities.mojo test_utility*.mojo test_extensor_*.mojo ..."
   for p in $PATTERNS; do
     if [[ "$p" == *"*"* ]]; then
       for f in $TEST_PATH/$p; do [ -f "$f" ] && basename "$f"; done
     else
       [ -f "$TEST_PATH/$p" ] && echo "$p"
     fi
   done | sort -u | wc -l
   ```

2. **Design sub-groups by functional domain** — group by filename prefix clusters.
   Target ≤25-30 files per group for reasonable CI wall-clock times.
   Use glob patterns (e.g., `test_extensor_*.mojo`) not explicit filenames:

   ```yaml
   - name: "Core Utilities A"
     path: "tests/shared/core"
     pattern: "test_utilities.mojo test_utility*.mojo test_utils*.mojo test_validation*.mojo ..."
   - name: "Core Utilities B"
     path: "tests/shared/core"
     pattern: "test_extensor_*.mojo"
   ```

3. **Use the Edit tool directly** — the security hook on workflow files is a warning, not
   a blocker. It reminds about command injection risks but does not prevent the edit.
   The prior skill's workaround (Python str.replace) is unnecessary.

4. **Remove stale patterns** — check if any patterns in the old group reference files
   that no longer exist (e.g., `test_inplace_simd.mojo`). Don't carry them forward.

5. **Validate** — run `python3 scripts/validate_test_coverage.py` (must exit 0) and
   verify no stale sub-patterns exist.

6. **Verify file counts per group** — use the `expand_pattern` function from the
   validation script to confirm each group has the expected file count:

   ```python
   import sys; sys.path.insert(0, 'scripts')
   from validate_test_coverage import parse_ci_matrix, expand_pattern
   from pathlib import Path
   root = Path('.')
   groups = parse_ci_matrix(root / '.github/workflows/comprehensive-tests.yml')
   for name in sorted(groups):
       if 'Core Utilities' in name:
           files = expand_pattern(groups[name]['path'], groups[name]['pattern'], root)
           print(f'{name}: {len(files)} files')
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Prior skill: explicit filenames | Listed all 71 files individually across 8 groups (A-H) | Fragile — new `_partN.mojo` files from future ADR-009 splits aren't auto-discovered | Use glob patterns like `test_extensor_*.mojo` to auto-include future splits |
| Prior skill: Python str.replace for workflow edits | Used Python to edit workflow file to avoid Edit tool security hook | Unnecessary — the hook is a warning about command injection, not a blocker for static YAML edits | The Edit tool works fine for workflow files; the hook just prints a reminder |
| Counting patterns instead of files | Assumed 28 patterns meant ~28 files | `test_extensor_*.mojo` alone expanded to 26 files; total was 91 | Always expand globs to count actual files before designing the split |

## Results & Parameters

**Session outcome**: Split `Core Utilities` (91 files) into 4 groups using glob patterns.

| Group | Files | Domain | Pattern |
|-------|-------|--------|---------|
| Core Utilities A | 31 | General utils, validation, bitwise, integration | `test_utilities.mojo test_utility*.mojo test_utils*.mojo test_validation*.mojo test_integration*.mojo test_lazy_expression.mojo test_constants.mojo test_hash.mojo test_setitem_view_part*.mojo test_int_bitwise*.mojo test_uint_bitwise*.mojo test_unsigned*.mojo test_normalize_slice*.mojo test_jit_crash*.mojo` |
| Core Utilities B | 26 | ExTensor operations | `test_extensor_*.mojo` |
| Core Utilities C | 19 | Memory, initializers, module system | `test_memory_pool_part*.mojo test_memory_leaks*.mojo test_initializers_*.mojo test_module.mojo test_sequential.mojo test_composed_op*.mojo test_dropout_part*.mojo` |
| Core Utilities D | 15 | Layer implementations | `test_layers*.mojo test_linear*.mojo test_conv*.mojo test_normalization*.mojo` |

**Validation**: `python3 scripts/validate_test_coverage.py` exits 0, no stale patterns.

**PR**: #5114, auto-merge enabled.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #4116: Split Core Utilities CI group | Pre-commit verified, CI pending |
