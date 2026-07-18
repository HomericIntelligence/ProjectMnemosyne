---
name: planning-state-dir-centralization-risk-audit
description: "Review checklist for plans that centralize a duplicated state/work directory path behind one constant and one mkdir helper. Use when: (1) replacing repeated `repo_root / \"build\" / \".issue_implementer\"` constructions, (2) adding a shared `ensure_*_dir()` helper with side effects, (3) a plan relies on rg-discovered call sites and test patch seams, (4) acceptance depends on a grep proving only one magic-string source remains."
category: architecture
date: 2026-06-27
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - state-directory
  - path-centralization
  - shared-helper
  - mkdir-side-effect
  - magic-string
  - call-site-sweep
  - patch-seams
  - projecthephaestus
---

# Planning: State-Directory Centralization Risk Audit

## Overview

| Field | Value |
| --- | --- |
| **Date** | 2026-06-27 |
| **Objective** | Capture the reviewer-facing risks in an unexecuted implementation plan to centralize ProjectHephaestus automation state-dir construction behind `DEFAULT_STATE_DIR = "build/.issue_implementer"` and `ensure_state_dir(repo_root: Path, subdir: str = DEFAULT_STATE_DIR) -> Path`. |
| **Outcome** | Planning learning only. The plan is coherent, but several claims depend on current source state, issue-body interpretation, import graph behavior, and grep/test coverage that were not verified end-to-end during this learn capture. |
| **Verification** | unverified — the underlying implementation plan was not run here; no ProjectHephaestus tests, grep acceptance check, or CI results were observed in this workflow. |

## When to Use

