---
name: planning-pr-open-file-scope-via-git-diff
description: "When planning a PR-open task, file-scope assertions ('this PR touches train.mojo and tests/models/test_mobilenetv1_train_step.mojo') MUST come from `git diff --name-only <base>...HEAD` run against the checked-out feature branch, never from hardcoded paths in the plan prose. Plan-authored hardcoded paths are always guesses about where files live — the test file might be under `tests/training/`, the source might be under `src/projectodyssey/training/train.mojo`, or the branch may contain files the planner did not anticipate. The correct pattern: the plan specifies `git diff --name-only <base>...HEAD | tee /tmp/changed_files.txt` runs first, the executor pastes the raw output verbatim into the PR body, and the plan includes a documented allow-list pattern (e.g. `train.mojo` or `tests/**/test_*.mojo`) that must match every path in the diff — if the count is unexpected OR any path falls outside the allow-list, abort with a specific verdict. This makes the plan branch-state-driven, not planner-state-driven. Use when: (1) planning any PR-open task where the plan wants to name the files that will change, (2) planning a PR that touches source + tests and the planner is tempted to hardcode the test filename based on the source filename, (3) any planning session where a file path in the plan does not appear in a `git diff --name-only` output the planner has actually seen."
category: architecture
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - pr-open
  - file-scope
  - git-diff
  - hardcoded-paths-hazard
  - allow-list
  - branch-state
---

# Planning: File-Scope Assertions in PR-Open Plans Come From `git diff --name-only`, Never Hardcoded Paths

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-02 |
| **Objective** | Prevent plan-authored hardcoded file paths (e.g. `train.mojo`, `tests/models/test_mobilenetv1_train_step.mojo`) from making it into PR-open plans and then into PR bodies without verification against the branch's actual diff. |
| **Outcome** | PLAN ONLY — captured during ProjectOdyssey #5527 planning where the plan hardcoded two file paths without running `git diff --name-only` against the feature branch. The paths may be right; they were not verified. This skill formalizes the corrective pattern. |
| **Verification** | unverified |

## When to Use

- Planning a PR-open task where the plan wants to name the files that will change.
- Planning a PR that touches source + tests: the planner knows the source filename and is tempted to derive the test filename by convention (`test_<source>.mojo`), then hardcode it — but naming conventions vary between subprojects and the actual test may live at `tests/training/test_train.mojo` rather than `tests/models/test_<model>_train_step.mojo`.
- Any planning session where a file path in the plan does not appear in a `git diff --name-only` output the planner has actually seen (either because the branch is not checked out yet or because the planner is drafting the plan from memory).
- Planning a PR body's "Files Modified" section: the section MUST be filled from `git diff --name-only` output, never from the plan's hardcoded list.

## Verified Workflow

> **Warning:** This section is a **Proposed Workflow**, not a verified one. It was
> *not* executed against a live ProjectOdyssey branch in this session; the specific
> allow-list regex below (`^(train\.mojo|tests/.+/test_.+\.mojo)$`) is illustrative,
> not verified against the actual repo's tests/ layout. Verify your repo's tests/
> conventions before writing your allow-list.

### Quick Reference

```bash
# 1. Enumerate the branch's actual diff:
base=main
git diff --name-only "$base"...HEAD | tee /tmp/changed_files.txt

# 2. Sanity-check the count matches the plan's expectation:
expected=2  # from the plan
actual=$(wc -l < /tmp/changed_files.txt)
[ "$actual" = "$expected" ] || { echo "ABORT: expected $expected changed files, got $actual"; cat /tmp/changed_files.txt; exit 1; }

# 3. Allow-list check — every path must match a documented pattern:
allow_re='^(train\.mojo|tests/[^/]+/test_[^/]+\.mojo)$'
grep -vE "$allow_re" /tmp/changed_files.txt && { echo "ABORT: path(s) above are outside the allow-list"; exit 1; }

# 4. Paste diff output into PR body via placeholder:
sed -e "/<<CHANGED_FILES>>/{
    r /tmp/changed_files.txt
    d
}" pr-body.md.template > pr-body.md
```

