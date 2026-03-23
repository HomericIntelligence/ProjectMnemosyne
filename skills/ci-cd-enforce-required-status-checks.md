---
name: ci-cd-enforce-required-status-checks
description: "Audit and enforce required CI status checks across all repositories in a GitHub organization. Use when: (1) multiple repos lack branch protection or required status checks, (2) you want to ensure all passing tests become merge gates, (3) setting up CI governance across an org."
category: ci-cd
date: 2026-03-23
version: "1.0.0"
user-invocable: false
tags:
  - branch-protection
  - required-checks
  - multi-repo
  - github-api
  - ci-governance
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-23 |
| **Objective** | Analyze all HomericIntelligence repos, identify consistently passing CI tests, and enforce them as required status checks for PR merges |
| **Outcome** | All 12 repos now have branch protection. 3 repos gained new required checks (Odyssey +12, Scylla +2, Hephaestus +2). Reusable scripts created for ongoing governance. |

## When to Use

- Multiple repos in an org lack branch protection or have incomplete required status checks
- You need to audit CI health across an entire GitHub organization
- Setting up CI governance: ensuring passing tests can't regress
- After adding new CI workflows, re-running to pick up new passing checks
- Verifying branch protection configuration after org-wide changes

## Verified Workflow

### Quick Reference

```bash
# 1. Audit all repos (read-only)
python3 scripts/audit_ci_status.py --runs 20

# 2. Dry-run enforcement
python3 scripts/enforce_required_checks.py

# 3. Apply changes
python3 scripts/enforce_required_checks.py --apply

# 4. Target a single repo
python3 scripts/enforce_required_checks.py --apply --repo ProjectScylla

# 5. Verify final state
gh api repos/ORG/REPO/branches/BRANCH/protection/required_status_checks --jq '.contexts[]'
```

### Step 1: Audit CI status across all repos

The audit script (`scripts/audit_ci_status.py`):
1. Lists all non-archived repos via `gh repo list`
2. Detects default branch (`main` vs `master`) via `gh api repos/.../default_branch`
3. Fetches last N workflow runs on the default branch
4. For each run, fetches job-level results (name + conclusion)
5. Computes per-job pass rate (excluding skipped/cancelled)
6. Fetches workflow YAML to detect `pull_request` triggers and `paths:` filters
7. Excludes GitHub-automated jobs (Dependabot, CodeQL `Analyze` jobs, push-only runs)
8. Produces JSON report + human-readable stdout summary

