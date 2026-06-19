---
name: planning-verify-live-state-before-assuming-work-remains
description: "When an issue describes work to be done (a migration, rename, or config change), verify the LIVE external state FIRST with gh/grep before planning any edits — the work may already be complete, making the correct plan a verify-and-close plan with ZERO source edits. An issue body is a snapshot from when it was filed and drifts: the default branch, CI config, open-PR bases, and linked-issue states all change underneath it. Includes the gh-API gotcha that `gh api repos/ORG/REPO/branches/master` RETURNS the default branch via HTTP redirect for a MISSING branch (false positive that master exists) — use the `git/refs/heads` listing instead. Also covers the static-analysis-only planning trap: when fixing a 'one-line' GitHub ruleset enforcement/required-check issue purely by reading config files (e.g. flipping `enforcement: evaluate` → `active`), you have NOT confirmed what is actually applied to the live org/repo, whether required-status-check contexts are reported as bare job names vs workflow-prefixed, or whether deletes/refactors are reversible — all of which can cause a bootstrap deadlock (PRs BLOCKED with 0 failing checks). Use when: (1) an issue/ticket describes a migration or change that may already be done, (2) planning work whose premise depends on live external state (default branch, CI config, issue status), (3) before recommending edits driven by an issue's stated assumptions, (4) before writing any 'Files to Modify' that exist only because the issue said so, (5) planning a ruleset enforcement flip or required-status-check context change from static file inspection without querying `gh api .../rulesets`, (6) a 'one-line' config fix that also deletes files / removes flags / refactors scripts (scope-creep + irreversible-delete risk)."
category: tooling
date: 2026-06-19
version: "1.2.0"
user-invocable: false
verification: verified-local
history: planning-verify-live-state-before-assuming-work-remains.history
tags: []
---

# Planning: Verify Live State Before Assuming Work Remains

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | When planning an issue that asserts work needs doing (e.g. "5 repos still on master, CI broken"), determine whether that work is already complete BEFORE writing edits — and if it is, produce a verify-and-close plan with zero source changes instead of a rename plan |
| **Outcome** | Successful: live-state verification of GitHub issue #24 ("Standardize default branch name across ecosystem") revealed the migration was ALREADY COMPLETE — all 15 repos default to `main`, no `master` refs exist, all workflows target `main`, all open PRs are based on `main`, all 4 linked tracking issues were already CLOSED. The plan correctly became "verify-and-close, zero source edits." |
| **Verification** | verified-local for the core branch-migration workflow (the gh/grep commands below were run this session and produced the cited outputs; not validated in ProjectMnemosyne CI). The v1.2.0 issue #177 ruleset-enforcement subsection is UNVERIFIED — a static-only plan, never executed; see the warning in that subsection. |
| **History** | [changelog](./planning-verify-live-state-before-assuming-work-remains.history) |

## When to Use

- An issue asserts a current state (e.g. "5 repos use master") that you can check directly before planning edits.
- The task premise depends on live GitHub/CI state that drifts after the issue was filed (default branch, CI config, open-PR bases, linked-issue status).
- Before writing any "Files to Modify" list whose entries exist only because the issue said the work was undone.
- Planning a migration, rename, or config-standardization issue that may already have shipped.
- Planning a GitHub ruleset enforcement flip (`evaluate`→`active`) or a required-status-check
  context change from STATIC config inspection alone — without ever running `gh api .../rulesets`
  to read what is actually applied, or confirming the exact context-string format GitHub reports.
- A nominally "one-line" config fix whose plan also DELETES files, removes a flag/branch in a
  script, or rewrites a runbook — weigh scope-creep and irreversible-delete/rollback risk before
  bundling them with the minimal change.

## Verified Workflow

The premise of an issue is a snapshot from filing time. Before planning any edit, run the
checks below to establish the LIVE state. If they show the work is done, the deliverable is a
verify-and-close plan (confirm state, close the issue) — not a rename/edit plan.

### Quick Reference

