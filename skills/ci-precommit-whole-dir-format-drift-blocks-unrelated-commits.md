---
name: ci-precommit-whole-dir-format-drift-blocks-unrelated-commits
description: "Pre-commit hooks configured with `pass_filenames: false` re-run over WHOLE DIRECTORIES (the entire tree, not just staged files) on every commit, so a pre-existing violation already committed on `origin/main` aborts EVERY new commit — even ones touching completely unrelated files — with 'files were modified by this hook' (`ruff format` drift), a hook failure on an untouched file (`ruff check` lint, e.g. `SIM102`), OR a tree-wide TYPE error (`pixi run mypy` whole-tree hook, after a mypy version bump newly flagging pre-existing code, OR after a just-merged PR leaves missing annotations like `[var-annotated]` that 'lint skipped on auto-merge' let reach main). The same whole-tree hook drives the required `lint`/Required Checks job, so a single error makes main's CI RED and blocks every commit/PR locally and in CI. Use when: (1) you stage only your own clean files but `git commit -S` / `pre-commit run` reformats, lint-fails, or type-errors on a DIFFERENT set of files you never touched (empty `git diff` vs origin/main), then aborts; (2) reverting/ignoring it makes it reappear on the next commit because the violation lives in main's committed tree; (3) `ruff format --check hephaestus/ scripts/ tests/` reports `Would reformat:`, `ruff check hephaestus/ scripts/ tests/` reports a lint error (e.g. `SIM102` nested-if), OR `pixi run mypy` reports a type error (e.g. `Need type annotation for X [var-annotated]`) for files unrelated to your change; (4) deciding whether to fix broken main IN your feature PR (fold) or via a separate standalone unblock PR first. Fix: land a separate one-file `chore(lint)` / `fix(lint)` PR first (or fold the unblock into your PR when that is the only way your commit can pass the gate), then stack your feature branches on it. Note `ruff check --fix` may NOT auto-resolve the lint (e.g. SIM102 under an elif chain is a manual hand-edit); version-bump mypy fixes mean the EXACT ignore code (`# type: ignore[method-assign]`, not blanket or `[attr-defined]`) and importing names from their canonical module under `implicit_reexport=false`; `[var-annotated]` fixes mean explicit annotations matching the target function signatures (`results: dict[str, Any] = {...}`, `improvements: list[dict[str, Any]] = []`). Do NOT pass a file arg to the bare `pixi run mypy` task (→ 'Duplicate module' error); beware a 'pass' `lint` check that was actually SKIPPED by a changes-gate on an auto-merge event; and a pytest path that no longer exists after a test reorg collects nothing and EXITS 0 (silent no-op) — confirm the 'N passed' line."
category: ci-cd
date: 2026-06-22
version: "1.3.0"
user-invocable: false
verification: verified-local
history: ci-precommit-whole-dir-format-drift-blocks-unrelated-commits.history
tags: []
---

# Pre-commit Whole-Directory Hook Blocks Unrelated Commits (Format Drift OR Lint Violation on Main)

## Overview

This skill is about **repo-wide / whole-dir pre-commit hooks configured with
`pass_filenames: false`**: they re-run over the ENTIRE tree on every commit, so a
**pre-existing violation already committed on `origin/main` blocks unrelated
commits on every branch**. Three variants (with two distinct mypy findings) share
this exact signature:

- **`ruff format` drift** — the hook reformats untouched files and aborts with
  "files were modified by this hook" (the original v1.0.0 case).
- **`ruff check` lint violation** (e.g. `SIM102`) — the hook *fails* on an
  untouched file with a lint error; `--fix` may NOT auto-resolve it, so you must
  hand-edit (the v1.1.0 case).
