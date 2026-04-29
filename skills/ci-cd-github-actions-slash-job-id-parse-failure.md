---
name: ci-cd-github-actions-slash-job-id-parse-failure
description: "GitHub Actions silently rejects an entire workflow file when any job ID (the YAML key) contains a forward slash. Zero jobs run, no check contexts are reported, and branch rulesets requiring those checks see them as permanently 'never run' → BLOCKED. Use when: (1) a workflow appears syntactically valid but shows 0 jobs in the Actions UI, (2) PRs are BLOCKED with mergeStateStatus=BLOCKED and all statusCheckRollup entries for the affected workflow are absent, (3) you see job IDs containing '/' in workflow YAML."
category: ci-cd
date: 2026-04-29
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [github-actions, job-id, yaml, parse-failure, silent-failure, branch-protection, ruleset, check-context]
---

# GitHub Actions: Forward Slash in Job ID Causes Silent Parse Failure

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-29 |
| **Objective** | Run CI jobs whose IDs contained slashes (e.g. `security/dependency-scan`) |
| **Outcome** | GitHub silently rejected the entire workflow at parse time — 0 jobs ever ran |
| **Verification** | verified-ci — fix confirmed working in HomericIntelligence/ProjectCharybdis PR #50 |

## When to Use

- A workflow file looks syntactically valid (passes local YAML linters) but shows **0 jobs** in the GitHub Actions UI
- PRs are stuck with `mergeStateStatus=BLOCKED` and required check contexts are **absent** (not failed — never ran)
- `statusCheckRollup` from the GitHub API returns no entries for the affected workflow
- Re-triggering CI pushes creates no new runs (GitHub rejects the file before queuing)
- Auto-merge was armed but never fires because required checks are permanently "never run"
- A workflow was deployed for days or weeks with 0 jobs ever executing

## Root Cause

GitHub Actions enforces that job IDs (the YAML mapping key under `jobs:`) must match the pattern:

```
[a-zA-Z_][a-zA-Z0-9_-]*
```

Forward slashes are **forbidden** in job IDs. When GitHub's workflow parser encounters a slash in any job ID, it **silently rejects the entire workflow file** — no error message is surfaced in the UI, no runs are created, and no check contexts are reported to GitHub.

The `name:` field (what GitHub displays in the Actions UI and reports as the check context name to branch rulesets) **CAN** contain slashes. Only the YAML key (job ID) must be slug-safe.

## Detection

```bash
# Scan for slash job IDs across all workflow files
grep -n "^  [a-zA-Z].*\/.*:" .github/workflows/*.yml
```

If this command returns any hits, those job IDs are invalid and will cause silent parse failure.

**Symptom checklist:**

| Symptom | Notes |
|---------|-------|
| 0 jobs in Actions UI for the workflow | GitHub UI shows no runs at all |
| `mergeStateStatus=BLOCKED` on PRs | Branch ruleset sees required checks as "never run" |
| `statusCheckRollup` entries absent for workflow | Not failed — missing entirely |
| No new runs after re-triggering | GitHub rejects the file at parse time, never queues it |
| Auto-merge armed but never fires | Required checks are "pending forever" |

## Verified Workflow

### Quick Reference

```yaml
# BROKEN — job IDs with slashes cause silent parse failure (0 jobs run):
jobs:
  security/dependency-scan:   # ← invalid job ID
    name: security/dependency-scan
    runs-on: ubuntu-latest
    ...

  security/secrets-scan:      # ← invalid job ID
    name: security/secrets-scan
    runs-on: ubuntu-latest
    ...

  deps/version-sync:          # ← invalid job ID
    name: deps/version-sync
    runs-on: ubuntu-latest
    ...
```

```yaml
# FIXED — hyphens in job IDs, slashes preserved in name: field:
jobs:
  security-dependency-scan:   # ← valid job ID
    name: security/dependency-scan   # ← display name + check context (can have slashes)
    runs-on: ubuntu-latest
    ...

  security-secrets-scan:      # ← valid job ID
    name: security/secrets-scan
    runs-on: ubuntu-latest
    ...

  deps-version-sync:          # ← valid job ID
    name: deps/version-sync
    runs-on: ubuntu-latest
    ...
```

### Detailed Steps

1. **Detect affected workflows** using the grep command above. Any hit is a bug.

2. **Rename job IDs**: Replace all forward slashes in YAML keys (job IDs) with hyphens.
   - `security/dependency-scan:` → `security-dependency-scan:`
   - `deps/version-sync:` → `deps-version-sync:`

3. **Preserve the `name:` field**: Keep the original slash-containing string as the `name:` value. GitHub uses `name:` as the display label and check context name reported to branch rulesets. If branch rulesets or required status checks reference the name (e.g. `security/dependency-scan`), the `name:` field must remain unchanged.

4. **Update `needs:` references**: If any job references the renamed job via `needs:`, update those references to use the new hyphenated ID:
   ```yaml
   # Before
   needs: [security/dependency-scan, security/secrets-scan]
   # After
   needs: [security-dependency-scan, security-secrets-scan]
   ```

5. **Push and verify**: After pushing, confirm the Actions UI shows the expected number of jobs and that check contexts are reported to open PRs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Re-triggering CI runs | Pushed empty commits / re-ran workflows via UI | No new runs created — GitHub rejects the file before queuing | The problem is at parse time, not run time |
| Armed auto-merge | `gh pr merge --auto --squash` | Auto-merge never fired — required check contexts are "never run", not "failed" | Auto-merge waits for checks to pass; checks that never run block forever |
| Checking YAML validity locally | `yamllint`, `python -c "import yaml; yaml.safe_load(...)"` | Local YAML parsers accepted the file (slashes are valid YAML keys) | GitHub imposes additional constraints beyond YAML spec — job IDs have a stricter character set |

## Results & Parameters

**Job ID valid character set**: `[a-zA-Z_][a-zA-Z0-9_-]*`
- Allowed: letters, digits, underscores, hyphens
- Forbidden: forward slashes, dots, spaces, and all other special characters

**`name:` field**: No restrictions — can contain slashes, spaces, dots, etc.

**Impact scope**: A single invalid job ID causes the **entire workflow file** to be rejected. All other jobs in the same file also fail to run.

**Error visibility**: GitHub does not surface the parse error in the Actions UI, workflow run list, or via webhook events. The failure is completely silent.

**Branch ruleset impact**: Required status checks that reference job names from a silently-rejected workflow will remain in a "pending" / "never run" state indefinitely, permanently blocking PRs.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectCharybdis | `_required.yml` had `security/dependency-scan`, `security/secrets-scan`, `deps/version-sync` as job IDs | File had been deployed for multiple weeks with 0 jobs ever running; fixed in PR #50 (2026-04-29) |
