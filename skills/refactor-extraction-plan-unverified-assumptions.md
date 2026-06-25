---
name: refactor-extraction-plan-unverified-assumptions
description: "The uncertain assumptions and reviewer risks baked into a verbatim-move cluster-extraction PLAN that extracts a group of functions from a large module into a new sibling module with backward-compat `import X as X` re-exports in the parent. Use when: (1) reviewing or authoring a plan that moves a function cluster out of a god-module and re-exports the moved names from the original module to preserve mock patch paths, (2) the plan claims `patch(\"...old_module._fn\")` keeps working after the move, (3) the plan cites exact line numbers for a multi-step sequential edit, (4) the plan depends on a 'frozen' allowlist/magic-number invariant, (5) the plan asserts 'no circular import' or 'unused import removable' by static reasoning rather than execution."
category: architecture
date: 2026-06-15
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [refactoring, extraction, cluster-extraction, backward-compat, re-export, mock-patch-path, planning, reviewer-risks, line-number-drift, circular-import, assumptions]
---

# Refactor Extraction Plan — Unverified Assumptions & Reviewer Risks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-15 |
| **Objective** | Capture the uncertain assumptions a verbatim-move cluster-extraction PLAN makes — extracting a 12-function repo-management cluster from `hephaestus/automation/loop_runner.py` into a new `loop_repo_manager.py` with backward-compat `import X as X` re-exports (issue #1360) — so a reviewer knows exactly what to check before approving. |
| **Outcome** | Plan produced; NOT executed. These are the assumptions a reviewer must verify and an implementer must not take on faith. |
| **Verification** | unverified — planning artifact only; no code was written or run |
| **History** | v1.0.0: initial capture of 5 uncertain assumptions + reviewer focus checklist from issue #1360 extraction plan. |

> This skill is about the **PLANNING-RISK** angle, not the mechanics of *how* to extract a cluster.
> For the how-to mechanics see `python-module-decomposition-and-refactor-patterns` and
> `testing-module-patch-target-after-extraction`. For DRY *consolidation* (two modules → one)
> see `dry-refactoring-plan-assumption-audit`. This skill covers a *single module → two modules*
> verbatim move with re-exports, and what silently breaks.

## When to Use

- Reviewing or authoring a plan that extracts a cluster of functions out of a large module into a new sibling module.
- The plan keeps the original module importable by adding `from .new_module import _fn as _fn` re-exports (backward-compat shim) and claims existing `unittest.mock.patch("...old_module._fn")` calls still work.
- The plan cites exact line numbers (`module.py:566-942`, `pyproject.toml:263`) for a sequence of edits that delete/insert large blocks.
- The plan depends on a "frozen" list or magic number (e.g. an omit/coverage allowlist "frozen at N modules") that must be bumped in multiple places.
- The plan asserts "introduces no circular import" or "this import is now unused and can be removed" by static reasoning rather than by actually importing/linting.

## Verified Workflow

<!-- Section title per honest verification level: PROPOSED WORKFLOW (unverified). The
"## Verified Workflow" heading is retained only because scripts/validate_plugins.py requires that
literal token; this content is a PROPOSAL, not a verified procedure. See the warning banner below. -->

### Proposed Workflow (UNVERIFIED — planning artifact only)

> **Warning:** This workflow has not been validated end-to-end. No code was written or run. It is the
> reviewer/author checklist distilled from an *unexecuted* plan. Treat every item as a hypothesis
> until CI confirms.

### Quick Reference

```bash
# === Reviewer / implementer pre-flight for a cluster-extraction-with-re-export plan ===
# Replace OLD_MODULE with the dotted path being extracted FROM (e.g. hephaestus.automation.loop_runner)
# and run from the repo root.

OLD_MODULE="hephaestus.automation.loop_runner"   # the module losing functions
OLD_PATH="hephaestus/automation/loop_runner.py"  # its file
NEW_MODULE="loop_repo_manager"                    # the new sibling (bare name as imported within the pkg)

# 1. CENTRAL CHECK — does ANY module import the moved private names directly (not via the namespace)?
#    Re-exports only preserve patch paths for callers that look up the name through OLD_MODULE
#    at call time. A `from OLD_MODULE import _fn` anywhere ELSE binds a separate name that
#    patching OLD_MODULE._fn will NOT affect. Grep the WHOLE repo, not just OLD_PATH + its test.
grep -rn "from ${OLD_MODULE} import" hephaestus/ tests/ scripts/
#    Inspect every hit: any moved symbol imported by name into another module = a patch path that breaks.

# 2. MAGIC-NUMBER / FROZEN-LIST CHECK — find EVERY occurrence of the invariant count/list literal,
#    then READ the assertion body (is it `len(...) == 16` literal, or set membership?). Don't trust the comment.
grep -rn "16" pyproject.toml | grep -i "omit\|allowlist\|module"   # adjust literal/keyword
grep -rn "allowlist\|omit" tests/ pyproject.toml
#    Open the test and read whether it asserts a count literal vs a set membership before bumping anything.

# 3. NO-CYCLE CHECK — prove by EXECUTION, not by reading comments.
python -c "import ${OLD_MODULE}; from hephaestus.automation import ${NEW_MODULE}; print('import OK')"

# 4. RE-EXPORT IDENTITY SMOKE TEST — prove the shim actually re-binds the moved object.
python -c "import ${OLD_MODULE} as o; from hephaestus.automation import ${NEW_MODULE} as n; \
assert o._gh_list_repos is n._gh_list_repos, 'identity broken'; print('re-export identity OK')"

# 5. UNUSED-IMPORT CHECK — let ruff be the source of truth, do NOT hand-judge.
ruff check ${OLD_PATH} --select F401   # then `ruff check --fix` only after the deletion

# 6. LINE-NUMBER DRIFT REMINDER — after the FIRST block deletion, every later cited line number is stale.
#    Re-derive targets by stable marker, not by the plan's pre-edit numbers:
grep -n "# Repo discovery\|^def _gh_list_repos\|^def _gh_" ${OLD_PATH}
```

### Detailed Steps

1. **Verify re-export patch-path preservation against the WHOLE repo (the central assumption).**
   The plan's load-bearing claim is that `patch("...loop_runner._gh_list_repos")` keeps working after
   the function moves, because the re-export makes the name a real attribute of `loop_runner` and
   callers resolve it through the `loop_runner` namespace at call time. This is **only true** when
   every internal caller does a bare global lookup in `loop_runner` (or `loop_runner._gh_list_repos`).
   It **breaks** if any other module did `from ...loop_runner import _gh_list_repos`: that binding is a
   separate name in the other module, and patching `loop_runner._gh_list_repos` will not touch it.
   Grep `from <old_module> import` across **`hephaestus/`, `tests/`, and `scripts/`** — not just the
   module and its own test file.

2. **Anchor multi-edit instructions to stable markers, not absolute line numbers.**
   In a sequential multi-edit plan, deleting the first block (e.g. `:566-942`) shifts every later cited
   line. Use function names, unique strings, or section banners (`# Repo discovery`) as anchors, OR state
   explicitly in the plan that line numbers are pre-edit and must be re-derived after each deletion.

3. **Enumerate every place the frozen invariant appears, and read the assertion body.**
   When the plan bumps a "frozen-at-16" allowlist to 17, grep the literal `16` and the keyword across
   `pyproject.toml` and `tests/`. Open the test and confirm whether it is a hardcoded count
   (`len(expected) == 16`) or a set-membership check — the required edits differ. The comment count
   and the asserted count can live in different files; miss one and CI fails.

4. **Prove "no circular import" by execution.**
   "New module → ci_driver introduces no cycle because ci_driver only mentions loop_runner in comments"
   is static reasoning. ci_driver may import another automation module that transitively loads
   loop_runner at import time. The claim is only proven when the import smoke test actually runs.
   Flag it as "verify by execution," never "verified by reading."

5. **Defer conditional import removals to ruff, gated by per-symbol grep.**
   "Drop `urlparse`/`gh_cli_timeout` only if no other references remain" is exactly where hand-judgement
   slips. Removing a still-used import breaks the module; leaving an unused one fails ruff F401. After the
   deletion, grep each symbol in the file and let `ruff check --select F401` (then `--fix`) be the source
   of truth instead of eyeballing it.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assume re-export preserves all mock patch paths | Plan claimed `patch("...loop_runner._gh_list_repos")` keeps working post-move because the `import X as X` re-export makes the name a real attribute, and only grepped within `loop_runner.py` + `test_loop_runner.py` | True only if every caller resolves the name through the `loop_runner` namespace at call time; a `from loop_runner import _gh_list_repos` in ANY other module is a separate binding that patching `loop_runner` does not affect — and that scope was never grepped | Before claiming re-exports preserve patch paths, grep the ENTIRE repo (`hephaestus/` AND `tests/` AND `scripts/`) for `from <old_module> import _<name>`, not just the two files you happened to read |
| Cite exact line numbers for a sequential multi-edit | Plan referenced `loop_runner.py:566-942`, `:1198`, `:1359`, `pyproject.toml:263`, `test_omit_allowlist.py:40-53` read at plan time | An implementer edits sequentially; deleting the `566-942` block shifts every later line, so literal line-number targeting after step 1 hits the wrong lines | Anchor multi-edit instructions to stable markers (function names, section banners, unique strings), or explicitly state line numbers are pre-edit and must be re-derived after each deletion |
| Trust the "frozen at 16 modules" comment | Plan asserted the omit allowlist is frozen at 16 and only the comment + one test need bumping to 17, without running the test or reading its assertion body | The "16" figure and the assertion mechanism (count literal vs set membership) were read, not verified; a hardcoded `len(...) == 16` elsewhere, or a third copy of the count, would be missed and fail CI | When a plan depends on a frozen-list/magic-number invariant, READ the actual assertion body (don't trust the comment) and grep the literal to enumerate EVERY place it appears |
| Reason about circular imports statically | Plan claimed `loop_repo_manager → ci_driver` adds no cycle because ci_driver references loop_runner only in comments | Static reasoning; ci_driver could import another automation module that transitively imports loop_runner at module load, creating a cycle the comment-scan never sees | The import-graph claim is only proven by the smoke-test step actually executing — label it "verify by execution," not "verified by reading" |
| Hand-judge conditional unused-import removal | Plan said to drop `urlparse` and `gh_cli_timeout` from loop_runner "only if no other references remain," left to manual judgement | Removing a still-used import breaks the module; leaving a genuinely-unused one fails ruff F401 — both directions of hand-judgement are wrong | Gate each import removal on a per-symbol grep AFTER the deletion and make `ruff check --select F401` / `--fix` the source of truth, not eyeballing |

## Results & Parameters

### What the plan got RIGHT (keep these strengths)

- **Read the actual code before planning** — confirmed the issue's line numbers were approximately right and that the 12 functions are genuinely self-contained pure helpers safe to move verbatim.
- **Enumerated call sites and patch sites with grep before asserting re-exports are safe** — correct instinct; the only defect was incomplete scope (see assumption #1).
- **Added an identity smoke test** (`assert loop_runner.X is loop_repo_manager.X`) to prove the re-export wiring binds the same object.
- **Mapped a per-criterion verification command to each acceptance criterion** so the plan is checkable rather than narrative.

### Reviewer focus (the 5 things to check hardest in such a plan)

```
## Cluster-extraction-with-re-export plan review checklist

- [ ] Did the grep for cross-module private-name imports cover the WHOLE repo
      (hephaestus/ + tests/ + scripts/), not just old_module.py + its test file?
- [ ] Are edit instructions anchored to stable markers (function names / banners),
      or to soon-stale absolute line numbers?
- [ ] Was the frozen-list/magic-number assertion mechanism actually READ
      (count literal vs set membership) and EVERY occurrence of the number grepped?
- [ ] Is the "no circular import" claim validated by an EXECUTED import smoke test,
      not just a comment scan / static reasoning?
- [ ] Are conditional import removals deferred to ruff (F401), not hand-judged?
```

### Issue #1360 specific findings

| Assumption in the plan | Status | What a reviewer must do |
|------------------------|--------|-------------------------|
| Re-export preserves all `patch("...loop_runner._fn")` paths | UNVERIFIED (scope too narrow) | Grep `from hephaestus.automation.loop_runner import` across hephaestus/, tests/, scripts/ — any direct private-name importer breaks |
| Cited line numbers (`:566-942`, `:1198`, `:1359`, `pyproject.toml:263`) are actionable as-is | FRAGILE | Re-derive by marker after the first block deletion; numbers are pre-edit snapshots |
| Omit allowlist "frozen at 16," bump in pyproject comment + one test | UNVERIFIED | Read the assertion body (count literal vs set membership); grep `16` for a third location |
| `loop_repo_manager → ci_driver` adds no cycle | REASONED, NOT RUN | Run `python -c "import ...loop_runner; from ...automation import loop_repo_manager"` |
| `urlparse` / `gh_cli_timeout` are safely removable | CONDITIONAL | Per-symbol grep after deletion; let `ruff --select F401` decide |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning phase for issue #1360 (extract 12-function repo-management cluster from `automation/loop_runner.py` into `loop_repo_manager.py` with backward-compat re-exports) | Plan produced, NOT executed; this skill records the unverified assumptions and reviewer risks. Implementation pending. |
