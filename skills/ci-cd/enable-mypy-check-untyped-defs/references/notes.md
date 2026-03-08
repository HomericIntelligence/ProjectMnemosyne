# Reference Notes: enable-mypy-check-untyped-defs

## Session Context

**Date**: 2026-03-07
**Project**: ProjectOdyssey
**Issue**: #3370 — Add --check-untyped-defs to mypy hook for full body coverage
**PR**: #4036
**Branch**: 3370-auto-impl

## Background

Issue #3370 requested enabling `--check-untyped-defs` in the mypy pre-commit hook and
`pyproject.toml` to ensure bodies of untyped functions are type-checked. Without this flag,
mypy silently skips checking the body of any function lacking full type annotations, which
can hide real bugs.

## Files Modified

- `pyproject.toml` — added `check_untyped_defs = true` to `[tool.mypy]`
- `.pre-commit-config.yaml` — added `--check-untyped-defs` to mypy hook args
- `scripts/analyze_warnings.py` — annotated `defaultdict(int)` as `defaultdict[str, int]`
- `scripts/agents/tests/test_integration.py` — annotated empty list `[]` as `list[str]`
- `scripts/convert_image_to_idx.py` — replaced deprecated Pillow 10+ attributes

## Errors Fixed

### 1. scripts/analyze_warnings.py — var-annotated

```text
error: Need type annotation for "file_counts" (hint: "file_counts: defaultdict[str, int] = ...")
```

Fix: Added explicit type annotation to `defaultdict(int)` assignment.

### 2. scripts/agents/tests/test_integration.py — var-annotated

```text
error: Need type annotation for "optional" (hint: "optional: list[<type>] = ...")
```

Fix: Changed `optional = []` to `optional: list[str] = []`.

### 3. scripts/convert_image_to_idx.py — attr-defined (Pillow 10+)

```text
error: Module has no attribute "LANCZOS"
error: Module has no attribute "TRANSPOSE"
error: Module has no attribute "FLIP_LEFT_RIGHT"
```

Pillow 10 removed deprecated module-level aliases. Fix: Use enum namespaces.

- `Image.LANCZOS` → `Image.Resampling.LANCZOS`
- `Image.TRANSPOSE` → `Image.Transpose.TRANSPOSE`
- `Image.FLIP_LEFT_RIGHT` → `Image.Transpose.FLIP_LEFT_RIGHT`

## Key Insight: Triage Before Config Change

Running mypy with the new flag before touching config files is the key to a clean implementation:

```bash
pixi run mypy scripts/ --check-untyped-defs --exclude generators/
```

This reveals all errors upfront. Fix them all first, then add the flag to `pyproject.toml` and
`.pre-commit-config.yaml`. This avoids a broken state where the config has the flag but errors
remain.

## Note on --exclude Consistency

The `exclude = "generators/"` in `pyproject.toml` is a regex that applies when mypy is run
without explicit paths. When invoking mypy directly with `scripts/` as the target, the
exclusion must also be passed on the command line as `--exclude generators/` to maintain
consistent behavior between CLI invocations and pre-commit hook runs.

## Test Results

- `pixi run mypy scripts/ --check-untyped-defs --exclude generators/` → Success: no issues found
- `pixi run pre-commit run mypy --all-files` → mypy.....Passed
- `pixi run pre-commit run --all-files` → All hooks passed