Key filtering rules:
- **Minimum runs threshold** (`--min-runs`, default 3): Jobs must have at least N executed runs to qualify
- **Pass rate threshold** (`--min-pass-rate`, default 1.0): Jobs must pass 100% of the time
- **Path-filtered exclusion**: Jobs from workflows with `paths:` on `pull_request` are excluded (they don't run on every PR)
- **PR trigger required**: Only jobs from workflows that trigger on `pull_request` qualify
- **Automated job exclusion**: `Analyze (*)`, `Dependabot`, and `Push on main` runs are filtered out

### Step 2: Review the audit report

Check `output/ci-audit-report.json` for per-repo breakdown:
- `current_required_checks`: what's already required
- `new_checks_to_add`: what the script recommends adding
- `warnings`: branch mismatches, failing required checks

### Step 3: Dry-run enforcement

```bash
python3 scripts/enforce_required_checks.py
```

Shows exactly what API calls would be made without modifying anything.

### Step 4: Apply incrementally

Start with the safest repo (one that already has protection):
```bash
python3 scripts/enforce_required_checks.py --apply --repo ProjectScylla
```

Then expand to all:
```bash
python3 scripts/enforce_required_checks.py --apply
```

### Step 5: Verify

Re-run the audit to confirm state matches expectations:
```bash
python3 scripts/audit_ci_status.py --runs 5
```

### API Patterns

**Repo has protection + existing checks** (PATCH replaces entire list):
```bash
gh api --method PATCH repos/ORG/REPO/branches/BRANCH/protection/required_status_checks \
  --input - <<< '{"strict":false,"contexts":["existing-check","new-check"]}'
```

**Repo has protection but no checks** (PUT with full protection body):
```bash
gh api --method PUT repos/ORG/REPO/branches/BRANCH/protection \
  --input - <<< '{"required_status_checks":{"strict":false,"contexts":["check"]},"enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null}'
```

**Repo has no protection** (same PUT, creates from scratch):
```bash
gh api --method PUT repos/ORG/REPO/branches/BRANCH/protection \
  --input - <<< '{"required_status_checks":{"strict":false,"contexts":[]},"enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null}'
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `gh api --jq` with `parse_json=True` | Used `gh("api", ..., "--jq", ".default_branch")` which returns plain text, but wrapper tried `json.loads()` | `json.loads("master")` fails, returns None, fallback returns "main" — wrong branch for 5 repos | When `--jq` extracts a scalar, use `parse_json=False` since the output is plain text, not JSON |
| Including Dependabot/CodeQL jobs | Initial audit recommended `Analyze (actions)`, `Analyze (python)`, `Dependabot` as required checks | These are GitHub-automated jobs that don't run on every PR; requiring them would block all PRs that don't trigger them | Filter out GitHub-automated run names (`* in /. - Update`, `CodeQL`) and job prefixes (`Analyze (`, `Dependabot`) |
| `min-runs=1` for all repos | Lowered threshold to include repos with limited CI history | For Odyssey, this included 19+ jobs with only 1 run (benchmarks, container builds) — too aggressive | Keep `min-runs=3` as default; jobs that only ran once are likely scheduled/manual, not PR-triggered |
| Protecting branch "main" when default is "master" | Audit reported "main" for all repos (due to jq bug), enforcement tried to protect "main" | `gh api` returned 404 "Branch not found" for 5 repos whose default branch is actually "master" | Always detect actual default branch; never assume "main" |
| Double-fetching run jobs | Collected job stats in one loop, then re-fetched same runs for workflow mapping | Doubled API calls, making the script 2x slower than needed | Cache run job data — fetch once, use for both stats collection and workflow mapping in a single pass |
| Including path-filtered workflows | Shell Tests (`bats`) in Scylla passes 100% but triggers only on `**/*.sh` changes | If required, PRs not touching `.sh` files would never get the check and be blocked forever | Detect `paths:` filter in workflow YAML's `pull_request` trigger section; exclude those jobs from required checks |

## Results & Parameters

### Final State (12 repos)

```
ProjectOdyssey    (main)   : PROTECTED, 27 required checks (+12 new)
ProjectMnemosyne  (main)   : PROTECTED, 1 required check (no change)
ProjectScylla     (main)   : PROTECTED, 4 required checks (+2 new)
ProjectHephaestus (main)   : PROTECTED, 2 required checks (+2 new)
ProjectKeystone   (main)   : PROTECTED, 0 checks (all CI failing)
AchaeanFleet      (main)   : PROTECTED, 0 checks (all CI cancelled)
Myrmidons         (main)   : PROTECTED, 0 checks (all CI cancelled)
Odysseus          (master) : PROTECTED, 0 checks (no CI workflows)
ProjectTelemachy  (master) : PROTECTED, 0 checks (CI branch mismatch)
ProjectHermes     (master) : PROTECTED, 0 checks (CI branch mismatch)
ProjectProteus    (master) : PROTECTED, 0 checks (CI branch mismatch)
ProjectArgus      (master) : PROTECTED, 0 checks (CI branch mismatch)
```

### Scripts Created

| Script | Purpose |
|--------|---------|
| `scripts/audit_ci_status.py` | Read-only audit of CI status across all repos |
| `scripts/enforce_required_checks.py` | Enforcement with --dry-run/--apply and rollback |

### Key Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `--runs` | 10 | Number of recent runs to analyze per repo |
| `--min-runs` | 3 | Minimum executed runs for a job to qualify |
| `--min-pass-rate` | 1.0 | Required pass rate (1.0 = 100%) |
| `--include-path-filtered` | false | Include path-filtered jobs (risky) |

### Rollback

Rollback files saved to `output/rollback-<timestamp>.json`. To undo:
```bash
# Manual rollback for a single repo
gh api --method PATCH repos/ORG/REPO/branches/BRANCH/protection/required_status_checks \
  --input - <<< '{"strict":false,"contexts":["original","checks","only"]}'

# Remove branch protection entirely
gh api --method DELETE repos/ORG/REPO/branches/BRANCH/protection
```

### Known Issues for Follow-Up

- 4 repos have CI YAML targeting `branches: [main]` but default branch is `master` — CI never runs
- ProjectOdyssey has 6 existing required checks failing on main (pre-commit, security-report, etc.)
- Repos with cancelled CI (AchaeanFleet, Myrmidons) may need self-hosted runner investigation

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence (all 12 repos) | Org-wide CI governance enforcement | [notes.md](./skills/ci-cd-enforce-required-status-checks.notes.md) |
