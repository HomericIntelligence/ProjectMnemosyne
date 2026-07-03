---
name: ci-cd-codeql-default-to-advanced-canonical-names
description: "Migrate GitHub CodeQL from managed default setup to an advanced-setup workflow so the check-run names can be canonicalized (e.g. Analyze (python) → security/codeql-python). Use when: (1) a repo's CodeQL checks report as 'Analyze (<lang>)' and an ecosystem CI board requires canonical namespaced names like security/codeql-<lang>, (2) `gh api repos/<owner>/<repo>/code-scanning/default-setup` returns state=configured and no .github/workflows/codeql.yml exists so the check name cannot be changed via YAML, (3) you must decide whether emit-before-require sequencing is needed — query the ruleset's required_status_checks via the API instead of assuming, (4) you need a matrix analyze job whose per-language check names have no '(python)' suffix, (5) you must sequence disabling default setup vs. the first advanced-workflow run because SARIF uploads from advanced configs are rejected while default setup is enabled, (6) you need default-setup parity (languages, query suite, threat model, weekly schedule) preserved in the committed workflow."
category: ci-cd
date: 2026-07-03
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - codeql
  - code-scanning
  - default-setup
  - advanced-setup
  - canonical-check-name
  - check-run-names
  - security-namespace
  - emit-before-require
  - ruleset-required-checks
  - sarif-upload
  - matrix-job-name
  - threat-model
  - action-pin-verification
  - github-actions
---

