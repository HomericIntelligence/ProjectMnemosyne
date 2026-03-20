---
name: rename-figure-convention
description: 'TRIGGER CONDITIONS: Renaming figure functions to match the fig{NN}_{description}
  sequential naming convention in ProjectScylla. Use when: (1) figure functions use
  ad-hoc names instead of sequential numbers (e.g. fig_r_prog_by_tier instead of fig28_r_prog_by_tier),
  (2) --list-figures output is out of alphabetical/sequential order, (3) a follow-up
  issue asks to standardize figure naming after figures were wired with unsequenced
  names.'
category: evaluation
date: 2026-03-02
version: 1.0.0
user-invocable: false
---
# rename-figure-convention

How to rename figure functions from ad-hoc names to the `fig{NN}_{description}` sequential convention used throughout ProjectScylla, covering all touch points in source, registry, and tests.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-02 |
| Objective | Rename `fig_r_prog_by_tier`, `fig_cfp_by_tier`, `fig_pr_revert_by_tier` → `fig28_r_prog_by_tier`, `fig29_cfp_by_tier`, `fig30_pr_revert_by_tier` |
| Outcome | Success — 4 files updated atomically, all 69 analysis tests pass, pre-commit clean |
| Issue | HomericIntelligence/ProjectScylla#1199 |
| PR | HomericIntelligence/ProjectScylla#1302 |

## When to Use

- `--list-figures` output is not in alphabetical/sequential order because some figures lack the `fig{NN}` prefix
- A follow-up issue from `wire-figure-pipeline` asks to assign sequential numbers to newly-wired figures
- An issue title contains "standardize figure naming" or "rename figures to fig## convention"
- Grep reveals figure names in `FIGURES` dict that don't match `fig\d+_` pattern

## Naming Convention

All figure functions and their output files must follow:

```
fig{NN}_{description}
```

Where `NN` is a zero-padded two-digit integer assigned sequentially from the current highest figure number. Examples: `fig01_score_variance_by_tier`, `fig27_impl_rate_distribution`, `fig28_r_prog_by_tier`.

**To find the current highest number:**

```bash
grep -E '"fig[0-9]+_' scripts/generate_figures.py | grep -oE 'fig[0-9]+' | sort -V | tail -1
```

## Touch Points (All 4 Must Be Updated Atomically)

A figure rename touches exactly 4 files:

| File | What changes |
|------|-------------|
| `scylla/analysis/figures/{module}.py` | Function name, `save_figure()` name arg, logger warning strings, module docstring |
| `scripts/generate_figures.py` | Import names, FIGURES dict keys and values |
| `tests/unit/analysis/test_figures.py` | Registry assertion strings, smoke test function names, import names, `.vl.json` filename assertions |
| `tests/unit/analysis/test_process_metrics_integration.py` | Smoke test function names, import names, call sites, `.vl.json` filename assertions |

**Do all four files in a single commit.** Partial renames cause import errors in the test collection phase.

## Verified Workflow

### Step 1: Confirm next available figure numbers

```bash
grep -E '"fig[0-9]+_' scripts/generate_figures.py | grep -oE 'fig[0-9]+' | sort -V | tail -3
# Example output: fig25, fig26, fig27  →  next is fig28
```

### Step 2: Update the figure module (`scylla/analysis/figures/{module}.py`)

For each function being renamed (example: `fig_r_prog_by_tier` → `fig28_r_prog_by_tier`):

1. **Module docstring** — replace old figure label with new number:
   ```python
   # Old: Generates Fig_RProg (R_Prog by tier), ...
   # New: Generates Fig 28 (R_Prog by tier), ...
   ```

2. **Function definition line**:
   ```python
   # Old: def fig_r_prog_by_tier(...)
   # New: def fig28_r_prog_by_tier(...)
   ```

3. **Function docstring first line**:
   ```python
   # Old: """Generate Fig_RProg: Fine-Grained Progress Rate by Tier.
   # New: """Generate Fig 28: Fine-Grained Progress Rate by Tier.
   ```

4. **Logger warning strings** — update all `skipping fig_*` references:
   ```python
   # Old: logger.warning("... skipping fig_r_prog_by_tier")
   # New: logger.warning("... skipping fig28_r_prog_by_tier")
   ```

5. **`save_figure()` call** — the name argument becomes the output filename:
   ```python
   # Old: save_figure(chart, "fig_r_prog_by_tier", output_dir, render)
   # New: save_figure(chart, "fig28_r_prog_by_tier", output_dir, render)
   ```

### Step 3: Update `scripts/generate_figures.py`

1. **Imports** — rename all three imported symbols:
   ```python
   # Old:
   from scylla.analysis.figures.process_metrics import (
       fig_cfp_by_tier,
       fig_pr_revert_by_tier,
       fig_r_prog_by_tier,
   )
   # New:
   from scylla.analysis.figures.process_metrics import (
       fig28_r_prog_by_tier,
       fig29_cfp_by_tier,
       fig30_pr_revert_by_tier,
   )
   ```

