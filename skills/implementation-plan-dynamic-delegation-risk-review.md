---
name: implementation-plan-dynamic-delegation-risk-review
description: "Reviewer checklist for unverified plans that replace explicit pass-through wrappers with allowlisted __getattr__ delegation. Use when: (1) a refactor keeps behavior-bearing wrappers explicit but delegates mechanical helpers dynamically, (2) patch.object or direct instance assignment compatibility must survive, (3) the plan relies on issue text, line numbers, or method inventories that may drift."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, refactoring, delegation, getattr, wrappers, patch-object, reviewer-risks, assumptions]
---

# Dynamic Delegation Refactor Plan — Reviewer Risk Checklist

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Preserve durable planning learnings from a ProjectHephaestus implementation plan for GitHub issue #1389: refactor `IssueImplementer` so only low-risk mechanical helpers delegate through allowlisted `__getattr__`, while behavior-bearing wrappers remain explicit. |
| **Outcome** | Plan produced; NOT implemented or verified. The durable value is the reviewer checklist for unverified assumptions around dynamic delegation, patch compatibility, issue-scope drift, and stale method inventories. |
| **Verification** | unverified |

## When to Use

- Reviewing or authoring a plan that replaces explicit pass-through methods with allowlisted `__getattr__` delegation.
- The refactor claims some wrappers are purely mechanical, but keeps orchestration, agent execution, PR creation, tests, and review-loop behavior explicit.
- The plan depends on exact local line ranges, method inventories, or issue title/body interpretation gathered during planning.
- Tests or callers use `patch.object(instance, "_helper")`, direct instance assignment, monkeypatch restoration, or introspection against delegated wrapper names.
- A misleading issue title points at one component, but the issue body and affected files point at a different implementation target.

<!-- Validator compatibility token for current scripts/validate_plugins.py: ## Verified Workflow -->

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Verify issue scope before accepting the target module.
gh issue view 1389 --repo HomericIntelligence/ProjectHephaestus \
  --json title,body --jq '{title, body}'

# 2. Rebuild the method inventory from current main; do not trust plan-time line numbers.
rg -n "^    def (_collect_diff|_collect_changed_files|_save_review_log|_save_review_iteration_state|_load_review_iteration_state|_parse_follow_up_items|_can_resume_state_session|_learn_needs_rerun)\\b" \
  hephaestus/automation/implementer.py \
  hephaestus/automation/implementer_phase_runner.py

# 3. Prove patch/direct-assignment semantics before replacing wrappers.
rg -n "patch\\.object\\([^\\n]*_(collect_diff|collect_changed_files|save_review_log|save_review_iteration_state|load_review_iteration_state|parse_follow_up_items|can_resume_state_session|learn_needs_rerun)|monkeypatch\\.setattr|setattr\\(" \
  tests hephaestus

# 4. Verify AttributeError behavior and introspection expectations.
rg -n "hasattr\\(|getattr\\(|dir\\(|AttributeError|__getattr__" tests hephaestus/automation

# 5. Keep behavior-bearing wrappers explicit; audit that none entered the dynamic allowlist.
rg -n "^    def (_run_claude_impl_session|_run_codex_code|_run_claude_code|_run_advise|_run_advise.*|_run_impl_review|_run_impl_review.*|_run_address_review_step|_resume_impl_with_feedback|_finalize_pr|_ensure_pr_created|_run_tests_in_worktree|_has_plan|_generate_plan|_run_learn|_run_follow_up_issues|_run_post_pr_followup)\\b" \
  hephaestus/automation/implementer.py
