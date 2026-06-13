---
name: automation-planner-learn-record-writing-robustness
description: "Robustness patterns for planner learn record writing in hephaestus/automation/planner_review_loop.py. Use when: (1) auditing or refactoring _write_planner_learn_record, (2) adding companion file writes (json + log), (3) changing persisted JSON schema fields, (4) designing multi-part prompt directives."
category: architecture
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: unverified
tags: ["planner", "learn-record", "write-order", "json", "schema", "prompt-design"]
---

# Automation Planner Learn Record Writing Robustness

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | Identify and address robustness gaps in `_write_planner_learn_record` in `hephaestus/automation/planner_review_loop.py` |
| **Outcome** | Planning session complete — three concrete patterns identified; implementation not yet executed |
| **Verification** | unverified |
| **Source Issue** | ProjectHephaestus #1138 |

## When to Use

- Auditing or refactoring `_write_planner_learn_record` in `planner_review_loop.py`
- Adding or changing any pair of companion files (authoritative `.json` + human-readable `.log`)
- Dropping or renaming a field in any persisted `.json` schema (e.g., `learn_succeeded_at`)
- Designing multi-part prompt strings where output format directives might be misplaced
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
3. Add a migration note in the PR body so downstream consumers of the JSON records are warned.

#### Pattern 3 — Prompt Directive Placement

1. In multi-part prompt strings (e.g., `capture_planner_learnings`), output format directives must appear AFTER the content block they govern.
2. Pattern: `[context/background] → [content block] → [output format directives]`
3. If a bullet-output directive appears mid-prompt before the plan block, restructure so `build_learn_prompt`'s imperatives trail naturally after the content.
4. Review the full prompt string after any refactor to verify directive ordering is preserved.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Log-before-json write order | `_write_planner_learn_record` wrote `.log` then `.json` | A crash mid-sequence leaves only the human-readable log with no authoritative record | Always write authoritative file first; human-readable is secondary |
| Dropping `learn_succeeded_at` without audit | Field removal planned without grep-checking consumers | Silent breakage in downstream readers that parse the JSON | Grep all consumers before any schema field removal |
| Mid-prompt directive placement | Output format directive placed before the content block in `capture_planner_learnings` | Directive appeared to govern earlier content, not the plan block that follows | Directives must follow the content they govern |

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
```

### Prompt Structure Template

```python
prompt = (
    f"{context_background_block}\n\n"
    f"{content_block}\n\n"
    f"{output_format_directives}"  # ALWAYS last
)
```

### Sentinel Value Note

`start: float = 0.0` in `_write_planner_learn_record` is a safe sentinel because `time.monotonic()` always returns a value > 0 after normal process initialization. However, document this assumption with an inline comment to prevent future confusion.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1138 planning session | Patterns identified via code review; implementation not yet executed |
