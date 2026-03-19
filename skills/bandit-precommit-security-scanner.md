---
name: bandit-precommit-security-scanner
description: 'Pattern for replacing a pygrep shell=True pre-commit hook with bandit
  AST-based Python security scanning. Use when: upgrading naive regex security hooks
  to AST analysis, distinguishing PR-introduced CI failures from pre-existing infrastructure
  crashes.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Bandit Pre-commit Security Scanner (Replacing pygrep shell=True Hook)

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-05 |
| **Objective** | Replace a `pygrep` hook that used `shell=True` pattern-matching with `bandit` AST-based security scanning |
| **Outcome** | PR correct as-is; CI failures confirmed pre-existing; no code changes needed |
| **PR** | HomericIntelligence/ProjectOdyssey#3355 |
| **Issue** | HomericIntelligence/ProjectOdyssey#3157 |

## When to Use

Invoke when:

- A `pygrep` hook uses `shell=True` detection via regex and produces false positives
- You need AST-based Python security scanning rather than string pattern matching
- You want to add `bandit` as a pre-commit hook scoped to specific directories
- You need to distinguish PR-introduced CI failures from pre-existing infrastructure crashes
- A review-fix task returns "no fixes required" and you must verify correctness before closing

## Verified Workflow

### Step 1 — Add bandit dependency to pixi.toml

```toml
[dependencies]
bandit = ">=1.7.5"
```

Regenerate the lock file:

```bash
pixi install
```

### Step 2 — Replace pygrep hook in .pre-commit-config.yaml

Remove the old pygrep hook:

```yaml
# REMOVE — uses shell=True which bandit itself would flag
- id: check-shell-injection
  name: Check for shell=True usage
  language: pygrep
  entry: 'shell\s*=\s*True'
  files: ^(scripts|tests)/.*\.py$
```

Add the bandit hook:

```yaml
- id: bandit-security-scan
  name: Bandit Security Scan
  language: system
  entry: pixi run bandit
  args: [-ll, --skip, "B310,B202", -r]
  files: ^(scripts|tests)/.*\.py$
  pass_filenames: true
```

Key fields:
- `language: system` — uses the pixi environment (not a standalone hook repo)
- `-ll` — medium and high severity only (suppress low-severity noise)
- `--skip B310,B202` — skip known false positives for your codebase
- `-r` — recursive scan
- `files:` — scope to specific directories via path regex

### Step 3 — Verify bandit passes locally

```bash
pixi run bandit -ll --skip B310,B202 -r scripts/ tests/
```

Expected output:
```
Test results:
    No issues identified.
Total issues (by severity):
    Medium: 0
    High: 0
```

### Step 4 — Verify pre-commit hook runs correctly

```bash
just pre-commit-all
# or: pre-commit run --all-files
```

Look for: `Bandit Security Scan: Passed`

### Step 5 — Distinguish PR failures from pre-existing CI crashes

When CI shows failures after a security-hook change, check if failures are related:

```bash
# Check if the failing tests touch any file in the PR diff
gh pr diff <PR_NUMBER> --name-only

# Compare against the failing test paths from CI
gh run view <RUN_ID> --json jobs | python3 -c "
import json, sys
d = json.load(sys.stdin)
for j in d['jobs']:
    if j['conclusion'] not in ('success', 'skipped'):
        print(j['name'], j['conclusion'])
"

# Check if same failures appear on main
gh run list --branch main --limit 5
```

If the failing tests (`test_batch_loader.mojo`, `test_trait_based_serialization.mojo`, etc.)
are not in the PR diff and show `mojo: error: execution crashed` — these are infrastructure
crashes pre-existing on `main`, not caused by the security hook change.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treating CI failures as PR-caused | Assumed all failing CI jobs were related to the PR changes | `Data Loaders` and `Test Examples` failures were Mojo runtime crashes (`execution crashed`) pre-existing on `main`, completely unrelated to `.pre-commit-config.yaml` changes | Always cross-reference CI failures against the PR diff before assuming causation |
| Unnecessary fix commit | Considered committing a no-op change to "complete" the review-fix task | The fix plan explicitly stated "No fixes needed" — a spurious commit would add noise | When a review-fix plan says "no fixes required," verify with local checks and do NOT commit |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Hook language | `system` (uses pixi environment) |
| Bandit severity filter | `-ll` (medium + high only) |
| Skipped rules | `B310,B202` |
| File scope | `^(scripts\|tests)/.*\.py$` |
| Bandit version | `>=1.7.5` |
| Medium/High issues found | 0 |
| Pre-existing CI failures | 2 (`Data Loaders`, `Test Examples`) — Mojo runtime crashes |

## Key Takeaways

1. **bandit > pygrep for security**: AST-based scanning catches real vulnerabilities; pygrep
   `shell=True` regex has false positives and misses complex patterns.

2. **Scope bandit with `-ll`**: Without `-ll`, bandit reports thousands of low-severity
   informational findings that create noise. Use medium/high only.

3. **Verify CI failure causation**: Before making any fix, check if failing tests are in the
   PR diff. `mojo: error: execution crashed` in unrelated test files = infrastructure flakiness,
   not your bug.

4. **"No fixes required" is valid**: When a review-fix analysis concludes no changes are
   needed, run local verification (bandit, pre-commit) and close without committing.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3355, Issue #3157 | [notes.md](../references/notes.md) |
