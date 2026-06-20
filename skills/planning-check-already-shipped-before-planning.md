---
name: planning-check-already-shipped-before-planning
description: "Before writing an implementation plan, verify the ACTUAL on-disk state — grep/wc/test the real source — instead of trusting the issue body's stated starting condition (LOC counts, method counts, \"needs to be done\"). The fix may already be merged, OR already landed uncommitted in a sibling worktree that git log will NOT show. This applies HARDEST to a large extraction/migration/\"do X\" EPIC filed months earlier: the work is often ALREADY DELIVERED under a different ADR/PR, so the correct plan is verification-and-closeout, NOT re-implementation — run cheap existence checks first (find target/src, ls source/src/<moved-dir> expecting ABSENT, grep -rl MovedSymbol source-repo), map every acceptance criterion to a runnable command, and build+run the actual suite to prove \"CI passes with the new code\" is ALREADY true. And even when the work IS already on disk, the plan-loop still demands a FORWARD-LOOKING plan — a retrospective status note gets NOGO'd, gates you defer to the reviewer are stage-handoff failures, and an EMPTY/placeholder artifact (output withheld while a background job runs) is an automatic Grade F. Use when: (1) planning a follow-up, consolidation, or EXTRACTION/MIGRATION epic, (2) issue body cites specific file paths or LOC/method counts, (3) git status shows an untracked sibling worktree directory, (4) the plan-loop reviewer NOGO'd your plan as a 'status note' / retrospective, (5) you're tempted to wait on a background job / Monitor / long test run before producing a due plan or review artifact, (6) an epic's premise asserts work must move from repo A to repo B and you have not confirmed it didn't already happen."
category: architecture
date: 2026-06-19
version: "1.4.0"
user-invocable: false
verification: verified-local
history: planning-check-already-shipped-before-planning.history
tags: [planning, already-shipped, stale-issue-premise, extraction-epic, migration, verification-and-closeout, reframe, cross-repo, adr-attribution, acceptance-criteria-mapping, ifdef-guarded-untested, residuals, ctest, cpp]
---

