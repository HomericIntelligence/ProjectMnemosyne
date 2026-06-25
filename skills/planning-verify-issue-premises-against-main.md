---
name: planning-verify-issue-premises-against-main
description: "Consolidated / auto-generated follow-up issue bodies often describe a PLANNED or PARALLEL-BRANCH state, not the state of `main` — AND, conversely, a 'fix this regression / revert this bad value' issue may already be FULLY REMEDIATED on `main` by a prior PR (a stale issue body that quotes a file:line and a specific bad value is NOT evidence the bad value is still present; issue bodies are point-in-time snapshots and are never edited). Before planning, verify EVERY premise against `main`: the issue's OPEN/CLOSED state, whether the PR it claims 'already did X' is actually merged, whether referenced files/recipes/commands exist on `main`, whether a parallel in-flight PR already does this work, AND whether the cited bad value is actually still present on disk + HEAD. Prove commits are/aren't on main with `git merge-base --is-ancestor`, read the on-main file with `git show HEAD:<path>`, find a prior remediating commit with `git log -S<value> -- <path>` / `git show <commit> --stat` (look for 'Closes #<earlier-dup-issue>'), confirm no pending regression with `git diff HEAD -- <path>` / `git status --short`, list on-main tests with `git ls-files`, check issue state with `gh issue view N --json state`, and surface overlapping PRs with `gh pr list`. Make the plan SELF-CONTAINED against main, not dependent on unmerged PRs; if a regression is already fixed, the deliverable is verification evidence + a recommendation to close the issue, NOT a no-op edit (a no-op diff fails review); never re-propose a regression GUARD that already exists; never copy an issue's prescribed 'mark X resolved' wording while the underlying issue is still OPEN; and never wire a CI gate to a recipe/target that does not yet exist on main (it hard-fails on day one). Use when: (1) planning a consolidated / auto-generated / follow-up issue that asserts 'PR #N did X' or 'issue #M is resolved', (2) the issue prescribes editing CLAUDE.md / docs to mark a defect resolved, (3) the issue tells you to wire a hook/gate to a named command (e.g. `just test-all`), (4) the issue overlaps work that may be in flight on a parallel branch / PR, (5) any premise depends on commits that may live on `*-auto-impl` or other unmerged branches, (6) planning a fix for a 'revert this regression / restore this value / fix this bad config value' issue — verify the cited bad value is actually still present on disk + HEAD before planning edits, because a prior PR may already have remediated it (and added the regression guard)."
category: documentation
date: 2026-06-20
version: "1.1.0"
user-invocable: false
verification: verified-local
history: planning-verify-issue-premises-against-main.history
tags:
  - planning
  - verify-before-planning
  - issue-premise
  - against-main
  - unmerged-pr
  - parallel-branch
  - follow-up-issue
  - consolidated-issue
  - auto-generated-issue
  - git-merge-base
  - git-show-head
  - gh-issue-state
  - parallel-pr-overlap
  - pre-commit
  - justfile-recipe
  - self-contained-plan
  - stale-issue
  - regression-already-fixed
  - no-op-edit
  - git-log-pickaxe
  - verified-local-vs-ci
---

# Verify Every Issue Premise Against `main` Before Planning

