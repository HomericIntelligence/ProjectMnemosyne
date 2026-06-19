---
name: planning-verify-live-state-before-assuming-work-remains
description: "When an issue describes work to be done (a migration, rename, or config change), verify the LIVE external state FIRST with gh/grep before planning any edits — the work may already be complete, OR the deployed state may be the OPPOSITE of what the issue claims, making the correct fix a drift-closure rather than a from-scratch change. An issue body is a snapshot from when it was filed and drifts: the default branch, CI config, open-PR bases, linked-issue states, AND the live applied ruleset all change underneath it. Includes the gh-API gotcha that `gh api repos/ORG/REPO/branches/master` RETURNS the default branch via HTTP redirect for a MISSING branch (false positive that master exists) — use the `git/refs/heads` listing instead. Also covers the static-analysis-only planning trap: fixing a 'one-line' GitHub ruleset enforcement/required-check issue purely by reading config files (e.g. flipping `enforcement: evaluate` → `active`) without confirming what is actually applied to the live org/repo — a single `gh api .../rulesets` query can confirm the live ruleset is ALREADY active (so re-applying the stale on-disk evaluate file via an idempotent PUT would DOWNGRADE it), prove the exact required-context format (bare names + integration_id), settle a docs 9-vs-8 count dispute, and confirm the org endpoint 404s on FREE plan — resolving several unverified assumptions at once. Use when: (1) an issue/ticket describes a migration or change that may already be done, (2) planning work whose premise depends on live external state (default branch, CI config, issue status, applied ruleset), (3) before recommending edits driven by an issue's stated assumptions, (4) before writing any 'Files to Modify' that exist only because the issue said so, (5) planning a ruleset enforcement flip or required-status-check context change from static file inspection without querying `gh api .../rulesets`, (6) a 'one-line' config fix that also deletes files / removes flags / refactors scripts (scope-creep + irreversible-delete + rollback-regression risk), (7) two in-repo docs disagree on a number — resolve it against the deployed system, not either doc."
category: tooling
date: 2026-06-19
version: "1.3.0"
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
| **Verification** | verified-local for the core branch-migration workflow (the gh/grep commands below were run this session and produced the cited outputs; not validated in ProjectMnemosyne CI). The issue #177 ruleset-enforcement findings are now VERIFIED-AGAINST-LIVE (v1.3.0): the re-plan ran `gh api .../rulesets` and confirmed the live ruleset (id 15556483) is already `active`, has exactly 8 bare-name contexts + `integration_id: 15368`, and the org endpoint 404s — replacing the v1.2.0 "unverified assumption" framing for those points. The #177 *implementation plan itself* remains proposed (NOT executed/merged); only the live-state findings are confirmed. |
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
- Fixing a config that is *applied* to an external system (ruleset, branch protection, deployed
  manifest): the on-disk file is intent, the live system is state, and the drift can be the OPPOSITE
  of what the issue claims — re-applying a stale file can REGRESS the live system. Read live first.
