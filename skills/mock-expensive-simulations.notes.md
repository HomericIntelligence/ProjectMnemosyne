# Raw Session Notes: mock-expensive-simulations

## Session Context

- **Project**: ProjectScylla / 1008-state-machine-refactor branch
- **Date**: 2026-02-23
- **Trigger**: User reported tests hang after ~7% of pytest run; push hook was blocked

## Timeline

1. User reports tests hang: `test_cop_integration.py`, `test_duration_integration.py`, `test_export_data.py`
2. Initial exploration agent identified `compute_statistical_results()` as the culprit — 36 cliff's delta CI calls × 10,000 resamples + 26 power simulation calls × 10,000 simulations = ~600,000 operations total
3. User clarified: **tests don't hang on main** — suggesting a branch-specific regression
4. Launched bisect agent with `git bisect bad HEAD; git bisect good f6fe77f`
5. Bisect result: **the baseline (`f6fe77f` / `origin/main`) also hangs** — the hang is pre-existing
6. True introducing commit: `6babcbd` on main — added `mann_whitney_power` and `kruskal_wallis_power` calls
7. Fixed by adding `autouse` mock fixture to `conftest.py`

## Exact Hang Calculation

`compute_statistical_results()` with 2 models × 7 tiers:
- `cliffs_delta_ci()`: 3 metrics × 12 pairwise transitions × 10,000 bootstrap resamples = **360,000 resamples**
- `mann_whitney_power()`: 12 transitions × 2 calls (observed + medium) × 10,000 simulations = **240,000 simulations**
- `kruskal_wallis_power()`: 2 models × 10,000 simulations = **20,000 simulations**

Note: `cliffs_delta_ci` is fast (numpy-vectorized), but the power functions run Python `for _ in range(10000)` loops calling `mann_whitney_u()` each iteration — these are the bottleneck.

At ~5s per 10,000 simulation iterations:
- `mann_whitney_power`: 24 calls × 5s = **120s**
- `kruskal_wallis_power`: 2 calls × 5s = **10s**
- Total per test that calls `compute_statistical_results()`: **~130s**

With 3 test files each calling it multiple times: **easily 10+ minutes**.

## Patch Target Discovery

```bash
# How export_data.py imports the functions:
grep "^from.*import" scripts/export_data.py | grep power
# Output: from scylla.analysis.stats import (... kruskal_wallis_power, mann_whitney_power, ...)
```

Since it's a `from ... import`, the names are bound in `export_data`'s module namespace.
Patching `scylla.analysis.stats.mann_whitney_power` after this import does NOT affect
the already-bound `export_data.mann_whitney_power`.

Solution: patch `export_data.mann_whitney_power` with `create=True` because `export_data`
is loaded via `sys.path.insert(0, "scripts/")` — not a proper package — so the module may
not be in `sys.modules` at conftest fixture definition time.

## Why `create=True` Is Needed

`export_data` is not a proper Python package — it lives in `scripts/` and is added to
sys.path. When the conftest fixture runs at collection time, `export_data` may not yet
be imported (lazy import via `from export_data import ...` inside test functions). The
`create=True` flag tells `unittest.mock.patch` to create the attribute if it doesn't
exist on the target object, preventing `AttributeError: <module 'export_data'> does not
have the attribute 'mann_whitney_power'`.

## Files Changed

```
tests/unit/analysis/conftest.py  (added 24 lines — autouse mock fixture)
```

## Commit

```
c2bc1a3 fix(tests): Mock power simulations in analysis conftest to prevent hangs
```

## Test Results After Fix

```
tests/unit/analysis/test_cop_integration.py .                   [  9%]
tests/unit/analysis/test_duration_integration.py .              [ 18%]
tests/unit/analysis/test_export_data.py .........               [100%]

11 passed in 14.80s
```

Full suite: 2968 passed, 77.91% coverage in 59.86s.