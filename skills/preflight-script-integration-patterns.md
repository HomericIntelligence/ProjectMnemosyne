---
name: preflight-script-integration-patterns
description: "Use when: (1) adding automated preflight safety gates to issue-implementation or worktree-creation workflows, (2) a preflight script produces false positives from PR title/body text search, (3) propagating a safety check from one entry-point skill to a sibling skill"
category: tooling
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [preflight, bash, automation, closingIssuesReferences, script, gh-implement-issue, false-positive]
---

# Preflight Script Integration Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-28 |
| **Objective** | Build and maintain automated preflight check scripts integrated into issue-implementation workflows |
| **Outcome** | Preflight gates worktree creation; 100% adoption enforced; false positives eliminated via `closingIssuesReferences` |
| **Key Learning** | Use `set -uo pipefail` (not `-e`), `\|\| true` for grep, and `closingIssuesReferences` (not free-text PR search) |

Consolidates: `gh-implement-issue-preflight-integration`, `preflight-check-skill-propagation`, `preflight-closing-issues-fix`.

## When to Use

- Adding preflight safety to any automated issue-implementation workflow
- A preflight/guard script uses `gh pr list --search "<number>"` and produces false positives
- A safety check exists in one entry-point skill (`gh-implement-issue`) but not sibling skills (`worktree-create`)
- Gating multi-step workflows on fast-fail checks to prevent wasted work

## Verified Workflow

### Quick Reference

```bash
# Script placement (collocate with skill, not repo root)
<test-path>/skills/github/gh-implement-issue/scripts/preflight_check.sh

# Usage
bash scripts/preflight_check.sh <issue-number>
# Exit 0 = safe to proceed (may include warnings)
# Exit 1 = critical failure — stop immediately

# Correct shell options (not -e)
set -uo pipefail

# Capture grep results safely (avoids exit-1 on no-match aborting script)
WORKTREE_MATCH=$(git worktree list 2>/dev/null | grep "$ISSUE" || true)
```

### Step 1: Create the Script with Correct Shell Options

Place the preflight script collocated with its skill, not at the repo root:

```
<test-path>/skills/github/gh-implement-issue/
├── SKILL.md
└── scripts/
    └── preflight_check.sh   ← new file
```

Use `set -uo pipefail` (not `-e`) so that `grep` returning no match does not abort the script:

```bash
#!/usr/bin/env bash
set -uo pipefail

ISSUE="${1:?Usage: preflight_check.sh <issue-number>}"

# Capture empty results safely — || true prevents exit on no-match
WORKTREE_MATCH=$(git worktree list 2>/dev/null | grep "$ISSUE" || true)
EXISTING_COMMITS=$(git log --all --oneline --grep="#${ISSUE}" 2>/dev/null | head -5 || true)
```

### Step 2: Use `closingIssuesReferences` for PR Check (Check 3)

**Never use `gh pr list --search "<number>"` for issue ownership** — it is full-text search that matches any PR mentioning the number in title or body, causing false positives.

**Before** (false-positive prone):

```bash
PR_JSON=$(gh pr list --search "$ISSUE" --state all --json number,title,state 2>/dev/null)
MERGED_PRS=$(echo "$PR_JSON" | jq -r '.[] | select(.state == "MERGED") | "\(.number): \(.title)"')
OPEN_PRS=$(echo "$PR_JSON"   | jq -r '.[] | select(.state == "OPEN")   | "\(.number): \(.title)"')
```

**After** (precise, authoritative):

```bash
CANDIDATE_JSON=$(gh pr list --state all --json number,title,state --limit 100 2>/dev/null)
MERGED_PRS=""
OPEN_PRS=""
while IFS=$'\t' read -r pr_num pr_title pr_state; do
    [[ -z "$pr_num" ]] && continue
    CLOSES=$(gh pr view "$pr_num" --json closingIssuesReferences \
        --jq '.closingIssuesReferences[].number' 2>/dev/null)
    if echo "$CLOSES" | grep -qx "$ISSUE"; then
        if [[ "$pr_state" == "MERGED" ]]; then
            MERGED_PRS+="${pr_num}: ${pr_title}"$'\n'
        elif [[ "$pr_state" == "OPEN" ]]; then
            OPEN_PRS+="${pr_num}: ${pr_title}"$'\n'
        fi
    fi
done < <(echo "$CANDIDATE_JSON" | jq -r '.[] | [.number,.title,.state] | @tsv')
MERGED_PRS="${MERGED_PRS%$'\n'}"
OPEN_PRS="${OPEN_PRS%$'\n'}"
```

Key: `grep -qx "$ISSUE"` uses full-line match to prevent `73` matching `735`.

### Step 3: Exit Code Discipline

| Exit | Check | Reason |
| ------ | ------- | -------- |
| 1 | Issue CLOSED | Never proceed — work complete or abandoned |
| 1 | PR MERGED (via `closingIssuesReferences`) | Duplicate work risk |
| 1 | Worktree exists | Git prevents two worktrees on same branch |
| 0 | Existing commits | May be partial — user decides |
| 0 | Open PR exists | May be collaborative — user decides |
| 0 | Existing branch | Orphaned — user should review, not blocked |

### Step 4: Write Bash Tests with Mocked `gh`

Mock `gh` as a bash function in a subshell. Use a temp file (not a pipe) to preserve exit codes:

