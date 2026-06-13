---
name: automation-planner-learn-record-writing-robustness
description: "Robustness patterns for planner learn record writing in hephaestus/automation/planner_review_loop.py. Use when: (1) auditing or refactoring _write_planner_learn_record, (2) adding companion file writes (json + log), (3) changing persisted JSON schema fields, (4) designing multi-part prompt directives in build_learn_prompt."
category: architecture
date: 2026-06-12
version: "1.1.0"
user-invocable: false
verification: unverified
tags: ["planner", "learn-record", "write-order", "json", "schema", "prompt-design", "build_learn_prompt"]
---

# Automation Planner Learn Record Writing Robustness

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | Identify and address robustness gaps in `_write_planner_learn_record` in `hephaestus/automation/planner_review_loop.py` |
| **Outcome** | Planning session complete (R0 + R1) — four concrete patterns identified; R1 corrects R0 POLA violation on prompt directive placement |
| **Verification** | unverified |
| **Source Issue** | ProjectHephaestus #1138 |

## When to Use

- Auditing or refactoring `_write_planner_learn_record` in `planner_review_loop.py`
- Adding or changing any pair of companion files (authoritative `.json` + human-readable `.log`)
- Dropping or renaming a field in any persisted `.json` schema (e.g., `learn_succeeded_at`)
- Designing multi-part prompt strings where output format directives might be misplaced in `build_learn_prompt`
- Comparing `_write_planner_learn_record` against `_write_learn_record` in `learn.py` for symmetry

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Audit consumers of a persisted JSON field before removing it
grep -r "learn_succeeded_at" hephaestus/ tests/ scripts/

# Verify write order in _write_planner_learn_record: json must come before log
grep -n "_write_planner_learn_record\|\.json\|\.log" hephaestus/automation/planner_review_loop.py | head -40

# Compare with learn.py reference implementation
grep -n "_write_learn_record\|\.json\|\.log" hephaestus/automation/learn.py | head -20

# Verify OSError patch path for test coverage
grep -n "from pathlib import Path" hephaestus/automation/planner_review_loop.py
# Expected at line 21 — confirms patch("hephaestus.automation.planner_review_loop.Path.write_text", ...)

