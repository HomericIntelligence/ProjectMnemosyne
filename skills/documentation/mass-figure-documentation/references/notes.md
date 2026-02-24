# Technical Notes: Mass Figure Documentation

## Session Details

**Date**: 2026-02-12
**Duration**: ~3 hours
**Objective**: Document all 30 analysis figures in `scylla/analysis/figures/`
**Method**: 30 parallel background agents with Sonnet 4.5

## Source Files Analyzed

### Figure Implementation Files (13 files)

```
scylla/analysis/figures/
├── variance.py (6 figures: fig01, fig03, fig16a, fig16b, fig18a, fig18b)
├── judge_analysis.py (3 figures: fig02, fig14, fig17)
├── tier_performance.py (2 figures: fig04, fig05)
├── cost_analysis.py (3 figures: fig06, fig08, fig22)
├── token_analysis.py (1 figure: fig07)
├── criteria_analysis.py (1 figure: fig09)
├── model_comparison.py (2 figures: fig11, fig12)
├── subtest_detail.py (4 figures: fig13, fig15a, fig15b, fig15c)
├── effect_size.py (1 figure: fig19)
├── correlation.py (2 figures: fig20, fig21)
├── diagnostics.py (2 figures: fig23, fig24)
├── impl_rate_analysis.py (3 figures: fig25, fig26, fig27)
└── spec_builder.py (utilities)
```

## Figure-to-Issue Mapping (Complete)

| Figure | Issue | Function | Source File | Output Filename |
|--------|-------|----------|-------------|-----------------|
| fig01 | #441 | `fig01_score_variance_by_tier` | variance.py:18-52 | score-variance-by-tier.md |
| fig02 | #447 | `fig02_judge_variance` | judge_analysis.py:18-61 | judge-variance.md |
| fig03 | #442 | `fig03_failure_rate_by_tier` | variance.py:55-119 | failure-rate-by-tier.md |
| fig04 | #450 | `fig04_pass_rate_by_tier` | tier_performance.py:18-71 | pass-rate-by-tier.md |
| fig05 | #451 | `fig05_grade_heatmap` | tier_performance.py:74-150 | grade-heatmap.md |
| fig06 | #452 | `fig06_cop_by_tier` | cost_analysis.py:18-57 | cost-of-pass-by-tier.md |
| fig07 | #455 | `fig07_token_distribution` | token_analysis.py:17-102 | token-distribution.md |
| fig08 | #453 | `fig08_cost_quality_pareto` | cost_analysis.py:60-207 | cost-quality-pareto-frontier.md |
| fig09 | #456 | `fig09_criteria_by_tier` | criteria_analysis.py:17-117 | criteria-performance-by-tier.md |
| fig11 | #457 | `fig11_tier_uplift` | model_comparison.py:27-* | tier-uplift.md |
| fig12 | #458 | `fig12_consistency` | model_comparison.py:177-* | consistency-analysis.md |
| fig13 | #459 | `fig13_latency` | subtest_detail.py:17-84 | latency-analysis.md |
| fig14 | #448 | `fig14_judge_agreement` | judge_analysis.py:64-170 | judge-agreement.md |
| fig15a | #460 | `fig15a_subtest_run_heatmap` | subtest_detail.py:87-150 | subtest-run-heatmap.md |
| fig15b | #461 | `fig15b_subtest_best_heatmap` | subtest_detail.py:153-228 | subtest-best-run-heatmap.md |
| fig15c | #462 | `fig15c_tier_summary_heatmap` | subtest_detail.py:231-290 | tier-summary-heatmap.md |
| fig16a | #443 | `fig16a_success_variance_per_subtest` | variance.py:122-217 | success-variance-per-subtest.md |
| fig16b | #444 | `fig16b_success_variance_aggregate` | variance.py:220-321 | success-variance-aggregate.md |
| fig17 | #449 | `fig17_judge_variance_overall` | judge_analysis.py:173-268 | judge-variance-overall.md |
| fig18a | #445 | `fig18a_failure_rate_per_subtest` | variance.py:324-396 | failure-rate-per-subtest.md |
| fig18b | #446 | `fig18b_failure_rate_aggregate` | variance.py:399-468 | failure-rate-aggregate.md |
| fig19 | #463 | `fig19_effect_size_forest` | effect_size.py:18-* | effect-size-forest-plot.md |
| fig20 | #464 | `fig20_metric_correlation_heatmap` | correlation.py:19-* | metric-correlation-heatmap.md |
| fig21 | #465 | `fig21_cost_quality_regression` | correlation.py:136-* | cost-quality-regression.md |
| fig22 | #454 | `fig22_cumulative_cost` | cost_analysis.py:209-284 | cumulative-cost.md |
| fig23 | #466 | `fig23_qq_plots` | diagnostics.py:20-* | qq-plots-for-normality.md |
| fig24 | #467 | `fig24_score_histograms` | diagnostics.py:161-* | score-histograms.md |
| fig25 | #468 | `fig25_impl_rate_by_tier` | impl_rate_analysis.py:25-153 | implementation-rate-by-tier.md |
| fig26 | #469 | `fig26_impl_rate_vs_pass_rate` | impl_rate_analysis.py:156-* | implementation-rate-vs-pass-rate.md |
| fig27 | #470 | `fig27_impl_rate_distribution` | impl_rate_analysis.py:237-340 | implementation-rate-distribution.md |

