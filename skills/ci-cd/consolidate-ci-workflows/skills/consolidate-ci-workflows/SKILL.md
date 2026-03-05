---
name: consolidate-ci-workflows
description: "Consolidate GitHub Actions workflows by extracting composite actions and merging redundant workflows. Use when: repo has repeated Pixi setup blocks, duplicated PR comment JS, overlapping security workflows, or placeholder-only jobs."
category: ci-cd
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Objective** | Reduce CI workflow count and eliminate duplication via composite actions and merges |
| **Trigger** | 15+ workflows with repeated setup blocks, duplicated JS scripts, or placeholder jobs |
| **Outcome** | Composite actions extracted, workflows merged, placeholder jobs removed |
| **Verified On** | ProjectOdyssey — 25 workflows → 23, ~933 net lines deleted |

## When to Use

1. Multiple workflows share the same Pixi setup + cache step pair
2. PR comment JavaScript (list comments → find bot comment → update/create) is copy-pasted across 5+ workflows
3. A `build-validation` workflow duplicates build steps already in a test/compilation workflow
4. Security workflows overlap: one for PR secret scan, one for push SAST — merge to single workflow
5. Jobs contain only `echo "placeholder"` and `exit 0` with no real logic

## Verified Workflow

### Step 1 — Audit workflows for duplication patterns

```bash
# Find workflows with repeated Pixi cache setup (double-setup pattern)
grep -rl "Cache Pixi environments" .github/workflows/

# Find workflows with duplicated PR comment JS
grep -rl "github-script" .github/workflows/

# Count total workflows
ls .github/workflows/*.yml | wc -l
```

### Step 2 — Extract PR comment composite action

Create `.github/actions/pr-comment/action.yml`:

```yaml
name: Post or Update PR Comment
description: Post a report file as a PR comment, updating an existing comment if one exists.

inputs:
  report-file:
    description: Path to the markdown report file
    required: true
  comment-marker:
    description: Unique string to find existing bot comment
    required: true
  github-token:
    required: false
    default: ${{ github.token }}

runs:
  using: composite
  steps:
    - name: Post or update PR comment
      uses: actions/github-script@v8
      with:
        github-token: ${{ inputs.github-token }}
        script: |
          const fs = require('fs');
          try {
            const report = fs.readFileSync('${{ inputs.report-file }}', 'utf8');
            const marker = '${{ inputs.comment-marker }}';
            const { data: comments } = await github.rest.issues.listComments({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
            });
            const botComment = comments.find(c =>
              c.user.type === 'Bot' && c.body.includes(marker)
            );
            if (botComment) {
              await github.rest.issues.updateComment({
                owner: context.repo.owner, repo: context.repo.repo,
                comment_id: botComment.id, body: report
              });
            } else {
              await github.rest.issues.createComment({
                owner: context.repo.owner, repo: context.repo.repo,
                issue_number: context.issue.number, body: report
              });
            }
          } catch (error) { console.error('Failed to comment on PR:', error); }
```

Replace all occurrences with:

```yaml
- name: Comment on PR
  if: github.event_name == 'pull_request'
  uses: ./.github/actions/pr-comment
  with:
    report-file: my-report.md
    comment-marker: "Unique Report Title"
```

### Step 3 — Extract setup-pixi composite action

Only needed for workflows using the **double-setup pattern** (both `prefix-dev/setup-pixi` AND a separate `actions/cache` step for `~/.pixi`):

```yaml
# .github/actions/setup-pixi/action.yml
name: Set Up Pixi Environment
runs:
  using: composite
  steps:
    - name: Set up Pixi
      uses: prefix-dev/setup-pixi@v0.9.4
      with:
        pixi-version: ${{ inputs.pixi-version || 'latest' }}
        cache: ${{ inputs.cache || 'true' }}
    - name: Cache Pixi environments
      uses: actions/cache@v5
      with:
        path: ~/.pixi
        key: pixi-${{ runner.os }}-${{ hashFiles('pixi.toml') }}
        restore-keys: |
          pixi-${{ runner.os }}-
```

Replace double-setup blocks with:

```yaml
- name: Set up Pixi
  uses: ./.github/actions/setup-pixi
```

### Step 4 — Merge build-validation into comprehensive-tests

If `build-validation.yml` runs `just build ci` and comprehensive-tests runs `mojo package`, add the build step to the compilation job and delete `build-validation.yml`:

```yaml
# In mojo-compilation job, add before the compile step:
- name: Build Mojo packages
  run: |
    if [ -d "shared" ]; then
      just build ci
      echo "✅ Shared package built successfully"
    else
      echo "⚠️  No shared package found yet"
    fi
```

### Step 5 — Consolidate security workflows

Pattern: 3 security workflows → 2:

- **`security.yml`** (PR + push to main): secret scan (gitleaks) + SAST (semgrep) + supply chain review
- **`dependency-audit.yml`** (weekly scheduled): full dependency audit, license check, creates issues

Delete `security-scan.yml` and `security-pr-scan.yml`.

### Step 6 — Remove placeholder-only jobs

Jobs consisting entirely of `echo "placeholder"` and `exit 0` with no real logic add noise and should be removed. Keep `exit 0` only when it's a **graceful skip** (e.g., "no papers/ directory yet, skip"):

```bash
# Pattern to find: jobs with ONLY echo + exit 0 (no real work)
grep -A5 "run: |" .github/workflows/*.yml | grep -B3 "exit 0"
```

### Step 7 — Validate

```bash
# All YAML must be valid
SKIP=mojo-format pixi run pre-commit run --all-files

# Verify composite actions work (uses: ./.github/actions/X requires checkout first)
# Local composite actions need `uses: actions/checkout` before they're callable
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Edit tool on unread file | Called Edit on `simd-benchmarks-weekly.yml` without re-reading | Edit tool requires the file to have been read in the same tool call context | Re-read the relevant section before each Edit call |
| Unicode emoji in YAML comment-marker | Used `🧪` directly in `comment-marker` input value | YAML interprets multi-byte chars inconsistently; pre-commit may warn | Use `\UXXXXXX` Unicode escape in YAML strings for emoji |
| Trying to reach 26→15 target | Attempted to delete more workflows to hit the stated target | The deliverables only listed specific items; the 15 target was aspirational | Match work to the actual deliverables list, not a stretch-goal count |
| Updating workflows without double-setup | Applied setup-pixi composite to all 15 pixi-using workflows | Only 5 had the double-setup pattern; others only had `setup-pixi` alone | Check which pattern each workflow uses before applying composite |
| Coverage.yml PR comment | Direct composite action usage | coverage.yml builds comment body dynamically via template string | Add a "build report" step to write the final file, then call composite |

## Results & Parameters

**Before**: 25 workflows, ~1227 lines of duplicated setup/JS
**After**: 23 workflows, net -933 lines

**Composite actions created**:
- `.github/actions/pr-comment/action.yml` — eliminates ~500 lines
- `.github/actions/setup-pixi/action.yml` — deduplicates 5 double-setup blocks

**Workflows deleted**: `build-validation.yml`, `security-scan.yml`, `security-pr-scan.yml`
**Workflows added**: `security.yml`
**Workflows modified**: `benchmark.yml`, `comprehensive-tests.yml`, `coverage.yml`, `paper-validation.yml`, `readme-validation.yml`, `simd-benchmarks-weekly.yml`

**Key constraint**: Local composite actions (`./.github/actions/X`) require the repository to be checked out before the step that uses them. Always ensure `actions/checkout` appears before any `./.github/actions/` usage.
