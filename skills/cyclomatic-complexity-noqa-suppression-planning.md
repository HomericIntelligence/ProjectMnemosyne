---
name: cyclomatic-complexity-noqa-suppression-planning
description: "Planning patterns for auditing and addressing accumulated # noqa: C901 suppressions in a Python codebase. Use when: (1) an issue asks you to reduce or document C901 suppressions across multiple files, (2) deciding between raising max-complexity threshold vs. refactoring vs. adding rationale text to surviving suppressions, (3) the suppression count in an issue differs from what a codebase grep finds (count discrepancy risk), (4) planning a threshold change in pyproject.toml and needing to verify the impact before committing."
category: ci-cd
date: 2026-06-13
version: "1.2.0"
user-invocable: false
verification: verified-ci
history: cyclomatic-complexity-noqa-suppression-planning.history
tags:
  - ruff
  - C901
  - cyclomatic-complexity
  - noqa
  - suppression
  - planning
  - audit
  - max-complexity
  - pyproject
  - threshold
  - RUF100
  - unused-noqa
---

# Cyclomatic Complexity noqa Suppression Planning

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-13 |
| **Objective** | Plan an audit-style fix for accumulated `# noqa: C901` suppressions — either raising `max-complexity` threshold, adding rationale comments, or refactoring — based on actual measured complexity scores |
| **Outcome** | Completed and CI-verified (ProjectHephaestus #1195, PR #1285) — raised threshold 10→12, dropped 3 suppressions (CC ≤ 12), documented rationale on 10 survivors (CC 13–23); all ruff checks and unit tests green |
| **Verification** | verified-ci |
| **Source Issue** | ProjectHephaestus #1195 |
| **Related PR** | ProjectHephaestus #1285 |
| **History** | v1.0.0: initial planning patterns (3 failed attempts). v1.1.0: added measure-first requirement, RUF100 interaction, fragile grep hazard; updated Quick Reference with correct command sequence; added measured CC table. v1.2.0: promoted to verified-ci, added function-level CC table, added `noqa-on-def-line` rule. |

## When to Use

- An issue asks you to reduce, document, or justify accumulated `# noqa: C901` suppressions across multiple files.
- The suppression count in the issue title differs from what a codebase grep finds (see risk #2 below).
- You are deciding between three strategies: (A) raise `max-complexity` threshold, (B) add rationale text to surviving suppressions without changing code, (C) refactor to remove suppressions.
- You are about to change `max-complexity` in `pyproject.toml` and need to predict the impact.
- You need to verify a grep pattern used as a CI verification criterion actually matches the suppression format in your codebase.

## Verified Workflow

> **Verified:** This workflow was validated end-to-end in ProjectHephaestus PR #1285 (issue #1195). All ruff checks and unit tests passed in CI.

### Quick Reference

```bash
# Step 0: Measure FIRST (before writing any plan)
pixi run ruff check hephaestus/ --select C901 --ignore-noqa
# → gives exact CC scores for every suppressed function

# Step 1: Identify drop candidates (CC ≤ new threshold)
# Functions with CC ≤ 12 after raising threshold: drop # noqa: C901 entirely
# (keeping them would trigger RUF100 unused-noqa lint failures)

# Step 2: Change threshold in pyproject.toml
# max-complexity = 12

# Step 3: Drop suppressions on CC ≤ 12 functions

# Step 4: Add rationale to CC > 12 survivors
# Format: def fn(...):  # noqa: C901  # <why complexity is acceptable>

# Step 5: Verify
pixi run ruff check hephaestus/ --select C901   # no uninstrumented violations
pixi run ruff check hephaestus/ --select RUF100  # no unused noqa directives
pixi run ruff check hephaestus/ tests/           # full clean
pixi run pytest tests/unit -x -q
```

### Detailed Steps

#### Phase 0 — Measure FIRST (Critical: before writing any plan)

**Do not write a single keep/drop decision before running this command.** A plan written before measuring is a hypothesis, not a plan — it will be NOGO'd.

```bash
pixi run ruff check hephaestus/ --select C901 --ignore-noqa
```

The `--ignore-noqa` flag causes ruff to report all violations even where `# noqa` would normally suppress them. This gives exact McCabe scores for every suppressed function.

Example output for ProjectHephaestus #1195:
```
hephaestus/automation/review_loop.py:148:1: C901 `_run_review_iteration` is too complex (11 > 10)
hephaestus/automation/planner.py:392:1: C901 `_score_issues` is too complex (11 > 10)
hephaestus/automation/implementer.py:215:1: C901 `_build_prompt` is too complex (12 > 10)
hephaestus/automation/planner.py:201:5: C901 `_filter_issues` is too complex (13 > 10)
...
```

Also grep for all suppressions to confirm total count:

```bash
grep -rn "# noqa: C901" hephaestus/ scripts/
```

Count them and compare to the issue's stated count. Discrepancies require a git-log audit:

```bash
git log --oneline -S "noqa: C901" -- "*.py" | head -10
```

#### Phase 1 — Derive Drop/Keep Table from Measured Scores

After running `--ignore-noqa`, build a table of every suppressed function:

| Function | CC Score | Action |
| -------- | -------- | ------ |
| `<function_name>` | CC ≤ new threshold | Drop `# noqa: C901` — keeping it triggers RUF100 (unused-noqa) |
| `<function_name>` | CC > new threshold | Keep suppression + add rationale comment |

**RUF100 interaction (critical):** The ruff select list in `pyproject.toml` includes `RUF` (e.g., `select = ["E", "F", "RUF", ...]`). `RUF100` flags unused `# noqa` directives. After raising `max-complexity = 12`, any function with CC ≤ 12 that still has `# noqa: C901` will trigger `RUF100`. These suppressions MUST be dropped, not kept. Skipping this step causes the plan's own verification command to fail.

#### Phase 2 — Choose a Strategy

Three options, from lowest risk to highest:

**Option A — Rationale-only (no threshold change, no refactoring)**
- Add `# noqa: C901  # <rationale>` to every suppression
- Risk: Does not reduce suppression count; reviewer may reject "pure documentation" approach
- Benefit: Zero code change, zero risk of exposing new violations or RUF100 failures

**Option B — Raise threshold + rationale for survivors (the issue #1195 revised plan)**
- Run `pixi run ruff check hephaestus/ --select C901 --ignore-noqa` to measure all CC scores
- Change `max-complexity = 10` → `max-complexity = 12` in `pyproject.toml`
- **Drop** `# noqa: C901` from functions with measured score ≤ 12 (RUF100 requires this)
- **Keep + rationale** for remaining functions with score > 12
- Verify with `--select RUF100` to confirm no unused suppression directives remain

**Option C — Refactor (see `ruff-specific-rule-fixes` skill)**
- Extract helper functions to reduce CC below threshold
- Risk: High scope; defer to follow-up PR

#### Phase 3 — Use RUF100 (not grep) as Verification Criterion

When verifying that no unused `# noqa: C901` directives remain, prefer the authoritative ruff check over a fragile grep:

```bash
# PREFERRED: authoritative unused-noqa check
pixi run ruff check hephaestus/ --select RUF100

# FRAGILE: avoid as the sole verification criterion
grep -v "# noqa: C901  #"   # edge cases: single-space variant passes undetected
```

The grep pattern `"# noqa: C901  #"` (double-space) is fragile. A suppression formatted as `# noqa: C901 # rationale` (single space) passes the grep but `RUF100` catches it correctly.

If you do use grep as a secondary check, test the exact pattern against real codebase lines first:

```bash
echo "# noqa: C901  # rationale" | grep -c "# noqa: C901  #"   # must be 1
echo "# noqa: C901 # rationale" | grep -c "# noqa: C901  #"    # returns 0 — single-space false negative
echo "# noqa: C901" | grep -c "# noqa: C901  #"                # must be 0 (bare suppression caught)
```

#### Phase 4 — Write Rationale Text

Rationale text should explain WHY the complexity is acceptable, not just restate the situation. Good patterns:

```python
# Bad — no rationale
def _build_prompt(self, ...):  # noqa: C901

# Bad — rationale just restates the problem
def _build_prompt(self, ...):  # noqa: C901  # complex function

# Good — rationale explains why complexity is acceptable
def _build_prompt(self, ...):  # noqa: C901  # sequential prompt-section assembly; splitting would fragment context

# Good — rationale explains the refactoring risk
def _parse_response(self, ...):  # noqa: C901  # dispatch over 8 mutually exclusive response types; extract-method would need shared mutable state
```

**Critical: `# noqa` MUST be on the opening `def` line.** For multi-line signatures, this is the `def` keyword line, not the closing `) -> T:` line:

```python
# WRONG — noqa on closing paren/return-type line is silently ignored by ruff
def _drive_issue(
    self, issue_number: int
) -> WorkerResult:  # noqa: C901  # orchestration: ...  ← ruff ignores this!

# CORRECT — noqa on the def keyword line
def _drive_issue(  # noqa: C901  # orchestration: poll loop + required-check classification + CI-fix path
    self, issue_number: int
) -> WorkerResult:
```

Standard rationale categories used in this codebase:
- `orchestration:` — thread pools, retry loops, multi-path dispatch
- `validation:` — many independent rule checks, multi-format config loading
- `CLI dispatch:` — many command branches
- `pipeline:` — sequential conditional stages

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Writing a plan without measuring McCabe scores | Issue #1195 first plan assumed "raising max-complexity to 12 may remove some suppressions" without running `ruff check --ignore-noqa` to get actual scores | Reviewer NOGO'd: "some suppressions will drop" was a hypothesis, not a measurement; no function's CC score was known | Always run `pixi run ruff check hephaestus/ --select C901 --ignore-noqa` BEFORE writing any keep/drop decisions — the measured table is the plan's foundation |
| Keeping suppressions that fall ≤ new threshold | First plan kept all 13 `# noqa: C901` directives after raising threshold to 12 | `RUF100` (unused-noqa) is in the ruff select list (`pyproject.toml` selects `RUF`; `RUF100` not in ignore); 3 functions at CC 11, 11, 12 would have unused noqa → plan's own verification step 13 would fail | After determining the new threshold, any `# noqa: C901` on a function with CC ≤ new threshold MUST be dropped — keeping unused suppressions is a lint failure |
| Using fragile grep for verification | Plan criterion 2 used `grep -v "# noqa: C901  #"` (double-space) to detect bare suppressions | Single-space variant `# noqa: C901 # rationale` passes the grep undetected (false negative) | Use `pixi run ruff check hephaestus/ --select RUF100` as the authoritative unused-noqa check; supplement with grep only after testing the pattern against real codebase lines |
| Trusting the issue's suppression count | The issue title said "15 C901 suppressions" but a grep found only 13 | Two suppressions were unaccounted for — possibly removed by a prior PR, or in a location not searched | Grep the actual codebase first; when the count differs, check `git log -S "noqa: C901"` to find recent removals before writing the plan |
| Relying on a stale file reference in the issue | Issue cited `hephaestus/automation/implementer_phase_runner.py:255` as a suppression location | Grep found no suppression at that location — the file may have been refactored | Cross-reference every file:line citation in an issue against the actual codebase before building a plan around it |
| Placing `# noqa: C901` on the closing `) -> T:` line of a multi-line signature | Added the noqa comment to the closing paren/return-type line: `def _drive_issue(\n    self, n: int\n) -> WorkerResult:  # noqa: C901` | Ruff only honours `# noqa` on the opening `def` line; placing it on any other line in a multi-line signature silently fails — C901 fires anyway | Always place `# noqa: C901` on the `def` keyword line, not on the closing `):` or `-> T:` line of a multi-line function signature |

## Results & Parameters

### Configuration (ProjectHephaestus at planning time)

```text
pyproject.toml:191   max-complexity = 10  (default Ruff C901 threshold)
scripts/** blanket-suppressed via per-file-ignores: ["scripts/**": ["C901"]]
hephaestus/ NOT blanket-suppressed — each violation requires an explicit # noqa
pyproject.toml selects RUF (includes RUF100 unused-noqa); RUF100 not in ignore list
```

### Measured CC Scores (ProjectHephaestus #1195, `--ignore-noqa` output, 2026-06-13)

Function-level breakdown (verified against actual `ruff check --select C901 --ignore-noqa` output):

| Function | File | CC | Action at threshold 12 |
| -------- | ---- | -- | ----------------------- |
| `_sweep_orphaned_arming_records` | `ci_driver.py` | 11 | **DROPPED** (RUF100 would flag as unused) |
| `implementer.run` | `implementer.py` | 11 | **DROPPED** (RUF100 would flag as unused) |
| `loop_runner.main` | `loop_runner.py` | 12 | **DROPPED** (RUF100 would flag as unused) |
| `is_plan_review_go` | `review_state.py` | 13 | KEPT + rationale |
| `tidy.main` | `tidy.py` | 13 | KEPT + rationale |
| `_implement_all` | `implementer.py` | 14 | KEPT + rationale |
| `run_follow_up_issues` | `follow_up.py` | 14 | KEPT + rationale |
| `_discover_prs` | `ci_driver.py` | 15 | KEPT + rationale |
| `ci_driver.run` | `ci_driver.py` | 18 | KEPT + rationale |
| `pr_merge.main` | `pr_merge.py` | 18 | KEPT + rationale |
| `ci_driver._run_ci_fix_session` | `ci_driver.py` | 20 | KEPT + rationale |
| `version/manager.verify` | `manager.py` | 20 | KEPT + rationale |
| `ci_driver._drive_issue` | `ci_driver.py` | 23 | KEPT + rationale |
| **Total** | | **13** | **3 drop, 10 keep** |

### Proposed Threshold Change

| Parameter | Before | Proposed | Risk |
| --------- | ------ | -------- | ---- |
| `max-complexity` | 10 | 12 | 3 functions (CC 11, 11, 12) must have `# noqa: C901` dropped or RUF100 will fail; 10 functions (CC 13–23) survive with rationale |

### Skill Relationship

- **`ruff-specific-rule-fixes`** — covers the *refactoring* approach (extract-method pattern, S101 conversions, linter-as-root-cause). Use that skill when the decision is to fix the violation by reducing CC.
- **This skill** — covers the *audit-and-document* approach (threshold change + rationale). Use this skill when the decision is to raise the threshold or document surviving suppressions without refactoring.
