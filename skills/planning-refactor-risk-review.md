---
name: planning-refactor-risk-review
description: "Review planning-only refactors that centralize repeated path/helper logic before implementation. Use when: (1) a plan proposes extracting a shared helper from repeated call sites, (2) the inventory is grep-derived and may be incomplete, (3) the helper's home could couple unrelated workflows, (4) filenames, suffixes, or write semantics must remain byte-for-byte compatible."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, refactoring, shared-helper, log-paths, reviewer-risks, coupling, grep-inventory, filename-compatibility, unverified]
---

# Planning Refactor Risk Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Preserve reviewer-facing risks from a planning session that proposed a shared log-path helper for repeated per-issue automation log filenames. |
| **Outcome** | Planning-risk capture only. No ProjectHephaestus files, GitHub issue body, external APIs, or verification commands were re-run during capture. |
| **Verification** | unverified - plan not executed; current repo state and call-site coverage not re-verified |

Use this skill when reviewing or authoring a refactor plan that centralizes repeated string/path construction into a helper, especially when the plan is based on a static grep inventory rather than a verified migration.

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

## When to Use

- A plan proposes extracting repeated per-issue file path construction into a shared helper.
- The plan relies on a grep-style call-site inventory and cites exact file/line references from a then-current checkout.
- The helper's proposed module is convenient but might create coupling between review utilities and non-review automation flows.
- Existing filenames include dynamic prefixes, optional iteration suffixes, parse-diagnostic suffixes, or other compatibility-sensitive conventions.
- The refactor is intended to be path-only, while each caller keeps different write mechanics, timeout handling, stdout handling, metadata capture, or caller-provided paths.

## Verified Workflow

### Proposed Workflow (UNVERIFIED - Planning Risk Checklist)

Before approving the plan, make the reviewer risks explicit and verify them against the live repository state.

### Quick Reference

```bash
# Re-run the inventory against current main before trusting the plan.
rg -n 'state_dir / f.*\.log|self\.state_dir / f.*\.log' hephaestus/automation -g '*.py'

# Expand the search for suffixes and non-canonical diagnostics that should not move.
rg -n '\.log|parse-error|iteration|state_dir|log_file' hephaestus/automation -g '*.py'

# After implementation, verify no canonical issue-log construction bypasses the helper.
rg -n 'state_dir / f.*\.log|self\.state_dir / f.*\.log' hephaestus/automation -g '*.py'

# Focused checks should be selected from the current call sites, then paired with format/lint.
pytest tests/unit/automation -q
ruff check hephaestus/automation tests/unit/automation
ruff format --check hephaestus/automation tests/unit/automation
```

### Detailed Steps

1. **Treat the call-site list as a stale hypothesis until re-run.**
   A grep inventory can be a useful starting point, but it is not proof of complete coverage. Re-run the inventory on the current branch, then broaden it to all `.log`, `state_dir`, iteration, and parse-diagnostic patterns before deciding which sites are canonical issue logs.

2. **Verify the helper belongs in the proposed module.**
   If the plan puts the helper in a file like `hephaestus/automation/_review_utils.py` because that file already hosts shared review utilities, explicitly check whether non-review modules would now depend on review-specific concepts. A helper used by implement, learn, planner, follow-up, or CI-driver flows may need a more neutral home if `_review_utils.py` creates undesirable coupling.

3. **Preserve filenames exactly.**
   Build a before/after table for every migrated call site. Include dynamic prefixes, issue numbers, optional iteration suffixes, and any existing extension details. Parse diagnostics such as `.parse-error.log` and non-canonical logs should stay out of the helper unless the plan intentionally broadens its contract.

4. **Keep the migration path-only.**
   Do not turn a path helper into an `issue_log()` context manager unless the write semantics are truly uniform. Existing callers may differ in append/write mode, metadata capture, timeout behavior, stdout/stderr handling, failure cleanup, or accepting caller-provided paths.

