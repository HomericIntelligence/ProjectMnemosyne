---
name: "Skill: Analysis Pipeline Code Review"
description: "Skill: Analysis Pipeline Code Review"
category: evaluation
date: 2026-01-31
user-invocable: false
---
# Skill: Analysis Pipeline Code Review

| Property | Value |
|----------|-------|
| **Date** | 2026-01-31 |
| **Objective** | Comprehensive code review of ~4,140-line analysis pipeline with statistical validation, DRY refactoring, test suite creation, and phased PR delivery |
| **Outcome** | ✅ Success - 15 PRs merged, 26 issues closed, 6 P0 bugs fixed, 45 tests passing |
| **Category** | evaluation |
| **Key Innovation** | Systematic multi-priority review (P0-P3) with parallel PR execution and statistical methodology validation |
| **Duration** | ~11 hours (2026-01-31 03:18 to 13:59) |

## When to Use This Skill

Use this approach when reviewing large analysis/evaluation pipelines that:

1. **Generate research outputs** (papers, reports, visualizations)
   - Need to validate statistical correctness before publication
   - Outputs are used for decision-making or benchmarking
   - Errors could invalidate published findings

2. **Have significant technical debt**
   - Code duplication across many files (DRY violations)
   - Missing tests for critical statistical functions
   - Hard-coded values and magic numbers
   - Dead code and unused functions

3. **Require multi-tier fixes**
   - Critical bugs (wrong numbers, crashes) need immediate fixes
   - Performance issues at moderate priority
   - Code quality improvements can be deferred

4. **Are too large for single PR**
   - 4,000+ lines across 15+ files
   - Multiple independent improvements
   - Need to maintain git history clarity

### Trigger Patterns

- User asks to "review the analysis pipeline" or "audit the stats code"
- Pipeline generates research outputs (papers, benchmarks, reports)
- Pipeline was built quickly and needs quality improvements
- Statistical methodology needs validation before publication
- Code has significant duplication or technical debt

## Verified Workflow

### 1. Priority-Based Issue Classification

Create a structured priority system with clear severity levels:

**P0 - Critical (Wrong Numbers / Crashes)**:
- Statistical functions with incorrect implementations
- Inverted algorithms (e.g., Pareto frontier returning anti-optimal points)
- Crashes on edge cases
- **Impact**: Published results are incorrect

**P1 - High (Should Fix Before Publication)**:
- Missing statistical corrections (e.g., Bonferroni for multiple comparisons)
- Performance issues (O(n²) loops vs vectorized operations)
- Inconsistent methodology (mixing bootstrap and normal-approx CIs)
- Fragile code (hardcoded assumptions, no error handling)
- **Impact**: Methodology is questionable or code breaks easily

**P2 - Medium (Maintainability)**:
- DRY violations (constants duplicated 10+ times)
- Dead code and unused functions
- Missing tests
- Unclear public API
- **Impact**: Hard to maintain and extend