**History:** [changelog](./planning-verify-issue-premises-against-main.history)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Capture a durable planning-discipline lesson: a consolidated / auto-generated / follow-up issue body narrates a PLANNED or PARALLEL-BRANCH state, NOT the state of `main`. Before planning, verify every premise (issue state, PR merge status, referenced files, referenced recipes/commands) against `main`, and make the plan self-contained against `main` rather than dependent on unmerged PRs |
| **Outcome** | Plan written for ProjectProteus issue #185. The issue asserted "PR #173 replaces stubs with real tests" and prescribed a pre-push hook running `just test-all`. Premise checks against `main` showed: issue #5 still OPEN, PR #173 still OPEN/unmerged, the #5 real-test commits NOT ancestors of main (they live on `*-auto-impl` branches), NO `test-all` recipe exists on main, the only on-main test is `tests/dispatch-apply.test.sh`, and a separate open PR #187 already did essentially the same work. The plan was reframed to be self-contained against `main`. The PLAN itself was NOT executed (no code committed, CI not run); the PREMISE-VERIFICATION commands WERE run and confirmed via git/gh |
| **Verification** | **verified-local** — the `gh issue view` / `gh pr list` / `git merge-base --is-ancestor` / `git show HEAD:justfile` / `git ls-files` premise checks (and, for the v1.1.0 #319 mirror case, the `jq` / `git show HEAD:<path>` / `git log -S` / `git show <commit> --stat` / `git diff HEAD` checks) were executed locally and produced the cited outputs. The resulting plans are **unexecuted** (no commit, no CI); CI gating of the jq guard was NOT observed running. Treat the plan prescriptions as a hypothesis; treat the premise findings as confirmed |
| **v1.1.0 (2026-06-20)** | Added the MIRROR case (Odysseus #319): a "revert this regression / fix this bad value" issue may already be FULLY REMEDIATED on `main` by a prior PR — verify the cited bad value is still present on disk + HEAD (and pickaxe for the prior remediating commit) before planning a no-op edit. See [changelog](./planning-verify-issue-premises-against-main.history) |

This is a planning-DISCIPLINE learning. It is the **temporal / branch** complement to the
spatial-disambiguation skill `verify-issue-premise-against-code-before-planning` (which greps the
premise tokens to find WHICH same-repo file matches). Here the question is not *which file* but
*which timeline*: the issue describes a future/parallel-branch state that is not yet on `main`.

> **Warning:** The resulting implementation plan was produced in a planning session and NOT
> executed end-to-end (no commit, no CI). The verification COMMANDS below were genuinely run
> against the live repo (`verified-local`); the plan they fed is a hypothesis until CI confirms.

## When to Use

- Planning a **consolidated / auto-generated / follow-up** issue whose body asserts "PR #N already
  did X" or "issue #M is resolved" — these bodies are snapshots of a PLANNED end-state, not `main`.
- The issue tells you to **edit CLAUDE.md / docs to mark a defect resolved**. Never copy the
  issue's prescribed "resolved" wording while the underlying issue is still OPEN.
- The issue tells you to **wire a hook / CI gate to a named command** (e.g. `just test-all`).
  Confirm that recipe/target actually exists on `main` before wiring a gate to it.
- The issue **overlaps work that may be in flight** on a parallel branch or another open PR.
- Any premise depends on commits that may live on `*-auto-impl` (or other) unmerged branches
  rather than on `main`.
- **Planning a fix for a "revert this regression / restore this value / fix this bad config
  value" issue** (the MIRROR case). A stale issue body that quotes a `file:line` and a specific
  bad value is NOT evidence the bad value is still present — a prior PR may have ALREADY reverted
  it (and added the regression guard). Before planning any edit, confirm the bad value is still on
  disk + HEAD; if it is already fixed, the deliverable is verification evidence + close the issue,
  NOT a no-op edit (a no-op diff fails review).

## Verified Workflow

> **Warning:** The numbered discipline below is the workflow that worked at planning time; its
> verification commands were run live (`verified-local`). The downstream plan was NOT executed.
> The heading is "Verified Workflow" to satisfy the marketplace validator (it requires that exact
> heading) — but the PLAN it produced is unexecuted.

### Quick Reference

```bash
ORG=HomericIntelligence
REPO=ProjectProteus

# 1. Is the issue the body claims is "resolved" actually CLOSED?
gh issue view 5 --repo "$ORG/$REPO" --json state --jq .state
#   -> OPEN  (so do NOT copy the issue's "mark #5 resolved" wording)

# 2. Is the PR the body says "already did X" actually MERGED?
gh pr view 173 --repo "$ORG/$REPO" --json state,mergedAt --jq '{state,mergedAt}'
#   -> {"state":"OPEN","mergedAt":null}  (unmerged — its changes are NOT on main)

# 3. Prove the claimed commits are / are NOT on main (the key technique).
git fetch origin
#    Find the branch the work really lives on (often *-auto-impl):
git branch -r --contains <commit-sha>
#    Then prove it is NOT an ancestor of main:
git merge-base --is-ancestor <commit-sha> origin/main && echo "ON MAIN" || echo "NOT ON MAIN"
#   -> NOT ON MAIN  (the real-test commits live on 27-auto-impl / 182-auto-impl)

# 4. Does the recipe/command the issue tells you to gate on EXIST on main?
git show HEAD:justfile | grep -nE '^[a-z0-9_-]+( [A-Z]|:)'   # list recipes ON MAIN
just --list                                                   # what `just` actually offers
#   -> only `test NAME` (a Dagger wrapper) and `validate`; NO `test-all`.
#      A pre-push hook running `just test-all` would crash on every push:
#      "Justfile does not contain recipe `test-all`".

# 5. What test files actually exist ON MAIN (not on a branch)?
git ls-files tests/
#   -> tests/dispatch-apply.test.sh   (the ONLY test file on main)
git show HEAD:dagger/package.json | grep -E '"test"|jest'   # -> no test/jest script

# 6. Is a PARALLEL PR already doing this work?
gh pr list --repo "$ORG/$REPO" --state open \
  --json number,title,headRefName --jq '.[]|"\(.number) \(.headRefName) — \(.title)"'
#   -> #187 add pre-push hook and mark #5 resolved (branch 182-auto-impl) — OVERLAP

# 7. THE REGRESSION-ALREADY-FIXED CASE (issue says "revert bad value V at file:line").
#    Do NOT trust the issue's quoted value — issue bodies are never edited after filing.
PATH_=configs/github/org-ruleset-active.json   # the cited file

# 7a. Is the bad value ACTUALLY still present on disk + HEAD? (grep / jq the cited field)
jq '.rules[] | select(.type=="pull_request") | .parameters.required_approving_review_count' "$PATH_"
git show HEAD:"$PATH_" | jq '.rules[]|select(.type=="pull_request")|.parameters.required_approving_review_count'
#   -> 1 1  (the bad value 0 is GONE — already reverted; no source edit needed)

# 7b. Find the prior commit that remediated it (pickaxe on the value, scoped to the path).
git log --oneline -- "$PATH_"
git log -S'"required_approving_review_count": 0' --oneline -- "$PATH_"   # commit that REMOVED the 0
git show <commit> --stat                                                 # confirm it touched all cited files
#   -> d34e291 (PR #308) "Closes #178" reverted all four files 0->1 AND added the jq CI guard

# 7c. Confirm there is NO pending regression in the working tree.
git diff HEAD -- "$PATH_"        # -> empty
git status --short "$PATH_"      # -> empty

# 7d. Does the regression GUARD the issue wants already exist? (don't re-propose it)
grep -rn 'required_approving_review_count' .github/workflows/
#   -> _required.yml already asserts [ "$count" -lt 1 ] && exit 1  — guard present
```

### Detailed Steps

1. **Treat the consolidated/auto-generated issue body as a description of a PLANNED end-state, not
   `main`.** Auto-generated follow-up issues are often written assuming a set of sibling PRs will
   have merged. They describe the intended steady state, which is frequently a parallel-branch or
   not-yet-merged reality. Every "PR #N did X" / "#M is resolved" assertion is a CLAIM to verify.

2. **Verify referenced issue states with `gh issue view N --json state`.** If the body says
   "issue #5 is resolved," confirm it. In #185, `gh issue view 5 --json state` returned `OPEN` —
   so any doc edit marking #5 resolved would have stated a falsehood on `main`.

3. **Verify referenced PRs are actually MERGED, not just open.** `gh pr view N --json state,mergedAt`.
   In #185 the body said "PR #173 replaces stubs with real tests," but #173 was `OPEN` / `mergedAt:
   null` — its changes are not on `main`, so the plan cannot assume real tests exist there.

4. **Prove commits are / are not on `main` with `git merge-base --is-ancestor`.** This is the load-
   bearing technique: `git merge-base --is-ancestor <sha> origin/main` exits 0 iff `<sha>` is on
   main. `git branch -r --contains <sha>` shows which branch *does* hold it — here the #5 real-test
   commits lived on `27-auto-impl` / `182-auto-impl`, not main. Read the *content* of `main`, never
   the working tree (which may be checked out to a feature branch).

5. **Confirm any recipe / command the issue tells you to gate on EXISTS on `main`.** Read the on-
   main file with `git show HEAD:justfile` and cross-check with `just --list`. In #185 there was NO
   `test-all` recipe on main — only `test NAME` (a Dagger wrapper) and `validate`. A pre-push hook
   wired to `just test-all` would hard-fail on EVERY push with "Justfile does not contain recipe
   `test-all`." Wiring a gate to a non-existent target is a day-one breakage, not a future-proofing.

6. **List the tests that actually exist on `main` with `git ls-files`.** In #185 the only on-main
   test was `tests/dispatch-apply.test.sh`; `git show HEAD:dagger/package.json` had no `test`/Jest
   script. So CLAUDE.md wording like "unit-tests runs Jest / integration-tests runs bats / #5
   resolved" would have been FALSE against main. Defect docs must stay truthful to `main`.

7. **Surface overlapping in-flight PRs with `gh pr list`.** A consolidated issue often overlaps a
   sibling PR already in flight. In #185, open PR #187 ("add pre-push hook and mark #5 resolved",
   branch `182-auto-impl`) already did essentially the same work. Cross-link it in the plan instead
   of duplicating it.

8. **Make the plan SELF-CONTAINED against `main`.** Once the premises are checked, write the plan
   so it stands on the actual state of `main` — do not write "assuming PR #173 lands, then…" forks.
   If the prerequisite work is not on main, either (a) scope the plan to what main can support now,
   or (b) explicitly mark the dependency and cross-link the in-flight PR. Keep defect docs (CLAUDE.md)
   reflecting main's real state; cross-link the open PRs rather than copying their "resolved" wording.

9. **For a "revert this regression / fix this bad value" issue, verify the bad value is still
   present on disk + HEAD BEFORE planning the edit (the mirror case).** An issue body that quotes
   a `file:line` and a specific bad value (e.g. "`required_approving_review_count: 0` at line 21")
   is a point-in-time snapshot — issue bodies are never edited, so a stale one can keep asserting a
   value that a prior PR already reverted. Run the four checks: **(a)** `grep`/`jq` the cited
   `file:line` to confirm the bad value is actually still there (also `git show HEAD:<path>` to
   check HEAD, not just the working tree); **(b)** `git log --oneline -- <path>` and the pickaxe
   `git log -S'<bad-value>' -- <path>` to find whether a prior commit already fixed it — then
   `git show <commit> --stat` to confirm it touched ALL the cited files, and look for a
   `Closes #<earlier-dup-issue>` trailer proving an earlier duplicate was already resolved;
   **(c)** `git diff HEAD -- <path>` + `git status --short <path>` to confirm there is NO pending
   regression in the working tree; **(d)** check whether the regression GUARD the issue asks for
   (a CI assertion) ALREADY exists, so the plan does not redundantly propose adding one. If every
   check shows the regression is already fixed, the plan's deliverable becomes the verification
   commands proving resolution plus a recommendation to close the issue as already-fixed by the
   prior PR — NOT a no-op edit. A no-op diff would fail review (there is nothing to change), so
   re-applying the "fix" is the wrong plan. (Worked example: Odysseus #319 — see Results.)

10. **State CI semantics honestly: distinguish "I READ the workflow YAML" from "I SAW it gate a
    PR."** If you assert a required-status-check runs a particular guard by READING
    `.github/workflows/_required.yml`, that is **verified-local** (file read), NOT **verified-ci**
    (you never observed the guard run or fail in an actual CI run). Label the claim accordingly in
    the plan; do not upgrade a file-read to an observed-CI-gate.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust "PR #173 replaces stubs with real tests" from the issue body | Planned as if real tests already existed on main | `gh pr view 173` showed `state:OPEN, mergedAt:null`; `git merge-base --is-ancestor` proved the #5 real-test commits were NOT on main (they live on `27-auto-impl`/`182-auto-impl`) | Verify a referenced PR is actually MERGED and its commits are ancestors of `origin/main` before assuming its output exists on main |
| Wire a pre-push hook to `just test-all` (as the issue prescribed) | Planned a hook with `entry`/command running `just test-all` | NO `test-all` recipe exists on `main` (`git show HEAD:justfile` + `just --list` show only `test NAME` and `validate`); the hook would crash every push with "Justfile does not contain recipe `test-all`" | Confirm a referenced recipe/command/target exists on `main` before wiring any gate to it; otherwise the gate hard-fails on day one |
| `entry: bash -c just test-all` in the pre-commit hook | Used `bash -c just test-all` to "run the recipe" | `bash -c` takes its FIRST word as the command and the rest as `$0`/positional args, so this runs command `just` with `$0=test-all` — the recipe is never invoked as intended | Use `entry: just test-all` (with `language: system`), or quote it: `bash -c "just test-all"` if a shell wrapper is truly needed |
| Copy the issue's "mark #5 resolved" / "unit-tests runs Jest, integration-tests runs bats" wording into CLAUDE.md | Transcribed the issue's prescribed "resolved" documentation edits | Issue #5 was still OPEN (`gh issue view 5 --json state` → OPEN); the only on-main test is `tests/dispatch-apply.test.sh` and `dagger/package.json` has no Jest script — so the wording was FALSE on main | Never copy an issue's prescribed "resolved" wording while the underlying issue is still OPEN; reconcile doc edits against the real state of `main` and cross-link the in-flight PRs |
| Plan without checking for parallel in-flight PRs | Treated #185 as standalone net-new work | A separate open PR #187 ("add pre-push hook and mark #5 resolved", branch `182-auto-impl`) already did essentially the same work — `gh pr list` surfaced it | `gh pr list` before planning a consolidated issue; cross-link overlapping in-flight PRs instead of duplicating their work |
| Read the working tree to learn "what's on main" | Inspected the checked-out files | The working tree may be on a feature branch; on-disk content is not evidence of `main` | Read on-main content explicitly: `git show HEAD:<path>` / `git ls-files` against `origin/main`, and prove ancestry with `git merge-base --is-ancestor` |
| Trust a stale issue body's quoted bad value + line numbers (Odysseus #319) | Issue said "revert `required_approving_review_count` 0→1 in four ruleset configs at the cited lines"; planned to re-apply that 0→1 edit | The value was ALREADY `1` on disk AND on HEAD — a prior PR (#308, commit d34e291, `Closes #178`) had reverted all four files. Re-applying would produce a NO-OP diff that fails review. The issue body is a point-in-time snapshot and is never edited | A quoted file:line + bad value in an issue is NOT evidence the bad value is still present. `grep`/`jq` the cited line on disk AND `git show HEAD:<path>`, and pickaxe `git log -S'<value>' -- <path>` for a prior remediating commit (look for `Closes #<earlier-dup>`) BEFORE planning any edit |
| Propose adding a regression GUARD that already exists (Odysseus #319) | Plan was going to recommend adding a CI assertion that `required_approving_review_count` cannot regress to 0 | The same prior PR (#308) had ALREADY added a jq guard to `.github/workflows/_required.yml` (`[ "$count" -lt 1 ] && exit 1`). Proposing it again is redundant and signals the live state was never checked | Before proposing a regression guard, `grep -rn '<field>' .github/workflows/` to confirm one does not already exist; if it does, cite it as evidence the regression is already prevented, don't re-add it |
| Claim verified-ci for a guard only READ in the workflow file (Odysseus #319) | Asserted "the schema-validation required status check runs this jq guard" on the strength of reading `.github/workflows/_required.yml` | Reading the workflow YAML proves the guard is WRITTEN, not that it RUNS or GATES — the guard was never observed running or failing in an actual CI run. Conflating the two over-states confidence | Label such a claim **verified-local** (file read), not **verified-ci** (observed gating a PR). Distinguish "I read the workflow YAML" from "I saw it gate a PR"; only the latter is verified-ci |

## Results & Parameters

### The premise-verification command set that worked (the core of this skill)

```bash
ORG=HomericIntelligence; REPO=ProjectProteus
gh issue view 5  --repo "$ORG/$REPO" --json state --jq .state                 # OPEN
gh pr view  173  --repo "$ORG/$REPO" --json state,mergedAt                    # OPEN / null
git merge-base --is-ancestor <real-test-sha> origin/main || echo "NOT ON MAIN"
git branch -r --contains <real-test-sha>                                      # *-auto-impl
git show HEAD:justfile | grep -nE 'test-all'                                  # (no output)
just --list                                                                   # test NAME, validate
git ls-files tests/                                                           # tests/dispatch-apply.test.sh
git show HEAD:dagger/package.json | grep -E '"test"|jest'                     # (no output)
gh pr list --repo "$ORG/$REPO" --state open --json number,title,headRefName   # surfaces #187
```

### Verified findings for ProjectProteus #185 (live, 2026-06-20)

- Issue #5: `state == OPEN` (not resolved, despite the body's prescribed "mark resolved" edit).
- PR #173: `state == OPEN`, `mergedAt == null` — unmerged; its "real tests" are NOT on main.
- The #5 real-test commits are NOT ancestors of `origin/main` (`git merge-base --is-ancestor`
  failed); they live on `27-auto-impl` / `182-auto-impl` branches.
- No `test-all` recipe on main — only `test NAME` (a Dagger wrapper) and `validate`.
- Only on-main test file: `tests/dispatch-apply.test.sh`; `dagger/package.json` has no test/Jest
  script.
- Open PR #187 (branch `182-auto-impl`) already does essentially the same work → cross-link, don't
  duplicate.

### The pre-commit `bash -c` parsing gotcha (copy-paste correct forms)

```yaml
# WRONG — `just` runs with $0=test-all; the recipe is never invoked as intended:
entry: bash -c just test-all
# CORRECT — run the command directly:
entry: just test-all
language: system
# CORRECT alternative — if a shell wrapper is genuinely needed, QUOTE it:
entry: bash -c "just test-all"
```

### Worked example: Odysseus issue #319 — regression already fixed by a prior PR (the mirror case)

Issue #319 was a follow-up that said: "security regression — revert `required_approving_review_count`
from `0`→`1` in four ruleset configs," quoting specific files and line numbers and the bad value `0`.
The premise was STALE.

**Verification command set that worked (the core of the mirror case):**

```bash
# (a) Is the bad value still present on disk + HEAD? (grep/jq the cited field)
for f in configs/github/org-ruleset.json configs/github/org-ruleset-active.json \
         configs/github/repo-ruleset.json configs/github/repo-ruleset-active.json; do
  jq '.rules[]|select(.type=="pull_request")|.parameters.required_approving_review_count' "$f"
done
#   -> 1 1 1 1  (the bad value 0 is GONE on disk)
git show HEAD:configs/github/org-ruleset-active.json \
  | jq '.rules[]|select(.type=="pull_request")|.parameters.required_approving_review_count'
#   -> 1  (also fixed on HEAD, not just the working tree)

# (b) Find the prior remediating commit (pickaxe on the value, scoped to path).
git log -S'"required_approving_review_count": 0' --oneline -- configs/github/
git show d34e291 --stat
#   -> d34e291 (PR #308) "Closes #178" reverted ALL FOUR files 0->1 AND added the jq CI guard

# (c) No pending regression in the working tree.
git diff HEAD -- configs/github/   # -> empty
git status --short configs/github/ # -> empty

# (d) Regression guard already exists?
grep -rn 'required_approving_review_count' .github/workflows/_required.yml
#   -> [ "$count" -lt 1 ] && { echo FAIL; exit 1; }  — already present
```

**Outcome:** the regression was ALREADY FULLY REMEDIATED on `main` (PR #308 / commit d34e291,
`Closes #178`). The correct plan was therefore "no source change; document verification evidence and
recommend closing #319 as already-fixed by #308" — NOT a re-applied 0→1 edit (which would be a no-op
diff that fails review).

**Planning-risk / honesty notes (the assumptions a plan reviewer should focus on):**

- **CI semantics are verified-LOCAL, not verified-CI.** The plan asserted "the schema-validation
  required status check runs this jq guard" by READING `.github/workflows/_required.yml` — that
  proves the guard is written, not that it ran or gated a PR. Distinguish "I read the workflow YAML"
  from "I saw it gate a PR." This skill's verification is `verified-local` for exactly this reason.
- **jq-`null` guard-robustness edge case.** The guard is `[ "$count" -lt 1 ]`. If jq ever emits `null`
  (the `pull_request` rule missing), `$count` is the string `"null"` and `-lt` errors —
  `[: null: integer expression expected`. A `-z` empty-string check does NOT catch `"null"`. A
  reviewer should confirm the rule is always present (or harden the guard to treat `null`/non-numeric
  as a failure). The guard's correctness depends on this.
- **Unverified external claim: the set of apply paths.** The mapping of the four config files to the
  issue's cited line numbers was confirmed by direct read, but the claim that
  `apply-repo-rulesets.sh` / `apply-org-ruleset.sh` are the ONLY apply paths that consume these files
  was taken from the issue body, NOT independently traced. Flag it as an unverified external claim;
  grep the repo for other consumers before relying on it.

### Related skills

- `github-ruleset-review-count-governance` — the DOING side of this exact fix: it documents PR #308 /
  issue #178 (revert `required_approving_review_count` 0→1 across the four canonical ruleset files and
  add the jq CI guard). THIS skill is the PLANNING-DISCIPLINE side: when a later issue (#319) re-files
  that same regression, verify it is not already remediated before planning a (no-op) edit.
- `planning-verify-live-state-before-assuming-work-remains` — verify live EXTERNAL state (default
  branch, applied ruleset) may already be done OR the opposite. THIS skill verifies on-`main` /
  on-HEAD git state, including a prior remediating commit for a "revert this regression" issue.
- `verify-issue-premise-against-code-before-planning` — the SPATIAL complement: grep the premise's
  distinctive tokens to disambiguate WHICH same-repo file/job matches. THIS skill is the TEMPORAL/
  branch complement: the premise describes a not-yet-on-main (planned/parallel-branch) state.
- `planning-verify-live-state-before-assuming-work-remains` — verify live external state (default
  branch, applied ruleset) may already be done OR the opposite. THIS skill focuses on commits/PRs
  that look merged in the narrative but live on unmerged branches.
- `planning-dependent-issue-unverified-upstream` — when the dependency IS already merged, read it
  and eliminate forks. THIS skill handles the case where the dependency is NOT merged (still open),
  so the plan must be made self-contained against main instead.
- `git-unmerged-branch-file-access` — reading files from branches that are not on main.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectProteus | Issue #185 planning (consolidated / auto-generated follow-up) | verified-local — premise checks run live: `gh issue view 5` → OPEN; `gh pr view 173` → OPEN/unmerged; `git merge-base --is-ancestor` proved #5 real-test commits not on main (on `*-auto-impl`); `git show HEAD:justfile` + `just --list` showed no `test-all`; `git ls-files tests/` → only `dispatch-apply.test.sh`; `gh pr list` surfaced overlapping open PR #187. The resulting plan is unexecuted (no commit, no CI). |
| HomericIntelligence/Odysseus | Issue #319 planning ("revert `required_approving_review_count` 0→1 regression" follow-up) — the mirror case | verified-local — on-disk + on-HEAD state and git history directly inspected: `jq` showed all four files already `1` on disk; `git show HEAD:<path>` confirmed `1` on HEAD; `git log -S'..._count": 0' -- configs/github/` + `git show d34e291 --stat` found the prior remediating commit (PR #308, `Closes #178`) that reverted all four AND added the jq guard; `git diff HEAD` empty. CI gating of the jq guard was NOT observed running. Correct plan: verify-and-close, zero source edits. |