```

### Detailed Steps

1. **Verify the issue scope mismatch before editing.** In the captured plan, the issue title allegedly said `CIDriver`, while the issue body and affected files identified `IssueImplementer` as scope. That was inferred from plan context, not refreshed against live GitHub. Before accepting that `ci_driver.py` stays untouched, read the current issue title/body and any linked review feedback.

2. **Rebuild all line-numbered observations from current files.** The plan cited `IssueImplementer` pass-through wrappers at `hephaestus/automation/implementer.py:496-765`, matching `ImplementationPhaseRunner` methods at `hephaestus/automation/implementer_phase_runner.py:1064-1413`, and runner phase attributes at lines 163-167. Treat these as plan-time coordinates only. Re-derive by symbol name on the branch being implemented.

3. **Classify the dynamic delegate allowlist by implementation, not name.** The proposed allowlist was `_collect_diff`, `_collect_changed_files`, `_save_review_log`, `_save_review_iteration_state`, `_load_review_iteration_state`, `_parse_follow_up_items`, `_can_resume_state_session`, and `_learn_needs_rerun`. Do not assume these are mechanical because their names look mechanical. Read each `IssueImplementer` wrapper, each `ImplementationPhaseRunner` target, and the tests that exercise them.

4. **Prove patch and assignment compatibility before deleting wrappers.** The riskiest compatibility assumption is that `patch.object(impl, "_collect_diff")`, direct instance assignment, and restoration semantics continue to work after replacing explicit instance methods with `__getattr__` delegation. Write focused regression tests that patch a delegated helper, assert the patched callable is used, exit the patch context, and assert lookup restores to the runner-backed delegate.

5. **Keep behavior-bearing wrappers explicit.** The plan intentionally left these methods out of dynamic delegation: `_run_claude_impl_session`, `_run_codex_code`, `_run_claude_code`, `_run_advise*`, `_run_impl_review*`, `_run_address_review_step`, `_resume_impl_with_feedback`, `_finalize_pr`, `_ensure_pr_created`, `_run_tests_in_worktree`, `_has_plan`, `_generate_plan`, `_run_learn`, `_run_follow_up_issues`, and `_run_post_pr_followup`. Audit the final diff so none of these are hidden behind `__getattr__`.

6. **Make `__getattr__` fail narrowly.** A dynamic delegate must return only allowlisted helper attributes and raise the original-style `AttributeError` for everything else. It must not mask a real `AttributeError` thrown inside the runner target, and it must not make introspection or typo failures confusing.

7. **Document all external and unverified sources.** The captured plan relied on GitHub issue #1389 title/body, prior review feedback mentioned in the plan, line-numbered local observations, and the existence/semantics of `dry-refactoring-workflow`. None were independently refreshed in the planning answer. Carry those forward as assumptions until implementation verifies them.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the issue title as the implementation target | The plan treated the title/body mismatch as resolved because the body and affected files pointed at `IssueImplementer`, while the title allegedly said `CIDriver` | The issue was not freshly read during the planning answer; a stale or misleading title could hide required `ci_driver.py` scope | Verify the live issue title/body and linked review comments before ruling any named component out of scope |
| Treat wrapper names as proof they are mechanical | The eight helpers were proposed for dynamic delegation because they looked like pass-through utility methods | A wrapper can hide local state behavior, argument normalization, logging, exception handling, or test patch semantics even if its name looks mechanical | Read both sides of every allowlisted wrapper and the tests before deleting explicit methods |
| Assume `__getattr__` preserves `patch.object` behavior | The plan asserted explicit wrappers could be replaced with dynamic lookup while existing `patch.object(impl, "_collect_diff")` style tests continue to work | Instance-level patching, direct assignment, deletion/restoration, and fallback lookup order can change when a method is no longer defined on the class | Add regression tests for patch context entry, patched-call dispatch, patch context exit, direct assignment shadowing, deletion, and restored delegated lookup |
| Let dynamic delegation absorb behavior-bearing methods | A broad delegation rule would reduce more boilerplate by sending all missing methods to `ImplementationPhaseRunner` | Orchestration, agent execution, review loops, PR creation, testing, planning, learn, and follow-up methods encode policy and local behavior; hiding them behind `__getattr__` makes review and debugging worse | Keep behavior-bearing wrappers explicit and allowlist only helpers proven mechanical |
| Rely on plan-time line ranges | The plan cited wrapper, runner, and phase-attribute locations by exact line number | Sequential edits or intervening commits make the coordinates stale before implementation starts | Rebuild inventories by symbol search from the branch under edit; never apply this plan by line number |
| Ignore `AttributeError` masking | A naive `__getattr__` could catch missing runner attributes and raise a generic error, or accidentally swallow an `AttributeError` thrown inside a target lookup | This changes Python's normal typo/debug behavior and can make introspection or test failures misleading | Restrict lookup to an explicit allowlist, use `object.__getattribute__` carefully, and test both unknown helper names and runner-internal errors |

## Results & Parameters

### Proposed Dynamic Delegate Allowlist

```text
_collect_diff
_collect_changed_files
_save_review_log
_save_review_iteration_state
_load_review_iteration_state
_parse_follow_up_items
_can_resume_state_session
_learn_needs_rerun
```

These names are not verified-safe by this skill. They are the plan-time candidate set and must be revalidated against current implementations and tests.

### Methods That Should Stay Explicit

```text
_run_claude_impl_session
_run_codex_code
_run_claude_code
_run_advise*
_run_impl_review*
_run_address_review_step
_resume_impl_with_feedback
_finalize_pr
_ensure_pr_created
_run_tests_in_worktree
_has_plan
_generate_plan
_run_learn
_run_follow_up_issues
_run_post_pr_followup
```

### Plan-Time Observations To Refresh

| Observation | Status | Refresh Method |
|-------------|--------|----------------|
| Issue #1389 title allegedly says `CIDriver`, but body/files indicate `IssueImplementer` | Unverified external source | `gh issue view 1389 --repo HomericIntelligence/ProjectHephaestus --json title,body` |
| `IssueImplementer` pass-through wrappers at `implementer.py:496-765` | Plan-time local line range | Rebuild with `rg -n "^    def "` in `implementer.py` |
| `ImplementationPhaseRunner` matching methods at `implementer_phase_runner.py:1064-1413` | Plan-time local line range | Rebuild with symbol search against the current branch |
| Runner phase attributes at `implementer_phase_runner.py:163-167` | Plan-time local line range | Re-read constructor/current attribute initialization |
| Prior review feedback and `dry-refactoring-workflow` semantics | Unverified referenced sources | Open current review thread/skill before relying on them |

### Reviewer Acceptance Checklist

```text
- [ ] Live issue scope checked; `ci_driver.py` intentionally touched or intentionally left alone.
- [ ] Wrapper inventory rebuilt from current code, not plan-time line numbers.
- [ ] Each allowlisted helper proven mechanical by reading wrapper, target, and tests.
- [ ] No behavior-bearing method appears in the dynamic delegate allowlist.
- [ ] `patch.object`, direct assignment, deletion/restoration, and restored delegated lookup have focused tests.
- [ ] Unknown attribute lookup raises normal `AttributeError`.
- [ ] Runner-internal `AttributeError` is not masked as an unknown delegated helper.
- [ ] Introspection or test helper expectations (`hasattr`, `getattr`, `dir`) are either preserved or deliberately updated.
```