- **`pixi run mypy` whole-tree TYPE error** — the `mypy-check-python` hook runs
  `entry: pixi run mypy` with `pass_filenames: false` and
  `files: ^(hephaestus|scripts|tests)/.*\.py$`, so it type-checks the entire tree
  on every commit. CI's required `lint` job runs the SAME hook, so local == CI.
  Two findings:
  - **version-bump finding (v1.2.0):** a mypy **version bump** (here 2.1.0) newly
    flagged pre-existing code (`[method-assign]` / re-export errors).
  - **just-merged-PR finding (v1.3.0):** a freshly-merged PR (#1566, a test-suite
    reorg) left missing annotations (`Need type annotation for "X"
    [var-annotated]`) that "lint skipped on auto-merge" let reach main; the NEXT
    author's unrelated commit surfaces all of them.

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-22 |
| **Objective** | Unblock feature PRs in ProjectHephaestus whose commits kept aborting because a whole-dir (`pass_filenames: false`) pre-commit hook re-hit a pre-existing violation already committed on `origin/main` — `ruff format` drift (v1.0.0), a `ruff check` `SIM102` lint (v1.1.0), a tree-wide `pixi run mypy` type error after a mypy 2.1.0 bump (v1.2.0), or 10 `[var-annotated]` errors a just-merged PR #1566 left in `tests/unit/benchmarks/test_compare.py` (v1.3.0) |
| **Outcome** | Successful — a separate one-file lint/format/type PR re-greened main first (or, in v1.3.0, the unblock was FOLDED into the carrying PR), then dependent work landed clean. v1.0.0: `chore(lint)` PR #1325 unblocked a 6-PR stack. v1.1.0: `fix(lint)` PR #1352 (issue #1351) re-greened main and the 4 dependents #1353–#1356 all merged green. v1.2.0: `[Fix]` PR #1530 (issue #1529) repaired two mypy 2.1.0 errors, then #1531/#1533/#1535/#1537 stacked on it all merged green. v1.3.0: the `[var-annotated]` fix was folded into the unrelated automation PR #1568 (the only way that PR's own commit could pass the whole-tree hook) — `pixi run mypy` → `Success: no issues found in 411 source files` |
| **Verification** | verified-ci for v1.0.0–v1.2.0 (the `SIM102` fix PR #1352 and dependents #1353–#1356, the mypy fix PR #1530 and dependents #1531/#1533/#1535/#1537 all merged green; original v1.0.0 format-drift case was verified-local). The v1.3.0 `[var-annotated]` finding is verified-LOCAL only — `pixi run mypy` passed locally (411 files) and the commit's pre-commit mypy hook passed, but the carrying PR #1568's full CI was still pending at capture time |

## When to Use

- You stage ONLY your own clean files, run `git commit -S` (or `pre-commit run`), and the hook reformats a **different** set of files you never touched, then aborts the commit with "files were modified by this hook".
- `ruff format --check hephaestus/ scripts/ tests/` against the committed `origin/main` content reports `Would reformat: <files>` for files **unrelated** to your change.
- Reverting those reformats with `git checkout --` / `git stash` just makes them reappear on the next commit attempt — because the drift lives in the committed tree on `main`, not in your working changes.
- The pre-commit config runs the formatter/linter over whole directory arguments (e.g. `ruff format hephaestus/ scripts/ tests/`) rather than only the staged files passed by pre-commit — i.e. the hook uses `pass_filenames: false`, so it lints/formats the ENTIRE tree on every commit regardless of what is staged.
- **Lint-check variant (not just format):** the `ruff-check-python` hook runs `ruff check --fix hephaestus/ scripts/ tests/` with `pass_filenames: false`, so a pre-existing **lint** violation on main (e.g. `SIM102` "Use a single if statement instead of nested if statements") aborts every signed commit on every feature branch — your `git diff` vs origin/main is empty, yet the hook fails on a file you never touched. KEY: `ruff check --fix` may **NOT** auto-resolve it (e.g. `SIM102` for a nested `if` under an `elif` chain is a manual/unsafe fix), so re-running the formatter does nothing — you must hand-edit (combine the nested `if` into the `elif` with `and`).
- **Type-check variant (mypy — v1.2.0):** the `mypy-check-python` hook runs `entry: pixi run mypy` with `pass_filenames: false` and `files: ^(hephaestus|scripts|tests)/.*\.py$`, so it type-checks the ENTIRE `hephaestus/ scripts/ tests/` tree on every commit. A **mypy version bump** (here 2.1.0) can newly flag pre-existing code, so a single tree-wide type error aborts EVERY commit and EVERY PR — including ones that don't touch the offending files — and makes main's required `lint`/Required Checks RED. The required `lint` CI job runs the SAME pre-commit hook, so local == CI. Detect it on a clean main with the bare task: `pixi run mypy`. Two real triggers under `warn_unused_ignores=true` / `implicit_reexport=false` in `pyproject.toml`:
  - A `mock.MagicMock()` assigned to a method carried `# type: ignore[attr-defined]`, but mypy 2.1.0 emits `[method-assign]` there → each line errors TWICE (Unused "type: ignore" + an unsuppressed method-assign). Fix: change the code to `# type: ignore[method-assign]` (NOT a blanket `# type: ignore`, NOT `[attr-defined]`).
  - A test referenced `pr_manager.AGENT_COMMIT_MESSAGE` / `pr_manager.AGENT_PR_MESSAGE`, which `pr_manager` only IMPORTS (does not re-export); under `implicit_reexport=false` mypy rejects that. Fix: import the constants from their canonical home (`session_naming`) instead.
- **`[var-annotated]` from a just-merged PR (v1.3.0):** `pixi run mypy` reports `Need type annotation for "X" [var-annotated]` errors ALL in a file your branch never touched (here 10 errors in `tests/unit/benchmarks/test_compare.py`). Root cause is a just-merged PR (#1566, a test-suite reorg) that left dict/list literals unannotated (`results = {"benchmarks": []}`, `improvements = []`) — and because **lint is SKIPPED on auto-merge events in this repo**, the breakage reached main and the NEXT author's unrelated commit surfaces it. FIRST confirm the errors pre-exist on origin/main (`git show origin/main:<file>` / `git diff --name-only main...HEAD` shows you never touched it) — do NOT assume your change caused them. Fix: add explicit annotations matching the target function signatures in `hephaestus/benchmarks/compare.py` (`results: dict[str, Any] = {...}`, `improvements: list[dict[str, Any]] = []`, `regressions: list[Regression] = []`, plus `from typing import Any`). Deciding whether to fix broken main IN your feature PR (fold) vs a separate standalone unblock PR is itself a When-to-Use trigger.

Use this specific skill when **main already has format drift OR a lint violation** and a whole-dir hook is therefore blocking unrelated commits. This is a DIFFERENT root cause from `ci-ruff-format-collapses-handwrapped-comprehensions` (where YOUR OWN clause-deletion edit collapses a comprehension you just touched) — see also that skill and `pre-commit-hooks-and-linting-config`. If the reformatted files are the ones you edited, you are in the wrong skill; the signature here is that the reformatted files are unrelated to your change and already drifted on main.

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm the diagnosis cheaply — does main itself carry drift?
#    (use the repo's pinned ruff so the version matches CI)
/path/to/.pixi/envs/default/bin/ruff format --check hephaestus/ scripts/ tests/
# -> lists drifted files. If they are UNRELATED to your change AND on main,
#    a separate format-fix PR is the clean unblock.

# 2. Create the format-only chore branch off main and fix the WHOLE tree:
git checkout -b chore/lint-format-drift origin/main
ruff format hephaestus/ scripts/ tests/
ruff check --fix hephaestus/ scripts/ tests/

# 3. Verify behavior-preserving (run the affected modules' tests):
pixi run pytest tests/unit/automation -q   # 199 passed, unchanged

# 4. Commit EXACTLY the drift-fix diff (no logic change), signed:
git add -A && git commit -S -m "chore(lint): clear ruff-format drift on main"
pre-commit run --all-files   # now passes clean

# 5. Stack feature branches on the chore branch so they commit cleanly:
git checkout -b 1234-my-feature chore/lint-format-drift
# ...work + commit; once the chore PR merges, GitHub auto-retargets stacked PRs to main.
```

### Detailed Steps

1. **Recognize the signature.** You commit clean, unrelated files and the hook reformats a *different* file set, then aborts. This is not your edit's fault — the drift is in main's committed tree.

2. **Confirm the diagnosis cheaply.** Run `ruff format --check hephaestus/ scripts/ tests/` (with the repo's pinned ruff) against the committed `origin/main` content. If it lists files unrelated to your change, main itself carries drift. This happens when those files were committed before a ruff version/range resolved differently, or merged via a PR whose own gate passed under a slightly different ruff.

3. **Land a SEPARATE one-file fix PR first (the core pattern — applies to format, lint, AND mypy).** Branch off main, fix exactly the offending file(s) — `ruff format` + `ruff check --fix` for drift/lint, or the precise mypy edit for a type error (correct `# type: ignore[<code>]`, or import re-exported names from their canonical module under `implicit_reexport=false`) — and commit only that diff, no logic change. Verify behavior-preserving by running the affected modules' tests (format case: 199 automation tests passed unchanged; mypy case: `pixi run mypy` → `Success: no issues found in N source files`). This is the prereq PR (`chore(lint)` #1325, `fix(lint)` #1352, or `[Fix]` mypy #1530 in ProjectHephaestus) that re-greens main FIRST; then stack the feature PRs on it.

4. **Stack your feature branches on the chore branch.** Base each feature branch on the chore branch so its commits land cleanly (the hook finds nothing to reformat). Once the chore PR merges to main, GitHub auto-retargets the stacked PRs to main.

5. **Never bypass.** Do not `--no-verify`, do not scope the hook to staged-only as a workaround, and do not silently bundle the unrelated reformats into your feature commit — that pollutes the PR. Fix the drift on main in its own PR.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Revert the unrelated reformats each commit attempt | `git checkout --` / `git stash` the files the hook reformatted, then re-run `git commit -S` | The reformats reappear on the next commit attempt because the drift lives in main's committed tree, not in your working changes — it is whack-a-mole | Stop reverting; land a separate format-fix PR that fixes the drift on main once |
| Scope the hook to staged-only / bypass it | Tried to limit the hook to staged files, or considered `--no-verify` to skip the reformat | Bypassing hooks is banned in this org, and it does not address the root cause — main is still drifted, so the next contributor hits the same wall | Fix the drift on main, don't hide it; never use `--no-verify` or any hook bypass |
| Bundle the unrelated reformats into the feature commit | Let the hook reformat the drifted files and committed them alongside the feature change | Pollutes the PR with unrelated whole-tree formatting noise, obscuring the actual feature diff in review | Keep format-only changes in their own `chore(lint)` PR; stack the feature on it |
| Re-run `ruff format` to clear the `SIM102` failure | Ran `ruff format hephaestus/ scripts/ tests/` expecting it to fix the blocking error | `SIM102` is a `ruff check` **lint** rule, not a format issue — the formatter never touches it; the failure persisted | A `ruff check` lint and a `ruff format` drift are different hooks; diagnose which one is failing before reaching for the formatter |
| Revert / ignore the unrelated lint-flagged file | Tried reverting the file the hook flagged, or considered skipping the hook for it | The `SIM102` is committed on `origin/main` (via PR #1346); every branch's whole-tree `ruff check --fix` re-hits it, and `--no-verify` is banned | Hand-fix the lint on main in a one-file `fix(lint)` PR, merge first; `ruff check --fix` won't auto-resolve `SIM102` (combine nested `if` into the `elif` with `and`) |
| Silence the mypy error with a blanket `# type: ignore` or the wrong code `[attr-defined]` | Added a broad `# type: ignore` (or kept `[attr-defined]`) on the `mock.MagicMock()` method assignment | Under `warn_unused_ignores=true`, mypy 2.1.0 emits the *new* `[method-assign]` error there, so a blanket/`[attr-defined]` ignore is both unused (Unused "type: ignore") AND fails to suppress the real error — the line double-errors | Use the EXACT narrow code mypy reports: `# type: ignore[method-assign]`. Never blanket-ignore under `warn_unused_ignores` |
| Pass a file arg to `pixi run mypy` | Ran `pixi run mypy path/to/file.py` to check one file | The `mypy` task already includes its own paths; adding a file arg makes mypy see the same module twice → `Duplicate module named "..."` error | Run the BARE task `pixi run mypy` — it already type-checks the configured tree; never append a path |
| Trust a "pass" `lint` check on an auto-merge event | Saw the `lint` check green after arming/disarming auto-merge and assumed the type errors were fixed | The `lint` job is behind a `changes-gate`: it is SKIPPED on `labeled`/`auto_merge_enabled`/`auto_merge_disabled` events (only runs on push/synchronize/opened). A *skipped* `lint` counts as PASS at the `required-checks-gate`, so the "pass" was vacuous | Get a genuine `lint` run from a real code event (push a commit, or rely on the opened/synchronize run) before trusting it — a skip is not a pass |
| Assume your branch introduced the `[var-annotated]` errors | Saw 10 `Need type annotation [var-annotated]` errors and started inspecting/blaming your own diff | All 10 were in `tests/unit/benchmarks/test_compare.py`, a file the branch never touched — a just-merged PR (#1566) left them, and "lint skipped on auto-merge" let them reach main | FIRST confirm errors pre-exist on origin/main (`git show origin/main:<file>`, `git diff --name-only main...HEAD`) before assuming your change caused them; a whole-tree hook surfaces other people's debt on YOUR commit |
| Run a targeted pytest path after a test reorg and trust exit 0 | Ran pytest against `tests/unit/test_import_surface.py` / `test_automation_boundary.py` (their pre-reorg paths) and saw exit 0 | PR #1566 MOVED those files under `tests/unit/validation/`; a now-nonexistent pytest path collects ZERO tests and EXITS 0 — a silent no-op that looks like success | After a reorg, confirm a targeted pytest path actually matched tests — look for the "N passed" line, not just exit code 0 |

## Results & Parameters

**Context:** ProjectHephaestus. The pre-commit hooks run `ruff format hephaestus/ scripts/ tests/` and `ruff check --fix hephaestus/ scripts/ tests/` over WHOLE DIRECTORIES, not just staged files. When `origin/main` itself carries ruff-format drift, every new commit — even one touching completely unrelated files — triggers the hook to reformat the drifted files, reports "files were modified by this hook", and aborts.

**Diagnostic signature:**

- Stage only your own clean files, run `git commit -S` / `pre-commit run` → the hook reformats a *different* set of files you never touched, then aborts.
- `ruff format --check hephaestus/ scripts/ tests/` against committed `origin/main` reports `Would reformat: <files>` for files unrelated to your change.
- Reverting the reformats (`git checkout --` / `git stash`) makes them reappear next commit, because the drift is in main's committed tree.

**The fix (verified this session):**

```bash
# Confirm the drift on main (repo's pinned ruff so the version matches CI):
/path/to/.pixi/envs/default/bin/ruff format --check hephaestus/ scripts/ tests/

# Land a separate format-only chore(lint) PR FIRST:
git checkout -b chore/lint-format-drift origin/main
ruff format hephaestus/ scripts/ tests/
ruff check --fix hephaestus/ scripts/ tests/
pixi run pytest tests/unit/automation -q   # 199 passed, behavior-preserving
git add -A && git commit -S -m "chore(lint): clear ruff-format drift on main"

# Then stack feature branches on the chore branch.
```

**Outcome:** The format-only PR (#1325) committed exactly the drift-fix diff with zero logic change (199 automation tests passed unchanged). It unblocked a stack of 6 fix PRs — each feature branch was based on the chore branch and committed cleanly. Once the chore PR merges to main, GitHub auto-retargets the stacked PRs to main.

**Lint-violation variant (v1.1.0 — `ruff check` `SIM102` on main):**

A pre-existing `SIM102` ("Use a single if statement instead of nested if
statements") landed on `origin/main` via PR #1346 (HEAD `580ab43`) in
`tests/unit/automation/test_ci_driver_failing_pr_discovery.py:348`. Because the
`ruff-check-python` hook runs `ruff check --fix hephaestus/ scripts/ tests/`
with `pass_filenames: false`, it lints the whole tree on every commit — so the
unrelated `SIM102` aborted EVERY signed commit on EVERY feature branch. Multiple
parallel fix agents all failed at commit time with the same untouched-file error
(empty `git diff` vs origin/main).

Detect it on a clean main without touching your branch:

```bash
# Either lint the whole tree on a clean main checkout:
ruff check hephaestus/ scripts/ tests/

# Or check just the suspected file straight from origin/main:
git show origin/main:tests/unit/automation/test_ci_driver_failing_pr_discovery.py \
  | ruff check --stdin-filename tests/unit/automation/test_ci_driver_failing_pr_discovery.py -
```

Fix (same shape as the format case, but hand-edited): land a one-file
`fix(lint)` PR that manually combines the nested `if` into the `elif` with `and`
(`ruff check --fix` will NOT auto-resolve `SIM102` under an elif chain), merge it
FIRST to re-green main, then base/stack the dependent fix PRs on it. Here:
`fix(lint)` PR #1352 (issue #1351) re-greened main; the 4 dependent fix PRs
(#1353–#1356) were based on `fix-main-sim102-lint`, GitHub auto-retargeted them
to main on its merge, and they dropped the now-redundant lint commit on rebase.
All 5 PRs merged green through the required-checks gate (verified-ci).

**Type-check variant (v1.2.0 — `pixi run mypy` whole-tree error on main):**

A mypy **2.1.0** version bump newly flagged pre-existing test code on
`origin/main`, so the `mypy-check-python` hook (`entry: pixi run mypy`,
`pass_filenames: false`, `files: ^(hephaestus|scripts|tests)/.*\.py$`) failed
tree-wide on every commit and made main's required `lint`/Required Checks RED —
even for PRs that never touched the offending files. Two concrete errors, both
pre-existing code freshly flagged under `warn_unused_ignores=true` /
`implicit_reexport=false`:

1. `tests/.../test_stage_phases.py`: a `mock.MagicMock()` assigned to a method
   carried `# type: ignore[attr-defined]`, but mypy 2.1.0 emits `[method-assign]`
   there → each line errored TWICE (Unused "type: ignore" + unsuppressed
   method-assign). **Fix:** change the code to `# type: ignore[method-assign]`
   (NOT a blanket `# type: ignore`, NOT `[attr-defined]`).
2. `tests/.../test_pr_manager.py`: referenced
   `pr_manager.AGENT_COMMIT_MESSAGE` / `pr_manager.AGENT_PR_MESSAGE`, which
   `pr_manager` only IMPORTS (does not re-export); under `implicit_reexport=false`
   mypy rejects that. **Fix:** import the constants from their canonical home
   `session_naming` instead.

Detect it on a clean main with the BARE task — do NOT pass a file arg (a file
arg makes the task double-see a module → `Duplicate module named "..."`):

```bash
pixi run mypy            # bare task; do NOT append a path
# After the fix:
# Success: no issues found in N source files
```

Fix shape is identical to the format/lint variants: land a small one-file/prereq
PR FIRST to re-green main, then stack the feature PRs on it. Here: `[Fix] Repair
mypy 2.1.0 errors blocking main lint gate` PR #1530 (issue #1529) merged green
through the required-checks gate, then the dependent fix PRs #1531/#1533/#1535/#1537
all merged green.

**`changes-gate` skipped-lint caveat (v1.2.0):** the CI `lint` job is gated by a
`changes-gate` — it is SKIPPED on `labeled`/`auto_merge_enabled`/`auto_merge_disabled`
events and only runs on real code events (push/synchronize/opened). A *skipped*
`lint` counts as a PASS at the `required-checks-gate`. So after arming/disarming
auto-merge, a `lint` you see "pass" may actually have been SKIPPED — push a real
commit (or rely on the opened/synchronize run) to get a genuine `lint` result
before trusting it.

**`[var-annotated]`-from-just-merged-PR finding (v1.3.0 — `pixi run mypy` whole-tree):**

A SECOND mypy finding under the SAME whole-tree hook, with a different cause than
the v1.2.0 version-bump errors. While implementing an unrelated automation fix,
`pixi run mypy` reported **10 `[var-annotated]` errors ALL in
`tests/unit/benchmarks/test_compare.py`** — a file the current branch never
touched. Root cause: **PR #1566** (a test-suite reorganization) merged to main
with missing type annotations on dict/list literals
(`results = {"benchmarks": []}`, `improvements = []`, etc.) that mypy flags as
`Need type annotation for "X" [var-annotated]`. Because **lint is SKIPPED on
auto-merge events in this repo**, the broken code reached main; the next person's
PR is the one that surfaces it.

Confirm the errors pre-exist on origin/main BEFORE assuming your change caused
them:

```bash
git diff --name-only main...HEAD                 # your branch never touched the file
git show origin/main:tests/unit/benchmarks/test_compare.py  # errors already on main
pixi run mypy                                    # bare task; reproduces the 10 errors
```

Fix: add explicit annotations matching the target function signatures in
`hephaestus/benchmarks/compare.py`
(`format_markdown_report(regressions: list[Regression], improvements: list[dict[str, Any]], current_results: dict[str, Any], baseline_results: dict[str, Any])`):

```python
from typing import Any

results: dict[str, Any] = {...}
improvements: list[dict[str, Any]] = []
regressions: list[Regression] = []
```

Verified by `pixi run mypy` → `Success: no issues found in 411 source files`.

**Fold vs standalone unblock decision:** This session FOLDED the main-unblock fix
INTO the unrelated feature PR (**#1568**) because there was no other way to make
that PR's own commit pass the whole-tree hook — fixing broken main is a
prerequisite for ANY other PR landing. Folding is acceptable when it is the only
way your commit can pass the gate; the alternative is a tiny standalone unblock
PR merged first (the v1.0.0–v1.2.0 pattern). **State which you did and why** in
the PR body so the unrelated diff is explained.

**Pytest silent-no-op on moved paths (related discovery, v1.3.0):** the same
reorg (#1566) MOVED files — `tests/unit/test_import_surface.py` /
`test_automation_boundary.py` are now under `tests/unit/validation/`. Passing a
now-nonexistent test path to pytest collects NOTHING and EXITS 0 (a silent
no-op that looks like success). Always confirm a targeted pytest path matched
tests — look for the "N passed" line, not just exit code 0.

**Cross-link:** this is the same whole-scope-hook-blocks-unrelated-PRs class as
[[ci-markdownlint-all-files-repo-wide-blocks-prs]] (a repo-wide `--all-files`
markdownlint/pre-commit gate failing every PR on one pre-existing malformed file).

**Verified On:**

| Project | Scenario | Result |
| ------- | -------- | ------- |
| ProjectHephaestus | 2026-06-14 `SIM102` broken-main blocked 4-way fan-out | PR #1352 re-greened main, #1353–#1356 merged |
| ProjectHephaestus | 2026-06-19 mypy 2.1.0 tree-wide type error broke main `lint` gate | PR #1530 (issue #1529) re-greened main; `pixi run mypy` → `Success: no issues found in N source files`; dependents #1531/#1533/#1535/#1537 merged |
| ProjectHephaestus | 2026-06-22 10 `[var-annotated]` errors from just-merged PR #1566 (`test_compare.py`) blocked an unrelated commit | Fix FOLDED into carrying PR #1568; `pixi run mypy` → `Success: no issues found in 411 source files` (verified-local; PR #1568 CI pending at capture) |

**Distinction from related skills:** This skill is specifically *"main already has a pre-existing violation (format drift OR a lint error) → a whole-dir (`pass_filenames: false`) hook re-hits it on unrelated commits → blocks every branch → fix via a separate one-file lint/format PR merged first + stack dependents"*. It is NOT `ci-ruff-format-collapses-handwrapped-comprehensions` (clause-deletion collapse of a comprehension YOU just edited — a different root cause). See also `pre-commit-hooks-and-linting-config` for hook configuration background.

**Verification:** mixed — the frontmatter `verification` field reflects the
NEWEST finding (v1.3.0), which is **verified-local**: the `[var-annotated]`
annotation fix made `pixi run mypy` pass locally (`Success: no issues found in
411 source files`) and the carrying commit's pre-commit mypy hook passed, but the
folding PR #1568's full CI was still PENDING at capture time (not verified-ci).
Earlier findings are stronger: the v1.2.0 mypy fix PR #1530 (issue #1529) merged
green through the required-checks gate (`pixi run mypy` → `Success: no issues
found in N source files`) with its 4 dependents (#1531/#1533/#1535/#1537) all
green; the v1.1.0 `SIM102` fix PR #1352 and its 4 dependents (#1353–#1356) all
merged green; the original v1.0.0 format-drift case was verified-local.