- Two in-repo docs disagree on a number (e.g. required-check count): resolve it against the deployed
  system (the live ruleset's `required_status_checks` length), then fix the stale doc — don't pick a doc.

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
11. **Assume the deployed state may be the OPPOSITE of the issue's claim — not just "ahead" of it.**
    The drift is not always "work already done." For a config that is *applied* to an external system,
    the on-disk file is *intent* and the live system is *state*; they can diverge in the direction that
    inverts the fix. In #177 the issue said `repo-ruleset.json` was in `evaluate` mode (not enforcing),
    but `gh api .../rulesets` showed the LIVE ruleset (id 15556483) was already `active`. The on-disk
    file was the stale one. Because the apply path is an idempotent PUT-if-exists, naively re-applying
    the on-disk `evaluate` file would have DOWNGRADED the live `active` ruleset. Reframe the fix from
    "enable from scratch" to "close the drift" (make the on-disk file match the already-correct live
    state), and add a guard so re-apply cannot regress enforcement.
12. **Spend one live query to collapse several unverified assumptions at once.** The single
    `gh api repos/$ORG/$REPO/rulesets` the reviewer flagged as missing resolved THREE separate NOGO
    findings simultaneously in #177: (a) the bare-vs-prefixed required-check format dispute — the live
    ruleset proved bare names + `integration_id: 15368` are correct (no bootstrap deadlock); (b) the
    9-vs-8 required-context count dispute — the live ruleset has exactly 8 (the workflow's 9th job
    `forbid-suppressions` is deliberately non-required; docs saying "9" counted jobs, not contexts);
    (c) the org-endpoint availability — `gh api orgs/$ORG/rulesets` → 404/needs admin:org, so the
    `org-ruleset.json` file is non-functional on this plan and must not be cited as an activation path
    or used in a verification command. Run the cheap live query BEFORE writing the plan, not after a NOGO.
13. **Reconcile doc-vs-doc disagreements against the deployed system, not against either doc.** When
    two in-repo docs disagree on a number (#177: `canonical-checks.md` implied 8, the runbook said
    "9 jobs"), the live applied state is the tiebreaker. Read the live ruleset's `required_status_checks`
    length (8), then fix the stale doc wording — don't silently pick one doc.
14. **For a narrowly-scoped issue, prefer ADDITIVE changes and never remove an existing operational
    safety/rollback path as a side effect.** The first #177 plan bundled file deletions, script-branching
    removal, and a runbook rewrite into a one-line-fix issue — and REGRESSED the rollback path (it deleted
    the only evaluate-mode file, then told operators to "pass an evaluate copy" that no longer existed).
    The re-plan reverted to minimal additive scope: line-4 `evaluate`→`active` flips + one ADDITIVE
    evaluate-mode file + one ADDITIVE `--evaluate` flag + two doc wording fixes; it deleted nothing.
    Treat "cleanup of now-redundant files" as a separate issue.

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
| (#177, UNVERIFIED) Trust `integration_id: 15368` = GitHub Actions app | Carried `integration_id: 15368` from the existing repo file + team KB as the GitHub Actions app id | Taken from a file + KB, not independently confirmed against the live app installation | Confirm an app/integration id against the live install (`gh api .../installations` or the applied ruleset) before relying on it in an enforcing ruleset (re-plan: the live ruleset 15556483 confirmed bare names + `integration_id: 15368`) |
| (#177, re-plan) Trust the issue's stated state without querying live | Issue said `repo-ruleset.json` is in `evaluate` (not enforcing); first plan accepted that and planned to "enable" it | The LIVE ruleset (id 15556483) was already `active`; the on-disk file was the stale one. Because the apply path is an idempotent PUT-if-exists, re-applying the on-disk `evaluate` file would have DOWNGRADED live enforcement back to evaluate | Query the live applied state (`gh api .../rulesets`) before fixing an applied config; the file is intent, not state, and the drift can INVERT the fix (drift-closure, not enable-from-scratch) |
| (#177, re-plan) Static-only first plan | Authored the entire #177 plan by reading config files (`apply-repo-rulesets.sh`, the JSON files, the justfile, docs) with NO `gh api` query | Reviewer NOGO on 5 MAJOR findings (live enforcement state, bare-vs-prefixed contexts, 9-vs-8 count, org-endpoint availability, integration id) — every one "taken on faith" from static files | One cheap live query (`gh api .../rulesets`) the reviewer flagged as missing collapsed all of those at once; run it BEFORE writing the plan, not after a NOGO |
| (#177, re-plan) Bundle deletions/refactor into a one-line fix | First plan deleted `-active.json` files, removed the `--active`/`ENFORCEMENT` script branching, and rewrote the runbook for a "flip enforcement to active" issue | Scope creep on a narrow issue AND a rollback regression: it deleted the only evaluate-mode file, then instructed operators to "pass an evaluate copy" that no longer existed — removing the shadow-test/rollback path | Keep narrowly-scoped fixes additive; never remove an existing operational safety/rollback path as a side effect; file "cleanup of redundant files" as a separate issue. Re-plan: additive evaluate file + additive `--evaluate` flag, deleted nothing |

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

### Worked example: issue #177 ruleset enforcement flip (re-planned, live-verified)

> **Status:** This is a two-pass case. The FIRST plan was static-only (see the v1.2.0 warning,
> preserved in `.history`) and got a NOGO on 5 MAJOR findings. The SECOND plan (this round) re-grounded
> every flagged point with actual `gh api` queries. The live-state FINDINGS below are now confirmed
> (observed live this session); the implementation PLAN itself is still proposed — it was NOT executed
> or merged. So: findings = verified-against-live; plan = proposed.

**Live findings that replaced the v1.2.0 unverified assumptions (`gh api`, 2026-06-19):**
- **Live enforcement is the OPPOSITE of the issue's claim.** The issue said `repo-ruleset.json` is in
  `evaluate` (not enforcing). `gh api repos/HomericIntelligence/Odysseus/rulesets` showed the live
  ruleset **id 15556483** is already `"enforcement":"active"`. The on-disk file is the stale one →
  the fix is drift-closure, NOT enable-from-scratch. Naively re-applying the on-disk `evaluate` file
  via the idempotent PUT-if-exists apply path would have DOWNGRADED live enforcement.
- **Required-check format is bare names + `integration_id: 15368`** (confirmed on the live ruleset),
  so there is no bootstrap-deadlock risk from a prefixed/`Required Checks / lint` form. The earlier
  bare-vs-prefixed dispute is settled.
- **Exactly 8 required contexts on the live ruleset** — settling the 9-vs-8 dispute. The workflow's
  9th job, `forbid-suppressions`, is deliberately NON-required; docs that said "9" were counting jobs,
  not required contexts. Fix the stale doc wording to "8 required contexts."
- **Org endpoint is unavailable on this plan.** `gh api orgs/HomericIntelligence/rulesets` →
  404 / needs `admin:org`. So `org-ruleset.json` is non-functional here and must NOT be cited as an
  activation path or used in any verification command. Use repo-level rulesets only.

**Re-planned minimal scope (additive, deletes nothing):** line-4 `evaluate`→`active` flips on the
repo ruleset config; ONE additive evaluate-mode file (preserving the shadow-test/rollback path the
first plan would have destroyed); ONE additive `--evaluate` flag on the apply script; two doc wording
fixes (the 8-vs-9 count reconciliation). No file deletions, no `--active` flag removal, no runbook
rewrite — those are deferred as a separate cleanup issue.

**Why the re-plan worked (apply this skill):** the single `gh api .../rulesets` query the reviewer
flagged as missing collapsed five NOGO findings at once (live enforcement state, bare-vs-prefixed
contexts, 9-vs-8 count, org-endpoint availability, integration id). Run it BEFORE writing the plan.
The on-disk config is intent; the live ruleset is state; resolve doc-vs-doc disagreements against the
deployed system, not against either doc.
