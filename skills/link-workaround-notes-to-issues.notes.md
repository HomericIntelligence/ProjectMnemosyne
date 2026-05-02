# Session Notes: link-workaround-notes-to-issues

## Session Context

- **Date**: 2026-03-05
- **Repo**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3073-auto-impl
- **Issue**: #3073 [Cleanup] Track temporary workaround NOTEs
- **PR**: #3286

## Objective

Issue #3073 required all temporary workaround `# NOTE:` comments in `.mojo` files to be linked
to tracking GitHub issues so they could be found, prioritized, and eventually resolved.

## Discovery Command

```bash
grep -rn "# NOTE:" --include="*.mojo" .
```

Found ~25 NOTEs total. Filtered to temporary workarounds (not informational notes).

## NOTE Inventory

| File | Line | Status | Action |
| ------ | ------ | -------- | -------- |
| shared/training/trainer_interface.mojo | 391 | Unlinked | Updated to NOTE(#3076) |
| examples/lenet-emnist/run_infer.mojo | 340 | Unlinked | Updated to NOTE(#3087) |
| shared/utils/file_io.mojo | 671 | Unlinked | Updated to NOTE(#3071) |
| shared/training/precision_config.mojo | 225 | Unlinked | Updated to NOTE(#3088) |
| tests/shared/core/test_conv.mojo | 602 | Unlinked | Updated to NOTE(#3085) |
| examples/googlenet-cifar10/train.mojo | 97 | Unlinked | Updated to NOTE(#3084) |
| shared/training/__init__.mojo | 410 | Already NOTE(#3092) | Skipped |
| shared/training/mixed_precision.mojo | 283 | Already refs #3015 in body | Skipped |
| shared/training/mixed_precision.mojo | 353 | Already refs #3015 in body | Skipped |
| examples/resnet18-cifar10/train.mojo | 272 | Already NOTE(#3013) | Skipped |

## Issue Mapping

All 6 updated NOTEs mapped to pre-existing cleanup issues — no new issues needed to be created:

- #3076: Python interop blocker NOTEs
- #3087: Image loading external dependency
- #3071: Mojo language limitation NOTEs (os.remove)
- #3088: BF16 type alias limitation
- #3085: Enable disabled Conv2D backward tests
- #3084: Track backward pass implementation NOTEs in examples

## Pre-commit Result

All hooks passed:
- mojo format: Passed
- markdownlint: Passed
- trailing-whitespace: Passed
- end-of-file-fixer: Passed
- check-yaml: Passed
- check-added-large-files: Passed