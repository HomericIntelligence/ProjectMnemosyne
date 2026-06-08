---
name: tooling-hephaestus-implementer-no-changes-state-skip
aliases:
  - automation-implementer-no-changes-state-skip
description: "When hephaestus implementer_phase_runner raises RuntimeError('No changes produced...') from pr_manager because a branch has 0 commits vs main (work already merged), detect this specific case and apply state:skip + return WorkerResult(success=True) instead of failing. Also: run_learn() in learn.py must accept model= parameter so ImplementationPhaseRunner._run_learn() can pass implementer_model() instead of the hardcoded learn_model() (Haiku). Use when: (1) an automation loop inflates rc=1 for issues whose work already landed via a prior merged PR, (2) diagnosing why drive-green stays suppressed after implementation loops 1-4 even though the actual code change is already merged, (3) implementing or reviewing error handling in _implement_issue in implementer_phase_runner.py, (4) the /learn step after an implementation session uses the wrong model tier."
category: tooling
date: 2026-06-08
version: "1.2.0"
user-invocable: false
verification: verified-precommit
history: tooling-hephaestus-implementer-no-changes-state-skip.history
tags:
  - implementer
  - implementer-phase-runner
  - no-changes-produced
  - state-skip
  - workerresult
  - pr-manager
  - no-commits-vs-main
  - automation-loop
  - rc-inflation
  - drive-green
  - run-learn
  - learn-model
  - implementer-model
  - model-parameter
---

# Implementer "No Changes Produced" → state:skip + Learn Model Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-08 |
| **Objective** | (1) Fix `_implement_issue` in `implementer_phase_runner.py` so that a `RuntimeError("No changes produced...")` is treated as success + state:skip, not failure. (2) Fix `run_learn()` to accept a `model=` parameter so `_run_learn()` in `ImplementationPhaseRunner` can pass `implementer_model()` instead of hardcoded `learn_model()` (Haiku). |
| **Outcome** | Successful — PR #1090 (no-changes fix) and PR #1100 (learn model fix); pre-commit hooks + mypy (320 files) + ruff + tests all pass. |
| **Verification** | verified-precommit |
| **History** | [changelog](./tooling-hephaestus-implementer-no-changes-state-skip.history) |

## When to Use

