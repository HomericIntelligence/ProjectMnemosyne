---
name: adr009-explicit-pattern-ci-update
description: 'Workflow for ADR-009 test splits where CI uses explicit filename lists
  (not glob). Use when: CI group lists filenames explicitly, new split files won''t
  be auto-discovered, Core Tensors or similar fixed-pattern groups fail with heap
  corruption.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Category | ci-cd |
| Complexity | Low |
| Risk | Low |
| Time | ~20 minutes |

Extends the `adr009-test-file-splitting` skill for the case where the CI workflow group uses an
**explicit filename list** (not a `test_*.mojo` glob). In this case, creating split files is not
sufficient — the workflow YAML must also be updated to reference the new filenames and remove the
original.

## When to Use

- A Mojo test file in a CI group with an **explicit pattern** (e.g., `"test_a.mojo test_b.mojo"`) exceeds ADR-009 limit
- Creating new `test_*_part1.mojo` files but they don't appear in CI runs
- CI group like `Core Tensors` uses `pattern: "file1.mojo file2.mojo ..."` (space-separated list)
- After splitting, the original filename is still in the workflow and new ones are missing

## Verified Workflow

### 1. Check the CI pattern type

Before splitting, check whether the CI group uses a glob or explicit list:

```yaml
# Glob pattern — new files auto-discovered (no workflow update needed)
pattern: "test_*.mojo"

# Explicit list — MUST update workflow after splitting
pattern: "test_tensors.mojo test_arithmetic.mojo test_reduction_forward.mojo ..."
```

### 2. Split the test file per ADR-009

Follow `adr009-test-file-splitting` for the split itself:

- Target ≤8 `fn test_` functions per file (hard limit: ≤10)
- Add ADR-009 header comment to each new file
- Preserve all test function bodies exactly
- Delete the original file

### 3. Update the CI workflow

Replace the original filename with the split filenames in the `pattern` field:

```yaml
# Before
pattern: "... test_reduction_forward.mojo ..."

# After
pattern: "... test_reduction_forward_part1.mojo test_reduction_forward_part2.mojo test_reduction_forward_part3.mojo test_reduction_forward_part4.mojo ..."
```

### 4. Verify counts

```bash
for f in tests/shared/core/test_reduction_forward_part*.mojo; do
  echo "$f: $(grep -c "^fn test_" $f) tests"
done
```

### 5. Commit — all hooks must pass

Pre-commit hooks validate: mojo format, YAML check, test coverage validation.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assuming glob auto-discovery | Expected new `part*.mojo` files to appear in CI without workflow changes | CI group used explicit space-separated filename list, not a glob | Always check the `pattern:` field type before splitting |
| Keeping original file | Left `test_reduction_forward.mojo` alongside the part files | Would result in 30+30 duplicate test runs and still exceed ADR-009 | Delete the original file after splitting |

## Results & Parameters

**ADR-009 limits:**

- Hard limit: ≤10 `fn test_` per file
- Target: ≤8 per file (safety buffer)

**Naming convention for splits:**

```text
test_<original_name>_part1.mojo
test_<original_name>_part2.mojo
...
```

**Grep count (avoiding header comment false positives):**

```bash
grep -c "^fn test_" <file>.mojo
```

**Workflow pattern update:**

```yaml
# Replace single filename with space-separated list of parts
pattern: "... test_X_part1.mojo test_X_part2.mojo test_X_part3.mojo test_X_part4.mojo ..."
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3415, PR #4159 | [notes.md](../../references/notes.md) |

**Related:** `adr009-test-file-splitting`, `docs/adr/ADR-009-heap-corruption-workaround.md`, issue #2942