```bash
ORG=HomericIntelligence
REPO=ProjectMnemosyne

# 1. Authoritative default branch (NOT the issue's table)
gh repo view "$ORG/$REPO" --json defaultBranchRef --jq .defaultBranchRef.name

# 2. Prove a branch does NOT exist — list refs, do NOT GET branches/<name>
gh api "repos/$ORG/$REPO/git/refs/heads" --jq '.[].ref'
#   GOTCHA: `gh api repos/$ORG/$REPO/branches/master` returns the DEFAULT
#   branch via HTTP redirect for a missing branch → FALSE POSITIVE.
#   FAIL-LOUD form (clean boolean, emits nothing on API failure):
gh api "repos/$ORG/$REPO/git/refs/heads" --jq 'any(.ref=="refs/heads/master")'
#   Do NOT use `... 2>&1 | grep 'Not Found' || echo 'Not Found'` — it masks
#   auth errors / rate-limits as a false-green "Not Found".

# 3. Workflow triggers still reference the old branch?
grep -rEn "branches:\s*\[?\s*[\"']?(main|master)" .github/workflows/*.yml

# 4. Any open PR based on something other than main?
gh pr list --repo "$ORG/$REPO" --state open --json baseRefName \
  --jq '[.[]|select(.baseRefName!="main")]|length'

# 5. Linked tracking issue states
gh issue view N --repo "$ORG/$REPO" --json state --jq .state
```

### Detailed Steps

1. **Confirm the real default branch** with `defaultBranchRef` per repo. Treat this as authoritative
   over any table in the issue body. If it already reads `main`, the rename premise is void for that repo.
2. **Prove the old branch is absent** by listing refs (`git/refs/heads`) and checking that
   `refs/heads/master` is NOT in the output. Do NOT probe `branches/master` — see the Failed Attempts
   table; it redirects to the default branch and falsely implies `master` exists.
3. **Check CI triggers** by grepping `.github/workflows/*.yml` for `branches:` entries. Confirm they
   target `main` and not `master`. A "CI broken because workflows point at master" claim is verifiable here.
