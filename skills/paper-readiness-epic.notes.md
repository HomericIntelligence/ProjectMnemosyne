# Paper-Readiness Epic - Raw Session Notes

## Session Context

**Date**: 2026-02-12
**Conversation ID**: Resumed from context-compacted session
**User Request**: "Implement the following plan" + "create PRs for the 4 completed branches" + "continue" (2x)

## Detailed Timeline

### Phase 1: Issue #315 (Expand Test Fixtures)
- Branch: `315-expand-tier-fixtures`
- Modified: `tests/unit/analysis/conftest.py`
- Change: `tiers = ["T0", "T1", "T2"]` → `tiers = ["T0", "T1", "T2", "T3", "T4", "T5", "T6"]`
- Updated docstring: 60 rows → 140 rows
- Commit: `cd03dca`
- Result: All tests passed ✅

### Phase 2: Issue #323 (Judge Count Discrepancy)
- Branch: `323-judge-count-discrepancy`
- Root cause: `loader.py` line 408 didn't check `fallback` field
- Files modified:
  - `scylla/analysis/loader.py` - Added fallback checking
  - `scripts/export_data.py` - Added consistency assertion
  - `tests/unit/analysis/test_dataframe_builders.py` - Regression test
- Side effects: Had to add `import pytest` to 2 more test files
- Commit: `e6f2d87`
- Result: All tests passed ✅

### Phase 3: Issue #316 (pytest.approx)
- Branch: `316-pytest-approx`
- Background agent a8c402e failed with "classifyHandoffIfNeeded is not defined"
- Completed manually: 8 test files total, ~100+ assertions
- Pattern: `assert value == 0.05` → `assert value == pytest.approx(0.05)`
- Commits: `9c9f727` (partial), `2a6e274` (complete)
- Result: All tests passed ✅

### Phase 4: Issue #314 (Tier-Specific Metrics)
- Branch: `314-tier-specific-metrics`
- Added `ModelUsage` dataclass
- Extended `RunData` with optional fields: `api_calls`, `num_turns`, `model_usage`
- Added `load_agent_result()` function
- Modified dataframes.py to add 4 new columns
- Added `_compute_delegation_cost_ratio()` helper
- Linter reformatted, required re-commit
- Commit: `4f5b48e`
- Result: All tests passed ✅

### Phase 5: PR Creation (Batch)
- Created PRs #519-#522 for issues #315, #323, #316, #314
- All 4 PRs auto-merged successfully
- Note: Label 'analysis' didn't exist, had to remove

### Phase 6: Issue #328 (Power Analysis)
- Branch: `328-post-hoc-power-analysis`
- Added power_analysis section to config.yaml
- Added 3 properties to config.py
- Implemented simulation-based power functions
- Algorithm: Convert Cliff's delta → normal shift via Φ^(-1)
- Testing: Medium effect ~48% power, zero effect ~5%
- Linter reformatted, required re-commit
- Commit: `e88d418`
- PR: #523 (still open, pending CI)
- Result: All tests passed ✅

### Phase 7: Issue #329 (Interaction Tests)
- Branch: `329-model-tier-interaction`
- Implemented Scheirer-Ray-Hare test
- Algorithm: Rank → SS computation → χ² test
- Test failures with weak patterns:
  - Attempt 1: p=0.036 for tier (should be >0.05)
  - Attempt 2: Interaction p=0.087 (should be <0.05)
- Solutions:
  - Use identical values within tiers
  - Increase sample size to n=20
  - Use extreme values (0.9 vs 0.1)
- Added to export_data.py pipeline
- Commits: `e41a3a0`, `4b0d1be`
- PR: #524 (auto-merged)
- Result: All 5 tests passed ✅

## Code Snippets

### Power Analysis - Cliff's Delta to Shift

```python
# Convert Cliff's delta to normal distribution shift
shift = np.sqrt(2) * norm.ppf((effect_size + 1) / 2)

# For d=0.5 (medium effect):
# shift = 1.414 * norm.ppf(0.75) = 1.414 * 0.674 = 0.953
```

### Scheirer-Ray-Hare - Interaction SS

```python
# Compute sum of squares for interaction
ss_cells = 0.0
for level_a in levels_a:
    for level_b in levels_b:
        mask = (data[factor_a_col] == level_a) & (data[factor_b_col] == level_b)
        n_ij = mask.sum()
        if n_ij > 0:
            mean_rank_ij = ranks[mask].mean()
            ss_cells += n_ij * (mean_rank_ij - mean_rank) ** 2

ss_ab = ss_cells - ss_a - ss_b  # Interaction is residual
```

### Export Pipeline Integration

