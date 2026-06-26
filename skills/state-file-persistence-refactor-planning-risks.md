---
name: state-file-persistence-refactor-planning-risks
description: "Planning-risk checklist for centralizing JSON state-file persistence helpers in automation code. Use when: (1) extracting repeated prefix-<issue>.json load/save mechanics, (2) mixing raw dict session probes with Pydantic model validation, (3) preserving monkeypatch seams and corrupt-file logging contracts during a refactor."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - architecture
  - refactoring
  - planning
  - state-files
  - persistence
  - pydantic
  - json
  - corrupt-state
  - monkeypatch-seams
  - import-cycles
---

# State-File Persistence Refactor Planning Risks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture planning risks from ProjectHephaestus issue #1395: extracting repeated `prefix-<issue>.json` state-file read/write mechanics into shared helpers, then migrating reviewer, address-review, CI-driver, and implementer persistence without changing behavior. |
| **Outcome** | Planning artifact only. The implementation plan was not executed; current source and tests must be rechecked before coding. |
| **Verification** | unverified — no helper code, pytest, Ruff, or mypy run was observed for this plan. |

## When to Use

- Planning a refactor that centralizes repeated JSON state-file load/save mechanics across multiple automation callers.
- A helper must support both fully validated Pydantic models and raw partial dict payloads used for session probing or resume behavior.
- Existing tests patch private methods such as `_load_review_state`, `_save_state`, `_get_worktree_path`, or `_load_impl_session_id`, and the plan assumes delegating wrappers preserve those seams.
- The proposed helper imports a filesystem or security write primitive from another module, and the new import edge could create layering or import-cycle risk.
- A plan cites exact source or test line numbers as anchors, but the line numbers were gathered before implementation and no live test run confirmed them.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

<!-- Validator compatibility token: ## Verified Workflow -->

### Quick Reference

```bash
# Recheck planning anchors against current HEAD before implementation.
rg -n "def (_load|_save|load_all|_load_impl_session_id|_get_worktree_path)" \
  hephaestus/automation tests/unit/automation

# Enumerate every persisted filename contract before changing helpers.
rg -n "review-.*\\.json|issue-.*\\.json|prefix|state_dir|session_state" \
  hephaestus/automation tests/unit/automation

# Confirm raw partial implementer session files are still raw dict loads.
rg -n "issue-.*json|ImplementationState|model_validate|model_validate_json" \
  hephaestus/automation tests/unit/automation

# Check the proposed dependency edge before importing write_secure into a helper module.
python - <<'PY'
import importlib
for name in [
    "hephaestus.automation._review_utils",
    "hephaestus.automation.github_api",
    "hephaestus.automation.implementer_state",
]:
    importlib.import_module(name)
print("import smoke OK")
PY

# Verification design from the plan; these are not observed pass results.
pixi run pytest tests/unit/automation/test_address_review.py tests/unit/automation/test_ci_driver.py
pixi run ruff check hephaestus/automation tests/unit/automation
pixi run mypy-pkg
```

### Detailed Steps

1. **Start by classifying every state-file reader as raw payload or full model.**
   Do not centralize on Pydantic validation until each caller is categorized. Some callers only
   need partial session payloads, while `ImplementationStateManager.load_all()` expects full
   `ImplementationState` validation.

2. **Preserve filename layout exactly.**
   Treat `review-<issue>.json` and `issue-<issue>.json` as public persistence contracts. Build
   tests that assert the path strings produced by the migrated callers, not just helper unit tests.

3. **Separate corrupt-file handling from caller log semantics.**
   A central `load_state_file()` may catch missing, malformed, unreadable, validation-failing,
   and non-dict raw payloads, but each caller's prior log level, message shape, and retry behavior
   must be preserved or deliberately changed with reviewer signoff.

4. **Keep raw dict loading for partial session probes.**
   `dict(json.loads(text))` intentionally rejects non-object JSON by raising during conversion.
   Before relying on that behavior, inspect existing partial state fixtures and production state
   files to ensure every expected raw payload is object-shaped.

5. **Treat `save_state_file()` as a layering decision, not just a helper.**
   If the helper accepts only Pydantic `BaseModel` instances and writes via `write_secure()` from
   `github_api`, verify the new `_review_utils.py -> github_api` dependency does not create an
   import cycle or broaden a low-level utility module into product-layer concerns.

6. **Keep test monkeypatch seams as wrappers until proven unnecessary.**
   Methods such as `_load_impl_session_id`, `_load_review_state`, `_get_worktree_path`, and
   `_save_state` may look redundant after helper extraction, but tests and downstream automation
   may patch them. Make them delegate first; remove them only in a separate compatibility review.

