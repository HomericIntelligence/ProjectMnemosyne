---
name: planning-shared-state-io-helper-refactor-risks
description: "Capture reviewer risks for unverified plans that extract duplicated JSON state-file read/write code into shared helpers. Use when: (1) a plan centralizes state I/O behind helper functions, (2) callers mix raw dict compatibility with Pydantic validation, (3) filename compatibility, malformed JSON handling, secure writes, or logging behavior must be preserved, (4) plan evidence came from grep inventories or issue context that was not refreshed live."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, refactoring, state-io, json, pydantic, secure-write, reviewer-risks, compatibility, line-number-drift]
---

# Planning Shared State I/O Helper Refactor Risks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Preserve the uncertain assumptions and reviewer checklist for plans that DRY up duplicated JSON state-file load/save mechanics into shared helpers while preserving legacy filenames, partial payload compatibility, validation behavior, and secure writes. |
| **Outcome** | Planning capture only. The implementation plan was produced but not executed, and its evidence was not refreshed against the current checkout during this capture. |
| **Verification** | unverified |

Use this skill for the **planning-risk review** of a shared state I/O helper extraction. It is not a recipe for the helper implementation itself. The central hazard is that duplicated state readers often encode subtle compatibility behavior: missing-file semantics, invalid JSON swallowing, partial raw dict payloads, validation timing, exact log text, and filename conventions.

## When to Use

- A plan proposes replacing several ad hoc `Path.read_text()` / `json.loads()` / model-validation call sites with shared `load_state_file(...)` and `save_state_file(...)` helpers.
- Some callers need full typed model validation while others intentionally read partial legacy payloads as raw dictionaries.
- The plan preserves exact state filenames or marker filenames, and accidentally sweeping extra JSON files would change behavior.
- The plan relies on a grep-derived inventory, exact line numbers, GitHub issue context, or prior review findings that were not refreshed live from the current checkout.
- The helper imports secure write or logging utilities from a module that may already import the helper target, creating circular-import risk.
- Tests may assert warning text, warning levels, or log silence around malformed state files.

## Verified Workflow

<!-- Section title retained for marketplace validator compatibility. This is a proposed workflow,
not a verified procedure. -->

### Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Refresh the duplicate state I/O inventory from the current checkout before editing.
rg -n "read_text|write_text|json\\.loads|json\\.dumps|model_validate|model_validate_json|write_secure" \
  hephaestus tests

# Confirm only the intended state filenames are touched by the refactor.
rg -n "review-\\{?|issue-\\{?|review-|issue-" hephaestus tests

# Prove raw dict mode rejects non-object JSON before dict-like access.
python - <<'PY'
import json
payload = json.loads('[["session_id", "abc"]]')
assert not isinstance(payload, dict)
PY