### Detailed Steps

1. **In the plan**, do NOT write literal file paths in prose. Write allow-list patterns. Example: instead of "this PR modifies `train.mojo` and `tests/models/test_mobilenetv1_train_step.mojo`," write "this PR is scoped to (a) exactly one file matching `train.mojo` at the training-entry-point path, and (b) exactly one file matching `tests/**/test_*.mojo`. The executor materializes the actual paths via `git diff --name-only main...HEAD`."
2. **The allow-list patterns come from the repo's conventions**, not from the planner's guess. Before writing an allow-list, grep the repo for the actual test-file naming pattern: `git ls-files 'tests/**/test_*.mojo' | head` — the observed pattern is the allow-list.
3. **Specify the file count in the plan** ("expected: 2 changed files"). At execute time, `wc -l` on the diff output must match; if not, abort. This catches (a) planner underestimation (branch touches more files than expected) and (b) branch-state drift (a rebase pulled unexpected files).
4. **The PR body's "Files Modified" section** is filled with a `<<CHANGED_FILES>>` placeholder that gets substituted from the `git diff --name-only` output — same pattern as the sibling-artifact-extraction skill.
5. **Do not** trust the planner's mental model of the branch. The planner may have designed the branch weeks ago and forgotten what was actually committed. The branch itself is authoritative.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | ProjectOdyssey #5527 planning session: hardcode `train.mojo` and `tests/models/test_mobilenetv1_train_step.mojo` in the plan as the exact files the PR touches, without running `git diff --name-only` against the feature branch. | The plan cannot verify the paths without either checking out the branch or trusting a mental model of what was committed. If `train.mojo` is actually under `src/projectodyssey/training/` or the test file is under `tests/training/`, the hardcoded paths in the PR body will be wrong. | Use allow-list patterns in the plan; materialize actual paths from `git diff --name-only` at execute time. |
| Attempt 2 | Derive the test filename from the source filename by convention (`test_<source>.mojo`). | The convention is not universal — different subprojects use different test paths (`tests/training/`, `tests/models/`, `tests/integration/`). Conventions drift; the branch is authoritative. | Grep the repo's actual test-file naming pattern with `git ls-files` before writing any allow-list. |

## Results & Parameters

### Configuration

```yaml
plan-pattern:
  file-scope:
    source: "git diff --name-only <base>...HEAD"
    expected-count: <integer>
    allow-list-regex: '^(<pattern1>|<pattern2>)$'
    guards:
      - "actual count == expected count"
      - "every path matches allow-list-regex"
    pr-body:
      files-modified-section: "<<CHANGED_FILES>>"
      substitute-from: /tmp/changed_files.txt
```

### Expected Output

- If the branch's diff count differs from the plan's expected count → abort with the actual diff for review.
- If any diff path falls outside the allow-list → abort with the offending paths.
- On success → the PR body's "Files Modified" section contains the verbatim `git diff --name-only` output, and every path was validated against a documented pattern from the plan.
- Plan prose contains ZERO literal file paths (only allow-list patterns).

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #5527 planning session (2026-07-02) — captured the anti-pattern (hardcoded `train.mojo` and `tests/models/test_mobilenetv1_train_step.mojo` in plan). Corrective pattern PLAN ONLY, not executed. | See ProjectOdyssey issue #5527 comments. |

## References

- [fix-hardcoded-target-path](fix-hardcoded-target-path.md) — sibling skill; covers hardcoded paths in SCRIPTS, whereas this skill covers hardcoded paths in PR-open PLANS.
- [planning-pr-body-extract-sibling-artifact-at-runtime](planning-pr-body-extract-sibling-artifact-at-runtime.md) — companion skill; uses the same `<<TOKEN>>` placeholder pattern for cross-issue artifact content.
- [planning-pr-body-numeric-claims-source-derived](planning-pr-body-numeric-claims-source-derived.md) — companion skill for numeric claims.
- [planning-pr-open-load-bearing-assumption-hygiene](planning-pr-open-load-bearing-assumption-hygiene.md) — companion skill for repo-settings and compat-script probes.