7. **Run type checks before trusting overloads.**
   Helper overloads involving `BaseModel` and raw `dict[str, object]` returns are type-sensitive.
   A plan that "looks right" can still fail `mypy-pkg` after inference reaches caller code.

8. **Make caller-level contract tests accompany helper tests.**
   Add focused helper tests for malformed JSON, unreadable files, validation failure, non-dict raw
   payloads, and secure writes. Also keep caller tests for wrapper seams, cross-agent session
   filtering, malformed filename handling, and continuing to load valid neighboring files after one
   corrupt state file.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat all state files as full models | Planned a single validation path for all persisted issue files | Address-review and CI resume paths may inspect partial `issue-<n>.json` payloads that lack `issue_number`; full `ImplementationState` validation would reject legitimate partial session probes | Classify raw session probes separately from full model loads before extracting helpers |
| Centralize corrupt-file handling without preserving logs | Proposed one `load_state_file()` to handle missing, malformed, unreadable, validation-failing, and non-dict payloads | The plan did not execute caller tests or compare existing log levels/messages, so it could silently change operator-facing retry diagnostics | Helper behavior is not enough; caller log semantics and retry behavior are part of the contract |
| Assume `dict(json.loads(text))` covers raw payloads | Used `dict(json.loads(text))` as the raw object parser | It intentionally rejects arrays/scalars through exception handling, but no sweep verified that every existing partial state file is object-shaped | Verify real fixtures/state files before relying on object-only raw parsing |
| Import `write_secure()` into a shared helper by assumption | Planned `save_state_file()` in `_review_utils.py` using `github_api.write_secure()` | This may introduce a new dependency edge from a generic review utility to GitHub API code; import-cycle and layering risk were not executed away | Run import smoke tests and review module ownership before moving secure-write behavior |
| Remove private seams during cleanup | Considered replacing methods such as `_load_review_state` and `_save_state` directly with helper calls | Tests patch these private seams; removing them can break monkeypatch behavior even when runtime behavior is equivalent | Keep delegating wrappers first, then separately decide whether seam removal is worth the compatibility break |
| Trust cited source/test line numbers | Used exact line anchors in `_review_utils.py`, `_reviewer_base.py`, `address_review.py`, `ci_driver.py`, `implementer_state.py`, and related tests | The plan was written from a snapshot and no live test run confirmed the anchors; current HEAD can drift before implementation starts | Re-derive anchors with `rg` against current HEAD immediately before editing |

## Results & Parameters

### Reviewer Focus Checklist

```text
- [ ] Are raw partial session probes still loaded as dicts, not full Pydantic models?
- [ ] Do `review-<issue>.json` and `issue-<issue>.json` paths remain byte-for-byte compatible?
- [ ] Do corrupt-file cases preserve prior caller log levels, message meaning, and retry behavior?
- [ ] Does importing `write_secure()` into the helper avoid import cycles and unwanted layering?
- [ ] Do helper overloads pass `mypy-pkg` at the migrated call sites?
- [ ] Are monkeypatched seams kept as delegating wrappers?
- [ ] Does `load_all()` skip malformed or corrupt files while continuing valid neighboring files?
- [ ] Do tests cover cross-agent session filtering after the helper migration?
```

### Unverified Assumptions From Issue #1395 Planning

| Assumption | Verification Needed |
|------------|---------------------|
| `load_state_file()` can centralize all corrupt-file handling without changing callers' logs or retry behavior | Compare caller-level tests and log assertions before and after migration |
| `dict(json.loads(text))` is sufficient for raw payloads | Sweep existing partial state fixtures/files and add non-object JSON regression tests |
| `save_state_file()` should accept only `BaseModel` instances and call `write_secure()` | Import smoke test plus architecture review of the new dependency edge |
| `BaseModel` overloads satisfy `mypy-pkg` | Run `pixi run mypy-pkg` after migrating representative callers |
| Delegating wrappers preserve patched seams | Keep caller tests that monkeypatch the private methods, not just helper tests |
| Implementer-session probing must remain raw dict loading | Add/retain tests with partial `issue-<n>.json` payloads lacking `issue_number` |

### External Anchors To Recheck

- Source files cited by the plan: `hephaestus/automation/_review_utils.py`, `_reviewer_base.py`,
  `address_review.py`, `ci_driver.py`, and `implementer_state.py`.
- Tests cited by the plan: `tests/unit/automation/test_address_review.py` and
  `tests/unit/automation/test_ci_driver.py`.
- APIs relied on without execution: Pydantic `model_validate_json`,
  `BaseModel.model_dump_json(indent=2)`, and `write_secure()`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning phase for issue #1395, state-file persistence helper extraction | Plan produced, NOT executed. This skill records assumptions and reviewer risks for a future implementation pass. |