## Agent Execution Timeline

### Batch 1 (10 agents) - Launched at T+0
- fig01 (#441) - ⚠️ Old naming
- fig03 (#442) - ⚠️ Old naming
- fig16a (#443) - ⚠️ Old naming
- fig16b (#444) - ⚠️ Old naming
- fig18a (#445) - ⚠️ Old naming
- fig18b (#446) - ⚠️ Old naming
- fig02 (#447) - ⚠️ Old naming (already existed)
- fig14 (#448) - ⚠️ Old naming
- fig17 (#449) - ⚠️ Old naming
- fig04 (#450) - ⚠️ Old naming

**User intervention**: Requested removal of figure numbers from filenames

### Batch 2 (10 agents) - Launched at T+5min
- fig05 (#451) - ✅ Correct naming
- fig06 (#452) - ✅ Correct naming
- fig08 (#453) - ✅ Correct naming
- fig22 (#454) - ✅ Correct naming
- fig07 (#455) - ✅ Correct naming
- fig09 (#456) - ✅ Correct naming
- fig11 (#457) - ✅ Correct naming
- fig12 (#458) - ✅ Correct naming
- fig13 (#459) - ✅ Correct naming
- fig15a (#460) - ✅ Correct naming

### Batch 3 (10 agents) - Launched at T+10min
- fig15b (#461) - ✅ Correct naming
- fig15c (#462) - ✅ Correct naming
- fig19 (#463) - ✅ Correct naming
- fig20 (#464) - ✅ Correct naming
- fig21 (#465) - ✅ Correct naming
- fig23 (#466) - ✅ Correct naming
- fig24 (#467) - ✅ Correct naming
- fig25 (#468) - ✅ Correct naming
- fig26 (#469) - ✅ Correct naming
- fig27 (#470) - ✅ Correct naming

### Completion Order

1. fig16a (PR #545) - First completion
2. fig11 (PR #547) - Correct naming
3. fig18a (PR #546) - MERGED
4. fig16b (PR #549)
5. fig01 (PR #548) - MERGED
6. ... (remaining completions)

## Pull Request Statistics

### Created PRs (31 total)

**Figure documentation PRs (29)**:
- #545-#573 (gaps due to non-sequential PR numbers)
- 15+ merged within 3 hours
- 14+ pending CI checks (auto-merge enabled)

**Standardization PRs (2)**:
- #574: Renamed 7 files (MERGED immediately)
- #575: Renamed 3 remaining files (pending CI)

### Auto-Merge Configuration

All PRs used:
```bash
gh pr merge --auto --rebase
```

This ensures:
- Automatic merge when CI passes
- Linear git history (rebase strategy)
- No manual intervention required

## Naming Convention Evolution

### Initial Convention (Batch 1)
```
figNN-descriptive-name.md
Examples:
- fig01-score-variance-by-tier.md
- fig02-judge-variance.md
```

### Final Convention (Batch 2+3)
```
descriptive-name.md
Examples:
- score-variance-by-tier.md
- judge-variance.md
```

### Standardization Process

**PR #574** (7 files from main branch):
```bash
git mv fig01-score-variance-by-tier.md score-variance-by-tier.md
git mv fig02-judge-variance.md judge-variance.md
git mv fig14-judge-agreement.md judge-agreement.md
git mv fig16a-success-variance-per-subtest.md success-variance-per-subtest.md
git mv fig17-judge-variance-overall.md judge-variance-overall.md
git mv fig18a-failure-rate-per-subtest.md failure-rate-per-subtest.md
git mv fig18b-failure-rate-aggregate.md failure-rate-aggregate.md
```

**PR #575** (3 files from recent merges):
```bash
git mv fig03-failure-rate-by-tier.md failure-rate-by-tier.md
git mv fig04-pass-rate-by-tier.md pass-rate-by-tier.md
git mv fig16b-success-variance-aggregate.md success-variance-aggregate.md
```

## Agent Prompt Template

```markdown
Document figure {fig_id} for issue #{issue}.

Create markdown at `docs/design/figures/{filename}.md` (NO figure number) with 9 sections.

Source: `{source_file}:{line_start}-{line_end}` (function `{function_name}`)

Key details:
- {technical_detail_1}
- {technical_detail_2}
- {technical_detail_3}

Create worktree, write doc, commit, push branch `{issue}-doc-{fig}`,
create PR for #{issue}, enable auto-merge, cleanup worktree.
```

### Example Prompt (fig01)

```markdown
Document figure fig01 for issue #441.

Create markdown at `docs/design/figures/fig01-score-variance-by-tier.md` with 9 sections.

Source: `scylla/analysis/figures/variance.py:18-52` (function `fig01_score_variance_by_tier`)

Key details:
- Histogram with 0.05 bin width
- Faceted by tier (column facets)
- Shows score distribution (0-1 range)
- Data source: runs_df["tier", "score"]

Create worktree, write doc, commit, push branch `441-doc-fig01`,
create PR for #441, enable auto-merge, cleanup worktree.
```

## Documentation Quality Metrics

### Average Documentation Length
- Minimum: 230 lines (fig13 - latency)
- Maximum: 882 lines (fig09 - criteria performance)
- Average: ~350-450 lines per figure

### Content Breakdown (Typical)
- Overview: 50-75 lines
- Purpose: 75-100 lines
- Data Source: 50-75 lines
- Mathematical Formulas: 100-150 lines (with LaTeX)
- Theoretical Foundation: 150-200 lines
- Visualization Details: 75-100 lines
- Interpretation Guidelines: 150-250 lines
- Related Figures: 50-75 lines
- Code Reference: 100-150 lines

## Key Learnings

### What Worked Well

1. **Parallel execution**: 30 agents completed in ~3 hours vs 30+ hours sequentially
2. **Background mode**: Main conversation remained uncluttered
3. **Sonnet model**: Good balance of quality and cost for technical documentation
4. **Detailed prompts**: Agents had all context needed without conversation history
5. **Auto-merge**: PRs merged automatically without manual intervention
6. **Git worktrees**: Isolated work prevented conflicts between agents

### What Could Be Improved

1. **Naming convention**: Should have been finalized before launching first batch
2. **Pre-flight checks**: Should verify which figures already have documentation
3. **Progress tracking**: Could create a tracking comment on #471 with checkboxes
4. **Batch sizing**: Could start with 5 agents to validate template before scaling
5. **Error handling**: Could implement retry logic for failed agents

### Unexpected Successes

1. **Agent quality**: Documentation was consistently high-quality across all 30 agents
2. **LaTeX formatting**: Agents correctly formatted mathematical formulas
3. **Cross-references**: Agents identified and linked related figures accurately
4. **Code references**: Agents extracted correct line numbers and function names
5. **Git history**: File renames preserved history using `git mv`

## Reusability

This pattern can be reused for:

- **API documentation**: Document 50+ API endpoints
- **Test documentation**: Document 100+ test cases
- **Configuration documentation**: Document 30+ config options
- **Command documentation**: Document 40+ CLI commands
- **Component documentation**: Document 60+ React components

### Adaptation Checklist

- [ ] Define documentation template (sections required)
- [ ] Create issue-to-item mapping
- [ ] Extract source code locations
- [ ] Identify key technical details per item
- [ ] Finalize naming convention
- [ ] Launch agents in batches (5-10-15 pattern)
- [ ] Monitor completions
- [ ] Create standardization PR if needed
- [ ] Verify all PRs have auto-merge enabled
- [ ] Post summary to tracking issue