4. **Semantically classify each `master` literal before editing.** Not every `master` is a branch ref.
   Distinguish: branch refs (rename candidates) vs. `no-commit-to-branch --branch master` pre-commit
   guards (intentional — leaving `master` here is correct) vs. third-party action pins like
   `action@master` (a version ref to someone else's repo — must NOT be rewritten). Blind find/replace
   corrupts the latter two.
5. **Check open-PR bases** — if zero PRs target anything but `main`, there is no in-flight work
   depending on the old branch.
6. **Check linked/tracking issue states** — if the tracking issues are already CLOSED, the work was
   already accepted and closed out; do not re-plan it.
7. **Run every verification command and paste its REAL output as the expected value.** Never
   annotate a check with a guessed count or boolean — a wrong expected value makes a reviewer
   running the exact command conclude the check FAILED (this round: an asserted grep count of `4`
   was actually `3`; a trailing `# master` comment is not matched by `@master|--branch, master`).
8. **Verify "already-applied" claims by a direct live read, not inference.** A justfile + config
   file is intent, not state. Read the live API (`gh api repos/$ORG/$REPO/rulesets`) — see Results.
9. **Scope the verification loop to the whole population, not just named entities.** If the issue
   is ecosystem-wide ("all repos"), enumerate the full set yourself and loop every check over all
   of it — see the companion skill
   `planning-verify-full-population-not-just-named-entities`. The unnamed members are where residue
   hides (this round: `ProjectKeystone`, not one of the 5 named repos, held the orphan `master`).
10. **Decide the deliverable from the evidence.** If every check shows the work is complete, write a
    forward-looking verify-and-close plan (state the verification commands and their outputs, then the
    single close step) with an explicit "zero source edits" note — not a rename plan, and not a bare
    retrospective status note.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the issue's repo table | Took the issue's "these 5 repos use master" table at face value and started listing rename edits | The table was a stale snapshot; all repos had already migrated to `main` — the rename would have been a no-op against current state | Always verify `defaultBranchRef` live per repo before planning any rename |
| Probe `branches/master` to test existence | `gh api repos/ORG/REPO/branches/master` to check whether a `master` branch still exists | For a missing branch GitHub HTTP-redirects to the default branch and returns 200 with the default branch's data → false positive that `master` exists | Use `gh api repos/ORG/REPO/git/refs/heads --jq '.[].ref'` and check for `refs/heads/master`; absence proves non-existence |
| Blind find/replace master→main | Considered a tree-wide literal `master`→`main` substitution to "do the migration" | Corrupts non-branch uses: `no-commit-to-branch --branch master` guards and third-party `action@master` pins are not branch refs of this repo | Semantically classify every `master` literal; only rewrite actual local branch refs |
| Verify only the 5 named repos | Listed refs for only the 5 repos the issue named as "on master," then declared the ecosystem migration complete | The issue was ecosystem-wide; a 5-of-15 scan structurally cannot find residue in the unnamed 10. `ProjectKeystone` (NOT one of the 5; already defaulting to `main`) still held a stale unprotected orphan `refs/heads/master` — the one real residue | Scope the loop to the full population; see companion skill `planning-verify-full-population-not-just-named-entities` |
| Assert grep count without running it | Annotated a verification step "this grep returns count `4`" from eyeballing the tree | Running it returned `3` — the 4th `master` was a trailing `# master` comment the `@master\|--branch, master` regex cannot match. A reviewer running the command would conclude the check FAILED | Run the verification command and paste its real output as the expected value |
| Fail-green existence check | `gh api .../branches/master 2>&1 \| grep -o 'Not Found' \|\| echo 'Not Found'` to test absence | Masks auth errors / rate-limits / any non-"Not Found" failure as a false-green "Not Found" | Use `gh api .../git/refs/heads --jq 'any(.ref=="refs/heads/master")'` — a clean boolean that emits nothing on API failure |
| Infer ruleset "applied" from config | Claimed branch protection active from `justfile` + `configs/github/org-ruleset.json` | Reviewer rejected inference-as-evidence; config is intent, not live state | Verify already-applied via direct read `gh api repos/ORG/REPO/rulesets` (org-level 404s on FREE plan; repo-level authoritative) |
| (#177, UNVERIFIED) Infer "canonical files never enforce" from script defaults | Read `apply-repo-rulesets.sh:32` + `justfile:667` and concluded the apply path defaults to the evaluate-mode JSON, so the canonical files never enforce in practice | The plan was static-only — no `gh api .../rulesets` run against the live org. What is *applied* may differ from what the script *would* apply | The premise "the canonical files never enforce" must be confirmed by reading the LIVE applied ruleset (`gh api`), not by reading the apply script. Default-in-code ≠ state-in-org |
| (#177, UNVERIFIED) Assume required-check contexts are BARE job names | Planned the org ruleset to use bare `lint` + `integration_id: 15368`, "fixing" the org file's workflow-prefixed `Required Checks / lint` form, citing canonical-checks.md "Verified 2026-04-26" | Never queried how GitHub reports the contexts for THIS org/repo. Org vs repo rulesets can behave differently; the prefixed form may have been deliberate. Wrong guess ⇒ bootstrap deadlock: PRs BLOCKED with 0 failing checks | Confirm the exact context string GitHub expects by reading the live applied ruleset and/or a recent merged PR's check names — do not trust a doc's "verified on date" note or assume org==repo format |
| (#177, UNVERIFIED) Drop the org's `typecheck` context as "safe" | Removed `typecheck` because it's absent from the 8-check canonical list and the repo file | No check that some workflow emits or depends on `typecheck`; absence from a doc list ≠ absence from CI | Before dropping a required context, grep the actual workflows for a job/check that produces it; a context no live workflow emits, if kept under `active`, deadlocks every PR |
| (#177, UNVERIFIED) Silently reconcile 9-vs-8 context count | Issue said "9 required status check contexts"; canonical list + repo file had 8; plan quietly used 8 | Never established which count is authoritative; a silent reconcile hides a real discrepancy from the reviewer | When the issue's stated count disagrees with the files, surface the mismatch explicitly and verify the live ruleset's count rather than picking one silently |
| (#177, UNVERIFIED) Delete `-active.json` + the `--active` flag as cleanup | Plan removed `org-ruleset-active.json`/`repo-ruleset-active.json` and the `--active`/`ENFORCEMENT` branching, verified "byte-identical except line 4" by reading the 4 files | Files can drift; the delete is irreversible and removes the evaluate-mode shadow-testing path (changes the rollback story). Only grepped within Odysseus — never across submodules/external automation for consumers | Before deleting a config or removing a flag, grep ALL consumers (submodules + external CI/automation), not just the current repo; and weigh whether the deleted path is a rollback/shadow-test capability worth keeping. Scope-creep on a "one-line" issue: a reviewer may prefer the minimal line-4-only change |
| (#177, UNVERIFIED) Trust `integration_id: 15368` = GitHub Actions app | Carried `integration_id: 15368` from the existing repo file + team KB as the GitHub Actions app id | Taken from a file + KB, not independently confirmed against the live app installation | Confirm an app/integration id against the live install (`gh api .../installations` or the applied ruleset) before relying on it in an enforcing ruleset |

## Results & Parameters

**Verified outcome for issue #24 (live state, 2026-06-19):**
- All 15 repos: `defaultBranchRef.name == main`.
- No `refs/heads/master` in any of the 5 named repos' ref listings.
- All `.github/workflows/*.yml` triggers target `main`.
- Open PRs based on non-`main`: `0`.
- All 4 linked tracking issues: `state == CLOSED`.
- Correct plan: verify-and-close, **zero source edits**.

**Org plan constraint:** `HomericIntelligence` is on the **FREE** plan, so
`gh api orgs/ORG/rulesets` returns 404/403. Use **repo-level** rulesets
(`gh api repos/ORG/REPO/rulesets`) instead of org-level endpoints.

**Ruleset confirmed by DIRECT live read (2026-06-19), replacing the prior inference:**

```json
{ "name": "homeric-main-baseline", "target": "branch", "enforcement": "active", "id": 15556483 }
```

**Population-scope correction (re-plan after NOGO):** the migration was NOT fully complete.
Extending the ref-listing loop from the 5 named repos to all 15 surfaced one residue:
- `ProjectKeystone` — default already `main` (hence NOT in the named 5), but still carrying a stale
  `refs/heads/master`: `protected == false`, `gh pr list --base master ... --jq length == 0`,
  `compare/main...master` → "No common ancestor" (orphan). Safe to delete via
  `gh api -X DELETE repos/HomericIntelligence/ProjectKeystone/git/refs/heads/master`.

**Companion skill:** `planning-verify-full-population-not-just-named-entities` — scope the
verification loop to the whole population when an issue is ecosystem-wide.

**Residual notes:**
- The closing step (closing issue #24) was specified in the plan but NOT executed by the planner —
  it remains an action for the implementer.

### Worked example: issue #177 ruleset enforcement flip (UNVERIFIED, static-only plan)

> **Warning:** This subsection documents a PLANNING-PROCESS learning from a plan that was authored
> by static file inspection only and never executed or CI-validated. Treat each item below as an
> unverified assumption / reviewer-risk, not a confirmed fact. The live org/repo ruleset state was
> NEVER queried with `gh api` during planning.

**Plan summary (Odysseus meta-repo, HomericIntelligence):** flip
`configs/github/org-ruleset.json` and `configs/github/repo-ruleset.json` from
`"enforcement": "evaluate"` (logs hits, does not block) to `"active"`; delete duplicate
`-active.json` files plus the `--active`/`ENFORCEMENT` branching in `apply-repo-rulesets.sh`;
normalize org-ruleset contexts to bare-name + `integration_id: 15368`; drop a stale `typecheck`
context; update the justfile and rollout runbook; add a documented pre-flight check.

**Highest-risk assumption (bootstrap deadlock):** flipping to `active` with any required-status-check
context that no workflow emits on `main` — or in a context-string format GitHub does not report —
BLOCKS every PR with 0 failing checks. The required-check format (bare `lint` vs prefixed
`Required Checks / lint`) was assumed bare from a doc + KB, never confirmed against the live
applied ruleset. The repo file used bare+`integration_id`; the org file used prefixed — the
divergence might be intentional, not a bug.

**External sources relied on WITHOUT direct verification:**
- Live GitHub org/repo ruleset state — never queried via `gh api .../rulesets` (entire plan static).
- `integration_id: 15368` = GitHub Actions app id — taken from the repo file + team KB.
- canonical-checks.md's "Verified 2026-04-26: GitHub reports bare names" — trusted as-is.
- Whether any consumer (other CI workflow, submodule, external automation) references the
  `-active.json` files before deleting them — only grepped within Odysseus.
- The 9-vs-8 required-context count: issue says 9, canonical list + repo file have 8; reconciled
  to 8 without confirming which is authoritative.

**Reviewer focus / risks (what to weigh, beyond the assumptions):**
- *Enforcement-by-runbook vs by-code:* the pre-flight (confirm every active context is emitted by a
  live `main` workflow) is documented in the runbook but NOT enforced in code/CI — is a runbook step
  sufficient guard against the bootstrap deadlock?
- *Irreversible deletes:* removing `-active.json` + the `--active` flag eliminates the evaluate-mode
  shadow-testing path and changes the rollback story.
- *Scope creep:* the issue is narrowly "flip enforcement to active"; the plan also refactors scripts,
  edits the justfile, deletes files, and rewrites a runbook. A reviewer may prefer the minimal
  line-4-only change.

**Corrective action the plan SHOULD have taken (apply this skill):** before flipping to `active`,
run `gh api repos/HomericIntelligence/<repo>/rulesets` (and `/rulesets/<id>`) to read the live
enforcement state and the exact `required_status_checks` context strings + integration ids; grep
the live `.github/workflows/*` for every context to be made required; surface the 9-vs-8 mismatch
explicitly; and grep all submodules/external automation for `-active.json` consumers before deleting.
