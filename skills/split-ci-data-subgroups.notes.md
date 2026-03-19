# Session Notes: split-ci-data-subgroups

## Session Context

- **Date**: 2026-03-15
- **Issue**: ProjectOdyssey #4458 — "Split 'Data' sub-groups into the matrix instead of one parent group"
- **Branch**: `4458-auto-impl`
- **PR**: #4883

## Problem

The `"Data"` CI matrix entry in `.github/workflows/comprehensive-tests.yml` had grown to enumerate
26 files across 6 subdirectories using space-separated subdirectory patterns:

```yaml
- name: "Data"
  path: "tests/shared/data"
  pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo transforms/test_*.mojo loaders/test_*.mojo formats/test_*.mojo"
  continue-on-error: true
```

This was fragile: any new test file added to a subdirectory was silently missed unless the `pattern`
field was manually updated to include it.

## Solution Applied

Replace with 6 leaf-level entries (Data Core, Data Datasets, Data Loaders, Data Transforms,
Data Samplers, Data Formats), each using `test_*.mojo` wildcard at a specific `path:`.

Key insight: `validate_test_coverage.py` uses a non-recursive glob
(`root_dir.glob(f"{base_path}/{pat}")`), so `path="tests/shared/data"` with `pattern="test_*.mojo"`
matches ONLY top-level files in that directory — not files in subdirectories. Zero overlap guaranteed.

## File Changed

`.github/workflows/comprehensive-tests.yml` (lines 240-248): replaced 1 entry with 6 entries.

## Validation

```bash
python scripts/validate_test_coverage.py
# Exit 0 — all 26+ test files covered
```

## History / Prior Art

- PR #3354 (Issue #3156): The inverse operation — consolidated fine-grained sub-groups INTO the
  parent "Data" entry to reduce CI job overhead. This session reverses that consolidation because
  explicit-list maintenance became a burden.
- The `consolidate-ci-matrix` skill documents the inverse: when to merge groups together.

## Coverage Map (26 files)

| Group | Path | Expected files |
|-------|------|---------------|
| Data Core | tests/shared/data | test_cache_part*.mojo, test_constants.mojo, test_dataset_with_transform.mojo, test_datasets.mojo, test_loaders.mojo, test_prefetch.mojo, test_random_transform_base.mojo, test_transforms.mojo |
| Data Datasets | tests/shared/data/datasets | test_base_dataset.mojo, test_cifar10.mojo, test_emnist.mojo, test_file_dataset.mojo, test_tensor_dataset.mojo |
| Data Loaders | tests/shared/data/loaders | test_base_loader.mojo, test_batch_loader.mojo, test_parallel_loader.mojo |
| Data Transforms | tests/shared/data/transforms | test_augmentations.mojo, test_generic_transforms.mojo, test_image_transforms.mojo, test_pipeline.mojo, test_tensor_transforms.mojo, test_text_augmentations.mojo |
| Data Samplers | tests/shared/data/samplers | test_random.mojo, test_sequential.mojo, test_weighted.mojo |
| Data Formats | tests/shared/data/formats | test_cifar_loader.mojo |