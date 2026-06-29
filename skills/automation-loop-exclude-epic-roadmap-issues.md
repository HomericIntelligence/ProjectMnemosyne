---
name: automation-loop-exclude-epic-roadmap-issues
description: "An automation/planning loop that auto-discovers GitHub issues MUST exclude epic/roadmap TRACKING issues (checklists of child work, not code tasks) or it will plan+implement them and produce a wrong code PR. Detect an epic via an `epic`/`roadmap` LABEL (case-insensitive) OR an `epic`/`roadmap` substring in the TITLE — native GitHub issue types are NOT reachable from the installed gh CLI. Filter at BOTH the loop discovery chokepoint and the standalone planner, tag excluded epics `state:skip` idempotently, and keep the write OUT of the pure 'return [] on failure / never raise' discovery function. Use when: (1) an auto-discovery loop plans an epic/roadmap tracking issue as if it were code, (2) designing an issue-type filter and reaching for `gh issue list --json issueType`, (3) a label convention exists but is not consistently applied, (4) you need to exclude tracking issues from convergence/open-issue gates too."
category: tooling
date: 2026-06-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [epic, roadmap, tracking-issue, automation-loop, issue-discovery, gh-cli, state-skip, partition, label-and-title-signal, planner-filter, dry-chokepoints, pure-function-contract]
---

# Automation Loop: Exclude Epic/Roadmap Tracking Issues from Discovery

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-29 |
| **Objective** | Stop an auto-discovery automation/planning loop from planning + implementing epic/roadmap TRACKING issues (checklists of child work) as if they were code tasks, which produces a wrong code PR |
| **Outcome** | Successful (local) — pure `is_epic`/`partition_epics` helper + filtering at both the loop discovery chokepoint and the standalone planner + idempotent `state:skip` tagging; 2217 automation unit tests pass locally, whole-tree mypy clean, ruff clean |
| **Verification** | verified-local — 2217 unit tests + mypy + ruff clean locally; CI pending on PR #1670 |
| **Source** | ProjectHephaestus issue #1669 / PR #1670 |

> verified-local — 2217 unit tests + mypy + ruff clean locally; CI pending on PR #1670 (not yet verified-ci).

An epic/roadmap issue is a **snapshot of child work** — its body is a checklist, not a spec. If an
auto-discovery loop treats it as a code task, the planner/implementer will fabricate a code change and
open a PR that has nothing to do with the actual (child) work. The fix is to detect tracking issues at
discovery time and exclude them from every path that feeds the planner.

## When to Use

- An auto-discovery automation/planning loop plans an epic/roadmap tracking issue and emits a wrong code PR.
- You are about to design an issue-type filter and reaching for `gh issue list --json issueType`.
- A repo has an `epic`/`roadmap` label convention but it is NOT consistently applied (so label-only detection misses issues).
- You need tracking issues excluded from convergence / open-issue-count gates as well as from planning.
- A loop supports both auto-discovery AND an explicit `--issues` override (both paths must filter).

## Verified Workflow

### Quick Reference

```bash
# 1. VERIFY native issue types are unreachable before designing any type filter:
gh issue list --json issueType   # -> "Unknown JSON field: issueType" on the installed gh
# => label + title are the ONLY available signals.

# 2. Detection signal (case-insensitive):
#    epic iff  ('epic' or 'roadmap' in labels)  OR  ('epic' or 'roadmap' substring in title)
```

```python
# Pure helper in the label-vocabulary module (hephaestus/automation/state_labels.py):
def is_epic(labels: Iterable[str], title: str) -> bool:
    lowered = {label.lower() for label in labels}
    if {"epic", "roadmap"} & lowered:
        return True
    title_l = title.lower()
    return "epic" in title_l or "roadmap" in title_l

def partition_epics(issues_meta):  # -> (kept, epics)
    kept, epics = [], []
    for meta in issues_meta:
        (epics if is_epic(meta.labels, meta.title) else kept).append(meta)
    return kept, epics
```

### Detailed Steps

1. **Confirm the gh field gap first.** Run `gh issue list --json issueType`. On the installed gh this
   returns `Unknown JSON field: issueType`. Native issue types are not available, so label + title are
   your only signals. Do not design a filter around `issueType`.

