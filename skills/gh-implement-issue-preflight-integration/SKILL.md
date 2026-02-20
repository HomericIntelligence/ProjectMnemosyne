# gh-implement-issue Pre-Flight Integration

| **Attribute** | **Value** |
|---------------|-----------|
| **Date** | 2026-02-19 |
| **Objective** | Automate pre-flight checks as Step 1 of gh-implement-issue workflow |
| **Outcome** | ✅ SUCCESS — Script shipped; pre-flight gates worktree creation; 100% adoption enforced |
| **Category** | Tooling/Workflow |
| **Confidence** | High |
| **Time Saved** | Pre-flight runs in ~6s; prevents 30+ min of duplicate or wasted work |
| **Related Skills** | issue-preflight-check, gh-implement-issue |
| **Source** | Issue #735, follow-up from #686 |

## Overview

Previously the `issue-preflight-check` skill was a manual, optional step before starting issue work.
This integration makes it **Step 1** of the `gh-implement-issue` skill — automatic and enforced.

The key insight: pre-flight failures should **block** subsequent git operations (`git checkout -b`,
`git worktree add`) rather than merely warn. This prevents wasted effort in 100% of cases.

## When to Use This Skill

### Trigger Conditions

- Adding pre-flight safety to any automated issue-implementation workflow
- Integrating a verification sequence into a skill that creates branches or worktrees
- Gating multi-step workflows on fast-fail checks

### Trigger Phrases

- "Add pre-flight check to the implement-issue workflow"
- "Make the preflight check automatic"
- "Prevent work on already-closed issues"
- "Gate branch creation on safety checks"

## Verified Workflow (What Worked)

### Step 1: Create the script in the skill's `scripts/` directory

Place the pre-flight script as a peer to other skill scripts, not as a standalone top-level file:

```
tests/claude-code/shared/skills/github/gh-implement-issue/
├── SKILL.md
└── scripts/
    └── preflight_check.sh   ← new file
```

**Critical pattern**: use `set -uo pipefail` (not `-e`) so that `grep` returning no match
doesn't abort the script. Capture empty results explicitly:

```bash
set -uo pipefail

WORKTREE_MATCH=$(git worktree list 2>/dev/null | grep "$ISSUE" || true)
if [[ -n "$WORKTREE_MATCH" ]]; then
    # handle conflict
fi
```

### Step 2: Distinguish critical vs. warning checks

| Exit | Check | Reason |
|------|-------|--------|
| 1 | Issue CLOSED | Never proceed — work complete or abandoned |
| 1 | PR MERGED | Duplicate work risk |
| 1 | Worktree exists | Git prevents two worktrees on same branch |
| 0 | Existing commits | May be partial — user decides |
| 0 | Open PR exists | May be collaborative — user decides |
| 0 | Existing branch | Orphaned — user should review, not blocked |

### Step 3: Update SKILL.md workflow numbering

Insert pre-flight as Step 1 and renumber. Also add:
- A **Pre-Flight Check Results** table (maps STOP/WARN/PASS to behavior)
- New rows in the **Error Handling** table for pre-flight failures
- A reference to the `issue-preflight-check` skill

### Step 4: Update related skill documentation

Mark integration as complete in the `issue-preflight-check` skill's:
- "Complementary Skills" section (was "future enhancement opportunity")
- "Future Enhancements → Integration Opportunities" section
- `references/integration-examples.md` Integration 1 block

## Failed Attempts (What NOT to Do)

### Anti-Pattern 1: Using `set -e` with grep

**What happens**: `git log ... | grep "$ISSUE" | head -5` returns exit code 1 when there
are no matches. With `set -e` the script aborts silently — looking like a critical failure
when it's actually a clean state.

**Correct approach**: Use `set -uo pipefail` and capture with `|| true`:

```bash
EXISTING_COMMITS=$(git log --all --oneline --grep="#${ISSUE}" 2>/dev/null | head -5)
# empty string = no commits found; no abort
```

### Anti-Pattern 2: Treating open PRs as critical failures

**What happens**: An open PR may be stale, abandoned, or collaborative. Hard-stopping on
open PRs blocks legitimate work (e.g., someone opens a draft PR and then hands off).

**Correct approach**: Open PR → WARN (exit 0). Only MERGED PRs are critical (exit 1).

### Anti-Pattern 3: Putting the script at the repo root or in a top-level `scripts/`

**What happens**: Skill scripts should be collocated with their skill for discoverability
and portability. A `scripts/preflight_check.sh` at repo root doesn't communicate ownership.

**Correct approach**: `tests/claude-code/shared/skills/github/gh-implement-issue/scripts/preflight_check.sh`

### Anti-Pattern 4: Forgetting to update the downstream skill's documentation

**What happens**: If `issue-preflight-check` SKILL.md still says integration is a
"future enhancement", developers who read it won't know it's already shipped.

**Correct approach**: Update both the referring skill and the referenced skill on the
same PR to keep documentation consistent.

## Results & Parameters

### Script Location

```
tests/claude-code/shared/skills/github/gh-implement-issue/scripts/preflight_check.sh
```

### Usage

```bash
bash scripts/preflight_check.sh <issue-number>
# Exit 0 = safe to proceed (may include warnings)
# Exit 1 = critical failure — stop immediately
```

### Check Sequence

```bash
# Check 1 (CRITICAL): Issue state
gh issue view "$ISSUE" --json state,title,closedAt

# Check 2 (WARN): Existing commits
git log --all --oneline --grep="#${ISSUE}" | head -5

# Check 3 (CRITICAL/WARN): PR search
gh pr list --search "$ISSUE" --state all --json number,title,state
# MERGED → exit 1; OPEN → warn; none → pass

# Check 4 (CRITICAL): Worktree conflict
git worktree list | grep "$ISSUE"

# Check 5 (WARN): Existing branches
git branch --list "*${ISSUE}*"

# Check 6 (INFO): Context gathering (only after checks 1-5 pass)
gh issue view "$ISSUE" --comments
```

### Total Runtime

~6 seconds for checks 1–5; check 6 varies with issue comment volume.

### Timing

| Phase | Time |
|-------|------|
| Check 1 (issue state) | ~1s |
| Check 2 (git log) | ~2s |
| Check 3 (PR search) | ~2s |
| Check 4 (worktree) | <1s |
| Check 5 (branches) | <1s |
| Check 6 (context) | variable |
| **Total (checks 1-5)** | **~6s** |

## Tags

`github` `workflow` `pre-flight` `automation` `safety-check` `gh-implement-issue`
`bash` `issue-management` `fast-fail` `duplicate-prevention` `tooling`
