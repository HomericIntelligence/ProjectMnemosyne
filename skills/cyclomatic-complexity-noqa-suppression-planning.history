---
name: cyclomatic-complexity-noqa-suppression-planning
description: "Planning patterns for auditing and addressing accumulated # noqa: C901 suppressions in a Python codebase. Use when: (1) an issue asks you to reduce or document C901 suppressions across multiple files, (2) deciding between raising max-complexity threshold vs. refactoring vs. adding rationale text to surviving suppressions, (3) the suppression count in an issue differs from what a codebase grep finds (count discrepancy risk), (4) planning a threshold change in pyproject.toml and needing to verify the impact before committing."
category: ci-cd
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
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
---

# Cyclomatic Complexity noqa Suppression Planning

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-13 |
| **Objective** | Plan an audit-style fix for accumulated `# noqa: C901` suppressions — either raising `max-complexity` threshold, adding rationale comments, or refactoring — based on actual measured complexity scores |
| **Outcome** | Planning session only (ProjectHephaestus #1195) — two-pronged approach proposed: raise threshold 10→12 + add rationale text to all surviving suppressions; refactoring deferred |
| **Verification** | unverified |
| **Source Issue** | ProjectHephaestus #1195 |

## When to Use

- An issue asks you to reduce, document, or justify accumulated `# noqa: C901` suppressions across multiple files.
- The suppression count in the issue title differs from what a codebase grep finds (see risk #2 below).
- You are deciding between three strategies: (A) raise `max-complexity` threshold, (B) add rationale text to surviving suppressions without changing code, (C) refactor to remove suppressions.
- You are about to change `max-complexity` in `pyproject.toml` and need to predict the impact.
- You need to verify a grep pattern used as a CI verification criterion actually matches the suppression format in your codebase.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. Verification status: `unverified` — planning session only, never executed.

### Quick Reference

```bash
# Step 0 — establish baseline BEFORE any changes
pixi run ruff check hephaestus/ --select C901 --statistics

# Step 1 — find all current suppressions with location
grep -rn "# noqa: C901" hephaestus/ scripts/

# Step 2 — measure McCabe score for each suppressed function
# (run ruff with the suppression temporarily removed on one file)
pixi run ruff check <file> --select C901 --no-cache 2>&1

# Step 3 — check current threshold in pyproject.toml
grep -A2 "max-complexity\|extend-select.*C901\|C901" pyproject.toml

# Step 4 — after threshold change, verify no new violations are exposed
pixi run ruff check hephaestus/ --select C901

# Step 5 — verify rationale grep pattern works before using in CI criterion
grep -n "noqa: C901" hephaestus/automation/planner.py
# Check: does the pattern "# noqa: C901  #" (two spaces) or "# noqa: C901 #" (one space) match?
echo "# noqa: C901  # rationale text" | grep -v "# noqa: C901  #"   # should print nothing if pattern is correct
echo "# noqa: C901 # rationale text" | grep -v "# noqa: C901  #"    # test single-space variant
```

### Detailed Steps

#### Phase 0 — Establish a Measured Baseline

Before writing any plan, run the baseline command. A plan that skips this is a hypothesis, not a plan.

```bash
pixi run ruff check hephaestus/ --select C901 --statistics
```

This tells you:
- How many violations ruff currently *sees* (before any suppression changes)
- Which files have suppressions that are *effectively hiding* violations

Then grep for all suppressions to get file:line pairs:

```bash
grep -rn "# noqa: C901" hephaestus/ scripts/
```

Count them and compare to the issue's stated count. Discrepancies (e.g., issue says 15, grep finds 13) require a git-log audit before proceeding:

```bash
git log --oneline --since="30 days ago" -- "*.py" | head -20
git log --oneline -S "noqa: C901" -- "*.py" | head -10
```

The discrepancy may indicate (a) stale issue, (b) files outside `hephaestus/` not checked, or (c) a recent PR already removed some.

#### Phase 1 — Measure Each Function's McCabe Score

For each suppressed function, temporarily remove its `# noqa: C901` comment and run ruff to get the exact score:

```bash
# Temporarily remove suppression, run ruff, restore
sed -i 's/  # noqa: C901//' hephaestus/automation/planner.py
pixi run ruff check hephaestus/automation/planner.py --select C901 --no-cache
git checkout hephaestus/automation/planner.py
```

Categorize results:

| Score Range | Implication |
| ----------- | ----------- |
| ≤ new threshold | Raising threshold removes need for suppression — just delete the `# noqa` line |
| new threshold + 1 to new threshold + 3 | Borderline — suppression survives but is close to cleanable |
| > new threshold + 5 | Suppression definitely survives; rationale is especially important |
| ≥ 20 | Consider real refactoring regardless of threshold |

#### Phase 2 — Choose a Strategy

Three options, from lowest risk to highest:

**Option A — Rationale-only (no threshold change, no refactoring)**
- Add `# noqa: C901  # <rationale>` to every suppression
- Risk: Does not reduce suppression count; reviewer may reject "pure documentation" approach
- Benefit: Zero code change, zero risk of exposing new violations

**Option B — Raise threshold + rationale for survivors (the issue #1195 plan)**
- Change `max-complexity = 10` → `max-complexity = 12` in `pyproject.toml`
- Remove `# noqa: C901` from functions with measured score ≤ 12
- Add `# noqa: C901  # <rationale>` to remaining functions with score > 12
- Risk: Raising threshold may expose violations ruff was already reporting as suppressed

**Option C — Refactor (see `ruff-specific-rule-fixes` skill)**
- Extract helper functions to reduce CC below threshold
- Risk: High scope; defer to follow-up PR

#### Phase 3 — Verify Grep Pattern Before Adding to CI

If you add a verification criterion like "all remaining suppressions must have rationale text," test the grep pattern before committing it:

```bash
# The double-space variant: "# noqa: C901  # rationale"
echo "# noqa: C901  # orchestrates N condition branches" | grep -c "# noqa: C901  #"   # must be 1
echo "# noqa: C901" | grep -c "# noqa: C901  #"                                         # must be 0

# Watch out: single-space variant "# noqa: C901 # rationale" will fail the double-space grep
echo "# noqa: C901 # rationale" | grep -c "# noqa: C901  #"   # returns 0 — false negative!
```

Pick one canonical format and enforce it consistently. The double-space convention (`# noqa: C901  #`) is common in this codebase but verify before assuming.

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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Writing a plan without measuring McCabe scores | Issue #1195 plan proposed raising threshold 10→12 to drop some suppressions | The plan never ran `ruff --select C901` to measure any function's actual score; the "some suppressions will drop" claim was a hypothesis, not a measurement | Always run `pixi run ruff check hephaestus/ --select C901 --statistics` BEFORE planning any threshold change — the baseline is the plan's foundation |
| Trusting the issue's suppression count | The issue title said "15 C901 suppressions" but a grep found only 13 | Two suppressions were unaccounted for — possibly removed by a prior PR, or in a location not searched | Grep the actual codebase first; when the count differs, check `git log -S "noqa: C901"` to find recent removals before writing the plan |
| Relying on a stale file reference in the issue | Issue cited `hephaestus/automation/implementer_phase_runner.py:255` as a suppression location | Grep found no suppression at that location — the file may have been refactored | Cross-reference every file:line citation in an issue against the actual codebase before building a plan around it |

## Results & Parameters

### Configuration (ProjectHephaestus at planning time)

```text
pyproject.toml:191   max-complexity = 10  (default Ruff C901 threshold)
scripts/** blanket-suppressed via per-file-ignores: ["scripts/**": ["C901"]]
hephaestus/ NOT blanket-suppressed — each violation requires an explicit # noqa
```

### Suppression Inventory (ProjectHephaestus #1195 audit, 2026-06-13)

| File | Line (approx) | Notes |
| ----- | -------------- | ----- |
| `hephaestus/automation/planner.py` | multiple | Largest concentration |
| `hephaestus/automation/implementer.py` | multiple | |
| `hephaestus/automation/review_loop.py` | multiple | |
| Total found by grep | 13 | Issue title said 15 — 2 unaccounted |

> **Caution**: Line numbers shift with every edit. Always re-grep before using as an implementation reference.

### Proposed Threshold Change

| Parameter | Before | Proposed | Risk |
| --------- | ------ | -------- | ---- |
| `max-complexity` | 10 | 12 | May expose functions that were at 11-12 and now no longer need `# noqa`; verify with a dry-run `ruff check` after the change before removing suppressions |

### Skill Relationship

- **`ruff-specific-rule-fixes`** — covers the *refactoring* approach (extract-method pattern, S101 conversions, linter-as-root-cause). Use that skill when the decision is to fix the violation by reducing CC.
- **This skill** — covers the *audit-and-document* approach (threshold change + rationale). Use this skill when the decision is to raise the threshold or document surviving suppressions without refactoring.
