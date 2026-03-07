---
name: verify-infrastructure-tracking
description: "Verify a known environment incompatibility is tracked as an open infrastructure issue before re-implementing a workaround. Use when: a pre-commit hook silently skips due to host constraints, or an issue asks you to 'verify X is tracked'."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

# Verify Infrastructure Tracking

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-07 |
| Objective | Confirm a known environment incompatibility (mojo-format GLIBC mismatch) is tracked as an infrastructure issue, and update documentation to reference all tracking issues |
| Outcome | Verified — existing tracking issues found, pre-commit comment updated |

## When to Use

- An issue asks you to "verify X is tracked as an infrastructure issue"
- A pre-commit hook silently skips or fails due to a host environment constraint (wrong OS, missing GLIBC version, etc.)
- You suspect the problem has been seen before but want to confirm before creating a duplicate tracking issue
- You need to update a comment/doc to reference existing tracking issues

## Verified Workflow

1. **Search for existing tracking issues** before creating anything:

   ```bash
   gh issue list --state open --search "<keyword>"
   gh issue list --state open --search "<tool-name> <error-keyword>"
   gh issue list --state all --search "<keyword>"   # include closed issues
   ```

2. **Read the pre-commit config** to check if documentation already exists:

   ```bash
   # Look for existing comments near the hook
   cat .pre-commit-config.yaml
   ```

3. **Evaluate the findings**:
   - If a tracking issue exists (open or closed): no new issue needed — proceed to update docs
   - If no tracking issue exists: create one with labels `infrastructure`, `environment`

4. **Update the tracking reference** in `.pre-commit-config.yaml` to include all relevant issues:

   ```yaml
   # See docs/dev/<topic>-compatibility.md for details. Tracked: #NNN (closed), #NNN2, #NNN3
   ```

5. **Post a comment on the originating issue** summarizing findings:

   ```bash
   gh issue comment <ISSUE_NUMBER> --body "..."
   ```

6. **Commit, push, and create PR** — even for comment-only changes, all changes go through PR.

## Key Patterns

**Deduplication search order:**

1. Search open issues by symptom keyword (e.g., `glibc`)
2. Search by tool name + error type (e.g., `mojo-format GLIBC`)
3. Search closed issues to find resolved originals that follow-up issues reference

**Comment format for pre-commit config:**

```yaml
repos:
  # <hook-name>: Requires <dependency> which is not available in <old-env>.
  # On incompatible hosts the wrapper script exits 0 with a warning.
  # <authoritative-env> always runs the full check.
  # See docs/dev/<topic>.md for details. Tracked: #NNN (closed), #NNN2, #NNN3
  - repo: local
    hooks:
      - id: <hook-id>
```

**Issue creation template** (only if no tracking issue exists):

```bash
gh issue create \
  --title "infra: <hook-name> silently skips due to <cause>" \
  --body "## Summary
The <hook> fails silently on <env> because <reason>.

## Impact
- <effect 1>
- <effect 2>

## Workaround
<steps>

## Resolution Path
- <option 1>
- <option 2>" \
  --label "infrastructure"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assuming no tracking issue exists | Planned to create a new tracking issue immediately | Three issues already existed (#3170 closed, #3253, #3365 open) | Always search before creating; use `--state all` to catch closed originals |
| Searching only by tool name | `gh issue list --search "mojo-format"` | Missed issues that described the symptom differently | Search by multiple terms: tool name, error type, and symptom |
| Treating a closed issue as "not tracked" | Assumed closed = resolved = no tracking | #3170 was closed after a partial fix; #3253 and #3365 remained open | A closed issue often spawns open follow-ups — check all three |

## Results & Parameters

**Session result (ProjectOdyssey issue #3212):**

- Found: #3170 (closed — original fix), #3253 (open), #3365 (open)
- Infrastructure already in place: `scripts/mojo-format-compat.sh`, `docs/dev/mojo-glibc-compatibility.md`, comment block in `.pre-commit-config.yaml`
- Change made: Updated line 9 of `.pre-commit-config.yaml` to reference all three issues

**Search commands that found the issues:**

```bash
gh issue list --state open --search "glibc"
gh issue list --state open --search "mojo-format GLIBC"
gh issue list --state open --search "infrastructure mojo-format"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3212, PR #3729 | [notes.md](../references/notes.md) |
