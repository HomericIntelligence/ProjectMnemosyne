---
name: planning-check-already-shipped-before-planning
description: "Before writing an implementation plan, verify the ACTUAL on-disk state — grep/wc/test the real source — instead of trusting the issue body's stated starting condition (LOC counts, method counts, \"needs to be done\"). The fix may already be merged, OR already landed uncommitted in a sibling worktree that git log will NOT show. Use when: (1) planning a follow-up or consolidation issue, (2) issue body cites specific file paths or LOC/method counts, (3) git status shows an untracked sibling worktree directory."
category: architecture
date: 2026-06-15
version: "1.1.0"
user-invocable: false
verification: verified-local
history: planning-check-already-shipped-before-planning.history
tags: []
---

# Planning: Check If Already Shipped Before Writing a Plan

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-15 |
| **Objective** | Detect whether a GitHub issue's fix is already done before writing an implementation plan — whether merged to `main` OR landed uncommitted on disk in a sibling worktree |
| **Outcome** | Successful — caught both a shipped fix (PR #1308, merged) and a fix that had already landed uncommitted in an untracked `1-fix` worktree (issue #1357) that `git log` would never have surfaced |
| **Verification** | verified-local (the uncommitted-worktree finding ran only a SUBSET of tests locally; the original merged-fix example remains verified-ci) |
| **History** | [changelog](./planning-check-already-shipped-before-planning.history) |

## When to Use

- Planning a follow-up or consolidation issue (issue body may lag behind actual implementation)
- Issue body cites specific file paths, line numbers, **or LOC/method counts** (e.g. "3,570 lines, ~60 methods, god-class needing decomposition") — these go stale after merges OR after the work lands uncommitted
- Picking up an issue from a batch/backlog queue — the fix may have been merged hours or days ago
- **`git status` shows an untracked sibling worktree directory** (e.g. `1-fix/`) — the implementation may already be done there but not yet committed/merged, so `git log` on `main` shows nothing
- The issue describes a refactor/decomposition as FUTURE work but a parallel branch/worktree may have already completed it
- Before any implementation plan step — running this check costs seconds and avoids wasted (and worse, duplicate/conflicting) work

## Verified Workflow

### Quick Reference

```bash
# 0. FIRST: is the work already done in an UNCOMMITTED sibling worktree?
#    git log only sees committed history — an untracked worktree is invisible to it.
git status --porcelain            # an untracked dir like "?? 1-fix/" is a red flag
git worktree list                 # enumerate every checkout that may hold the work

# 1. MEASURE the file the issue describes — do NOT trust the issue's stated counts.
#    Issue claims "3,570 lines / ~60 methods, needs decomposition"? Count it yourself:
wc -l path/to/real/file.py                              # actual LOC vs claimed LOC
grep -cE "^\s+def " path/to/real/file.py               # actual method count

# 2. Grep for the function/symbol cited in the issue — find the real file
grep -r "function_name_from_issue" hephaestus/ --include="*.py" -l

# 3. Check if the fix is already in place (new module files, delegation stubs, wiring)
grep -n "the_new_behavior_or_regex" path/to/real/file.py
ls path/to/expected/new_collaborator_modules.py        # do the "to-be-created" files exist?

# 4. Check recent commits for matching descriptions (catches MERGED work only)
git log --oneline -10
git show --stat <sha>

# 5. Run the relevant tests — a passing suite means it's already implemented.
#    NOTE: a SUBSET run will fail the coverage gate (e.g. 9% < threshold) — that is a
#    gate artifact of the subset, NOT a code failure. Run the FULL suite + mypy + ruff
#    before claiming "done"; a green subset is only verified-local.
pixi run pytest tests/unit/path/to/relevant_tests.py -v
```

### Detailed Steps

0. **Check for an uncommitted sibling worktree FIRST** — `git log` only sees committed history. If the work landed in an untracked worktree (`git status` shows `?? 1-fix/`) or any checkout in `git worktree list`, the merged-commit checks below will all come up empty even though the work is fully done on disk. Always run `git status --porcelain` and `git worktree list` before trusting "git log shows nothing → not done yet."

1. **Measure the file, don't trust the issue's stated counts** — The issue body's starting condition (LOC, method count, "needs to be done") is a NARRATIVE that may describe an older state. The issue may have been filed before the work landed. Ground every plan claim in a real measurement: `wc -l file.py`, `grep -cE "^\s+def " file.py`. If the issue says "3,570 lines needing decomposition" but `wc -l` reports 2,449 (already at the target) with the four collaborator modules already on disk, the work is DONE — planning blind would re-do it and risk a duplicate/conflicting implementation.

2. **Find the real file** — Issue bodies frequently cite stale file paths or wrong line numbers. Never trust them directly. Grep the codebase for the function name, class name, or constant names mentioned in the issue. Cite `file.py:line` evidence for every plan claim.

3. **Check for the fix already present** — Once you have the real file path, grep for the new behavior (new constant, new code path, new branch). For a decomposition: `ls` the collaborator modules the issue says should be CREATED, grep for the delegation stubs, and confirm the wiring. If they already exist, the fix is in.

4. **Confirm preservation notes against the live facade** — When a consolidation issue names specific methods/PRs to preserve verbatim (e.g. `_resolve_dirty_pr` #1347, `_resolve_blocked_pr`/`_address_threads_once` #1356, the `resolve_dirty` recursion guard #1355), `grep` to confirm each named method STILL exists on the facade before claiming preservation. This is a critical planning input — a missing method means a regression slipped in.

5. **Confirm via git log (catches MERGED work only)** — Run `git log --oneline -10` to see recent commits. Look for a message matching the issue description. Run `git show --stat <sha>` to confirm the modified files match. Remember this finds only committed work; combine with step 0.

6. **Run tests — and know what a SUBSET proves** — Run `pixi run pytest <relevant test module> -v`. A green subset shows the implementation works, but the coverage gate WILL fail on a subset (e.g. 9% < 83%) purely because most modules went unexercised — that is a gate artifact, not a code failure. Do not claim "done"/`verified-ci` from a subset. The full suite + `mypy` + `ruff` + import-surface/automation-boundary tests are the real proof; if you did not run them this session, the claim is `verified-local`.

7. **Verify DIP/constructor claims against actual signatures, not call sites** — Asserting "no collaborator receives `self`" from reading only the `__init__` wiring is an inference, not proof: a collaborator's own constructor could secretly accept a back-reference. Open each collaborator's `__init__` signature, or let `mypy` be the proof — and label the claim "inferred from call site" until you do.

8. **Document for auditability** — Even when already done, record the evidence: for merged work the commit SHA + PR number + `file:line` range + covering tests; for uncommitted-worktree work the worktree path, the `wc -l`/method counts observed, and which tests passed. Note that line numbers cited from an uncommitted tree may SHIFT if that work is rebased/squashed before merge.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust issue body file paths | Used `python_version.py:290-293` as the implementation target (as cited in the issue) | Actual code lived in `scripts_lib/check_python_version_consistency.py` — a completely different file | Issue bodies cite stale paths; always grep to locate the real code |
| Skip pre-plan grep | Started outlining implementation steps before checking whether the code was already there | Would have produced a plan to re-implement something already merged in PR #1308 | A 10-second grep check prevents hours of wasted planning |
| Assume consolidation issue = unshipped | Treated the issue as describing future work because its body said "not yet done" | The issue was a consolidation tracker that lagged behind the actual PR by hours | Consolidation/follow-up issues are high-risk for describing already-shipped work |
| Rely on `git log` alone for "is it done?" | Checked recent commits on `main`; saw nothing matching the decomposition | The work had landed in an UNCOMMITTED untracked `1-fix` worktree — invisible to `git log` because it was never committed | `git log` sees only committed history; always run `git status --porcelain` + `git worktree list` first to catch on-disk-but-uncommitted work |
| Trust the issue's stated LOC/method counts | Planned a decomposition against the issue's "3,570 lines, ~60 methods" starting condition | The file was already 2,449 lines (at the target), all four collaborator modules already existed, tests already green | Measure with `wc -l` / `grep -cE "^\\s+def "` before trusting the issue's narrative; planning blind would re-do landed work and risk a conflicting duplicate |
| Infer DIP from `__init__` call site | Asserted "no collaborator receives self" by reading only the `__init__` wiring | Never opened each collaborator's own constructor to confirm none accept a back-reference — the claim was inferred, not proven | Verify constructor signatures directly (or let `mypy` prove it); label call-site inferences as "inferred" until confirmed |
| Treat a green test SUBSET as "done" | Ran 211 tests across the facade + 4 helper files; all passed | The coverage gate FAILED (9.18%) purely because the subset left most modules unexercised; full suite, mypy, ruff, import-surface tests were NOT run | A green subset is `verified-local`, not `verified-ci`; a failing coverage gate on a subset is a gate artifact, not a code failure — run the full gate before claiming done |

## Results & Parameters

### Concrete example (ProjectHephaestus issue #1291 / PR #1308)

Issue body said: "add YAML sequence format support to `extract_ci_matrix_python_versions`" and cited `python_version.py:290-293` as the bug location.

Grep revealed the real file:
```
hephaestus/scripts_lib/check_python_version_consistency.py
```

Fix confirmed present at lines 17–21 (regex constants) and 173–183 (two-phase dispatch):
```python
_CI_MATRIX_BRACKET_RE = re.compile(r"\[([^\]]+)\]")
_CI_MATRIX_SEQUENCE_RE = re.compile(r"^\s*-\s+(.+)$", re.MULTILINE)
```

Commit: `dd15c35f` — merged via PR #1308 on 2026-06-13 with CI green.
All 11 tests in `tests/unit/scripts_lib/test_check_python_version_consistency.py::TestExtractCiMatrixPythonVersions` pass.

### Concrete example (ProjectHephaestus issue #1357 — already done in an UNCOMMITTED worktree)

Issue body described a FUTURE refactor: "Decompose CIDriver god-class (3,570 lines, ~60 methods)
into 4 SRP collaborators." `git log` on `main` showed nothing matching.

But `git status` showed an untracked sibling worktree:

```text
?? 1-fix/
```

Measuring the file inside that worktree instead of trusting the issue:

```bash
wc -l hephaestus/automation/ci_driver.py     # → 2,449  (already ≤ the 2,450 target)
ls hephaestus/automation/pr_discovery.py \
   hephaestus/automation/ci_check_inspector.py \
   hephaestus/automation/ci_fix_orchestrator.py \
   hephaestus/automation/post_merge_processor.py   # → all four already exist
```

Reality: the work was COMPLETE — facade with one-line delegation stubs, lambda-wrapped DIP
providers wired in `__init__`, and 211 tests green across `test_ci_driver.py` + 4 collaborator
helper files. Planning against the issue's narrative would have produced a plan to RE-DO landed
work, creating a conflicting duplicate implementation. The decomposition execution patterns
themselves live in the `python-module-decomposition-and-refactor-patterns` skill; THIS skill's
lesson is the discipline of catching that it was already done before planning.

Caveats recorded honestly for this finding (why it is `verified-local`, not `verified-ci`):

- Only a SUBSET of tests ran (211 passed); the coverage gate failed at 9.18% as a subset artifact.
- `mypy`, `ruff`, and the import-surface/automation-boundary tests were NOT run this session.
- "No collaborator receives `self`" was inferred from the `__init__` call site, not from reading
  each collaborator's own constructor — `mypy` is the real proof, deferred.
- The "3,570 → 2,449" reduction is reconstructed from the issue's stated original + observed
  current; the actual diff was not inspected.
- Cited line numbers come from the uncommitted tree and may shift if `1-fix` is rebased/squashed.

### Decision tree for planners

```
Before writing any implementation plan:
│
├─ 0. git status --porcelain + git worktree list
│   └─ untracked sibling worktree (?? 1-fix/) → INSPECT IT; the work may be done-but-uncommitted
│
├─ 1. wc -l / grep -c the file the issue describes
│   └─ counts already at/past the issue's target → work likely already done (verify, don't re-plan)
│
├─ 2. Grep for the function/symbol name → find the real file path
│
├─ 3. Grep for the new behavior / ls the "to-be-created" modules
│   ├─ FOUND on disk → check BOTH git log (merged?) AND the worktree (uncommitted?)
│   │   └─ implementation present + tests pass → REPORT AS ALREADY DONE (do not re-plan)
│   └─ NOT FOUND → proceed with implementation planning
│
└─ 4. Run tests for the relevant module
    ├─ SUBSET green → verified-local only (coverage gate fails on subsets — a gate artifact)
    ├─ FULL suite + mypy + ruff green → verified-ci, safe to report done
    └─ SOME FAIL → issue is genuinely open; proceed with planning
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1291 — YAML sequence support in CI matrix extractor | PR #1308 merged 2026-06-13, commit dd15c35f (verified-ci) |
| ProjectHephaestus | Issue #1357 — CIDriver god-class decomposition already landed in an uncommitted `1-fix` worktree | `ci_driver.py` measured 2,449 lines (≤ target), all 4 collaborator modules present, 211 subset tests green; full gate not run (verified-local) |