2. **FIGURES dict keys and values**:
   ```python
   # Old:
   "fig_r_prog_by_tier": ("tier", fig_r_prog_by_tier),
   "fig_cfp_by_tier": ("tier", fig_cfp_by_tier),
   "fig_pr_revert_by_tier": ("tier", fig_pr_revert_by_tier),
   # New:
   "fig28_r_prog_by_tier": ("tier", fig28_r_prog_by_tier),
   "fig29_cfp_by_tier": ("tier", fig29_cfp_by_tier),
   "fig30_pr_revert_by_tier": ("tier", fig30_pr_revert_by_tier),
   ```

### Step 4: Update `tests/unit/analysis/test_figures.py`

1. **Registry presence assertions**:
   ```python
   # Old: assert "fig_r_prog_by_tier" in FIGURES
   # New: assert "fig28_r_prog_by_tier" in FIGURES
   ```

2. **Category assertions**:
   ```python
   # Old: assert FIGURES["fig_r_prog_by_tier"][0] == "tier"
   # New: assert FIGURES["fig28_r_prog_by_tier"][0] == "tier"
   ```

3. **Smoke test function names**:
   ```python
   # Old: def test_fig_r_prog_by_tier(sample_runs_df, tmp_path):
   # New: def test_fig28_r_prog_by_tier(sample_runs_df, tmp_path):
   ```

4. **Imports inside smoke tests**:
   ```python
   # Old: from scylla.analysis.figures.process_metrics import fig_r_prog_by_tier
   # New: from scylla.analysis.figures.process_metrics import fig28_r_prog_by_tier
   ```

5. **`.vl.json` existence assertions**:
   ```python
   # Old: assert (tmp_path / "fig_r_prog_by_tier.vl.json").exists()
   # New: assert (tmp_path / "fig28_r_prog_by_tier.vl.json").exists()
   ```

6. **Non-existence assertions** (missing-columns tests):
   ```python
   # Old: assert not (tmp_path / "fig_r_prog_by_tier.vl.json").exists()
   # New: assert not (tmp_path / "fig28_r_prog_by_tier.vl.json").exists()
   ```

### Step 5: Update `tests/unit/analysis/test_process_metrics_integration.py`

Same pattern as Step 4 — apply all six sub-changes to smoke tests, skip tests, and all-null tests.

### Step 6: Grep-verify — zero stale references

```bash
grep -rn "fig_r_prog_by_tier\|fig_cfp_by_tier\|fig_pr_revert_by_tier" . \
  --include="*.py" --include="*.md" --include="*.yaml"
# Expected: no matches (or only the original issue prompt file)
```

### Step 7: Run tests and pre-commit

```bash
# Run targeted analysis tests
pixi run python -m pytest tests/unit/analysis/ -v

# Pre-commit on changed files
pre-commit run --files \
  scylla/analysis/figures/process_metrics.py \
  scripts/generate_figures.py \
  tests/unit/analysis/test_figures.py \
  tests/unit/analysis/test_process_metrics_integration.py
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Critical Lesson: Plan the Target Numbers First

The `mass-figure-documentation` skill documented a cautionary lesson: if you start editing before confirming the target numbers, you risk mid-flight inconsistency. The correct sequence is:

1. **Confirm ceiling** (`grep` the FIGURES dict for the current highest `fig{NN}`)
2. **Choose target numbers** (ceiling + 1, +2, +3…)
3. **Edit all touch points atomically** in a single commit

Do **not** rename some functions to fig28/29/30 and leave others with old names across multiple commits — the import in `generate_figures.py` will fail between commits.

## Results & Parameters

### Figure number assignment (issue #1199)

| Old name | New name | Number |
|----------|----------|--------|
| `fig_r_prog_by_tier` | `fig28_r_prog_by_tier` | 28 |
| `fig_cfp_by_tier` | `fig29_cfp_by_tier` | 29 |
| `fig_pr_revert_by_tier` | `fig30_pr_revert_by_tier` | 30 |

Confirmed: fig27 (`fig27_impl_rate_distribution`) was the previous ceiling.

### Test counts

69 analysis unit tests pass post-rename (no net change — renaming tests is 1:1).

### Pre-commit result

All hooks pass: ruff-format, ruff-check, mypy, unit-test-structure.

## Relationship to `wire-figure-pipeline` Skill

This skill is the **follow-up pattern** to `wire-figure-pipeline`:

1. `wire-figure-pipeline` — adds a new figure to `generate_figures.py` (may use an ad-hoc name initially)
2. `rename-figure-convention` — standardizes the name to `fig{NN}` after the ceiling is confirmed

When filing issues after `wire-figure-pipeline`, note whether the wired figures used unsequenced names — if so, file a follow-up referencing this skill.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1199, PR #1302 | Follow-up from #1136 (wire-figure-pipeline) |

## References

- Related skill: `wire-figure-pipeline` (prerequisite pattern)
- Related skill: `mass-figure-documentation` (cautionary lesson on renaming mid-flight)
- Source file: `scylla/analysis/figures/process_metrics.py`
- Registry file: `scripts/generate_figures.py`
- Test files: `tests/unit/analysis/test_figures.py`, `tests/unit/analysis/test_process_metrics_integration.py`