2. **Put the detection logic in ONE pure module.** Add `is_epic(labels, title)` and
   `partition_epics(issues_meta) -> (kept, epics)` to the existing label-vocabulary module
   (`hephaestus/automation/state_labels.py`). Both are pure functions — easy to unit test, reused by
   every caller (DRY).

3. **Filter at the loop discovery chokepoint.** In `_list_open_issue_numbers`
   (`hephaestus/automation/loop_repo_manager.py`), change the `gh issue list` JSON projection from
   `number` to `number,labels,title`, JSON-parse the output (do NOT use `--jq` — you need the structured
   fields), call `partition_epics`, and return only the kept numbers. `_count_open_issues` calls this
   same function, so convergence / open-issue gates auto-exclude epics for free.

4. **Filter at the standalone planner too.** In `PlannerStateManager.filter`
   (`hephaestus/automation/planner_state.py`), reuse the already-cached labels plus a NEW batched
   `fetch_all_issue_titles_graphql` (write it as a sibling of `fetch_all_issue_labels_graphql` in
   `review_state.py`). Both paths are required: an explicit `--issues` run bypasses the loop's discovery
   filter (`cfg.issues or _list_open_issue_numbers(...)`), so the planner must filter independently.

5. **Tag excluded epics `state:skip` idempotently — OUTSIDE the pure discovery function.** Add a
   `skip_epics(epics_labels)` helper that guards with `is_skipped` (no-op if already skipped) and reuses
   `gh_issue_add_labels`. Do the tagging best-effort, wrapped in `try/except`, in the CALLER — never
   inside `_list_open_issue_numbers`, which must keep its "return `[]` on any failure, never raise"
   contract. A write that can fail must not be able to break discovery.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Native issue type | `gh issue list --json issueType` to filter by GitHub issue type | Installed gh returns `Unknown JSON field: issueType` — native types are not exposed by the CLI | Fall back to label + title detection; verify gh field availability BEFORE designing any issue-type filter |
| Label-only detection | Detect epics solely by the `epic`/`roadmap` label | Convention not consistently applied — at the time, 94 open issues and ZERO carried the label | Add a title-substring fallback (`epic`/`roadmap` in the title, case-insensitive) |
| Tag inside pure discovery | Write `state:skip` from inside `_list_open_issue_numbers` | Violates that function's "return `[]` on failure / never raise" contract — a failed label write would break discovery | Keep writes OUT of pure discovery; do best-effort tagging in the caller, wrapped in try/except |

## Results & Parameters

```text
Detection rule (case-insensitive):
  is_epic = ('epic' or 'roadmap' in labels) OR ('epic' or 'roadmap' substring in title)

Why the title fallback matters: 94 open issues, 0 carried the epic/roadmap label at the time.
Native gh issue types are NOT reachable: `gh issue list --json issueType` -> "Unknown JSON field".

Two chokepoints, one shared pure helper (DRY):
  hephaestus/automation/state_labels.py
    - is_epic(labels, title) -> bool                 # pure
    - partition_epics(issues_meta) -> (kept, epics)  # pure
    - skip_epics(epics_labels)                       # idempotent write; guards via is_skipped,
                                                     #   reuses gh_issue_add_labels

  hephaestus/automation/loop_repo_manager.py
    - _list_open_issue_numbers: gh issue list --json number,labels,title  (JSON-parse, NOT --jq)
        -> partition_epics -> return kept numbers
        -> MUST keep "return [] on any failure, never raise" contract
        -> skip_epics tagging done best-effort in the CALLER, wrapped try/except
    - _count_open_issues calls _list_open_issue_numbers -> convergence/open-issue gates auto-exclude epics

  hephaestus/automation/planner_state.py
    - PlannerStateManager.filter: reuse cached labels + NEW fetch_all_issue_titles_graphql
        (sibling of fetch_all_issue_labels_graphql in review_state.py)
    - Needed because explicit `--issues` runs bypass loop discovery:
        cfg.issues or _list_open_issue_numbers(...)

Verification (local only): 2217 automation unit tests pass; whole-tree mypy clean; ruff clean.
CI on PR #1670 still pending -> NOT verified-ci.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1669 / PR #1670 — exclude epic/roadmap tracking issues from the automation discovery + planner loop | 2217 unit tests + mypy + ruff clean locally; CI pending |
