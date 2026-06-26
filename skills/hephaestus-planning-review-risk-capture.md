---
name: hephaestus-planning-review-risk-capture
description: "Plan-review checklist for ProjectHephaestus automation refactors that centralize repeated state-directory path construction. Use when: (1) an issue title and body appear to disagree, (2) a plan introduces DEFAULT_STATE_DIR or ensure_state_dir(), (3) repeated state_dir literals are being collapsed, (4) reviewer confidence depends on grep coverage over hephaestus/automation."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - projecthephaestus
  - planning
  - plan-review
  - state-dir
  - automation
  - path-construction
  - refactoring-risk
---

# ProjectHephaestus Planning Review: State Directory Risk Capture

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Preserve the review risks from a ProjectHephaestus issue #1393 implementation plan that proposed centralizing repeated automation state-directory path construction behind `DEFAULT_STATE_DIR` and `ensure_state_dir()`. |
| **Outcome** | Planning guidance captured; implementation was not executed as part of this learning. |
| **Verification** | unverified |

This skill is about the plan-review risks, not the full implementation. Treat it as a checklist for reviewers deciding whether a state-directory centralization plan is precise enough to implement safely.

## When to Use

- Reviewing a ProjectHephaestus plan that centralizes repeated `Path("automation_state")` or similar automation state-directory construction.
- A plan introduces `DEFAULT_STATE_DIR`, `ensure_state_dir()`, or another helper for directory creation semantics.
- The issue title names one symbol, such as `_build_parser`, but the plan infers that the implementation target is different based on the body or proposed solution.
- A plan claims all production construction sites were found with one grep over `hephaestus/automation`.
- A reviewer needs to distinguish behavioral preservation from replacing duplicated magic strings with a constant.

## Verified Workflow

### Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Re-verify the issue before accepting the plan target.
gh issue view 1393 --repo HomericIntelligence/ProjectHephaestus --comments

# Do not rely on plan snapshot line numbers.
rg -n "automation_state|state_dir|DEFAULT_STATE_DIR|ensure_state_dir" hephaestus tests scripts

# Confirm every production construction site, then classify explicit injection separately.
rg -n "Path\\(.+automation_state|mkdir\\(|state_dir\\s*=" hephaestus/automation tests/unit/automation

# After implementation, prove the helper preserves creation semantics.
rg -n "parents=True|exist_ok=True|AuditReviewer\\(state_dir=" hephaestus/automation tests
```

### Detailed Steps

1. **Verify the issue target before approving the plan.**
   In the issue #1393 plan, the title mentioned `_build_parser`, but the plan inferred that wording was stale based on the issue body and proposed solution. A reviewer should open the live issue before treating the target as settled.

2. **Evaluate the helper's module boundary, not just the first convenient home.**
   The plan assumed `_review_utils.py` was the right home for `DEFAULT_STATE_DIR` and `ensure_state_dir()` because it already contains shared automation helpers. That may be correct, especially if it avoids import cycles, but reviewers should still ask whether a narrower state/path module would be clearer and safer.

3. **Rerun broader searches before implementation.**
   The plan assumed a single grep over `hephaestus/automation` found all production construction sites, including `BaseReviewer`, `IssueImplementer`, `implementer.main`, `CIDriver`, `AuditReviewer`, and `PlannerReviewLoop`. Before coding, rerun searches across `hephaestus`, `tests`, and `scripts`, then classify each hit as production construction, explicit dependency injection, docs, or test fixture.

4. **Preserve directory creation semantics exactly.**
   Any helper replacing local construction must preserve `mkdir(parents=True, exist_ok=True)` behavior wherever that behavior existed. Tests should assert behavior such as nested parent creation and idempotent reuse, not merely that callers reference a shared constant.

5. **Do not collapse explicit injection behavior.**
   `AuditReviewer(state_dir=...)` and similar explicit arguments are a contract. A central helper may supply defaults, but it must not erase caller-provided paths or silently redirect injected state directories.

6. **Use import-cycle checks as a gate.**
   If the helper lives in `_review_utils.py`, prove that importing the modules that consume it does not introduce cycles. If a narrower module is chosen, prove the same. Static reasoning is not enough for this kind of shared automation utility.

7. **Require tests that catch behavioral regressions.**
   A weak test only checks that duplicated literals are gone or that one constant name exists. Stronger tests exercise default directory creation, injected directory preservation, and the production call paths that previously built the directory themselves.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat issue title as authoritative | The plan topic was accepted from a title mentioning `_build_parser` while the body/proposed solution appeared to point at state-directory centralization | The title could be stale; implementing the wrong target wastes a review cycle or changes unrelated code | Open the live issue and reconcile title, body, proposed solution, and acceptance criteria before approving the target |
| Pick `_review_utils.py` solely because it is shared | The plan placed `DEFAULT_STATE_DIR` and `ensure_state_dir()` in `_review_utils.py` because shared automation helpers already live there | That may avoid cycles, but it may also broaden a review utility module into state/path ownership without considering a narrower module | Review module ownership explicitly and require an import-cycle smoke test for the chosen home |
| Trust one grep over `hephaestus/automation` | The plan listed `BaseReviewer`, `IssueImplementer`, `implementer.main`, `CIDriver`, `AuditReviewer`, and `PlannerReviewLoop` as all production construction sites | A narrow grep can miss scripts, tests that encode production contracts, or indirect construction patterns | Rerun broader searches over `hephaestus`, `tests`, and `scripts`, then classify every hit |
| Replace literals without proving behavior | Tests only assert a shared constant or fewer duplicated strings | This can pass while changing `mkdir(parents=True, exist_ok=True)` semantics or breaking injected `state_dir` behavior | Test nested parent creation, idempotency, and explicit override preservation |
| Over-migrate documentation and fixtures | A plan treats every literal occurrence as production duplication | Docs and tests may intentionally preserve examples, fixtures, or assertions about old behavior | Collapse production definitions to one canonical source without blindly rewriting docs or unrelated test data |

## Results & Parameters

### Reviewer Focus Checklist

```text
- [ ] Issue #1393 was re-read live; title/body/proposed-solution mismatch resolved.
- [ ] All cited line numbers were treated as snapshot hints, not stable edit targets.
- [ ] Broader search covered hephaestus/, tests/, and scripts/, not only hephaestus/automation.
- [ ] Every hit was classified: production construction, explicit injection, fixture, docs, or unrelated.
- [ ] Helper location was justified against module ownership and import-cycle risk.
- [ ] Directory creation still uses parents=True and exist_ok=True where required.
- [ ] Explicit AuditReviewer(state_dir=...) and comparable overrides still win over defaults.
- [ ] Tests prove behavior, not just constant reuse or string-count reduction.
- [ ] Production literals collapse to one canonical definition without over-migrating docs/tests.
```

### Unverified Reliances to Carry Forward

- The plan's line numbers came from a snapshot and may drift.
- The issue #1393 body and proposed solution were referenced indirectly from the plan text and were not re-verified during this learning capture.
- Behavior of `pixi` test commands, GitHub issue/PR metadata, and the current ProjectHephaestus code layout must be verified live before coding.
- The listed production sites are review leads, not a complete inventory until broad searches confirm them.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1393 planning review context | unverified planning guidance derived from a plan-review risk capture; no implementation or end-to-end workflow was executed |