# Verify prompt directive ordering in build_learn_prompt
grep -n "Do NOT return a plan\|plan text\|build_learn_prompt" hephaestus/automation/learn.py | head -20
```

### Detailed Steps

#### Pattern 1 — Write Order Atomicity (json before log)

1. Locate the two companion file writes in `_write_planner_learn_record` (around line 599–666 of `planner_review_loop.py` at planning time — line numbers may shift).
2. Confirm the current order: if `.log` is written before `.json`, swap them.
3. The authoritative `.json` file must always be written first so that a mid-write crash leaves the authoritative record present (even if incomplete) rather than only the human-readable log.
4. Reference: `learn.py:_write_learn_record` writes `.json` only — mirror that discipline in the planner variant.

#### Pattern 2 — Schema Field Removal Audit

1. Before removing any field from a persisted `.json` schema, run a consumer audit:
   ```bash
   grep -r "<field_name>" hephaestus/ tests/ scripts/
   ```
2. For the specific case of `learn_succeeded_at → learn_duration_s`:
   - Confirm all readers of the old field name are updated or that the field is truly unused.
   - `learn_duration_s` is computed from `time.monotonic()` start/end; the `start: float = 0.0` sentinel is safe in practice (monotonic is always > 0 at normal process start) but document the assumption.
3. **Audit scope caveat (R1):** The grep-based consumer audit is NOT exhaustive — it covers the local repo but does not traverse the full dependency graph across sibling projects. Flag this as a risk in the PR body so downstream consumers of the JSON records are warned.
4. Add a migration note in the PR body so downstream consumers of the JSON records are warned.

#### Pattern 3 — Prompt Directive Placement (CORRECTED in R1)

> **R1 Correction:** R0 described this pattern as editing `capture_planner_learnings`. R1 corrects: the fix belongs in `build_learn_prompt` in `learn.py`. Editing `capture_planner_learnings` violates POLA because issue #1138 explicitly named `build_learn_prompt` as the target function. When an issue spec names a specific function, edit that function — not an adjacent one with similar context.

1. In `build_learn_prompt` (in `learn.py`), output format directives must appear AFTER the content block they govern.
2. Pattern: `[context/background] → [content block] → [output format directives]`
3. If a bullet-output directive appears mid-prompt before the plan block, restructure `build_learn_prompt` so its imperatives trail naturally after the content.
4. Do NOT make this change in `capture_planner_learnings` — that function provides context strings, not the final prompt assembly.
5. Review the full prompt string in `build_learn_prompt` after any refactor to verify directive ordering is preserved.

**Assertion to add in tests:**
```python
# Verify imperatives appear AFTER content in build_learn_prompt output
prompt = build_learn_prompt(plan_text="plan text", ...)
assert prompt.index("Do NOT return a plan") < prompt.index("plan text") is False
# More precisely: the directive should follow the plan block
assert prompt.index("plan text") < prompt.index("Do NOT return a plan")
```

#### Pattern 4 — Sentinel Value Safety

1. The `start: float = 0.0` sentinel in `_write_planner_learn_record` uses `if start else None` to detect "not set".
2. This is theoretically unsafe: `0.0` is a valid `time.monotonic()` return value at process start (though extremely rare in practice).
3. Safer alternative: `start: float | None = None` with `if start is not None else None`.
4. A reviewer may flag the sentinel check. Document the assumption with an inline comment, or use the `None`-typed sentinel.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Log-before-json write order | `_write_planner_learn_record` wrote `.log` then `.json` | A crash mid-sequence leaves only the human-readable log with no authoritative record | Always write authoritative file first; human-readable is secondary |
| Dropping `learn_succeeded_at` without audit | Field removal planned without grep-checking consumers | Silent breakage in downstream readers that parse the JSON | Grep all consumers before any schema field removal |
| Mid-prompt directive placement (wrong function) | R0 plan — added `Do NOT return a plan` directive to `_capture_planner_learnings` context string | Issue #1138 explicitly named `build_learn_prompt` in `learn.py` as the target; editing the adjacent function violates POLA and doesn't fix the actual prompt structure | When the issue spec names a specific function, that is the target — read the function signature before editing neighbors |

## Results & Parameters

### Write Order Rule (copy-paste pattern)

```python
# CORRECT — authoritative first, human-readable second
_write_json_record(path_json, record)   # authoritative
_write_log_record(path_log, record)     # human-readable

# INCORRECT — do not write log before json
_write_log_record(path_log, record)     # human-readable (wrong order)
_write_json_record(path_json, record)   # authoritative too late
```

### Schema Change Audit Command

```bash
# Run before removing any persisted JSON field
FIELD="learn_succeeded_at"
grep -rn "$FIELD" hephaestus/ tests/ scripts/ docs/
# NOTE: This audits the local repo only. Cross-project consumers are NOT covered.
```

### Prompt Structure Template (build_learn_prompt)

```python
# In build_learn_prompt (learn.py) — NOT in capture_planner_learnings
prompt = (
    f"{context_background_block}\n\n"
    f"{content_block}\n\n"
    f"{output_format_directives}"  # ALWAYS last; edit THIS function, not capture_planner_learnings
)
```

### Sentinel Value Note

`start: float = 0.0` in `_write_planner_learn_record` uses `if start else None`. This is safe in practice because `time.monotonic()` always returns a value > 0 after normal process initialization. However:

- **Theoretical risk:** `0.0` is a valid monotonic value at process start — the sentinel check would incorrectly treat it as "not set"
- **Safer alternative:** `start: float | None = None` with `if start is not None`
- Document the assumption with an inline comment to prevent future reviewer flags

### OSError Test Patch Path

When testing OSError handling in `_write_planner_learn_record`, the correct patch path is:
```python
patch("hephaestus.automation.planner_review_loop.Path.write_text", side_effect=OSError(...))
```
This is valid because `from pathlib import Path` is at line 21 of `planner_review_loop.py`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1138 planning session (R0) | Patterns identified via code review; implementation not yet executed |
| ProjectHephaestus | Issue #1138 planning session (R1) | R0 POLA violation corrected; sentinel gotcha documented; OSError patch path confirmed |
