# Session Notes: Fix Flaky Glob Ordering

## Session Date
2026-03-05

## Repository
HomericIntelligence/ProjectOdyssey

## Problem
`test_named_tensor_collection` in `tests/shared/test_serialization.mojo` failed on CI (Feb 14)
but passed previously (Feb 10) with identical code and Mojo version `0.26.1.0.dev2025122805`.

Root cause: `load_named_tensors()` in `shared/utils/serialization.mojo` used `p.glob("*.weights")`
without sorting. `pathlib.glob()` does not guarantee ordering. Test asserted `loaded[0].name == "weights"`
which worked when OS returned `weights.weights` first, but failed when `bias.weights` came first.

## Steps Taken

1. Read `shared/utils/serialization.mojo:311-329` and `tests/shared/test_serialization.mojo:185-203`
2. Identified `var weight_files = p.glob("*.weights")` as the non-deterministic line
3. First fix attempt: `var weight_files = sorted(p.glob("*.weights"))` — Mojo compile error
4. Searched codebase for `builtins` usage — found pattern in `config.mojo` and `toml_loader.mojo`
5. Correct fix: import builtins, call `builtins.sorted(p.glob("*.weights"))`
6. Updated test assertions: alphabetical order means `bias` (index 0) before `weights` (index 1)
7. Created PR #3239, CI passed compilation after second commit

## CI Failures Encountered

- `Mojo Package Compilation`: `error: use of unknown declaration 'sorted'`
  - Fix: use `Python.import_module("builtins").sorted()`
- `link-check`: pre-existing failures on all PRs (root-relative links, not my change)

## Files Changed
- `shared/utils/serialization.mojo:318` — added builtins import + sorted() call
- `tests/shared/test_serialization.mojo:192-198` — swapped assertion order

## PR
https://github.com/HomericIntelligence/ProjectOdyssey/pull/3239