```python
# Power analysis addition
for comparison in results["pairwise_comparisons"]:
    n1 = comparison["n1"]
    n2 = comparison["n2"]
    effect_size = comparison["cliffs_delta"]
    power = mann_whitney_power(n1, n2, effect_size)
    comparison["power"] = float(power)

# Interaction tests addition
for metric in ["score", "impl_rate", "cost_usd", "duration_seconds"]:
    metric_data = runs_df[["agent_model", "tier", metric]].dropna()
    srh_results = scheirer_ray_hare(
        metric_data,
        value_col=metric,
        factor_a_col="agent_model",
        factor_b_col="tier"
    )
    # Store each effect separately
    for effect_name, effect_result in srh_results.items():
        results["interaction_tests"].append({...})
```

## Error Messages

### Background Agent Failure
```
Task a8c402e (type: local_agent) (status: failed)
Delta: classifyHandoffIfNeeded is not defined
```

### Git Label Issue
```
Label 'analysis' didn't exist when creating PR
Fixed by: Removing the invalid label
```

### Linter Auto-Formatting
```
Ruff Format Python.......................................................Failed
- hook id: ruff-format-python
- files were modified by this hook
```

## Test Commands

```bash
# Individual test suite
pixi run python -m pytest tests/unit/analysis/test_stats.py::test_scheirer_ray_hare_no_effects -xvs

# All scheirer_ray_hare tests
pixi run python -m pytest tests/unit/analysis/test_stats.py -k scheirer_ray_hare -v

# Full stats test suite
pixi run python -m pytest tests/unit/analysis/test_stats.py -v

# Export integration tests
pixi run python -m pytest tests/unit/analysis/test_export_data.py -v

# Pre-commit on specific files
pre-commit run --files scylla/analysis/stats.py tests/unit/analysis/test_stats.py
```

## Git Commands Used

```bash
# Standard workflow
git checkout main && git pull origin main
git checkout -b <issue-number>-<description>
git add <files>
git commit -m "type(scope): description"
git push -u origin <branch-name>

# PR creation
gh pr create --title "..." --body "Closes #<number>" --label "..."
gh pr merge --auto --rebase

# Branch cleanup after merge
# (Not needed - auto-merge handles this)

# Check PR status
gh pr list --state all --limit 50 --json number,title,state
```

## Configuration Files Modified

**config.yaml additions:**
```yaml
power_analysis:
  n_simulations: 10000
  random_state: 42
  adequate_power_threshold: 0.80
```

**config.py additions:**
```python
@property
def power_n_simulations(self) -> int:
    return self.get("statistical", "power_analysis", "n_simulations", default=10000)

@property
def power_random_state(self) -> int:
    return self.get("statistical", "power_analysis", "random_state", default=42)

@property
def adequate_power_threshold(self) -> float:
    return self.get("statistical", "power_analysis", "adequate_power_threshold", default=0.80)
```

## Metrics

**Lines of Code by Issue:**
- #316: ~100 modified assertions (no new code)
- #315: 1 line changed + docstring
- #323: ~50 lines (loader + export + test)
- #314: ~200 lines (dataclass + loader + dataframes + stats)
- #328: ~150 lines (config + power functions + tests)
- #329: ~260 lines (scheirer function + export + tests)
- **Total: ~760 lines changed**

**Test Coverage by Issue:**
- #316: 0 new tests (refactoring existing)
- #315: 0 new tests (fixture expansion)
- #323: 1 new test (regression)
- #314: 11 new tests (comprehensive)
- #328: 8 new tests (power analysis)
- #329: 5 new tests (interaction)
- **Total: 25 new tests**

**Time Estimates:**
- #316: 30 minutes (manual replacement)
- #315: 5 minutes (1-line change)
- #323: 45 minutes (debugging + fix)
- #314: 90 minutes (implementation + tests)
- #328: 90 minutes (algorithm + tests)
- #329: 120 minutes (implementation + failed attempts + fixes)
- **Total: ~6 hours**

## References Consulted

1. Scheirer, Ray, and Hare (1976) - Original SRH paper
2. scipy.stats documentation - mann_whitney_u, chi2, rankdata
3. ProjectScylla metrics definitions (.claude/shared/metrics-definitions.md)
4. Bootstrap BCa method - scipy.stats.bootstrap
5. Cliff's Delta calculation - existing implementation in stats.py

## Lessons Learned

1. **Test data design is critical** - Weak patterns lead to spurious significance
2. **Sample size matters** - n=20+ needed for interaction detection
3. **Linters will reformat** - Expect to commit twice per PR
4. **Background agents can fail** - Have manual fallback plan
5. **Simulation is powerful** - When closed-form doesn't exist, simulate
6. **Systematic workflow** - Branch → Implement → Test → PR → Auto-merge scales well