5. **Separate planned verification from executed verification.**
   If pytest, Ruff, and custom scans are listed in the plan but were not run, label them as planned checks. A reviewer should run the current focused tests and scans before treating the refactor as behavior-preserving.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust a grep inventory as complete | The plan relied on `rg -n 'state_dir / f.*\.log|self\.state_dir / f.*\.log' hephaestus/automation -g '*.py'` and file/line references from the then-current checkout | Exact line numbers and full call-site coverage were not re-verified during learn capture; later edits can add, delete, or move sites | Re-run and broaden the inventory on current `main` before approving or implementing |
| Put the helper in the most convenient existing utility module | `_review_utils.py` was assumed to be the right home because it already hosts shared review automation utilities | A generic log-path helper may be used by non-review modules, creating review-module coupling in implement, learn, planner, follow-up, or CI-driver flows | Review module ownership as a design decision, not a default |
| Assume string construction can be centralized without filename drift | The helper was expected to preserve all existing filenames, dynamic prefixes, and optional iteration suffixes while leaving diagnostics unchanged | Small formatting differences can silently move logs or break tooling that expects exact names | Build a before/after filename table and test suffix conventions explicitly |
| Convert a path helper into a write abstraction | An `issue_log()` context manager was considered but intentionally rejected | Write mechanics differ across sites; abstracting writes risks changing metadata, timeouts, stdout/stderr capture, append mode, or caller-provided paths | Keep this refactor path-only unless write semantics are independently audited |
| Present planned checks as completed evidence | Focused pytest targets, Ruff, and a bypass scan were included in the verification plan | They were planned, not executed during the planning session or learn capture | Mark verification as `unverified` until the checks are actually run and recorded |

## Results & Parameters

### ProjectHephaestus Issue #1396 Planning Capture

The planning session proposed adding:

```python
log_file_path(state_dir, prefix, issue_number, *, iteration=None)
```

in `hephaestus/automation/_review_utils.py`, then migrating repeated per-issue automation log path constructions to it.

### Most Uncertain Assumptions

| Assumption | Why It Is Uncertain | Reviewer Focus |
|------------|---------------------|----------------|
| The grep inventory found every canonical issue-log call site | The inventory and line references were not re-run during learn capture | Re-run the exact grep and broaden it before implementation |
| `_review_utils.py` is the right home | The helper may serve non-review flows | Check import direction and coupling for implement, learn, planner, follow-up, and CI driver modules |
| Helper output preserves all filenames | Dynamic prefixes and optional iteration suffixes are easy to drift | Compare before/after filenames for every migrated call site |
| Parse diagnostics should stay unchanged | `.parse-error.log` and non-canonical logs may intentionally differ | Exclude them or document why the helper contract includes them |
| Migration is path-only | Write behavior differs across sites | Confirm no write mode, stdout/stderr, metadata, timeout, cleanup, or caller-path behavior changes |

### Unverified Inputs Relied On

- GitHub issue #1396 body was not directly verified during learn capture.
- Current ProjectHephaestus source files were not directly re-read during learn capture.
- External APIs were not queried during learn capture.
- The grep inventory, file/line references, pytest targets, Ruff commands, and custom bypass scan were planning artifacts, not executed evidence.

### Reviewer Checklist

```text
- [ ] Re-run the exact grep inventory on current main.
- [ ] Broaden the search to all log/state_dir/iteration/parse-error patterns.
- [ ] Decide whether the helper home is neutral enough for all users.
- [ ] Produce a before/after filename table for every migrated canonical log.
- [ ] Confirm parse diagnostics and non-canonical logs are intentionally left alone.
- [ ] Confirm the implementation changes only path construction, not writes.
- [ ] Run focused tests, Ruff check/format, and the final bypass scan.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning session for issue #1396 | Planning artifact only; see [notes](./planning-refactor-risk-review.notes.md) for preserved raw risk capture. |