# Prove import graph and validation behavior by execution after implementation.
python -c "from hephaestus.automation import _review_utils; print('import OK')"
pixi run pytest tests/unit/automation/test_review_utils.py tests/unit/automation/test_implementer_state.py -q
pixi run ruff check hephaestus/ tests/
pixi run ruff format --check hephaestus/ tests/
pixi run mypy hephaestus/
```

### Detailed Steps

1. **Refresh the state I/O inventory before implementation.** Treat every grep-derived file list and exact line number in a plan as a snapshot, not ground truth. Re-run `rg` from the current branch and update the plan if files moved, helper names changed, or additional readers/writers appeared.

2. **Separate full-model readers from raw-dict compatibility readers.** A shared `load_state_file` helper that optionally accepts `model_class=None` is only safe if raw dict mode is an intentional compatibility surface, not a shortcut for tests. Confirm each raw caller really consumes partial payloads such as `session_id` / `session_agent` and does not need full schema validation.

3. **Reject non-object JSON before any dict-like access or coercion.** Do not rely on `dict(payload)`, Pydantic coercion, or later key access to fail. Explicitly require `isinstance(payload, dict)` so a JSON list-of-pairs like `[["session_id", "abc"]]` cannot become a dictionary and bypass the intended malformed-state path.

4. **Preserve filename contracts exactly.** The helper should construct only the filenames the previous call sites used, such as `review-<issue>.json` and `issue-<issue>.json`. Do not refactor unrelated marker JSON, lock files, or future state files unless the plan names them and tests cover them.

5. **Check validation-equivalence assumptions.** Replacing `model_validate_json(path.read_text())` with `json.loads(...)` plus `model_validate(payload)` changes the stage at which JSON syntax, non-object payloads, and model validation errors surface. The plan may still be right, but tests must assert the desired behavior explicitly.

6. **Keep malformed-state logging behavior visible to reviewers.** Centralized helper logging can change logger name, warning level, and message text. If callers previously swallowed invalid JSON or Pydantic errors differently, add focused tests for returned value, log presence or absence, and whether warning text is intentionally changed.

7. **Prove secure-write imports do not create cycles.** Importing `write_secure` into the new helper module can be a dependency inversion improvement or a circular import, depending on the existing graph. Add an import smoke test and run it before claiming the refactor is safe.

8. **Keep method seams and patch targets stable.** If existing tests patch private methods like `_load_review_state`, `_load_review_state_from_disk`, `_load_impl_session_id`, `_save_state`, or manager methods such as `save` / `load_all`, either preserve those seams as thin delegators or update tests deliberately with reviewer-visible rationale.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust a stale grep inventory | Plan listed state-reader/writer files and line numbers from a prior snapshot | Refactor plans that touch multiple callers drift quickly; missing one duplicate reader leaves inconsistent behavior, while editing the wrong line after code movement can change unrelated logic | Re-run `rg` on the current checkout and anchor changes by function names and filename patterns, not old line numbers |
| Treat raw dict mode as an implementation convenience | Plan allowed `model_class=None` for partial session readers without proving those partial payloads are a real compatibility surface | If the partial payloads were only test shortcuts, raw dict mode weakens validation unnecessarily; if they are real legacy state, removing them breaks resume behavior | Read each caller and its tests to decide whether raw dict mode is required compatibility or debt to remove |
| Validate after coercion | Let `dict(payload)` or model validation handle non-object JSON | JSON list-of-pairs can become a dict-like object, defeating the malformed-state expectation and hiding a regression | Check `isinstance(payload, dict)` immediately after `json.loads` and before any coercion or key access |
| Assume `model_validate(json.loads(...))` equals `model_validate_json(read_text())` | Plan swapped validation APIs without a focused behavior test | Syntax errors, non-object payloads, and validation errors may be logged or classified differently | Add tests for missing file, invalid JSON, non-object JSON, and schema-invalid object for both raw and typed modes |
| Centralize logging without checking assertions | Helper emitted a common warning for malformed state | Existing tests or operators may depend on previous logger attribution, warning text, warning level, or silence | Assert the intended log behavior explicitly and mention any changed wording in the PR |
| Import secure write utilities by inspection only | Plan assumed the helper can import `write_secure` directly | Existing modules may already import the helper target or the helper's package, creating a cycle only visible at import time | Run an import smoke test after wiring imports and before committing |
| Claim schema-neutral rollback without checking formatting consumers | Plan said rollback is safe because state schema does not change | Pretty-printed JSON, key order, or newline behavior can matter to brittle consumers or golden-file tests even when the schema is unchanged | Confirm there are no formatting-sensitive consumers, or preserve the prior serialization format |

## Results & Parameters

### Reviewer Checklist

```text
Shared state I/O helper refactor review checklist

- [ ] Current `rg` inventory was refreshed from the branch being implemented.
- [ ] The helper only touches the intended state filenames and no unrelated marker JSON files.
- [ ] Missing file returns None in every migrated path.
- [ ] Invalid JSON logs the intended warning and returns None.
- [ ] Non-object JSON is rejected before dict-like access or coercion.
- [ ] Raw dict mode is justified by real partial payload compatibility.
- [ ] Full-state paths still use typed validation and preserve caller behavior.
- [ ] `model_validate` vs `model_validate_json` behavior differences are covered by tests.
- [ ] `write_secure` import path has an executed import smoke test proving no cycle.
- [ ] Existing method seams and patch.object targets remain stable or are intentionally updated.
- [ ] Formatting-sensitive consumers of the state files were checked before calling rollback schema-neutral.
```

### Planning Evidence To Refresh

For any plan based on issue text, prior reviews, or a previous grep pass, refresh these before editing:

- The duplicate state I/O inventory, including all state readers, writers, filenames, and tests.
- The existence and intended behavior of legacy partial payload readers.
- Current Pydantic version behavior and typing expectations for overloads, `cast`, and `model_validate`.
- Any issue requirements or reviewer findings that were taken from context rather than fetched live.
- The exact tests that assert malformed-state logging, model validation, method seams, and patch targets.

### Verification Commands To Require In The Implementation PR

```bash
python3 scripts/validate_plugins.py  # for this ProjectMnemosyne skill file only

# For the consuming repository implementation, tailor paths but keep the same proof categories:
pixi run pytest tests/unit/automation/test_review_utils.py tests/unit/automation/test_implementer_state.py -q
pixi run pytest tests/unit/automation -q
pixi run ruff check hephaestus/ tests/
pixi run ruff format --check hephaestus/ tests/
pixi run mypy hephaestus/
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning capture for issue #1395: extract duplicated per-issue state-file read/write mechanics into `hephaestus/automation/_review_utils.py` | Plan proposed `load_state_file(state_dir, prefix, issue_number, model_class=None)` and `save_state_file(state_dir, prefix, issue_number, state)`, preserving `review-<issue>.json` and `issue-<issue>.json`, missing-file `None`, invalid-JSON warning plus `None`, raw dict mode for partial session readers, Pydantic validation for full state, and secure writes. Implementation and consuming-repo verification were not executed during planning; mark `unverified`. |
