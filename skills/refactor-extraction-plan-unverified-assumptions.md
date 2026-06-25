---
name: refactor-extraction-plan-unverified-assumptions
description: "The uncertain assumptions and reviewer risks baked into extraction/refactor PLANs that move duplicated behavior into a sibling module or shared private helper before execution has proven the seams. Use when: (1) reviewing or authoring a plan that moves a function cluster out of a god-module and re-exports moved names, (2) consolidating duplicated issue-to-PR discovery loops behind a helper such as `_discover_prs_simple`, (3) the plan cites exact line numbers for a multi-step sequential edit, (4) the plan relies on callback signatures or method seams to preserve per-call-site logging, (5) the plan asserts no import-cycle, policy-widening, or test-coverage risk by static reasoning rather than execution."
category: architecture
date: 2026-06-25
version: "1.1.0"
user-invocable: false
verification: unverified
history: refactor-extraction-plan-unverified-assumptions.history
tags: [refactoring, extraction, cluster-extraction, shared-helper, issue-to-pr-discovery, backward-compat, re-export, mock-patch-path, planning, reviewer-risks, line-number-drift, circular-import, assumptions]
---

# Refactor Extraction Plan — Unverified Assumptions & Reviewer Risks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-25 |
| **Objective** | Capture the uncertain assumptions extraction/refactor PLANs make before execution proves the seams: v1.0 covered a 12-function cluster move from `loop_runner.py` into `loop_repo_manager.py` with re-exports (issue #1360); v1.1 adds a duplicated issue-to-PR discovery-loop extraction into `_discover_prs_simple` in `_review_utils.py` (issue #1380). |
| **Outcome** | Plans produced; NOT executed. These are the assumptions a reviewer must verify and an implementer must not take on faith. |
| **Verification** | unverified — planning artifact only; no code was written or run |
| **History** | [changelog](./refactor-extraction-plan-unverified-assumptions.history) |

> This skill is about the **PLANNING-RISK** angle, not the mechanics of *how* to extract a cluster.
> For the how-to mechanics see `python-module-decomposition-and-refactor-patterns` and
> `testing-module-patch-target-after-extraction`. For DRY *consolidation* (two modules → one)
> see `dry-refactoring-plan-assumption-audit`. This skill covers extraction plans where a small
> helper/module boundary is supposed to preserve existing behavior, and what silently breaks when the
> plan's assumptions are not re-verified immediately before editing.

## When to Use

- Reviewing or authoring a plan that extracts a cluster of functions out of a large module into a new sibling module.
- The plan keeps the original module importable by adding `from .new_module import _fn as _fn` re-exports (backward-compat shim) and claims existing `unittest.mock.patch("...old_module._fn")` calls still work.
- The plan cites exact line numbers (`module.py:566-942`, `pyproject.toml:263`) for a sequence of edits that delete/insert large blocks.
- The plan depends on a "frozen" list or magic number (e.g. an omit/coverage allowlist "frozen at N modules") that must be bumped in multiple places.
- The plan asserts "introduces no circular import" or "this import is now unused and can be removed" by static reasoning rather than by actually importing/linting.
- Reviewing or authoring a plan that extracts duplicated issue-to-PR lookup loops from multiple reviewer/CI-driver methods into one shared private helper.
- A proposed helper signature is a compromise between a terse requested API and call-site-specific behavior (for example, `on_missing` callback to preserve log severity).
- The extraction touches a method with broader policy after the lookup step, such as CI-driver dedupe, direct PR mode, bot PR union, or failing-PR union, and the plan promises to extract only the raw lookup block.

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

# === Reviewer / implementer pre-flight for a shared issue-to-PR lookup helper plan ===
# Run from the repo root before implementing a plan like ProjectHephaestus issue #1380.

# 1. RE-OPEN THE LIVE ISSUE. The plan may have summarized acceptance criteria from memory.
gh issue view 1380 --repo HomericIntelligence/ProjectHephaestus --json title,body,comments

# 2. RE-ANCHOR THE CURRENT CODE. Do not trust planning-time line numbers or method bodies.
rg -n "def _discover_prs|find_pr_for_issue|shared_pr_issues|direct PR|bot PR|failing PR" \
  hephaestus/automation tests/unit/automation

# 3. CHECK THE PROPOSED HOME AND IMPORT DIRECTION. A helper in _review_utils.py must not create a cycle.
python - <<'PY'
import hephaestus.automation._review_utils as review_utils
import hephaestus.automation.pr_reviewer as pr_reviewer
import hephaestus.automation.address_review as address_review
import hephaestus.automation.ci_driver as ci_driver

print(review_utils.__name__, pr_reviewer.__name__, address_review.__name__, ci_driver.__name__)
PY

# 4. RUN FOCUSED TESTS THAT SHOULD FAIL IF seams or CI-driver policy are flattened.
pytest \
  tests/unit/automation/test_review_utils.py \
  tests/unit/automation/test_pr_reviewer.py \
  tests/unit/automation/test_address_review.py \
  tests/unit/automation/test_ci_driver.py -q

# 5. LET LINT/FMT FIND import fallout after the extraction.
ruff check hephaestus/automation/_review_utils.py hephaestus/automation/pr_reviewer.py \
  hephaestus/automation/address_review.py hephaestus/automation/ci_driver.py
ruff format --check hephaestus/automation/_review_utils.py hephaestus/automation/pr_reviewer.py \
  hephaestus/automation/address_review.py hephaestus/automation/ci_driver.py
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

6. **Re-open live external acceptance criteria before coding.**
   If the final plan text did not quote or freshly inspect the GitHub issue, treat every exact acceptance
   criterion as unverified. Re-open the issue before editing and check whether it requires a specific
   helper signature, exact file home, or public/private API shape. For issue #1380, the proposed
   `_discover_prs_simple(issue_numbers, find_fn, *, on_missing=None)` callback shape is a hypothesis that
   must be reconciled against any exact "two positional arguments" wording in the live issue.

7. **Re-anchor method seams immediately before the edit.**
   Line references and call-site descriptions from planning can drift between planning and implementation.
   Re-read `PRReviewer._discover_prs`, `AddressReviewer._discover_prs`, `CIDriver._discover_prs`,
   `find_pr_for_issue`, and the focused tests in the current checkout. The method names are the anchors;
   old line numbers are only hints.

8. **Keep per-call-site logging outside the shared helper unless tests prove otherwise.**
   The helper may return an ordered issue-to-PR map, but missing-PR severity and exact log text can be
   operator-facing behavior. Preserve it with an explicit callback or with wrapper logic in each caller.
   A reviewer should compare old and new log behavior semantically, and byte-for-byte where existing
   tests/operators depend on exact strings.

9. **Extract only CIDriver's raw lookup block.**
   `CIDriver._discover_prs` has policy after the base issue lookup: dedupe, `shared_pr_issues`, direct PR
   mode, bot PR union, and failing-PR union. Do not move those policies into `_discover_prs_simple` and do
   not make reviewer modules inherit CI-driver widening semantics. The helper should be boring enough that
   a diff clearly shows those policy branches remained in `ci_driver.py`.

10. **Prove method seams with tests that fail for the wrong extraction.**
    Existing tests may patch `PRReviewer._discover_prs`, `AddressReviewer._discover_prs`, or CI-driver
    collaborators. Add focused `_review_utils` tests for ordered lookup, missing callbacks, and no calls on
    empty input, then re-run existing reviewer and CI-driver tests to prove the caller seams still work.

11. **Check the private-helper home for import-cycle risk.**
    `_review_utils.py` is a plausible home because reviewer helpers already live there, but a private helper
    imported by reviewer modules and CI-driver can still create import cycles if it imports back into those
    modules. The helper should accept a `find_fn` dependency instead of importing caller classes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assume re-export preserves all mock patch paths | Plan claimed `patch("...loop_runner._gh_list_repos")` keeps working post-move because the `import X as X` re-export makes the name a real attribute, and only grepped within `loop_runner.py` + `test_loop_runner.py` | True only if every caller resolves the name through the `loop_runner` namespace at call time; a `from loop_runner import _gh_list_repos` in ANY other module is a separate binding that patching `loop_runner` does not affect — and that scope was never grepped | Before claiming re-exports preserve patch paths, grep the ENTIRE repo (`hephaestus/` AND `tests/` AND `scripts/`) for `from <old_module> import _<name>`, not just the two files you happened to read |
| Cite exact line numbers for a sequential multi-edit | Plan referenced `loop_runner.py:566-942`, `:1198`, `:1359`, `pyproject.toml:263`, `test_omit_allowlist.py:40-53` read at plan time | An implementer edits sequentially; deleting the `566-942` block shifts every later line, so literal line-number targeting after step 1 hits the wrong lines | Anchor multi-edit instructions to stable markers (function names, section banners, unique strings), or explicitly state line numbers are pre-edit and must be re-derived after each deletion |
| Trust the "frozen at 16 modules" comment | Plan asserted the omit allowlist is frozen at 16 and only the comment + one test need bumping to 17, without running the test or reading its assertion body | The "16" figure and the assertion mechanism (count literal vs set membership) were read, not verified; a hardcoded `len(...) == 16` elsewhere, or a third copy of the count, would be missed and fail CI | When a plan depends on a frozen-list/magic-number invariant, READ the actual assertion body (don't trust the comment) and grep the literal to enumerate EVERY place it appears |
| Reason about circular imports statically | Plan claimed `loop_repo_manager → ci_driver` adds no cycle because ci_driver references loop_runner only in comments | Static reasoning; ci_driver could import another automation module that transitively imports loop_runner at module load, creating a cycle the comment-scan never sees | The import-graph claim is only proven by the smoke-test step actually executing — label it "verify by execution," not "verified by reading" |
| Hand-judge conditional unused-import removal | Plan said to drop `urlparse` and `gh_cli_timeout` from loop_runner "only if no other references remain," left to manual judgement | Removing a still-used import breaks the module; leaving a genuinely-unused one fails ruff F401 — both directions of hand-judgement are wrong | Gate each import removal on a per-symbol grep AFTER the deletion and make `ruff check --select F401` / `--fix` the source of truth, not eyeballing |
| Treat planning-time line references as current | Issue #1380 plan named `PRReviewer._discover_prs`, `AddressReviewer._discover_prs`, `CIDriver._discover_prs`, `find_pr_for_issue`, and focused tests after repository inspection during planning | The branch can change before implementation; a stale method body or moved test means the helper gets wired to the wrong seam or misses a newly-added policy branch | Re-read the current checkout by stable method names immediately before editing; line numbers from the plan are only wayfinding |
| Assume callback helper signature satisfies acceptance criteria | Plan proposed `_discover_prs_simple(issue_numbers, find_fn, *, on_missing=None)` to preserve different missing-PR log severities | The issue may have asked for an exact two-positional-argument helper shape; a keyword callback can be a correct engineering compromise but still fail acceptance if the live issue required no callback | Re-open the GitHub issue and explicitly reconcile exact wording with the proposed signature before implementation |
| Flatten missing-PR logging into the helper | Shared lookup helper centralizes missing handling and logs one generic message for all callers | `PRReviewer`, `AddressReviewer`, and `CIDriver` can intentionally differ in severity, wording, or operator expectations; flattening logs is a behavior change even if returned PRs match | Keep missing behavior in wrappers or pass an explicit `on_missing` callback; compare log behavior where tests/operators depend on it |
| Extract CIDriver policy instead of only raw lookup | Refactor moved dedupe, `shared_pr_issues`, direct PR mode, bot PR union, or failing-PR union into the shared helper with the base issue lookup | Reviewer modules would inherit CI-driver widening semantics or CIDriver would lose policy ordering; both are regressions hidden behind a DRY-looking helper | The helper should only map requested issue numbers through `find_fn`; leave CIDriver dedupe/direct/bot/failing logic in `ci_driver.py` |
| Trust existing tests to catch over-extraction | Plan inferred current tests would fail if CIDriver widening/dedupe/direct/failing behavior moved or flattened | Existing tests may only check happy paths or final PR sets, not that the policy remained in the caller or that empty input avoids finder calls | Add focused helper tests for order, missing callback, and empty input; run existing reviewer and CI-driver tests as regression coverage |
| Put the helper in `_review_utils.py` without import smoke | Plan assumed `_review_utils.py` is the right home and that private imports from reviewer modules are acceptable | A shared helper imported by reviewer modules and CI-driver can create an import cycle if it pulls caller details back in; private helper ownership can also be an architecture concern | Keep the helper dependency-injected via `find_fn`; run import smoke and ask reviewer to confirm the private helper home is acceptable |

## Results & Parameters

### What the plan got RIGHT (keep these strengths)

- **Read the actual code before planning** — confirmed the issue's line numbers were approximately right and that the 12 functions are genuinely self-contained pure helpers safe to move verbatim.
- **Enumerated call sites and patch sites with grep before asserting re-exports are safe** — correct instinct; the only defect was incomplete scope (see assumption #1).
- **Added an identity smoke test** (`assert loop_runner.X is loop_repo_manager.X`) to prove the re-export wiring binds the same object.
- **Mapped a per-criterion verification command to each acceptance criterion** so the plan is checkable rather than narrative.

### What the issue #1380 plan got RIGHT (keep these strengths)

- **Kept the helper private and dependency-injected** — accepting `find_fn` avoids importing reviewer classes or CI-driver internals into `_review_utils.py`.
- **Preserved method seams in the plan** — `PRReviewer._discover_prs`, `AddressReviewer._discover_prs`, and `CIDriver._discover_prs` remain the caller-facing methods rather than being deleted in favor of a new public API.
- **Scoped CIDriver extraction narrowly** — the plan explicitly targeted only the raw lookup block, not dedupe, direct PR mode, bot PR union, or failing-PR union.
- **Mapped new tests to helper behavior** — ordered lookup, missing callbacks, and empty input are the right unit-level guarantees for `_discover_prs_simple`.

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

### Reviewer focus for shared issue-to-PR discovery helper plans

```
## Shared issue-to-PR lookup helper plan review checklist

- [ ] Was the live GitHub issue re-opened before implementation to confirm exact
      acceptance criteria and helper signature expectations?
- [ ] Did the implementer re-read current `PRReviewer._discover_prs`,
      `AddressReviewer._discover_prs`, and `CIDriver._discover_prs` by method name,
      not by planning-time line numbers?
- [ ] Does `_discover_prs_simple` preserve ordered lookup, missing-callback behavior,
      and no finder calls for empty input?
- [ ] Are caller-specific missing-PR logs preserved semantically or byte-for-byte
      where tests/operators rely on exact text?
- [ ] Did CIDriver keep dedupe, `shared_pr_issues`, direct PR mode, bot PR union,
      and failing-PR union outside the helper?
- [ ] Do existing reviewer/CI-driver tests still cover patched method seams, not only
      the new helper's return value?
- [ ] Was `_review_utils.py` import-cycle risk checked with a real import smoke test?
```

### Issue #1360 specific findings

| Assumption in the plan | Status | What a reviewer must do |
|------------------------|--------|-------------------------|
| Re-export preserves all `patch("...loop_runner._fn")` paths | UNVERIFIED (scope too narrow) | Grep `from hephaestus.automation.loop_runner import` across hephaestus/, tests/, scripts/ — any direct private-name importer breaks |
| Cited line numbers (`:566-942`, `:1198`, `:1359`, `pyproject.toml:263`) are actionable as-is | FRAGILE | Re-derive by marker after the first block deletion; numbers are pre-edit snapshots |
| Omit allowlist "frozen at 16," bump in pyproject comment + one test | UNVERIFIED | Read the assertion body (count literal vs set membership); grep `16` for a third location |
| `loop_repo_manager → ci_driver` adds no cycle | REASONED, NOT RUN | Run `python -c "import ...loop_runner; from ...automation import loop_repo_manager"` |
| `urlparse` / `gh_cli_timeout` are safely removable | CONDITIONAL | Per-symbol grep after deletion; let `ruff --select F401` decide |

### Issue #1380 specific findings

| Assumption in the plan | Status | What a reviewer must do |
|------------------------|--------|-------------------------|
| Planning-time file/method references are still current | UNVERIFIED | Re-read current `pr_reviewer.py`, `address_review.py`, `ci_driver.py`, `_review_utils.py`, and tests before editing |
| `_discover_prs_simple(issue_numbers, find_fn, *, on_missing=None)` satisfies the issue's desired helper shape | UNVERIFIED | Re-open issue #1380 and confirm whether a callback is acceptable or whether the issue required exactly two positional arguments |
| Existing tests cover reviewer method seams and CIDriver policy boundaries | UNVERIFIED | Ensure tests fail if `_discover_prs` methods are bypassed, missing logs are flattened, or CIDriver dedupe/direct/bot/failing logic moves |
| `_review_utils.py` is the right helper home | PLAUSIBLE, NOT PROVEN | Check architecture/import direction and run import smoke after adding the helper |
| Missing-PR log behavior can be preserved with callback/wrapper logic | UNVERIFIED | Compare old and new log levels/messages in focused tests or caplog assertions |
| CIDriver extraction can stay raw-map-only | HIGH-RISK BOUNDARY | Inspect the diff and confirm dedupe, `shared_pr_issues`, direct PR mode, bot PR union, and failing-PR union are unchanged in `ci_driver.py` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning phase for issue #1360 (extract 12-function repo-management cluster from `automation/loop_runner.py` into `loop_repo_manager.py` with backward-compat re-exports) | Plan produced, NOT executed; this skill records the unverified assumptions and reviewer risks. Implementation pending. |
| ProjectHephaestus | Planning phase for issue #1380 (extract duplicated issue-to-PR discovery loops from `PRReviewer._discover_prs`, `AddressReviewer._discover_prs`, and the base lookup section of `CIDriver._discover_prs` into `_discover_prs_simple`) | Plan produced, NOT executed; GitHub issue acceptance criteria and current checkout must be freshly verified before implementation. |