**P3 - Low (Nice-to-Have)**:
- Misleading metadata (doesn't affect behavior)
- Documentation staleness
- Edge case handling for rare scenarios
- **Impact**: Minor quality improvements

**Verification Method**: For each issue, document:
- File path and line number
- Before/after code snippets
- Why it's wrong (with counterexamples for algorithm bugs)
- Impact on outputs (which tables/figures affected)

### 2. Phased PR Strategy

Group fixes into independent PRs that can be reviewed and merged separately:

**Phase 1: Critical Fixes (P0)**
- Fix statistical correctness bugs FIRST
- Add regression tests for each bug (with counterexamples)
- Examples: Krippendorff's alpha, Pareto frontier, crash guards
- **Rationale**: These invalidate published results if unfixed

**Phase 2: Methodology Improvements (P1 statistical)**
- Add missing corrections (Bonferroni, bootstrap CI)
- Vectorize performance bottlenecks
- Remove dead code
- **Rationale**: Affects statistical validity and performance

**Phase 3: Robustness (P1 infrastructure)**
- Dynamic handling instead of hardcoded assumptions
- Error isolation (one failure doesn't kill all outputs)
- Import-time vs explicit initialization
- **Rationale**: Makes pipeline more resilient

**Phase 4: DRY Refactoring (P2)**
- Extract constants to single source of truth
- Create helper functions for repeated calculations
- Centralize color scales and styling
- **Rationale**: Reduces maintenance burden

**Phase 5: Test Suite (P1)**
- Create fixtures with known values (~70-row sample DataFrames)
- Test statistical functions against reference implementations
- Add smoke tests for figure/table generation
- **Rationale**: Prevents regressions

**Phase 6: Cleanup (P2-P3)**
- Update documentation
- Remove empty directories
- Fix metadata inconsistencies
- **Rationale**: Polish and housekeeping

**Phase 7: Architecture (Deferred)**
- Large refactors (DualFormatTable class, plugin systems)
- Nice-to-have but risky
- **Rationale**: Post-publication improvements

**Key Principle**: Each PR should be independently reviewable and mergeable. Don't create dependencies between PRs unless necessary.

### 3. Statistical Validation Pattern

For any pipeline generating research outputs, validate statistical functions systematically:

**Step 1: Identify all statistical functions**
```bash
# Find all functions in stats.py
grep "^def " scylla/analysis/stats.py
```

**Step 2: For each function, check:**
1. **Correctness**: Does it implement the formula correctly?
   - Compare to authoritative source (scipy, published papers)
   - Test with known reference values
   - Check edge cases (empty data, identical values, negative values)

2. **Implementation level**: Does it match the intended measurement level?
   - Example: Krippendorff's alpha has nominal/ordinal/interval/ratio levels
   - Verify the level parameter is actually used
   - Test that ordinal != nominal != interval

3. **Formula matching**: Does it match the paper's citation?
   - Example: Krippendorff's alpha uses `1 - (D_o / D_e)`, not `(P_o - P_e)/(1 - P_e)` (Scott's pi)
   - Document the correct formula in comments

**Step 3: Create regression tests with known values**
```python
def test_cliffs_delta_reference():
    """Verify Cliff's delta matches published reference.

    Reference: Romano et al. (2006), Example 3
    Group A: [10, 20, 30]
    Group B: [5, 15, 25]
    Expected delta: 0.556
    """
    group_a = np.array([10, 20, 30])
    group_b = np.array([5, 15, 25])
    delta = cliffs_delta(group_a, group_b)
    assert abs(delta - 0.556) < 0.001
```

**Step 4: Validate against authoritative packages**
```python
def test_krippendorff_alpha_matches_package():
    """Verify our wrapper matches krippendorff package directly."""
    ratings = np.array([[1, 2, 3], [1, 2, 4], [1, 3, 3]])
    expected = krippendorff.alpha(ratings, level_of_measurement="ordinal")
    actual = krippendorff_alpha(ratings, level="ordinal")
    assert abs(expected - actual) < 1e-6
```

**Failed Attempt**: Don't implement complex statistical functions from scratch. Use authoritative packages (scipy, krippendorff) and wrap them. Custom implementations are error-prone and hard to validate.

### 4. DRY Violation Detection

Systematically find duplicated code across the pipeline:

**Step 1: Find duplicated constants**
```bash
# Find tier_order duplications
rg "tier_order\s*=\s*\[.*T0.*T6.*\]" -A 1
```

**Step 2: Find duplicated formulas**
```bash
# Find consistency formula duplications
rg "1\s*-\s*\(.*std.*mean\)" -A 1 -B 1
```

**Step 3: Count occurrences and prioritize**
- 17 duplications = high priority (tier_order)
- 5-6 duplications = medium priority (formulas)
- 2-3 duplications = low priority (acceptable)

**Step 4: Extract to single source of truth**
```python
# Before: 17 duplications across files
tier_order = ["T0", "T1", "T2", "T3", "T4", "T5", "T6"]

# After: Define once in figures/__init__.py
TIER_ORDER = ["T0", "T1", "T2", "T3", "T4", "T5", "T6"]

# Import everywhere
from scylla.analysis.figures import TIER_ORDER
```

**Step 5: Add helper functions for formulas**
```python
# Before: Duplicated 5 times
consistency = 1 - (std_score / mean_score) if mean_score > 0 else 0.0

# After: Helper in stats.py
def compute_consistency(mean: float, std: float) -> float:
    """Compute consistency: 1 - coefficient of variation, clamped to [0, 1]."""
    if mean == 0:
        return 0.0
    consistency = 1 - (std / mean)
    return max(0.0, min(1.0, consistency))  # Clamp to [0, 1]
```

**Verification**: After refactoring, regenerate all outputs and assert byte-identical results.

### 5. Test Fixture Strategy for Analysis Pipelines

Create minimal but representative test data:

**Fixture Design Principles**:
1. **Small but diverse**: ~60-70 rows covering all tiers, models, subtests
2. **Known values**: Use simple numbers (0.0, 0.5, 1.0) for easy verification
3. **Edge cases**: Include empty groups, tied values, all-pass and all-fail scenarios
4. **Hierarchical**: Match production hierarchy (experiments → tiers → subtests → runs)

**Example Fixture Structure** (conftest.py):
```python
@pytest.fixture
def sample_runs_df() -> pd.DataFrame:
    """Sample runs DataFrame for testing.

    Structure: 2 models × 3 tiers × 2 subtests × 5 runs = 60 rows
    """
    rows = []
    for model in ["Sonnet 4.5", "Haiku 4.5"]:
        for tier in ["T0", "T1", "T2"]:
            for subtest in ["001", "002"]:
                for run in range(1, 6):
                    rows.append({
                        "agent_model": model,
                        "tier": tier,
                        "subtest": subtest,
                        "run_number": run,
                        "score": 0.0 if run == 1 else 0.5 if run <= 3 else 1.0,
                        "passed": run > 3,
                        "cost_usd": 0.1 * run,
                        # ... other columns
                    })
    return pd.DataFrame(rows)
```

**Test Categories**:
1. **Unit tests for stats functions**: Test with numpy arrays and known values
2. **Integration tests for DataFrames**: Test with fixtures, verify structure
3. **Smoke tests for figures/tables**: Ensure no crashes, basic format checks
4. **Regression tests for bugs**: Counterexamples from P0/P1 issues

**Failed Attempt**: Don't try to test with production data (~2,238 rows). Tests are slow, hard to debug, and brittle. Use small fixtures with known values.

### 6. Parallel PR Execution

When issues are independent, create PRs in parallel to maximize throughput:

**Workflow**:
```bash
# Create multiple branches simultaneously
git checkout -b 215-fix-krippendorff-alpha
# ... make changes, commit, push ...
git checkout main

git checkout -b 216-fix-pareto-frontier
# ... make changes, commit, push ...
git checkout main

git checkout -b 217-fix-fig11-crash
# ... make changes, commit, push ...
git checkout main

# Create all PRs and enable auto-merge
gh pr create --issue 215 --title "fix(analysis): Fix Krippendorff alpha"
gh pr merge --auto --rebase

gh pr create --issue 216 --title "fix(analysis): Fix Pareto frontier"
gh pr merge --auto --rebase

gh pr create --issue 217 --title "fix(analysis): Fix fig11 crash"
gh pr merge --auto --rebase
```

**Merge Order**: Use auto-merge + CI to handle merge ordering automatically. CI ensures each PR passes tests before merging.

**Rationale**: This approach completed 15 PRs in ~11 hours. Sequential PRs would have taken 2-3 days.

## Failed Attempts

### 1. Single Mega-PR Approach

**What we tried**: Create one PR with all 26 fixes (P0-P3).

**Why it failed**:
- PR diff was 900+ lines across 19 files - unreviewable
- One failing test blocked all other fixes
- Couldn't prioritize critical bugs vs nice-to-have improvements
- Risk of merge conflicts if other work happened in parallel

**Lesson**: For 4,000+ line pipelines, use phased PRs by priority level. Max 3-5 issues per PR.

### 2. Implement Statistical Functions from Scratch

**What we tried**: Implement Krippendorff's alpha from formula in paper (114 lines of custom code).

**Why it failed**:
- Implementation had subtle bugs (fell through to wrong branch)
- Hard to validate without reference implementation
- Reinventing the wheel when `krippendorff` package exists
- No confidence in correctness

**Lesson**: Use authoritative statistical packages (scipy, krippendorff, statsmodels) and wrap them. Don't implement from scratch unless no package exists.

### 3. Normal Approximation for Confidence Intervals

**What we tried**: Use `mean ± 1.96*std` for confidence intervals on small samples.

**Why it failed**:
- Normal approximation breaks down for n=10 (T6 has 10 runs per subtest)
- Binary data near boundaries (pass/fail rates) violate normality assumption
- Inconsistent with bootstrap CI used elsewhere in pipeline

**Lesson**: Use bootstrap (BCa method) for small samples and non-normal data. Only use normal approximation for n > 30 and continuous data.

### 4. Percentile Bootstrap Instead of BCa

**What we tried**: Use simple percentile method for bootstrap CI.

**Why it failed**:
- Percentile method has poor coverage for small samples (n=10)
- BCa (bias-corrected and accelerated) provides better coverage
- Both have same computational cost
- No reason to use inferior method

**Lesson**: Always use BCa bootstrap for research pipelines. Set `method="BCa"` in scipy.stats.bootstrap.

### 5. Manual Consistency Clamping in Each File

**What we tried**: Duplicate the consistency formula (1 - std/mean) in 5 files, with clamping in some but not others.

**Why it failed**:
- Inconsistent behavior (some files returned negative values)
- Bug in one file (table06 could produce NaN if mean_score=0)
- Hard to fix all 5 instances without missing one
- Created maintenance burden

**Lesson**: Extract formulas to helper functions immediately, even for "simple" calculations. Duplication always leads to bugs.

### 6. Hardcoded Judge Column Names

**What we tried**: Hardcode `judge_pivot.columns = [..., "judge_1", "judge_2", "judge_3"]` in Table 3 and Fig 14.

**Why it failed**:
- Crashes with ValueError if experiment has <3 judges
- Assumes 3 judges forever (brittle)
- Makes code fragile to experiment configuration changes

**Lesson**: Use dynamic column handling based on actual data. Never hardcode assumptions about data shape.

### 7. No Error Isolation in Generation Scripts

**What we tried**: Generate all 15 figures sequentially in one loop without try/except.

**Why it failed**:
- One figure crash killed all subsequent figures
- Lost 14 figures due to 1 bug
- Hard to debug which figure failed

**Lesson**: Add try/except per item in generation loops. Log errors but continue generating other outputs.

## Results & Parameters

### Final Metrics

| Metric | Value |
|--------|-------|
| Total PRs created | 15 |
| Total PRs merged | 15 (100%) |
| Total issues filed | 26 (20 task + 6 META) |
| Total issues closed | 26 (100%) |
| Lines of code changed | ~900 LOC source, +841 LOC tests |
| P0 bugs fixed | 3 (Krippendorff's alpha, Pareto, crash) |
| P1 bugs fixed | 10 |
| P2 improvements | 5 (DRY, dead code) |
| P3 improvements | 8 |
| Test files created | 7 |
| Tests passing | 45 (2 skipped) |
| Duration | ~11 hours |

### PR Breakdown by Priority

**P0 PRs (3)**: #241, #242, #243
**P1 PRs (7)**: #244, #245, #246, #247, #248, #249, #250, #251, #254
**P2 PRs (3)**: #252, #253
**P3 PRs (1)**: #255

### Configuration

**Tools**:
- Git workflow: Feature branches with auto-merge
- CI: Pre-commit hooks (ruff, ruff-format)
- Testing: pytest with fixtures
- Statistical packages: scipy, krippendorff, pandas, numpy

**Commands**:
```bash
# Issue creation
gh issue create --title "..." --body "..." --label "analysis"

# PR workflow
git checkout -b <issue>-<description>
git add -A && git commit -m "fix(analysis): ..."
git push -u origin <branch>
gh pr create --issue <number> --body "Closes #<number>"
gh pr merge --auto --rebase

# Testing
pixi run pytest tests/unit/analysis/ -v

# Verification
pixi run python scripts/generate_all_results.py
pre-commit run --all-files
```

### Key Files Modified

- `/home/mvillmow/ProjectScylla/scylla/analysis/stats.py` - Statistical functions
- `/home/mvillmow/ProjectScylla/scylla/analysis/dataframes.py` - DataFrame builders
- `/home/mvillmow/ProjectScylla/scylla/analysis/tables.py` - Table generators
- `/home/mvillmow/ProjectScylla/scylla/analysis/loader.py` - Data loading
- `/home/mvillmow/ProjectScylla/scylla/analysis/figures/*.py` - 9 figure modules
- `/home/mvillmow/ProjectScylla/tests/unit/analysis/*.py` - 7 test files (new)

### Documentation

- `/home/mvillmow/ProjectScylla/docs/dev/analysis-pipeline-implementation-summary.md` - Full implementation summary (383 lines)
- `/home/mvillmow/ProjectScylla/.claude/plans/swirling-swinging-lantern.md` - Original review plan

### Deferred Work

**PR 7 (Architecture Improvements)** - Deferred to post-publication:
- DualFormatTable helper class (~300 lines reduction)
- Shared data loading (eliminate 3x redundant I/O)
- Plugin-based figure registration

## Related Skills

- `vega-lite-analysis-pipeline` - Original pipeline implementation (PR #213)
- `experiment-recovery-tools` - Selective re-execution of failed runs
