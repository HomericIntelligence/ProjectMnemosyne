---
name: deduplicate-ci-test-groups
description: "Fix overlapping test group patterns in GitHub Actions matrix workflows. Use when: CI test files run in multiple jobs due to wildcard overlap, or a parent group wildcard subsumes dedicated child groups."
category: ci-cd
date: 2026-03-08
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Category** | ci-cd |
| **Trigger** | CI test groups with overlapping wildcard patterns |
| **Problem** | Tests run in multiple jobs → doubled load, heap corruption risk |
| **Solution** | Enumerate files explicitly; remove patterns that duplicate sub-groups |

## When to Use

- A parent CI test group uses subdirectory wildcards like `datasets/test_*.mojo` while dedicated sub-groups already cover those paths
- A test group pattern matches files that are excluded from per-PR CI (e.g., training tests requiring dataset downloads)
- `validate_test_coverage.py` exclusion list is out of sync with CI job patterns
- CI failure rate is high and rotates randomly — consistent with load-dependent heap corruption from doubled test execution

## Verified Workflow

1. **Read the issue / understand the overlap**: identify which groups have patterns that subsume other groups' patterns
2. **Enumerate actual files on disk** before editing the workflow:

   ```bash
   find tests/shared/data -name "*.mojo" | sort
   ```

3. **Replace wildcard patterns with explicit file lists** using YAML `>-` block scalar:

   ```yaml
   pattern: >-
     test_cache.mojo test_constants.mojo
     datasets/test_base_dataset.mojo datasets/test_cifar10.mojo
   ```

4. **Remove patterns that duplicate excluded tests** (e.g., `training/test_*.mojo` when all training tests are in the exclusion list)
5. **Update the exclusion list** in `validate_test_coverage.py` to add any new files not previously listed
6. **Verify coverage** — both uncovered files AND duplicates:

   ```bash
   python scripts/validate_test_coverage.py
   ```

   ```python
   # Check for duplicate coverage across all groups
   python3 -c "
   import sys; sys.path.insert(0, 'scripts')
   from validate_test_coverage import parse_ci_matrix, expand_pattern
   from pathlib import Path
   from collections import defaultdict
   root = Path('.')
   workflow = root / '.github/workflows/comprehensive-tests.yml'
   groups = parse_ci_matrix(workflow)
   file_to_groups = defaultdict(list)
   for group_name, info in groups.items():
       for f in expand_pattern(info['path'], info['pattern'], root):
           file_to_groups[f].append(group_name)
   dupes = {f: gs for f, gs in file_to_groups.items() if len(gs) > 1}
   print(f'Duplicates: {len(dupes)}')
   for f, gs in sorted(dupes.items()):
       print(f'  {f}: {gs}')
   "
   ```

7. **Run pre-commit hooks** to verify YAML validity and coverage validation hook

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | No failed attempts in this session | — | Read actual filesystem before writing explicit lists to avoid missing files |

## Results & Parameters

**Before (overlapping)**:

```yaml
- name: "Data"
  path: "tests/shared/data"
  pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo transforms/test_*.mojo loaders/test_*.mojo formats/test_*.mojo"
```

**After (explicit, no overlap)**:

```yaml
- name: "Data"
  path: "tests/shared/data"
  pattern: >-
    test_cache.mojo test_constants.mojo test_dataset_with_transform.mojo
    test_datasets.mojo test_loaders.mojo test_prefetch.mojo
    test_random_transform_base.mojo test_transforms.mojo
    datasets/test_base_dataset.mojo datasets/test_cifar10.mojo
    datasets/test_emnist.mojo datasets/test_file_dataset.mojo
    datasets/test_tensor_dataset.mojo
    formats/test_cifar_loader.mojo
    loaders/test_base_loader.mojo loaders/test_batch_loader.mojo
    loaders/test_parallel_loader.mojo
    samplers/test_random.mojo samplers/test_sequential.mojo
    samplers/test_weighted.mojo
    transforms/test_augmentations.mojo transforms/test_generic_transforms.mojo
    transforms/test_image_transforms.mojo transforms/test_pipeline.mojo
    transforms/test_tensor_transforms.mojo transforms/test_text_augmentations.mojo
```

**Key rule**: When a CI group has dedicated sub-groups (e.g., "Data Datasets", "Data Loaders"), the parent group should only list top-level files — never subdirectory wildcards.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3640, PR #4453 | Mojo test suite, `just test-group` runner, `validate_test_coverage.py` gate |
