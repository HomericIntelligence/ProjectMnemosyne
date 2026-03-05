---
name: consolidate-ci-matrix
description: "Consolidate GitHub Actions matrix test groups to reduce job overhead. Use when: (1) CI matrix has >20 groups with ~30-60s startup cost each, (2) grouping related tests that rarely fail independently, (3) reducing CI summary noise while preserving failure signal."
category: ci-cd
date: 2026-03-05
user-invocable: false
---

# Consolidate CI Test Matrix

Reduce GitHub Actions job count by merging related test groups without losing coverage or failure signal.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-03-05 | Reduce 31-group CI matrix to ~15 for ProjectOdyssey | 31 → 16 groups; all tests covered; validate_test_coverage.py passes |

## When to Use

- (1) CI matrix has >20 groups causing excessive startup overhead (each job = ~30-60s overhead)
- (2) CI summary is cluttered with fine-grained groups that rarely fail independently
- (3) Related test directories (e.g. Core Activations + Core DTypes) can share a runner
- (4) Redundant matrix entries exist (same files covered by multiple patterns)

## Verified Workflow

1. **Read the full matrix** in `.github/workflows/comprehensive-tests.yml` (or equivalent)
2. **Identify consolidation candidates**:
   - Groups with overlapping paths (e.g. `tests/shared/data/formats` already covered by `tests/shared/data`)
   - Groups that test the same subsystem and rarely fail separately
   - Tiny groups (1-3 test files) that can be appended to a related group's pattern
3. **Keep separate** any group that:
   - Frequently fails independently (e.g. gradient math, integration tests)
   - Has different `path:` root (e.g. `benchmarks/` vs `tests/`)
   - Has `continue-on-error: true` (already a special case)
4. **Merge patterns** by combining space-separated file lists in the `pattern:` field
5. **Remove duplicate entries** — groups whose files are already matched by a broader pattern
6. **Run validate_test_coverage.py** to confirm no tests were dropped:

   ```bash
   python scripts/validate_test_coverage.py
   # Exit 0 = all test files covered
   ```

7. **Commit and PR**: No Mojo changes needed — YAML-only diff

## Key Decisions

### What to merge

| Merge candidates | Rationale |
|-----------------|-----------|
| Core Activations + Core DTypes | Different feature areas but same `path:`, rarely fail together |
| Core Initializers + Core NN Modules | Same subsystem (layer construction) |
| Core Elementwise + Core ExTensor | Both test tensor operation primitives |
| Shared Infra + Testing Fixtures + Helpers | All support test infrastructure, not core logic |
| Top-Level + Debug + Tooling + Fuzz | Low-frequency failures, heterogeneous but all under `tests/` |

### What NOT to merge

| Keep separate | Reason |
|--------------|--------|
| Core Gradient | Numerical gradient math fails independently; clear signal needed |
| Integration Tests | Already `continue-on-error: true`; segfault-prone |
| Models | Primary PR-blocking suite; important standalone signal |
| Data | Already uses subdirectory patterns — don't merge into others |
| Benchmark Framework | Different root path (`benchmarks/`) than `tests/` |

### Redundant entries to remove

The "Data" group pattern `datasets/test_*.mojo samplers/test_*.mojo ...` already covers
all data subdirectory tests. Remove separate "Data Formats", "Data Datasets", "Data Loaders",
"Data Transforms", "Data Samplers" entries entirely.

## Results & Parameters

### Before/After

| Metric | Before | After |
|--------|--------|-------|
| Matrix groups | 31 | 16 |
| Separate non-blocking jobs | 3 | 3 (unchanged) |
| Test files covered | 100% | 100% |
| Startup overhead saved | — | ~15 × 45s = ~11min saved |

### Pattern for merging two groups

```yaml
# Before (2 jobs):
- name: "Core Activations"
  path: "tests/shared/core"
  pattern: "test_activations.mojo test_activation_funcs.mojo"
- name: "Core DTypes"
  path: "tests/shared/core"
  pattern: "test_unsigned.mojo test_dtype_dispatch.mojo"

# After (1 job):
- name: "Core Activations & Types"
  path: "tests/shared/core"
  pattern: "test_activations.mojo test_activation_funcs.mojo test_unsigned.mojo test_dtype_dispatch.mojo"
```

### Pattern for subdirectory consolidation

```yaml
# Before (redundant — formats already covered by parent):
- name: "Data"
  path: "tests/shared/data"
  pattern: "test_*.mojo datasets/test_*.mojo formats/test_*.mojo loaders/test_*.mojo"
- name: "Data Formats"  # REDUNDANT
  path: "tests/shared/data/formats"
  pattern: "test_*.mojo"

# After (remove "Data Formats" entry entirely):
- name: "Data"
  path: "tests/shared/data"
  pattern: "test_*.mojo datasets/test_*.mojo formats/test_*.mojo loaders/test_*.mojo"
```

### Validation command

```bash
python scripts/validate_test_coverage.py
# Script parses YAML matrix and checks every test_*.mojo file is covered
# Exit 0 = success; exit 1 = uncovered tests found
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Merging groups with different `path:` roots | Combined `benchmarks/` and `tests/shared/benchmarking/` into one entry | `just test-group` uses a single `path` prefix; can't glob across two roots | Keep separate matrix entries when root paths differ |
| Removing all data sub-groups | Deleted Data Formats/Loaders/etc. without checking "Data" group coverage first | Would have dropped tests if "Data" group didn't include subdirectory patterns | Always verify parent group patterns cover subdirs before removing child entries |
| Setting `path: "tests"` for Autograd tests | Used `tests` as path with `autograd/test_*.mojo` pattern | Correct approach (glob works), but confusing — easier to use specific path | Use specific path when single-subsystem; use parent path only when grouping multiple subsystems |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3156, PR #3354 | Mojo test suite, `just test-group` runner, `validate_test_coverage.py` gate |

## References

- See `validate-workflow` skill for general workflow validation
- See `github-actions-mojo` skill for Mojo-specific CI setup
- ProjectOdyssey `scripts/validate_test_coverage.py` — Python script that parses YAML matrix and checks coverage
