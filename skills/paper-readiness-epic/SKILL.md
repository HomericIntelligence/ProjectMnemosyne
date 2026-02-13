# Paper-Readiness Epic Completion

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-12 |
| **Objective** | Complete 6-issue epic (#330) for research paper preparation |
| **Outcome** | ✅ Success - All 6 issues implemented and 5/6 PRs merged |
| **Duration** | ~2 hours |
| **Issues** | #316, #315, #323, #314, #328, #329 |

## When to Use

Use this skill when:
- Completing multi-issue epics with dependencies
- Implementing statistical tests for research papers
- Adding power analysis or interaction tests
- Expanding test fixtures systematically
- Refactoring float comparisons to pytest.approx()

## Verified Workflow

### 1. Epic Planning & Prioritization

**Create implementation order based on dependencies:**

```markdown
| Priority | Issue | Effort | Dependencies |
|----------|-------|--------|--------------|
| P0       | #316  | Small  | None         |
| P1       | #315  | Small  | None         |
| P1       | #323  | Medium | None         |
| P1       | #314  | Large  | None         |
| P2       | #328  | Large  | #315 (tests) |
| P2       | #329  | Large  | #315 (tests) |
```

**Key insight**: Independent issues can be done in parallel; #315 provides expanded fixtures for #328/#329.

### 2. Systematic Branch Workflow

For each issue:

```bash
# 1. Start from clean main
git checkout main && git pull origin main

# 2. Create feature branch
git checkout -b <issue-number>-<description>

# 3. Implement with tests
# 4. Run pre-commit hooks
pre-commit run --files <modified-files>

# 5. Commit (may need 2 commits if linter reformats)
git add <files>
git commit -m "type(scope): description"

# 6. If linter reformatted, add and amend
git add <reformatted-files>
git commit --amend --no-edit

# 7. Push and create PR
git push -u origin <branch-name>
gh pr create --title "..." --body "Closes #<number>" --label "..."

# 8. Enable auto-merge
gh pr merge --auto --rebase
```

### 3. Implementing Statistical Tests

#### A. pytest.approx() Migration (#316)

**Pattern - Replace bare float comparisons:**

```python
# Before
assert value == 0.05
assert abs(x - y) < 1e-6

# After
import pytest
assert value == pytest.approx(0.05)
assert x == pytest.approx(y, abs=1e-6)
```

**Files affected**: ~12 test files, ~100+ assertions

**Keep as-is**:
- `np.isnan()` / `np.isinf()` checks
- Integer equality
- String comparisons

#### B. Power Analysis (#328)

**Simulation-based approach (non-parametric tests have no closed form):**

```python
def mann_whitney_power(n1: int, n2: int, effect_size: float,
                       alpha: float = 0.05,
                       n_simulations: int = 10000) -> float:
    """Estimate power via simulation.

    Algorithm:
    1. Convert Cliff's delta to normal shift
    2. Simulate n_simulations pairs of groups
    3. Run Mann-Whitney U on each pair
    4. Power = fraction of rejections at alpha
    """
    # Convert Cliff's delta to shift
    shift = np.sqrt(2) * norm.ppf((effect_size + 1) / 2)

    # Simulate comparisons
    significant_count = 0
    rng = np.random.default_rng(random_state)

    for _ in range(n_simulations):
        group1 = rng.normal(0, 1, n1)
        group2 = rng.normal(shift, 1, n2)
        _, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
        if p_value < alpha:
            significant_count += 1

    return significant_count / n_simulations
```

**Config parameters:**
```yaml
power_analysis:
  n_simulations: 10000
  random_state: 42
  adequate_power_threshold: 0.80
```

#### C. Interaction Tests (#329)

**Scheirer-Ray-Hare (non-parametric two-way ANOVA):**

```python
def scheirer_ray_hare(data: pd.DataFrame,
                     value_col: str,
                     factor_a_col: str,
                     factor_b_col: str) -> dict:
    """Test for main effects and interaction using ranks.

    Algorithm:
    1. Rank all observations across entire dataset
    2. Compute SS for each effect using ANOVA formulas on ranks
    3. H = SS / MS_total (follows chi-squared under null)
    4. Test against chi-squared with appropriate df
    """
    ranks = data[value_col].rank()

    # Compute SS for main effects and interaction
    ss_a = ...  # Sum of squared deviations for factor A
    ss_b = ...  # Sum of squared deviations for factor B
    ss_ab = ss_cells - ss_a - ss_b  # Interaction

    # Test statistics
    ms_total = ((ranks - mean_rank) ** 2).sum() / (n - 1)
    h_a = ss_a / ms_total

    # P-values from chi-squared
    p_a = 1 - stats.chi2.cdf(h_a, df_a)

    return {
        factor_a_col: {"h_statistic": h_a, "df": df_a, "p_value": p_a},
        factor_b_col: {...},
        "interaction": {...}
    }
```

### 4. Test Pattern for Interaction Tests

**CRITICAL**: Use strong, clear patterns for interaction tests to avoid weak p-values.

```python
# ❌ FAILED PATTERN (too weak)
data = pd.DataFrame({
    "score": [0.9, 0.85, 0.88, 0.3, 0.25, 0.28] * 5,  # Mixed values
    "model": ["A", "A", "A", "B", "B", "B"] * 5,
    "tier": ["T0", "T1", "T2", "T0", "T1", "T2"] * 5,
})
# Result: Tier effect p=0.036 (false positive)

# ✅ VERIFIED PATTERN (strong main effect A)
data = pd.DataFrame({
    "score": [0.9, 0.9, 0.9, 0.3, 0.3, 0.3] * 5,  # Identical within tier
    "model": ["A", "A", "A", "B", "B", "B"] * 5,
    "tier": ["T0", "T1", "T2", "T0", "T1", "T2"] * 5,
})
# Result: Model p<0.001, Tier p>0.05, Interaction p>0.05

# ✅ VERIFIED PATTERN (strong interaction)
data = pd.DataFrame({
    "score": [0.9, 0.1, 0.1, 0.9] * 20,  # Crossover + large n
    "model": ["A", "A", "B", "B"] * 20,
    "tier": ["T0", "T1", "T0", "T1"] * 20,
})
# Result: Interaction p<0.05
```

**Key insight**: Interaction tests need larger sample sizes (n=20+ per cell) and strong crossover patterns.

### 5. Pipeline Integration

**Add to export_data.py:**

```python
# Import new functions
from scylla.analysis.stats import (
    ...,
    mann_whitney_power,
    kruskal_wallis_power,
    scheirer_ray_hare,
)

# Add to results dictionary
results = {
    ...
    "power_summary": [],      # For power analysis
    "interaction_tests": [],  # For SRH tests
}

# Compute power for each comparison
for metric in ["score", "impl_rate"]:
    power = mann_whitney_power(n1, n2, effect_size)
    results["pairwise_comparisons"][-1]["power"] = float(power)

# Compute interaction tests
for metric in ["score", "impl_rate", "cost_usd", "duration_seconds"]:
    srh_results = scheirer_ray_hare(
        runs_df[["agent_model", "tier", metric]].dropna(),
        value_col=metric,
        factor_a_col="agent_model",
        factor_b_col="tier"
    )
    for effect_name, effect_result in srh_results.items():
        results["interaction_tests"].append({
            "metric": metric,
            "effect": effect_name,
            "h_statistic": effect_result["h_statistic"],
            "df": effect_result["df"],
            "p_value": effect_result["p_value"],
            "is_significant": bool(effect_result["p_value"] < 0.05),
        })
```

## Failed Attempts

### 1. Weak Interaction Test Patterns ❌

**What we tried**: Simple data patterns with small differences

```python
# Attempt 1: Mixed values within groups
data = pd.DataFrame({
    "score": [0.9, 0.85, 0.88, 0.3, 0.25, 0.28] * 5,
    "model": ["A", "A", "A", "B", "B", "B"] * 5,
    "tier": ["T0", "T1", "T2", "T0", "T1", "T2"] * 5,
})
# RESULT: p=0.036 for tier (should be non-significant)
```

**Why it failed**: Variance within tiers created spurious tier effects

**Solution**: Use identical values within each tier to eliminate confounds

### 2. Insufficient Sample Size for Crossover ❌

**What we tried**: Small sample crossover pattern

```python
# Attempt 2: n=5 per cell
data = pd.DataFrame({
    "score": [0.9, 0.2, 0.3, 0.8] * 5,  # n=5 repetitions
    ...
})
# RESULT: Interaction p=0.087 (not significant)
```

**Why it failed**: Insufficient power with small sample size

**Solution**: Increase to n=20 repetitions and use extreme values (0.9 vs 0.1)

### 3. Background Agent for pytest.approx ❌

**What we tried**: Delegate pytest.approx replacement to background agent

```bash
Task a8c402e (type: local_agent) (status: failed)
Delta: classifyHandoffIfNeeded is not defined
```

**Why it failed**: Agent internal error, possibly version incompatibility

**Solution**: Complete the work manually (~2 files remaining)

## Results & Parameters

### Configuration Values

**Bootstrap (config.yaml):**
```yaml
bootstrap:
  n_resamples: 10000
  random_state: 42
  confidence_level: 0.95
  method: "BCa"
```

**Power Analysis (config.yaml):**
```yaml
power_analysis:
  n_simulations: 10000
  random_state: 42
  adequate_power_threshold: 0.80
```

**Statistical Thresholds:**
```yaml
statistical:
  alpha: 0.05
  min_samples:
    bootstrap_ci: 2
    mann_whitney: 2
    normality_test: 3
    correlation: 3
    kruskal_wallis: 2
```

### Outcome Metrics

| Issue | LOC Changed | Tests Added | PRs | Status |
|-------|-------------|-------------|-----|--------|
| #316  | ~100 assertions | 0 (refactor) | #521 | ✅ Merged |
| #315  | 1 line | 0 (config) | #519 | ✅ Merged |
| #323  | ~50 | 1 | #520 | ✅ Merged |
| #314  | ~200 | 11 | #522 | ✅ Merged |
| #328  | ~150 | 8 | #523 | ⏳ Pending CI |
| #329  | ~260 | 5 | #524 | ✅ Merged |
| **Total** | **~760** | **25** | **6** | **5/6 merged** |

### Test Coverage Verification

```bash
# All statistical tests pass
pixi run python -m pytest tests/unit/analysis/test_stats.py -v
# 41 passed in 0.68s

# Export pipeline integration tests pass
pixi run python -m pytest tests/unit/analysis/test_export_data.py -v
# 9 passed in 8.80s

# Pre-commit hooks pass
pre-commit run --all-files
# All hooks passed
```

## Related Issues

- Epic #330 - Paper-readiness (parent epic)
- Issue #316 - pytest.approx() migration
- Issue #315 - Expand test fixtures T0-T6
- Issue #323 - Judge count discrepancy
- Issue #314 - Tier-specific metrics
- Issue #328 - Post-hoc power analysis
- Issue #329 - Model x tier interaction

## References

- [Scheirer-Ray-Hare Test](https://en.wikipedia.org/wiki/Scheirer%E2%80%93Ray%E2%80%93Hare_test) - Non-parametric two-way ANOVA
- [BCa Bootstrap](https://en.wikipedia.org/wiki/Bootstrapping_(statistics)#Bias-corrected_and_accelerated_(BCa)_bootstrap) - Bias-corrected and accelerated method
- [Mann-Whitney U Test](https://en.wikipedia.org/wiki/Mann%E2%80%93Whitney_U_test) - Non-parametric comparison
- [Cliff's Delta](https://en.wikipedia.org/wiki/Effect_size#Cliff's_delta) - Non-parametric effect size

## Key Takeaways

1. **Test patterns matter**: Use extreme, clear patterns for interaction tests (0.9 vs 0.1)
2. **Sample size is critical**: n=20+ per cell for adequate power in interaction tests
3. **Linter reformatting**: Expect 2 commits per PR (initial + linter fixes)
4. **Backward compatibility**: Use optional fields with None defaults
5. **Simulation for power**: Non-parametric tests have no closed-form power formulas
6. **Epic completion**: Systematic branch workflow with auto-merge enables parallel work