- Reviewing or authoring a plan that replaces repeated state/work directory construction with a module constant plus a shared helper.
- The helper creates directories (`mkdir(parents=True, exist_ok=True)`) and the plan assumes every existing call site should keep that side effect.
- The change fans out across constructors, CLI entrypoints, reviewers, planners, and CI drivers.
- Tests patch local `get_repo_root()` functions, and the plan must preserve those patch seams by calling each module's local root resolver before passing the result into the shared helper.
- The acceptance criterion is a grep proving a magic string appears in only one production location.
- The plan cites issue-body intent, source line numbers, or existing test coverage without showing fresh command output.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
> Verification level: `unverified`. The literal `## Verified Workflow` section below exists because
> `scripts/validate_plugins.py` expects it; read the steps as a proposed review checklist.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Re-derive the production call-site list before implementing.
rg -n 'build/\.issue_implementer|/[[:space:]]*["'\'']build["'\''][[:space:]]*/[[:space:]]*["'\'']\.issue_implementer["'\'']' \
  hephaestus/automation -g '*.py'

# Re-read the proposed helper home and import graph before adding imports.
rg -n 'from \._review_utils|from \.models|DEFAULT_WORKER_COUNT|get_repo_root' \
  hephaestus/automation

# After migration, prove the magic path is centralized in the production constant only.
bash -lc 'rg -n "build/\\.issue_implementer|/[[:space:]]*[\"'"'"']build[\"'"'"'][[:space:]]*/[[:space:]]*[\"'"'"']\\.issue_implementer[\"'"'"']" hephaestus/automation -g "*.py" | tee /tmp/heph-state-dir-hits.txt && test "$(wc -l < /tmp/heph-state-dir-hits.txt)" -eq 1 && rg -q "hephaestus/automation/models.py:" /tmp/heph-state-dir-hits.txt'
```

### Detailed Steps

1. **Verify the issue premise and scope before treating the issue body as authoritative.**
   The plan deliberately treats the body as the actionable requirement because the title mentions
   `_build_parser`, while current code supposedly already has `build_automation_parser` and parser
   wrapper coverage. Before implementing, fetch or open the issue and confirm that this interpretation
   is still correct. A title/body mismatch is a scope risk, not a fact to silently resolve.

2. **Re-run the call-site sweep immediately before editing.**
   The plan names six production construction sites: `_reviewer_base.py:82`, `implementer.py:153`,
   `implementer.py:836`, `ci_driver.py:142`, `audit_reviewer.py:206`, and
   `planner_review_loop.py:623`. Treat these as a stale snapshot. Re-run `rg`, then classify each hit:
   production construction, test fixture, docs, or unrelated string. If a new production hit appears,
   it must migrate in the same change or the centralization is incomplete.

3. **Check the helper home's import graph before adding the shared import.**
   Putting `DEFAULT_STATE_DIR` in `models.py` and `ensure_state_dir()` in `_review_utils.py` is plausible
   because `_review_utils.py` already imports automation defaults from `models.py`, but importing
   `_review_utils.ensure_state_dir` from many automation modules can expose hidden cycles. Prove the
   import graph by running the focused imports/tests, not by reading one file.

4. **Preserve local root-resolution patch seams exactly.**
   The plan's most important compatibility detail is: each migrated module still calls its local
   `get_repo_root()` first, then passes that value to `ensure_state_dir(...)`. Do not replace those
   calls with a central `get_repo_root()` hidden inside the helper. Tests may patch
   `implementer.get_repo_root`, `ci_driver.get_repo_root`, or another local binding; moving the lookup
   would silently bypass those patches.

5. **Audit the mkdir side effect per call site.**
   `ensure_state_dir()` creates the directory. For call sites that already did `.mkdir(...)`, this is
   behavior-preserving. For any call site that only computed the path before, it is a behavior change:
   importing or constructing an object may now create `build/.issue_implementer`. Verify creation timing
   and working-tree cleanliness expectations before approving.

6. **Make the grep acceptance check match the intended population.**
   The supplied grep scopes only `hephaestus/automation -g "*.py"`. That is a production centralization
   check, not a repo-wide guarantee. If tests, docs, or scripts should also stop spelling the magic path,
   add separate scoped checks. If the intended invariant is production-only, say so in the plan and PR.

7. **Run behavior tests for each migrated call-site family, not just the helper unit test.**
   The new `test_review_utils.py -k ensure_state_dir` only proves helper behavior. It does not prove
   constructors, CLI setup logging, audit reviewer defaults, or planner-learn state persist behavior
   are unchanged. Keep the broader focused test suite in the plan and add any missing test that covers
   a changed creation-timing seam.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Treat the plan's `rg` output as exhaustive | Use the listed six files as the migration population without re-running the search | The list is a point-in-time snapshot; another branch or earlier edit can add a direct `build/.issue_implementer` construction before implementation starts | Re-run the grep immediately before editing and after editing; classify every hit |
| Hide root discovery inside the shared helper | Simplify to `ensure_state_dir()` with no `repo_root` argument, or call a single central `get_repo_root()` inside it | Breaks tests and callers that patch each module's local `get_repo_root()` binding; the helper would look up a different symbol than the caller expects | Keep the helper as `ensure_state_dir(repo_root: Path, subdir: str = DEFAULT_STATE_DIR)` and pass the locally resolved root |
| Assume `mkdir` is always behavior-preserving | Replace every path expression with a helper that creates the directory | Safe only where the old code already created the directory. A pure path calculation site would gain a filesystem side effect | For each call site, check whether it already did `.mkdir(parents=True, exist_ok=True)` before migration |
| Trust static import reasoning | Add `from ._review_utils import ensure_state_dir` to multiple automation modules because the module "already hosts shared helpers" | `_review_utils` is widely imported; adding a new dependency can expose circular imports only when import-time code executes | Run targeted import/constructor tests and lint after adding the import |
| Treat a one-line grep count as full verification | Prove only one production hit remains, then assume the refactor is complete | The grep may exclude tests/docs/scripts by design, and regex quoting mistakes can miss split-string constructions | State the population the grep covers and add separate checks for any other population that matters |

## Results & Parameters

### Concrete Plan Facts to Preserve

| Item | Value |
| --- | --- |
| Canonical constant | `DEFAULT_STATE_DIR = "build/.issue_implementer"` |
| Proposed helper | `ensure_state_dir(repo_root: Path, subdir: str = DEFAULT_STATE_DIR) -> Path` |
| Helper behavior | `repo_root / subdir`, then `state_dir.mkdir(parents=True, exist_ok=True)`, then return `state_dir` |
| Intended helper home | `hephaestus/automation/_review_utils.py` |
| Intended constant home | `hephaestus/automation/models.py` beside `DEFAULT_WORKER_COUNT` |
| Patch-seam rule | Each module calls its own local `get_repo_root()` first, then passes that path into `ensure_state_dir(...)` |

### Most Uncertain Assumptions Reviewers Should Check

1. **Issue-body interpretation.** The plan says the title's `_build_parser` hint is stale and the body is the true requirement. Verify this against the current issue, not just the plan text.
2. **Current call-site inventory.** The six named files and line numbers may drift. Re-run `rg` before implementation and review the final diff against the fresh list.
3. **Import-cycle safety.** `_review_utils` is a shared module; importing it from additional automation modules must be proven by import/tests.
4. **Side-effect preservation.** Directory creation must occur at the same points as before; the helper should not create the state dir earlier than callers used to.
5. **Patch seam preservation.** Local `get_repo_root()` patch targets must remain load-bearing. This is easy to break with an over-convenient helper.
6. **Grep acceptance scope.** The provided magic-string grep proves only a production-path invariant under `hephaestus/automation/*.py`; it is not a full-repo invariant unless expanded.

### External Sources / Files Relied On Without Direct Verification Here

- The GitHub issue body/title mismatch (`_build_parser` vs `build_automation_parser`) was taken from the implementation plan, not re-fetched with `gh issue view`.
- The current parser wrapper coverage claim (`tests/unit/automation/test_automation_parsers.py:682`) was taken from the plan, not re-run.
- The call-site line numbers were copied from the plan. They must be treated as stale until re-grepped.
- The proposed verification commands (`pixi run pytest ...`, `pixi run ruff check ...`) were not executed during this learn capture.

### Reviewer Focus Checklist

```text
- [ ] Did the implementer re-run the direct-construction grep before editing?
- [ ] Does every fresh production hit migrate, with no new duplicates?
- [ ] Does each migrated module still call its local get_repo_root() binding?
- [ ] Did the helper add a mkdir side effect only where one already existed?
- [ ] Do import smoke tests/focused suites prove no _review_utils cycle was introduced?
- [ ] Does the final grep check state whether it is production-only or repo-wide?
- [ ] Were focused behavior tests run for implementer, ci_driver, audit_reviewer, and planner paths?
```

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectHephaestus | Planning capture for automation state-dir centralization | Planning-only; unverified. The implementation plan was not executed in this workflow, and no ProjectHephaestus tests or CI were run. |