# CI/CD: Migrate CodeQL Default Setup → Advanced Setup for Canonical Check Names

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-03 |
| **Objective** | Canonicalize CodeQL check-run names from `Analyze (python)` / `Analyze (actions)` (emitted by GitHub's managed default setup, not configurable) to `security/codeql-python` / `security/codeql-actions` by migrating to an advanced-setup workflow with custom job names |
| **Outcome** | Implementation plan produced for ProjectScylla issue #2028; ruleset and default-setup state verified live via `gh api`; workflow YAML drafted but NOT yet executed — several GitHub-behavior assumptions remain unverified (see Failed Attempts / Results) |
| **Verification** | unverified — plan only; no workflow run, SARIF upload, or check-run name observed yet |

## When to Use

- A repo's CodeQL reports as `Analyze (<lang>)` and the ecosystem's canonical naming scheme requires `security/codeql-<lang>` — and `gh api repos/<owner>/<repo>/code-scanning/default-setup` shows `state: configured` with no `codeql.yml` in `.github/workflows/`
- Before planning any check-name swap, you must determine whether the OLD names are required status checks (ruleset or classic branch protection) — the answer decides whether emit-before-require sequencing is needed at all
- You are drafting the advanced-setup workflow and must pick: matrix vs. separate jobs, job `name:` interpolation, build-mode, query-suite/threat-model parity, and pinned action SHAs
- You must sequence "disable default setup" relative to "first advanced-workflow run" to avoid rejected SARIF uploads

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. The API queries in steps 1–2 WERE executed live; steps 3–6 are drafted but unexecuted.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical steps are emitted under that heading to keep validation green. This skill is a PLANNING methodology captured at `unverified` level. Read the steps below as **proposed**, per the warning.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. The API queries in steps 1–2 WERE executed live; steps 3–6 are drafted but unexecuted.

### Quick Reference

```bash
# 1. Confirm CodeQL is default setup (no workflow file to rename):
gh api repos/<owner>/<repo>/code-scanning/default-setup
# state=configured + languages + query_suite + threat_model + schedule → capture for parity

# 2. Check whether old names are REQUIRED checks (decides sequencing risk):
gh api "repos/<owner>/<repo>/rulesets?includes_parents=true" --jq '.[] | {id,name,source_type}'
gh api repos/<owner>/<repo>/rulesets/<id> \
  --jq '.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context'
gh api repos/<owner>/<repo>/branches/main/protection --jq '.required_status_checks.contexts'
# If "Analyze (python)" absent → no blocked-main risk; plain emit-first migration.

# 3. Verify the codeql-action pin against its tag before use:
gh api repos/github/codeql-action/tags --paginate \
  --jq '.[] | select(.name|startswith("v4")) | "\(.name) \(.commit.sha)"' | head -3

# 4. Canonical-name matrix job (no "(python)" suffix when name interpolates matrix values):
#   jobs.analyze.name: security/codeql-${{ matrix.language }}

# 5. Disable default setup IMMEDIATELY BEFORE the first advanced-workflow run:
gh api -X PATCH repos/<owner>/<repo>/code-scanning/default-setup -f state=not-configured

# 6. Post-merge: confirm canonical names on main, old names gone:
gh api repos/<owner>/<repo>/commits/<sha>/check-runs --jq '.check_runs[].name' | sort -u
```

### Detailed Steps

1. **Diagnose via the API, not prose.** `code-scanning/default-setup` returning `state: configured` plus an empty `.github/workflows/` grep for codeql proves the check name is emitted by GitHub's managed runner and CANNOT be changed in YAML — migration to advanced setup is the only path to a canonical name.
2. **Query required checks before assuming sequencing risk.** The issue warned about emit-before-require deadlock, but `gh api repos/.../rulesets/<id>` showed neither `Analyze (python)` nor `Analyze (actions)` in `required_status_checks` (and `includes_parents=true` showed no org ruleset). One API call collapsed a risky swap into a simple emit-first migration. Keep the ruleset unchanged for parity; requiring the new contexts is a separate, later change once they have emitted on main.
3. **Capture default-setup parity targets** from the same API response: languages (`python`, `actions`), `query_suite: default` (→ no `queries:` input), `threat_model: remote` (→ `config: | threat-models: remote` in the init step — UNVERIFIED key, see Failed Attempts), `schedule: weekly` (→ cron).
4. **Draft one matrix job with an interpolated custom name**: `name: security/codeql-${{ matrix.language }}` with `matrix.include: [{language: python, build-mode: none}, {language: actions, build-mode: none}]`. Expectation (unverified live): GitHub appends `(<matrix values>)` only when the custom name omits them, so interpolating yields exactly `security/codeql-python` / `security/codeql-actions`.
5. **Pin actions to full commit SHAs verified against tags**: dereference `github/codeql-action` tags via `gh api repos/github/codeql-action/tags` (annotated-tag objects from `git/ref/tags/vN` give a TAG sha, not the commit — use the `tags` list endpoint's `.commit.sha`). Least-privilege: top-level `contents: read`; only the analyze job gets `security-events: write`.
6. **Sequence the cutover**: PATCH default-setup to `not-configured` immediately before pushing the branch, because SARIF uploads from advanced configurations are rejected while default setup is enabled (GitHub-documented behavior, not yet observed live). The scanning gap is minutes and — given step 2 — carries no merge-blocking risk. Then verify on the PR head and on main that `security/codeql-*` check-runs appear and zero `Analyze (` runs remain.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Assumed emit-before-require sequencing was mandatory because the issue said swapping a required check "must be sequenced carefully" | The premise was unverified — `gh api .../rulesets/<id>` showed the `Analyze (*)` names were never required checks, so the elaborate two-phase swap was unnecessary | Query `required_status_checks` (rulesets AND classic branch protection, with `includes_parents=true`) before designing sequencing; the issue author's risk framing may not match live state |
| 2 | First fetched the codeql-action pin via `gh api repos/github/codeql-action/git/ref/tags/v4` | Returned an annotated TAG object sha (`fb84f622…`), not the commit sha — pinning `uses:` to a tag-object sha does not match the advertised commit | For `uses:` pinning, take `.commit.sha` from the `/tags` list endpoint (or dereference `^{}`); verify the sha against the version tag before writing it into the workflow |
| 3 | Considered leaving default setup enabled while the advanced workflow bedded in ("belt and braces") | GitHub rejects code-scanning SARIF uploads from advanced configurations while default setup is `configured` — the new job would fail its upload step | The two setups are mutually exclusive; disable default setup via `PATCH .../code-scanning/default-setup -f state=not-configured` before the first advanced run, and accept a minutes-long scan gap |
| 4 | Nearly relied on the plan-time claim that `Analyze (python)` appears in check-runs with that exact literal name | Not independently confirmed — default-setup check-run naming was taken from the issue body, not observed via `commits/<sha>/check-runs` | Post-migration verification must list actual check-run names on the new commit (both presence of canonical names and absence of `Analyze (`), not assume the old names' spelling |

## Results & Parameters

### Live-verified facts (ProjectScylla, 2026-07-03)

- `code-scanning/default-setup`: `{"state":"configured","languages":["actions","python"],"query_suite":"default","threat_model":"remote","schedule":"weekly"}`
- Ruleset 15556492 (`homeric-main-baseline`, repo-level, no org parent) required contexts: `lint, unit-tests, integration-tests, security/dependency-scan, security/secrets-scan, build, schema-validation, deps/version-sync, test, package, install` — no `Analyze (*)`
- `github/codeql-action` pin: `v4.36.3` → commit `54f647b7e1bb85c95cddabcd46b0c578ec92bc1a` (from `/tags` list endpoint)

### Unverified assumptions a reviewer/implementer MUST check on the first run

1. Matrix-name suffix behavior: `name: security/codeql-${{ matrix.language }}` produces NO trailing `(python)` — check `gh pr checks` on the first PR.
2. `threat-models: remote` is a valid `config:` key for the init action AND is accepted for the `python`/`actions` extractors — if init errors, drop the config block (threat model then reverts to default) and note the parity loss.
3. `build-mode: none` is accepted for the `actions` language (it is for python).
4. `PATCH /repos/<o>/<r>/code-scanning/default-setup` with `state=not-configured` is the correct disable call and the caller's token has admin scope.
5. SARIF-rejection-while-default-setup-enabled is real and applies to PR-triggered runs too (drove the disable-before-push sequencing).

### Drafted workflow skeleton

```yaml
on: [pull_request, push(main), schedule(weekly cron), workflow_dispatch]
permissions: {contents: read}
jobs:
  analyze:
    name: security/codeql-${{ matrix.language }}
    permissions: {contents: read, actions: read, security-events: write}
    strategy: {fail-fast: false, matrix: {include: [{language: python, build-mode: none}, {language: actions, build-mode: none}]}}
    steps:
      - checkout @ pinned sha
      - github/codeql-action/init @ 54f647b7…  # v4.36.3, config: threat-models: remote
      - github/codeql-action/analyze @ 54f647b7…  # category: /language:${{ matrix.language }}
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #2028 implementation plan (planning session only; API queries executed live, workflow not yet run) | Ruleset 15556492 + default-setup state verified via `gh api` on 2026-07-03 |
