---
name: planning-verify-issue-claims-and-required-check-gating
description: "Before planning a change to CI gating, distinguish a job that RUNS from a job that GATES the PR — a test 'wired into CI' is not actually enforced unless its job is a REQUIRED status-check context in the branch ruleset. Confirm the gate is real with `gh api repos/<org>/<repo>/rulesets` (and per-id `required_status_checks[].context`); a job absent from that list runs but does NOT block merges. SEPARATELY, treat an issue's own factual claims — WHICH job a step lives in, WHAT a test covers — as CLAIMS to grep-verify against the codebase, because they drift from reality. Worked example (ProjectProteus #184, follow-up from #97): the issue claimed a host-contract test was 'wired into CI' as done, but it ran in a standalone `dispatch-contract-test` job that was NOT in the required list (`lint, unit-tests, integration-tests, security/dependency-scan, security/secrets-scan, build, schema-validation, deps/version-sync`) — running, not gating. The issue also said the step lived in `integration-tests` (naming drift — it was a separate job) and that the test covers 'RFC 1123 format + allowlist validation' (a `grep -rniE 'rfc.?1123|allowlist|hostname'` over scripts/ .github/ docs/ returned NOTHING — no such logic exists; the test only checks host-presence/fail-closed). The fix folds the test into the already-required `integration-tests` job so no destructive ruleset PUT is needed. Use when: (1) an issue claims a fix is 'already done' / 'wired into CI' — confirm the wiring is ENFORCED (required context), not merely running; (2) an issue names WHERE a change lives (a job) or WHAT a test covers — verify against the actual files first; (3) planning any change to required CI checks / branch protection. Cross-link: gha-required-checks-branch-protection (the YAML/aggregator fix mechanics), verify-issue-premise-against-code-before-planning (grep-the-premise discipline)."
category: ci-cd
date: 2026-06-20
version: "1.1.0"
history: planning-verify-issue-claims-and-required-check-gating.history
user-invocable: false
verification: verified-local
tags:
  - planning
  - verification
  - required-status-checks
  - branch-protection
  - issue-claims
  - evidence-grounded
  - ci-cd
  - dispatch-apply
  - runs-vs-gates
  - rulesets
  - grep-the-claim
  - naming-drift
  - working-tree-clean
  - guard-dependency-floor
  - scope-discipline
---

# Verify Issue Claims and the Reality of CI Gating Before Planning

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Capture two planning-time verification disciplines that must run BEFORE planning a CI-gating change: (a) a CI job that RUNS is not branch-protection-GATED unless it is a required status-check context — confirm via `gh api .../rulesets`, not by reading the workflow YAML; and (b) verify an issue's OWN factual claims (which job a step lives in, what a test covers) against the codebase with grep, because they drift from reality |
| **Outcome** | Plan written for ProjectProteus #184 (follow-up from #97). The issue claimed a host-contract test was "wired into CI" as done, but it ran in a standalone `dispatch-contract-test` job NOT present in the required ruleset contexts — running, not gating. The issue's job-name claim (`integration-tests`) and coverage claim ("RFC 1123 + allowlist") were both grep-falsified. The chosen fix folds the test into the already-required `integration-tests` job, avoiding a destructive ruleset PUT |
| **Verification** | **verified-local** — the `gh api`/grep/test commands were executed against the live repo (HomericIntelligence/ProjectProteus, ruleset `homeric-main-baseline`) and confirmed the gating reality and the falsified claims; but the PLAN's edits were NOT merged or CI-confirmed. Treat the plan's edits as a hypothesis |

This skill is the **planning/verification** complement to two related skills:

- `gha-required-checks-branch-protection` — that skill is about *fixing* the
  required-checks / aggregator / `workflow_call` YAML wiring (skip-vs-success semantics,
  GET-before-PUT, the RESULTS-loop aggregator). THIS skill is the upstream **planning
  discipline**: before you touch any of that, confirm the gate you think exists is real.