```bash
run_preflight_with_exit() {
    local issue="$1"
    local mock_body="$2"
    local tmpfile
    tmpfile=$(mktemp)
    bash -c "
        ${mock_body}
        export -f gh
        bash '${PREFLIGHT}' '${issue}' 2>&1
    " > "$tmpfile" 2>&1
    LAST_EXIT=$?
    LAST_OUTPUT=$(strip_ansi "$(cat "$tmpfile")")
    rm -f "$tmpfile"
}

# SC2001 is suppressed: bash parameter expansion cannot match \x1b hex escapes.
# shellcheck disable=SC2001
strip_ansi() { echo "$1" | sed 's/\x1b\[[0-9;]*m//g'; }
```

Six test cases to cover:

| Test | Scenario | Expected exit |
| ------ | ---------- | --------------- |
| 1 | No PRs exist | 0 (PASS) |
| 2 | MERGED PR, `closingRef=[issue]` | 1 (STOP) |
| 3 | OPEN PR, `closingRef=[issue]` | 0 (WARN) |
| 4 | MERGED PR mentioning issue in title, empty `closingRef` | 0 (regression test) |
| 5 | Multiple PRs, only one with `closingRef` | 1 (only that PR listed) |
| 6 | PRs exist but `closingRef` targets different issue | 0 (PASS) |

### Step 5: Propagate to Sibling Skills

When a safety gate exists in one entry-point (`gh-implement-issue`) but not a sibling (`worktree-create`):

1. **Verify the script path exists** before referencing it in the target skill docs
2. **Update Quick Reference** — add Step 0 above the create command
3. **Insert Step 1 "Run pre-flight check"** — renumber remaining steps
4. **Sync Error Handling table** — copy the four preflight rows from the source skill exactly
5. **Add References entry** — link to the authoritative preflight skill documentation
6. **Update both skills in the same PR** — if source skill says integration is "future enhancement", update it to reflect that it shipped

### Step 6: Commit and Create PR

```bash
git add scripts/preflight_check.sh SKILL.md tests/test_preflight_check.sh
git commit -m "fix(preflight): use closingIssuesReferences for precise PR-issue matching

Closes #<issue-number>"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<issue-number>"
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `set -e` with grep in script | Used `set -e` and ran `git log ... \| grep "$ISSUE" \| head -5` | `grep` returns exit code 1 when no matches found; script aborted silently, looking like a critical failure | Use `set -uo pipefail` and capture with `\|\| true`: `EXISTING_COMMITS=$(...\|\| true)` |
| Treating open PRs as critical failures | Hard-stopped on any open PR | An open PR may be stale, abandoned, or collaborative — blocks legitimate handoff scenarios | Open PR → WARN (exit 0). Only MERGED PRs closing the issue are critical (exit 1) |
| Script at repo root or top-level `scripts/` | Placed `preflight_check.sh` at `scripts/preflight_check.sh` | Breaks discoverability and portability; doesn't communicate skill ownership | Collocate scripts with their skill: `<test-path>/skills/<skill-name>/scripts/` |
| Using `gh pr list --search "<issue-number>"` for ownership | Free-text PR search for issue number | Full-text search matches any PR mentioning the number in title or body — false positives on "Fix issue 735-related bug" for issue 735 | Use `closingIssuesReferences` via `gh pr view "$pr_num" --json closingIssuesReferences` |
| Pipe to preserve exit code in bash tests | `bash -c "... bash $PREFLIGHT" \| cat; echo $?` | Pipe runs in subshell, `$?` is lost | Write output to temp file with `> "$tmpfile" 2>&1`, capture `LAST_EXIT=$?` after |
| ANSI colors breaking test assertions | Grep for `[PASS]` / `[STOP]` in script output | Color codes embedded in output caused silent mismatches | Strip ANSI before assertions using `strip_ansi()` with `sed 's/\x1b\[...//g'` |
| Forgetting to update the downstream skill's docs | Updated `preflight_check.sh` but left `issue-preflight-check` SKILL.md unchanged | Source skill still said integration was a "future enhancement" after shipping | Update both the referring skill and the referenced skill in the same PR |

## Results & Parameters

### Script Location Pattern

```
<test-path>/skills/github/gh-implement-issue/scripts/preflight_check.sh
```

### Check Sequence Summary

| Check | Type | Exit on failure |
| ------- | ------ | ---------------- |
| 1. Issue state | `gh issue view "$ISSUE" --json state,title,closedAt` | exit 1 (CLOSED) |
| 2. Existing commits | `git log --all --oneline --grep="#${ISSUE}" \| head -5` | exit 0 (WARN) |
| 3. PR via `closingIssuesReferences` | Two-phase lookup (see above) | exit 1 (MERGED), exit 0 (OPEN) |
| 4. Worktree conflict | `git worktree list \| grep "$ISSUE"` | exit 1 |
| 5. Existing branches | `git branch --list "*${ISSUE}*"` | exit 0 (WARN) |
| 6. Context gathering | `gh issue view "$ISSUE" --comments` | N/A (info only) |

### Key Parameters

| Parameter | Value |
| ----------- | ------- |
| PR fetch limit | `--limit 100` (avoids timeout on large repos) |
| `closingIssuesReferences` jq expression | `.closingIssuesReferences[].number` |
| grep for exact issue match | `grep -qx "$ISSUE"` (full-line match, avoids 73 matching 735) |
| Total runtime (checks 1-5) | ~6 seconds |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issue #735 — integrate preflight into gh-implement-issue | PR #917, 100% adoption enforced |
| ProjectScylla | Issue #802 — fix false positives in Check 3 | PR #912, 6 bash tests passing |
| ProjectScylla | Issue #803 — propagate preflight to worktree-create | PR #917, docs-only change |
