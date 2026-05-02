---
name: documentation-multi-file-ecosystem-sync
description: "Synchronize ecosystem repository listings across multiple documentation files using GitHub API as source of truth. Use when: (1) ecosystem docs list wrong repo count or descriptions, (2) same repo table appears in multiple files and needs consistency, (3) adding new repos to existing ecosystem documentation."
category: documentation
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-precommit
supersedes: []
tags:
  - documentation
  - ecosystem
  - multi-file-sync
  - github-api
---

# Documentation: Multi-File Ecosystem Sync

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Update stale 3-repo ecosystem listing to accurate 12-repo table across CLAUDE.md, README.md, and architecture.md simultaneously |
| **Outcome** | Successful — all 3 files updated consistently, pre-commit passes, PR created |
| **Verification** | verified-precommit |

> **Note:** CI validation pending — pre-commit hooks pass locally (Markdown Lint, trailing whitespace, end-of-file, etc.) but CI has not yet confirmed.

## When to Use

- Ecosystem documentation lists wrong number of repos or incorrect descriptions
- Same repo listing appears in multiple files (CLAUDE.md, README.md, architecture.md, agent configs) and needs consistent updates
- A new repo was added to the org and needs to be reflected across documentation
- Repo descriptions have drifted from actual purpose (e.g., ProjectKeystone described as "Communication" when it's actually a "DAG execution engine")

## Verified Workflow

> **Note:** Verified at precommit level only — CI validation pending.

### Quick Reference

```bash
# 1. Verify repos against GitHub org API
gh api orgs/<ORG>/repos --paginate --jq '.[] | "\(.name) -- \(.description // "no description")"' | sort

# 2. Find all ecosystem listing locations
grep -rn "ecosystem\|three-project\|12-repository" CLAUDE.md README.md docs/ .claude/agents/

# 3. Edit each file with consistent table format
# 4. Run pre-commit
pre-commit run --all-files
```

### Detailed Steps

1. **Verify repo list against GitHub org API** — Run `gh api orgs/<ORG>/repos --paginate` to get the authoritative list of repos and their descriptions. Cross-reference with any existing ecosystem-audit skills for verified role descriptions (GitHub repo descriptions are often generic placeholders).

2. **Locate all ecosystem listing sites** — Search across the repo for stale listings:

   ```bash
   grep -rn "three-project\|ecosystem.*:$\|Ecosystem Context" \
     CLAUDE.md README.md docs/ .claude/agents/
   ```

3. **Build the canonical table** — Use a markdown table format for 5+ repos (more readable than bullet lists). Keep descriptions concise (under 80 chars per cell). Alphabetical order by repo name for easy scanning.

4. **Apply the same table to all locations** — Edit each file using the Edit tool. Key consistency rules:
   - Same column headers: `Repository | Role`
   - Same descriptions for the same repo across all files
   - Mark the current project with "(this project)" suffix
   - CLAUDE.md gets the most detailed descriptions; README.md and architecture.md can use shorter versions

5. **Handle permission-restricted files** — Some paths (e.g., `.claude/agents/`) may be restricted in worktree environments. If edits are denied, note the stale references for manual follow-up rather than trying workarounds.

6. **Run pre-commit hooks** — `pre-commit run --all-files` to validate markdown formatting, trailing whitespace, and end-of-file fixers.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Edit .claude/agents/ in worktree | Tried to update chief-evaluator.md ecosystem references | Permission denied in don't-ask mode for `.claude/agents/` path | Some paths are restricted in auto-impl worktrees — note for follow-up instead of blocking |
| Edit before Read | Attempted Edit tool on files not yet read in conversation | Edit tool requires Read first | Always Read target files before editing, even for simple text replacements |

## Results & Parameters

### File Locations Updated (ProjectScylla)

| File | Section | Lines |
| ------ | --------- | ------- |
| `CLAUDE.md` | `**Ecosystem Context**:` | ~15-19 |
| `README.md` | `## Ecosystem` | ~103-109 |
| `docs/design/architecture.md` | `### Ecosystem Context` | ~17-25 |
| `.claude/agents/chief-evaluator.md` | Lines 50, 119 | Permission restricted — manual follow-up needed |

### Table Format Template

```markdown
| Repository | Role |
|------------|------|
| **RepoName** | Brief description of role |
```

### Verification Commands

```bash
# Verify all files list the same repo count
grep -c "^\|" CLAUDE.md README.md docs/design/architecture.md

# Verify no stale "three-project" references remain
grep -rn "three-project" CLAUDE.md README.md docs/
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issue #1507 — update ecosystem from 3 to 12 repos | PR #1551 |