- An automation loop reports `rc=1` for an issue whose implementation was already merged via a prior PR (work IS done, branch is clean, but the implementer calls `create_or_update_pr` and gets "no commits vs main").
- Drive-green stays suppressed on loops 1–4 (pre-existing Bug #818 suppresses it on `rc != 0`); the root cause can be rc inflation here.
- Implementing or reviewing error handling inside `_implement_issue` in `hephaestus/automation/implementer_phase_runner.py`.
- Distinguishing "agent ran but produced no new work" (genuine failure) from "branch has no new commits because the work already merged" (already done — not a failure).
- The `/learn` step after an implementer session is running with the wrong model tier (Haiku instead of Opus/Sonnet) — `run_learn()` hardcoded `learn_model()` before the model parameter was added.
- Adding a new pipeline step to `implementer_phase_runner.py` that calls a shared function which previously hardcoded a model — add a `model: str | None = None` parameter and pass `implementer_model()` from the caller.

## Verified Workflow

### Quick Reference

```python
# ── Fix 1: No-changes-produced → state:skip ──────────────────────────────────
# In hephaestus/automation/implementer_phase_runner.py
# Inside _implement_issue, in the `except RuntimeError as e:` block:

msg = str(e)
if "no commits vs" in msg.lower() or "no changes produced" in msg.lower():
    impl._log("info",
              f"Issue #{issue_number}: no new commits vs main — work already merged; applying state:skip",
              thread_id)
    self.status_tracker.update_slot(slot_id, f"{issue_ref(issue_number)}: already implemented — state:skip")
    with contextlib.suppress(Exception):
        gh_issue_add_labels(issue_number, [STATE_SKIP])
    return WorkerResult(issue_number=issue_number, success=True)
# fall through to other RuntimeError handling below

# ── Fix 2: run_learn() model parameter ──────────────────────────────────────
# In hephaestus/automation/learn.py:

def run_learn(
    ...,
    model: str | None = None,   # NEW: allow caller to override default learn_model()
) -> LearnResult:
    effective_model = model or learn_model()
    # pass effective_model to the claude invocation

# In hephaestus/automation/implementer_phase_runner.py:

def _run_learn(self, ...) -> None:
    run_learn(
        ...,
        model=implementer_model(),   # use same model as the implementation session
    )
```

### Detailed Steps

#### Fix 1: No-changes-produced → state:skip

1. **Understand the root cause.** `pr_manager.create_or_update_pr` raises `RuntimeError("No changes produced...")` when `_branch_has_commits_vs_base(branch, base)` returns False. This means the implementation branch has 0 commits beyond `main`. This happens legitimately when the code change already landed via a prior merged PR.

2. **Add the early-return check at the TOP of the `except RuntimeError as e:` block** in `_implement_issue`. The check must be added before any other RuntimeError handling so the success path fires before the failure path.

3. **Call `gh_issue_add_labels` directly — no `dry_run` guard.** The handler is only reachable when `dry_run=False` because `_implement_issue` already returns early at ~line 241 when `dry_run=True`. The RuntimeError from `_finalize_pr` (where this handler lives, ~line 380) is unreachable in dry-run mode. Adding `if not self.options.dry_run:` would be dead code and misleading.

4. **Apply `state:skip` (not `state:done` or close).** `state:skip` is the existing mechanism the implementer checks at the top of `_implement_issue` to skip re-processing. It reuses the existing pattern without making a judgment about full resolution — a human can verify the closed state and close the issue.

5. **Return `WorkerResult(success=True)`.** This prevents rc inflation that would suppress drive-green on subsequent loops.

6. **Write a unit test** in `tests/unit/automation/test_implementer.py` under class `TestNoChangesProducedAppliesStateSkip`:
   - Mock `_finalize_pr` to raise `RuntimeError("No changes produced for issue #736 ...")`
   - Assert `gh_issue_add_labels(736, ["state:skip"])` was called
   - Assert `result.success is True`
   - Do NOT write a dry_run variant — the handler is unreachable in dry-run mode (the test would be vacuous).

#### Fix 2: run_learn() model parameter

1. **Understand the model mismatch.** `run_learn()` in `hephaestus/automation/learn.py` hardcoded `learn_model()` (Haiku) when invoking the `/learn` Claude step. The caller `_run_learn()` in `ImplementationPhaseRunner` resumes the `AGENT_IMPLEMENTER` session — the session transcript was written by an Opus/Sonnet model. Having Haiku resume an Opus/Sonnet session risks capability mismatch and inconsistent behavior.

2. **Add `model: str | None = None` to `run_learn()`.** Use `None` as the default so existing callers that don't pass `model` continue to use `learn_model()` (backward-compatible).

   ```python
   # hephaestus/automation/learn.py
   def run_learn(
       ...,
       model: str | None = None,
   ) -> LearnResult:
       effective_model = model if model is not None else learn_model()
       # Pass effective_model to the claude invocation
   ```

3. **Update `ImplementationPhaseRunner._run_learn()` to pass `implementer_model()`.**

   ```python
   # hephaestus/automation/implementer_phase_runner.py
   def _run_learn(self, ...) -> None:
       run_learn(
           ...,
           model=implementer_model(),
       )
   ```

4. **No change needed to callers that want Haiku.** Any caller not passing `model=` still gets `learn_model()` (Haiku) — the default is unchanged.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add `if not self.options.dry_run:` guard inside the no-changes handler | Wrapped `gh_issue_add_labels` call in a dry-run check | Dead code — `_implement_issue` returns early on `dry_run=True` at ~line 241; the handler (`_finalize_pr` region ~line 380) is unreachable in dry-run mode | Do NOT add the guard; call `gh_issue_add_labels` directly. Adding it is misleading and will confuse future readers. |
| Apply the no-changes fix in `pr_manager.py` (not raise, return instead) | Changed `create_or_update_pr` to return None instead of raising | Changes the throw/no-throw contract of `create_or_update_pr` — callers relying on the exception for error flow break | Fix at the orchestration layer (`implementer_phase_runner.py`), not in the data-access layer. The semantic distinction (already-done vs genuine failure) belongs at the orchestration level. |
| Write a vacuous dry_run test for the no-changes handler | Added a test that mocked `_implement_issue` to return before the handler | Tests nothing — the handler is unreachable in dry-run mode by design | Only write reachable tests; explicitly document that a dry_run test is vacuous and was removed. |
| Hardcode `learn_model()` in `run_learn()` and not expose a `model=` param | `run_learn()` always used Haiku regardless of which model invoked the session | `ImplementationPhaseRunner._run_learn()` resumes an Opus/Sonnet implementation transcript with a Haiku model — capability mismatch | Add `model: str | None = None` to `run_learn()` so callers that need a non-Haiku model can pass it; default remains `learn_model()` for backward compatibility. |

## Results & Parameters

### Error message to detect (no-changes fix)

Source: `pr_manager.create_or_update_pr` → `_branch_has_commits_vs_base` returns False.

```text
"No changes produced for issue ...#<N>: branch '<N>-auto-impl' has no commits vs 'main'. Skipping PR creation..."
```

Detection idiom:
```python
"no commits vs" in msg.lower() or "no changes produced" in msg.lower()
```

### run_learn() signature change

```python
# Before (hardcoded):
def run_learn(...) -> LearnResult:
    invoke_claude_with_session(..., model=learn_model(), ...)

# After (configurable):
def run_learn(..., model: str | None = None) -> LearnResult:
    effective_model = model if model is not None else learn_model()
    invoke_claude_with_session(..., model=effective_model, ...)
```

### Why the rc inflation mattered

With `rc=1` returned for "already merged" issues, Bug #818 (drive-green structurally suppressed on loops 1–4 via the not-final-loop gate) was triggered on EVERY loop, not just the last. The combined effect: the loop ran 5 times, flagged already-done issues as failures, and never reached a clean-pass to run drive-green. This fix stops the rc inflation; Bug #818 is separately tracked.

### Related skills

- `multi-repo-pr-automation-loop-orchestration` — see "Hephaestus loop deadlocks (drive-green discovery)" and the existing-PR labeling deadlock fix (PRs #1073–#1079). That skill has the opposite "no-commit guard" (pre==post HEAD ⇒ hard-fail) in the CI driver; the semantics here are DIFFERENT (0 commits vs main in the implementer = work already landed = success, not failure).
- `automation-session-naming-pr-scoped-not-commit-scoped` — two-turn session patterns and cwd invariant for `invoke_claude_with_session`.

### Verification metrics

- 1303 unit tests pass (PR #1100)
- 3402 unit tests passed (PR #1090)
- mypy clean (320 files)
- ruff clean
- pre-commit hooks pass
- PR #1090 (no-changes fix), PR #1100 (learn model fix)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1090, Issues #1088/#1089 — "no changes produced" RuntimeError should apply state:skip | verified-ci; 3402 tests passed; mypy/ruff/pre-commit clean; 2026-06-07 |
| ProjectHephaestus | PR #1100 — run_learn() model parameter fix | verified-precommit; 1303 tests pass; mypy/ruff/pre-commit clean; 2026-06-08 |