# Planning: Check If Already Shipped Before Writing a Plan

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Detect whether a GitHub issue's fix is already done before writing an implementation plan — covering merged fixes, uncommitted-worktree work, AND large EXTRACTION/MIGRATION epics already delivered under a different ADR/PR — and, even when it IS done, still emit a FORWARD-LOOKING plan (not a retrospective status note) and run every gate yourself instead of deferring to the plan reviewer |
| **Outcome** | Successful — caught a shipped fix (PR #1308, merged), a fix that had already landed uncommitted in an untracked `1-fix` worktree (issue #1357), and a months-old ProjectAgamemnon extraction epic whose move was ALREADY delivered under a different ADR (586/589 tests pass, agents+integration labels 100% green) so the plan reframed to verification-and-closeout; also diagnosed why a "status note" plan for landed work was NOGO'd (Grade D), and why a SUBSEQUENT plan that withheld its content while a background `pytest` ran was NOGO'd even harder (Grade F, empty placeholder), and what resolves each |
| **Verification** | verified-local — the extraction-epic INVESTIGATION procedure (find/ls/grep + `cmake --build --preset debug` + `ctest --preset debug -L`) was actually run this session and confirmed the move complete, but the downstream PLAN was NOT executed end-to-end in CI; cross-repo Keystone build, ADR-015 attribution, the 3 failing tests, the `#ifdef ENABLE_GRPC` path, and the 3,393-line figure all remain inferred/unreconciled. The earlier uncommitted-worktree finding ran a SUBSET of tests; the boundary/mypy/ruff gates ran GREEN; the original merged-fix example remains verified-ci |
| **History** | [changelog](./planning-check-already-shipped-before-planning.history) |

## When to Use

- Planning a follow-up or consolidation issue (issue body may lag behind actual implementation)
- **Planning a large EXTRACTION / MIGRATION / "move X from repo A to repo B" epic filed weeks or months ago** — these are the single highest-risk class for "already delivered." A big move tends to land under a NEW ADR / PR that does not reference the old epic number, so the epic sits OPEN long after the work shipped. Before planning the move, prove it didn't already happen: `find <target>/src -name '*.cpp'` (does the moved code already live in the destination?), `ls <source-repo>/src/<moved-dir>` (expect ABSENT if moved), `grep -rl <MovedSymbol> <source-repo>` (expect no compiled hits). The correct plan is then **verification-and-closeout**, not re-implementation.
- Issue body cites specific file paths, line numbers, **or LOC/method counts** (e.g. "3,570 lines, ~60 methods, god-class needing decomposition") — these go stale after merges OR after the work lands uncommitted
- **The epic lists acceptance criteria phrased as future work** ("CI passes with the new code", "the type no longer exists in repo A", "downstream repo still builds") — map EACH criterion to a runnable command and check current state rather than assuming it is unmet; the criteria are often ALREADY satisfied
- Picking up an issue from a batch/backlog queue — the fix may have been merged hours or days ago
- **`git status` shows an untracked sibling worktree directory** (e.g. `1-fix/`) — the implementation may already be done there but not yet committed/merged, so `git log` on `main` shows nothing
- The issue describes a refactor/decomposition as FUTURE work but a parallel branch/worktree may have already completed it
- **The plan-loop reviewer NOGO'd your plan as a "status note" / retrospective** — discovering the work is already on disk does NOT exempt you from writing a forward-looking implementation plan; describing what shipped (bullets + caveats) fails the rubric even when the code is correct
- **You're tempted to wait on a background job / Monitor / long test run before producing a due plan or review artifact** — a deliverable with a hard turn-boundary (a plan-loop artifact, a review verdict, any "your output IS the posted artifact" contract) must be emitted NOW from evidence in hand; blocking the emission on a pending background task produces an empty/placeholder artifact that is an automatic Grade F
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

# 6. EXTRACTION/MIGRATION EPIC: prove the move already happened with cheap existence checks FIRST.
find <target-repo>/src -name '*.cpp'                 # moved code already in the destination?
ls <source-repo>/src/agents 2>&1                      # expect "No such file" if it moved out
grep -rl "<MovedSymbol>" <source-repo>/src            # expect NO compiled hits (residuals are .ifdef/comments only)
# Then map every acceptance criterion to a command and BUILD + RUN the real suite:
cmake --build --preset debug
ctest --preset debug -L <label>                       # e.g. -L agents -L integration → "CI passes" is ALREADY true
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

9. **Still emit a FORWARD-LOOKING plan even when the work is already on disk** — The plan-loop reviewer grades the PLAN ARTIFACT, not the on-disk reality. "The fact that the underlying work appears correct on disk does not rehabilitate the plan artifact itself." Writing 5 bullets that DESCRIBE what shipped (plus caveats) is a **category error** — it is a retrospective status note, not a plan, and gets NOGO'd (Grade D) on Completeness, Concreteness, Verification-Plan, and Stage-Handoff. Reshape it as a real plan even when describing already-landed code: frame each module as a "files to create/modify" step with the actual code, give a numbered build order, and give a per-acceptance-criterion verification command. The plan reads as forward-looking; the only honest footnote is "implemented identically to this on disk."

10. **RUN the gates yourself — never DEFER a verification you could run to the reviewer** — Listing a checkable gate (e.g. ADR-0001 boundary tests, `mypy`) as "highest-value follow-up for the plan reviewer" is a **stage-handoff failure** that triggers NOGO. If you can run it during planning, run it and cite it as completed. For the #1357 decomposition this session ran and observed GREEN: the import-surface + automation-boundary tests (ADR-0001 intact), whole-tree `mypy` (the real proof of DIP — no collaborator secretly takes `self`/`CIDriver`, upgrading step 7's call-site inference to proof), `ruff`, and an import-graph confirmation that all 4 collaborators import only sibling `hephaestus.automation.*` + `hephaestus.agents.runtime`, never the base `hephaestus` surface (dependency arrow points automation→library, never reversed). **Gotchas:** (a) the `pixi run mypy` task already targets the whole tree — passing file paths causes `error: Duplicate module named ...`; run `pixi run mypy` with NO arguments. (b) `pixi run pytest` injects `--cov`; ad-hoc subset runs need `--no-cov` (or `-p no:cov`) or pytest errors `unrecognized arguments: --cov`. (c) a subset run reporting low TOTAL coverage (e.g. 9.18%) is a SUBSET ARTIFACT — never cite it as the suite being red OR green.

11. **NEVER gate the emission of a due artifact on an in-flight background job** — Emit the COMPLETE forward-looking plan (or review verdict) from the evidence already in hand: line counts, grep'd stubs, already-green gates. If one verification is still running (a background `pytest`, a `Monitor` you launched, an external job), mark THAT one criterion as "not yet confirmed — open risk, run before completion" INSIDE the Verification section, and emit the rest of the artifact anyway. A plan that is 95% confirmed + 1 flagged open risk is gradeable; a placeholder is an automatic Grade F. Distinguish two situations: (a) a **transient external dependency still in progress when you have NO deadline** — fine to keep working/waiting; (b) **an artifact is due THIS turn** ("your output IS the posted artifact") — you MUST emit now from evidence in hand, never output nothing. Pausing the turn to wait for a background full-suite count, then submitting the literal placeholder "Output not yet flushed. I'll wait for the monitor notification rather than polling.", fails EVERY rubric dimension (Requirements / Completeness / Concreteness / Risk / Verification / Stage-Handoff all F) and is STRICTLY WORSE than the status-note NOGO of step 9 — it addresses none of the prior findings either.

12. **EXTRACTION/MIGRATION EPIC: verify the premise before planning the move, and run the CHEAP existence checks first** — A large "extract/move X from repo A into repo B" epic is the highest-risk class for already-being-done, because big moves land under a NEW ADR/PR that does not back-reference the old epic, so the epic stays OPEN long after delivery. Run the cheapest disconfirming checks FIRST, in this order, because each instantly reveals "already moved": (a) `find <target-repo>/src -name '*.cpp'` — does the moved implementation already live in the destination? (b) `ls <source-repo>/src/<moved-dir>` — expect "No such file or directory" if it really moved OUT. (c) `grep -rl "<MovedSymbol>" <source-repo>/src` — expect NO hits in compiled code. Then **map every acceptance criterion in the epic to a runnable command** and check current state rather than assuming the criteria are unmet — "the type no longer exists in A", "downstream still builds", "CI passes with the new code" are usually ALREADY satisfied. Confirm the strongest criterion ("CI passes with the new code") by actually building and running the suite: `cmake --build --preset debug` then `ctest --preset debug -L <label>` (e.g. `-L agents -L integration`). When this all holds, the correct plan is **verification-and-closeout**, not re-implementation.

13. **Distinguish residuals that MATTER from harmless ones — do not over-scope the closeout** — After concluding "already moved," a `grep` for the moved symbol in the source repo may still return hits. Triage them before deciding the move is incomplete: a hit inside ACTIVELY-COMPILED code (a moved type still referenced from a `.cpp` that the default build compiles) is a real residual the closeout must address; a hit inside a `#ifdef`-guarded include that the current build config never compiles, or inside a Doxygen `@code`/comment example, is harmless and must NOT inflate the closeout scope. **Caveat the build-config gap explicitly:** an `#ifdef ENABLE_GRPC`-guarded path (e.g. a coordinator-submission branch) never compiles in the default preset, so "extraction complete" covers only the non-guarded surface — the guarded path is UNTESTED in this build and must be flagged as an open risk, not silently claimed done.

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
| Submit a "status note" as the plan | Wrote 5 descriptive bullets + caveats summarizing what already shipped, instead of a forward-looking plan | NOGO, Grade D — a category error: it described reality rather than planning work; failed Completeness/Concreteness/Verification-Plan/Stage-Handoff. "On disk being correct does not rehabilitate the plan artifact" | Even when the work is done, emit a REAL plan: design + files-to-modify-with-code + numbered build order + per-criterion verification commands |
| Defer a checkable gate to the reviewer | Listed `test_import_surface.py` / `test_automation_boundary.py` / `mypy` as "highest-value follow-up for the plan reviewer" | Stage-handoff failure → NOGO; a verification you can run yourself must not be punted downstream | RUN every gate you can during planning and cite it as completed; only genuinely-unrunnable checks may be handed off |
| Run `pixi run mypy <paths>` | Passed explicit file paths to the mypy task to type-check only the touched files | `error: Duplicate module named ...` — the `pixi run mypy` task already targets the whole tree, so extra paths double-register modules | Run `pixi run mypy` bare (no arguments); it already covers the whole source tree |
| Run subset `pixi run pytest <files>` without `--no-cov` | Invoked an ad-hoc subset pytest run to check a few modules | `pytest: error: unrecognized arguments: --cov` — the pixi pytest task injects `--cov`, which the bare pytest invocation rejects | Add `--no-cov` (or `-p no:cov`) for ad-hoc subset runs; and treat any low TOTAL-coverage number from a subset as an artifact, not a result |
| Pause the turn on a background job, submit an empty artifact | Started a long-running background `pytest tests/unit/automation` / `Monitor` to get a full-suite pass count, then PAUSED and deferred the turn — so the submitted plan artifact was the literal placeholder "Output not yet flushed. I'll wait for the monitor notification rather than polling." | NOGO, Grade F — an empty/placeholder artifact fails EVERY rubric dimension (Requirements / Completeness / Concreteness / Risk / Verification / Stage-Handoff all F); STRICTLY WORSE than the status-note NOGO and addresses none of the prior findings | Never gate a due artifact on an in-flight background job. Emit the complete plan from evidence in hand; a still-running gate becomes a flagged open-risk line in Verification, never a reason to output nothing. "No deadline → may wait" vs "artifact due this turn → emit from evidence + flag open risk" |
| Assume an extraction epic = unstarted work | Treated an "extract agents from repo A into repo B" epic (filed months earlier) as future work to plan top-to-bottom | The extraction was ALREADY delivered under a different ADR/PR that never back-referenced the epic; `find <target>/src`, `ls <source>/src/agents` (absent), and a `grep` for the moved symbol proved the move was complete and the suite (586/589) already green | A large move filed long ago is the highest-risk class for "already done" — run cheap existence checks FIRST and reframe to verification-and-closeout, never re-implement |
| Trust a sibling working tree for a cross-repo "still builds" claim | Asserted "ProjectKeystone CI still passes" (an epic acceptance step) from a local `cmake` build in the sibling `../ProjectKeystone` working tree | The local clone could be stale/dirty; a local build is NOT the repo's CI on its main branch — the claim was inferred, not observed | Cross-repo "downstream still builds/CI passes" claims must be confirmed against that repo's actual CI/main, not a local sibling tree; label sibling-tree builds as "inferred, local only" |
| Attribute provenance from an in-repo comment | Concluded the work was "delivered under ADR-015 / Odysseus#143" because `CMakeLists.txt` comments said so | The ADR doc itself was never opened; an in-repo comment is hearsay, not the ADR | Verify "delivered under ADR-N" against the ADR document, not a code comment that cites it |
| Dismiss failing tests as out-of-scope WIP | Wrote off 3 failing tests as another branch's work-in-progress because `git status` showed the file as untracked (`??`) | If that file is actually within the epic's intended scope, dismissing it is wrong — untracked ≠ unrelated | Before dismissing failures as out-of-scope, confirm the file is NOT part of the issue's acceptance scope; untracked status alone does not prove irrelevance |
| Claim "extraction complete" while a path is `#ifdef`-guarded out | Declared the move done after a green build/suite, when the gRPC/coordinator-submission path sat behind `#ifdef ENABLE_GRPC` and never compiled in the default preset | "Complete" covered only the non-guarded surface; the guarded coordinator path in `chief_architect_agent.cpp` was UNTESTED in this config | A guarded path that the current build never compiles is an open risk, not a verified surface — flag it explicitly; don't claim coverage you didn't compile |
| Treat the move as byte-for-byte complete from the epic's LOC figure | Implicitly trusted the epic's "3,393 lines" scope estimate as the size of the moved code | Actual counts (1,732 src + 4,349 hdr) did not reconcile to 3,393 — the original estimate and the delivered code differ | An epic's LOC estimate is a forecast, not a manifest; don't assume the move is byte-for-byte complete because a count "roughly matches" — they often don't |

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

### Concrete example (issue #1357 — the NOGO and what resolved it)

After confirming the #1357 work was on disk, the first plan submitted was a retrospective
status note: ~5 bullets describing the landed facade + collaborators, plus the caveats above.
The plan-loop reviewer returned **NOGO, Grade D** — a category error: a status note is not a
plan. It failed Completeness, Concreteness, Verification-Plan, and Stage-Handoff. The reviewer
was explicit: "the fact that the underlying work appears correct on disk does not rehabilitate
the plan artifact itself." The specific stage-handoff trigger was deferring the ADR-0001 boundary
check (`test_import_surface.py` / `test_automation_boundary.py` / `mypy`) to the reviewer as
"highest-value follow-up" instead of running it during planning.

Two-part fix that resolves the NOGO: (1) RUN the deferred gates and cite them as completed;
(2) RESHAPE the artifact into a forward-looking plan (each module as a "files to create/modify"
step with its actual code, a numbered build order, a per-criterion verification command).

Gate outputs observed GREEN this session (these RESOLVE the "not run" caveats above for
mypy/ruff/boundary; the full `tests/unit/automation` suite still had no reported pass/fail count
at write time, so the strongest defensible claim remains "affected ci_driver + 4 collaborator
helper tests pass (211) AND the boundary/mypy/ruff gates are green," not "entire automation
suite is green"):

```text
pixi run pytest tests/unit/validation/test_import_surface.py \
                tests/unit/validation/test_automation_boundary.py --no-cov
  → 2 passed                       # ADR-0001 automation→library boundary intact

pixi run mypy                      # NO arguments — task already targets the whole tree
  → Success: no issues found in 402 source files   # proves type-level DIP

pixi run ruff check hephaestus/automation/
  → All checks passed.

wc -l hephaestus/automation/ci_driver.py
  → 2449                           # ≤ 2450 target; 25 delegation stubs
  # preservation methods present at ci_driver.py:781 / :880 / :943 / :1019
```

What mypy-green does and does NOT prove: it proves the import-graph boundary holds and DIP at the
type level (no collaborator secretly takes `self`/`CIDriver`), upgrading step 7's call-site
inference to proof. It does NOT prove each collaborator is behaviorally SRP (single reason to
change) — that remains asserted from the responsibility table, not demonstrated.

### Concrete example (issue #1357 — the SECOND NOGO: an empty placeholder artifact, Grade F)

After the status-note plan was reshaped (step 9) and the deferred gates were run (step 10), the
plan-loop reviewer returned a SECOND NOGO — this time **Grade F**, because the submitted plan
artifact was an EMPTY PLACEHOLDER: the literal text

```text
Output not yet flushed. I'll wait for the monitor notification rather than polling.
```

Root cause: the planner had launched a long-running background verification (a `Monitor` /
background `pytest tests/unit/automation` run to get a full-suite pass count) and PAUSED, deferring
its turn — so when the plan was DUE the artifact contained zero plan content. The reviewer noted
this is STRICTLY WORSE than the prior status-note NOGO: an empty/placeholder artifact fails every
rubric dimension (Requirements / Completeness / Concreteness / Risk / Verification / Stage-Handoff
all F) and addresses none of the prior findings.

The fix (verified — the very next iteration produced a complete plan): never gate the plan artifact
on an in-flight background job. Emit the COMPLETE forward-looking plan from the evidence already in
hand (line counts, grep'd stubs, already-green gates); if one verification is still running, mark
THAT criterion as "not yet confirmed — open risk, run before completion" inside the Verification
section rather than withholding the whole artifact. A plan that is 95% confirmed + 1 flagged open
risk is gradeable; a placeholder is an automatic F.

Generalizable rule: when a deliverable has a hard turn-boundary (a plan-loop artifact, a review
verdict, any "your output IS the posted artifact" contract), treat already-collected evidence as
sufficient to emit a complete draft. A background task that has not reported by the deadline becomes
a documented open-risk line item, never a reason to emit nothing. Distinguish "transient external
dependency still in progress" (legit to keep working/waiting when you have NO deadline) from "an
artifact is due THIS turn" (must emit now from evidence in hand).

### Concrete example (ProjectAgamemnon extraction epic #1 — already delivered under a different ADR)

The epic asked to EXTRACT the agent layer out of a source repo and into ProjectAgamemnon, with
acceptance criteria phrased as future work ("the types no longer exist in the source repo",
"downstream still builds", "CI passes with the new code"). The epic had been open for months.

Cheap existence checks run THIS session, in order, each disconfirming the "not started" premise:

```bash
find <agamemnon>/src -name '*.cpp'        # the moved agent .cpp files are ALREADY in the destination
ls <source-repo>/src/agents               # → "No such file or directory" — the dir moved OUT
grep -rl "<MovedAgentSymbol>" <source-repo>/src   # → no hits in compiled code (only .ifdef/comment residuals)
```

Then the strongest criterion ("CI passes with the new code") was confirmed by actually building
and running the suite, not assumed:

```text
cmake --build --preset debug
ctest --preset debug -L agents        # green
ctest --preset debug -L integration   # green
# → 586 / 589 tests pass; agents + integration labels 100% green
```

Conclusion: the extraction was COMPLETE; the correct plan was **verification-and-closeout**, not
re-implementation. The lesson is the discipline of catching that BEFORE planning the move.

Caveats recorded honestly (why this finding is `verified-local` and NOT `verified-ci`, and the
exact assumptions a reviewer should re-check — the investigation procedure WAS run locally this
session, but the downstream plan was NOT executed end-to-end in CI):

- **Cross-repo "Keystone CI still passes" was inferred from a local `cmake` build in the sibling
  `../ProjectKeystone` working tree, NOT from Keystone's actual CI/main** — the local clone could
  be stale or dirty; treat this as inferred, not observed.
- **The "delivered under ADR-015 / Odysseus#143" attribution came from `CMakeLists.txt` comments,
  not from reading the ADR doc itself** — provenance rests on an in-repo comment.
- **The 3 failing tests (of 589) were dismissed as out-of-scope WIP from another branch** based
  only on `git status` showing the file as untracked (`??`); if that file is actually within the
  epic's intended scope, dismissing it is wrong.
- **The gRPC/coordinator path is behind `#ifdef ENABLE_GRPC` and never compiles in this preset** —
  `chief_architect_agent.cpp`'s coordinator-submission branch is UNTESTED here, so "extraction
  complete" covers only the non-gRPC surface.
- **Line counts do not reconcile to the epic's 3,393-line figure** (found 1,732 src + 4,349 hdr) —
  the original scope estimate and the actual moved code differ; do not treat the move as
  byte-for-byte complete.

### Decision tree for planners

```
Before writing any implementation plan:
│
├─ Is this a large EXTRACTION / MIGRATION / "move X from repo A to repo B" epic filed weeks/months ago?
│   └─ YES → run cheap existence checks FIRST (each instantly disconfirms "not started"):
│           find <target>/src -name '*.cpp'      (moved code already in destination?)
│           ls <source>/src/<moved-dir>           (expect ABSENT if moved out)
│           grep -rl <MovedSymbol> <source>/src   (expect NO compiled hits)
│       ├─ ALREADY MOVED → map each acceptance criterion to a command; build+run the suite
│       │   (cmake --build --preset debug; ctest --preset debug -L <label>); if green →
│       │   plan = VERIFICATION-AND-CLOSEOUT, not re-implementation. Triage residuals:
│       │   compiled-code hit = real; #ifdef-guarded / Doxygen @code hit = harmless (don't over-scope).
│       │   Flag #ifdef-guarded paths as UNTESTED-in-this-config open risk.
│       └─ NOT moved → proceed with normal extraction planning
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
│   │   └─ implementation present + tests pass → it's ALREADY DONE
│   │       └─ STILL write a FORWARD-LOOKING plan (NOT a status note):
│   │           design + files-to-modify-with-code + numbered build order
│   │           + per-criterion verification command, and RUN every gate
│   │           yourself (boundary/mypy/ruff) rather than deferring to the
│   │           reviewer — a status note or a deferred gate = NOGO (Grade D)
│   └─ NOT FOUND → proceed with implementation planning
│
└─ 4. Run tests + gates for the relevant module
    ├─ SUBSET green → verified-local only (coverage gate fails on subsets — a gate artifact;
    │                 run subsets with --no-cov; run `pixi run mypy` bare, no paths)
    ├─ FULL suite + mypy + ruff + boundary green → verified-ci, safe to report done
    └─ SOME FAIL → issue is genuinely open; proceed with planning

When the artifact is DUE this turn (plan-loop / review verdict):
│
└─ Is a background job (pytest / Monitor / external) still running?
    ├─ NO deadline this turn → fine to keep working/waiting
    └─ ARTIFACT DUE THIS TURN → EMIT NOW from evidence in hand; mark the still-running
        gate as an open-risk line in Verification. NEVER withhold the artifact / submit a
        placeholder ("Output not yet flushed…") — that is an automatic Grade F, worse than
        a status note.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1291 — YAML sequence support in CI matrix extractor | PR #1308 merged 2026-06-13, commit dd15c35f (verified-ci) |
| ProjectHephaestus | Issue #1357 — CIDriver god-class decomposition already landed in an uncommitted `1-fix` worktree | `ci_driver.py` measured 2,449 lines (≤ target), all 4 collaborator modules present, 211 subset tests green; full gate not run (verified-local) |
| ProjectHephaestus | Issue #1357 — plan-loop NOGO (Grade D) on a retrospective "status note" for the landed work | Reshaped into a forward plan + ran the deferred gates: boundary tests 2 passed, `pixi run mypy` clean (402 files), ruff clean, 25 delegation stubs; full automation suite count unconfirmed (verified-local) |
| ProjectHephaestus | Issue #1357 — SECOND plan-loop NOGO (Grade F) on an EMPTY placeholder artifact (output withheld while a background `pytest`/Monitor ran) | Fix verified: emit the complete plan from evidence in hand and flag the still-running gate as an open risk — the very next iteration got a complete, gradeable plan (verified-local) |
| ProjectAgamemnon | Epic #1 — "extract the agent layer into Agamemnon" was already delivered under a different ADR/PR | Existence checks (`find <agamemnon>/src`, `ls <source>/src/agents` absent, `grep -rl <MovedSymbol>`) + `cmake --build --preset debug` + `ctest --preset debug -L agents -L integration` confirmed the move complete: 586/589 tests pass, agents+integration labels 100% green → plan = verification-and-closeout (verified-local; investigation run this session, downstream plan NOT executed in CI; cross-repo Keystone build, ADR-015 attribution, the 3 failing tests, the `#ifdef ENABLE_GRPC` path, and the 3,393-line figure all remain inferred/unreconciled) |