- `verify-issue-premise-against-code-before-planning` — grep the issue's premise tokens to
  confirm WHICH file/job matches. THIS skill extends that to two further claim types specific
  to CI work: the *gating-reality* claim ("it's enforced") and the *coverage* claim ("the test
  checks X").

> **Warning:** The plan's edits were produced in a planning session and not merged or CI-run.
> The *verification commands* below were executed live (hence `verified-local`); the *fix* is a
> hypothesis until CI confirms it.

## When to Use

- An issue claims a fix is **"already done"** / **"wired into CI"** — confirm the wiring is
  actually *enforced* (a required status-check context), not merely running in some job.
- An issue describes **WHERE** a change lives (a named job) or **WHAT** a test covers — verify
  both against the actual files before trusting them; CI issues drift, and job names drift.
- You are **planning any change to required CI checks / branch protection** and need to know the
  current real set of gated contexts before proposing an edit.

## Verified Workflow

> **Warning:** The numbered discipline below was the workflow that worked at planning time and
> its commands were run live against the repo (`verified-local`). The downstream *fix* (folding
> the test into `integration-tests`) was NOT executed end-to-end. The heading is "Verified
> Workflow" to satisfy the marketplace validator.

### Quick Reference

```bash
# Is a CI job actually a REQUIRED check, or just running?
gh api repos/<org>/<repo>/rulesets --jq '.[].id' | while read id; do
  gh api repos/<org>/<repo>/rulesets/$id \
    --jq '.rules[]?|select(.type=="required_status_checks")|.parameters.required_status_checks[].context'
done
# A job NOT printed here runs but does NOT block PRs. "Runs in CI" != "gates the PR".

# Verify an issue's factual claim about test coverage before trusting it:
grep -rniE "<claimed-validation-keywords>" scripts/ .github/ docs/
# e.g. grep -rniE "rfc.?1123|allowlist|hostname" scripts/ .github/ docs/
# Empty result => the claimed logic does NOT exist; do not plan around it.

# After running the test locally, assert the working tree stayed clean
# (a test that leaks files into CWD is not hermetic):
git status --porcelain   # must be empty
```

### Detailed Steps — the discipline that worked

1. **Confirm the test/job exists AND runs.** Read the workflow file; run the test locally. This
   establishes "running" — necessary but NOT sufficient for "gated."

2. **Confirm the gate is REAL via the rulesets API, not the YAML.** Enumerate ruleset IDs with
   `gh api repos/<org>/<repo>/rulesets --jq '.[].id'`, then for each id pull the
   `required_status_checks[].context` list. A job absent from that list runs but does NOT block
   a PR. In #184 the test ran in job `dispatch-contract-test`, which was NOT in the required
   list (`lint, unit-tests, integration-tests, security/dependency-scan, security/secrets-scan,
   build, schema-validation, deps/version-sync`). Because `integration-tests` IS already
   required, folding the test into that job makes it gating with NO destructive ruleset `PUT`.

3. **Verify the issue's factual claims with grep — do not trust prose.**
   - The issue said the test covers "RFC 1123 format + allowlist validation." A
     `grep -rniE "rfc.?1123|allowlist|hostname"` over `scripts/ .github/ docs/` returned
     NOTHING — no such logic exists. The test actually checks host-presence / fail-closed only.
   - The issue said the step lives in `integration-tests`; it was actually a SEPARATE
     `dispatch-contract-test` job. Naming drift. Read the workflow file; don't trust the
     issue's location claim.

4. **Assert the test is hermetic** — exit code 0 is not enough. The test leaked an `err.txt`
   into CWD (no cleanup), dirtying the working tree; only `git status --porcelain` after the run
   caught it. Add a working-tree-clean assertion to the verification, not just an exit-code
   check.

5. **Disclose the deviation between issue text and reality in the plan/PR body.** Cross-reference
   `gha-required-checks-branch-protection` §I (requirements-deviation disclosure): when the
   issue's claims don't match the tree, say so explicitly with grep/`gh api` evidence rather
   than silently re-targeting.

### Keep regression guards at the host's dependency floor

When you add a structural guard to an EXISTING test, match the host's toolchain — do not import
new dependencies. A shell test gets a bash/grep/awk guard, NOT an `import yaml` block: the shell
test also runs locally/standalone where pyyaml may be absent, so a hidden python+pyyaml
dependency is a Principle-of-Least-Astonishment violation. For a 2-space-indented GitHub Actions
job, extract just that job's block (no YAML parser needed) and `grep` inside it:

```bash
awk '/^  JOBNAME:/{grab=1;print;next} grab&&/^  [A-Za-z0-9_-]+:/{exit} grab{print}' "$wf" \
  | grep -q "<expected-line>"
```

Likewise, do NOT bundle opportunistic cleanups into a scoped fix. If you do touch something
adjacent, verify the rationale against the actual enforcement code: before citing a CI guard as
justification, READ the guard's literal regex (e.g. `_required.yml:85,100`) — a guard that greps
for `\|\| true` and `continue-on-error: true` does NOT match `&& exit 0`, so "same class of
suppression" is factually wrong and a reviewer will flag it (P2/YAGNI).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Trust the issue's "wired into CI" as done | Issue #184 claimed commit 6a851c5 finished the work | The test ran in `dispatch-contract-test`, which is NOT a required ruleset context → it can fail without blocking a PR | "Runs in CI" ≠ "gates the PR"; confirm via `gh api .../rulesets` |
| Trust the issue's description of the job name | Issue said the step was added to `integration-tests` | It was a separate standalone job (`dispatch-contract-test`); naming drift | Read the workflow file; don't trust the issue's location claim |
| Trust the issue's description of test coverage | Issue said the test covers "RFC 1123 + allowlist validation" | No such logic exists anywhere (`grep -rniE 'rfc.?1123|allowlist|hostname'` returned nothing); the test only checks host-presence / fail-closed | grep the codebase to verify factual claims before planning around them |
| Assume the test was hermetic | Ran the test and checked only the exit code | The test leaked `err.txt` into CWD (no cleanup), dirtying the working tree; only `git status --porcelain` after the run caught it | Add a working-tree-clean assertion to the verification, not just an exit-code check |
| Rode an opportunistic out-of-scope edit into a focused plan | Plan removed a trailing `&& exit 0` from `_required.yml:150` as "same class as `\|\| true`" | The repo's `forbid-suppressions` CI job greps for `\|\| true` and `continue-on-error: true` ONLY — it does NOT match `&& exit 0`, so the justification was factually wrong; and the `exit 0` was inert as the step's last command. Reviewer flagged P2/YAGNI | Before citing a CI guard as justification, READ the guard's actual regex (`_required.yml:85,100`). Don't bundle opportunistic cleanups into a scoped fix; if you do, verify the rationale against the actual enforcement code |
| Added a regression guard that silently imported a new dependency | Appended a `python3 -c "import yaml"` block to a pure-shell test to parse the workflow YAML | The shell test also runs locally/standalone where pyyaml may be absent; a shell test gaining a hidden python+pyyaml dependency is a POLA violation (reviewer P7) | A regression guard should use only tools its host already depends on. Rewrite YAML structural checks as pure-bash `awk`/`grep` (extract a job block with `awk '/^  job:/{g=1}...'` then `grep`) when the test is shell |

## Results & Parameters

- **Real repo:** HomericIntelligence/ProjectProteus, ruleset `homeric-main-baseline`.
- **Required contexts at plan time:** `lint, unit-tests, integration-tests,
  security/dependency-scan, security/secrets-scan, build, schema-validation, deps/version-sync`.
  `dispatch-contract-test` was NOT among them.
- **Chosen fix:** fold the host-contract test into the already-required `integration-tests`
  job → it becomes gating with no destructive ruleset `PUT`.
- **Reviewer-risk note (highest-uncertainty residual assumption):** the structural guard
  (Failed-Attempts Case 4 territory) parses `_required.yml` and asserts the test runs in
  `integration-tests` AND that `dispatch-contract-test` is gone — but it does NOT assert
  `integration-tests` is itself a required context (that lives in the ruleset API, not the
  YAML). If someone later drops `integration-tests` from the ruleset, the guard still passes.
  Note this gap explicitly in the plan/PR. This residual gap RECURS: a structural unit/shell
  guard that asserts a test is wired into job X cannot detect X later being dropped from the
  branch ruleset (that membership lives in the rulesets API). Correct handling = assert it at
  runtime in the verification command via `gh api .../rulesets`, and deliberately DO NOT couple
  a unit/shell test to a live API call — disclose the residual gap explicitly in the PR body
  instead.
- **`verified-local` justification:** the `gh api` / grep / test commands were executed against
  the live repo and confirmed both the gating reality and the falsified claims; the plan's edits
  are NOT yet merged or CI-confirmed.

### Related skills

- `gha-required-checks-branch-protection` — the YAML/aggregator fix mechanics (skip-vs-success,
  GET-before-PUT, RESULTS-loop). THIS skill is the planning-time precondition: confirm the gate
  is real before fixing its wiring.
- `verify-issue-premise-against-code-before-planning` — grep the issue's premise tokens to
  disambiguate WHICH file/job a premise matches. THIS skill adds the gating-reality and
  coverage-claim verification specific to CI work.

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectProteus | Issue #184 planning (follow-up from #97) | verified-local; ruleset `homeric-main-baseline` checked via `gh api`, claims grep-verified (RFC 1123 / allowlist coverage falsified, `integration-tests` job-name claim falsified), test hermeticity caught via `git status --porcelain`. Plan edits not merged/CI-run. |
| ProjectProteus | Issue #184 R1 (NOGO→revision) | verified-local; `forbid-suppressions` regex read live (`_required.yml:85,100`) to confirm it matches `\|\| true`/`continue-on-error: true` but NOT `&& exit 0`; regression guard rewritten from a `python3 import yaml` block to a pure-bash `awk`+`grep` job-block check. Plan edits not merged/CI-run. |
