# Session Notes: CI Matrix Timeout Guidance

**Date**: 2026-03-07
**Issue**: ProjectOdyssey #3357
**PR**: #4001
**Branch**: `3357-auto-impl`

## Objective

Add inline YAML comments to the `test-mojo-comprehensive` matrix in
`.github/workflows/comprehensive-tests.yml` to document:

- The 15-minute shared timeout policy
- How to monitor wall-clock time via `test-results-*.json` artifacts
- The >10 min split threshold (referencing ADR-009)
- Per-entry file counts and risk tiers for all 15 matrix groups

Follow-up to issue #3156 (consolidate-ci-matrix), which merged 31 groups into 16.

## What Was Done

1. Read `comprehensive-tests.yml` to understand the matrix structure
2. Counted files in each explicit-pattern group by counting space-separated `.mojo` filenames
3. Added a 9-line policy block above `test-group:` in the matrix
4. Added per-entry comments to all 15 groups:
   - Explicit groups: file count + risk tier + split priority
   - Glob groups: "Glob pattern — file count varies; monitor wall-clock time before splitting"
   - Mixed groups: "Mixed explicit + glob patterns — monitor wall-clock time before splitting"
5. Validated YAML syntax with `python -c "import yaml; yaml.safe_load(...)"`
6. All pre-commit hooks passed (check-yaml, validate-test-coverage, trailing-whitespace)
7. Committed and pushed; PR created with auto-merge

## File Counts Per Group

| Group | Files | Risk |
|-------|-------|------|
| Core Tensors | 20 | High (split first) |
| Core Activations & Types | 13 | Medium |
| Core Loss | 3 | Low |
| Core Gradient | 8 | Medium |
| Core Utilities | 27 | High (split second) |
| Data | glob | monitor |
| Autograd & Benchmarking | glob | monitor |
| Integration Tests | glob | monitor |
| Shared Infra & Testing | mixed | monitor |
| Models | glob | monitor |
| Misc Tests | mixed globs | monitor |
| Examples | glob | monitor |
| LeNet-5 Examples | 2 | Low |
| Core Types & Fuzz | glob | monitor |
| Benchmark Framework | glob | monitor |

## Key Insights

- GitHub Actions does NOT support per-matrix-entry `timeout-minutes` — only job-level
- Matrix entry `name:` values are referenced by `continue-on-error` expressions — never modify them
- For glob patterns, file count is dynamic, so "monitor" phrasing is more accurate than a static number
- The `validate-test-coverage` pre-commit hook checks matrix names specifically — changes to `name:` would fail it
- Pure comment diffs (24 insertions, 0 deletions) still require YAML validation

## Diff Summary

```
.github/workflows/comprehensive-tests.yml | 24 ++++++++++++++++++++++++
1 file changed, 24 insertions(+)
```
