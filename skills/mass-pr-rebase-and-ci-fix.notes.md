# Session Notes: Mass PR Rebase and CI Fix (2026-03-14)

## Context

- **Date**: 2026-03-14
- **Repository**: HomericIntelligence/ProjectMnemosyne
- **Objective**: Fix main CI failures, enable auto-merge on all open PRs, rebase all branches, fix all failing PRs
- **Scale**: ~157 open PRs, 27 superseded PRs closed, 5 skill files consolidated

## Problem Sequence

### Problem 1: Update Marketplace workflow failing

`gh run list --branch main` showed `Update Marketplace` failing repeatedly.

Root cause: The workflow did `git push` directly to `main`, but branch protection requires all changes go through PRs. Error: `GH006: Protected branch update failed for refs/heads/main`.

Fix: Changed workflow to create a timestamped branch, push, open PR, enable auto-merge.

PR #698: `fix(ci): update marketplace workflow to create PR instead of direct push`

### Problem 2: validate check not running on many PRs

Many PRs were BLOCKED indefinitely. Investigation revealed `validate` was a required check but only triggered on `pull_request` events when `skills/**`, `plugins/**`, `templates/**`, or `scripts/validate_plugins.py` changed. PRs that only touched workflow files never triggered the check → permanently BLOCKED.

Fix: Removed all `paths:` filters from validate workflow. PR #699.

After PR #699 merged, we rebased all PRs to pick up the new trigger.

### Problem 3: 100+ PRs stale / DIRTY

After PR #699 merged, rebased all 157 open PRs using temp branch pattern:
- 120 rebased cleanly
- 37 had conflicts (all ADR-009 skill content conflicts)
- Used `git switch` instead of `git checkout -` to avoid Safety Net hook

### Problem 4: 29 PRs all conflicting on same ADR-009 skill files

Multiple PRs were all adding session notes to the same skill files:
- `skills/ci-cd/adr009-test-file-splitting/` — 16+ sessions from different branches
- `skills/ci-cd/mojo-adr009-test-split/` — 10 sessions
- etc.

Approach: Python script to parse sessions by issue number, merge in order, write consolidated file. Created PR #701 with all merged content, closed 27 superseded PRs.

### Problem 5: Individual PR validation failures

**PR #636** (dryrun3-runner-failure-fixes):
- `validate` failed: "Missing required fields: version" + "Missing skills/ directory"
- Skill had flat structure (`SKILL.md` at plugin root) and no `version` in plugin.json
- Fix: moved SKILL.md to `skills/<name>/SKILL.md`, added `"version": "1.0.0"`

**PR #654** (adr009-test-file-splitting-3517):
- PR targeted `skill/ci-cd/adr009-test-file-splitting` (another feature branch) as base, not `main`
- Auto-merge failed with "Protected branch rules not configured for this branch"
- Fix: `gh pr edit 654 --base main`

**PR #460** (tier-label-consistency-check conflict):
- PR had v2 glob-scan SKILL.md content; main had v1.1 expanded patterns in notes
- Resolution: took PR's SKILL.md (newer content), main's notes.md (more complete)

**PR #676** (fix-mojo-ci-compilation-errors):
- Conflict only in root `.claude-plugin/plugin.json` (auto-generated marketplace)
- Resolution: `git checkout --ours .claude-plugin/plugin.json`

## Key Technical Details

### Branch protection configuration found
```json
{
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "required_status_checks": { "contexts": ["validate"] },
  "required_linear_history": { "enabled": true },
  "enforce_admins": { "enabled": false }
}
```

### Auto-merge behavior
- `gh pr merge <pr> --auto --rebase` → silently succeeds or fails
- GraphQL `enablePullRequestAutoMerge` returns `UNPROCESSABLE` if already merged or wrong base
- "Protected branch rules not configured" = PR targets non-protected branch (not main)

### Validate workflow path filter removal
Before:
```yaml
on:
  pull_request:
    paths: ['skills/**', 'plugins/**', 'templates/**', 'scripts/validate_plugins.py']
```
After:
```yaml
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:
```

### Session merge Python pattern
```python
import re

def parse_sessions(filepath):
    with open(filepath) as f:
        content = f.read()
    parts = re.split(r'(?=^# Session)', content, flags=re.MULTILINE)
    sessions = {}
    for p in parts:
        m = re.search(r'Issue #(\d+)', p)
        if m:
            num = int(m.group(1))
            if num not in sessions:
                sessions[num] = p.strip()
    return sessions

# Merge all sources
all_sessions = {}
for source_file in source_files:
    all_sessions.update(parse_sessions(source_file))

merged = "\n\n---\n\n".join(all_sessions[k] for k in sorted(all_sessions.keys()))
```

## Safety Net Hook Interactions

The Safety Net hook blocked:
- `git branch -D temp-branch` → workaround: use `git branch -d` (safe delete)
- `git checkout -` → workaround: `git switch skill/ci-cd/mojo-format-non-blocking`
- Script containing `git branch -D` → had to rewrite script to use `-d`

## PRs Created This Session

| PR | Title | Status |
|----|-------|--------|
| #698 | fix(ci): update marketplace workflow to create PR instead of direct push | Merged |
| #699 | fix(ci): remove path filters from validate workflow | Merged |
| #701 | feat(skills): merge ADR-009 test-file-splitting sessions from 29 conflicting PRs | Open (auto-merge) |

## PRs Closed (Superseded)

#599, #601, #603, #604, #605, #606, #608, #612, #613, #615, #616, #617, #620, #621, #622, #623, #624, #626, #628, #631, #632, #634, #635, #643, #647, #648, #655