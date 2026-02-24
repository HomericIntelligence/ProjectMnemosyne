# Verification Sequence: Detailed Breakdown

## Overview

This document provides a detailed breakdown of the 6-step pre-flight verification sequence, including expected outputs, failure scenarios, timing information, and decision logic for each check.

---

## Sequence Summary

| Step | Check | Time | Critical | Stop on Fail |
|------|-------|------|----------|--------------|
| 1 | Issue State | 1s | YES | YES |
| 2 | Git History | 2s | NO | NO (warn) |
| 3 | PR Search | 2s | CONDITIONAL | YES (if merged) |
| 4 | Worktree Conflicts | 1s | YES | YES |
| 5 | Branch State | <1s | NO | NO (warn) |
| 6 | Context Gathering | var | NO | NO |

**Total**: ~6 seconds
**Fast-Fail**: Stop at first critical failure (steps 1, 3 if merged, 4)

---

## Check 1: Issue State Verification

### Purpose

Verify the issue is open and not already resolved/closed.

### Command

```bash
gh issue view <number> --json state,title,closedAt
```

### Timing

- **Typical**: 0.8s
- **Max**: 1.5s
- **Network dependent**: Yes
- **Cache available**: No

### Success Criteria

```json
{
  "state": "OPEN",
  "title": "Issue description",
  "closedAt": null
}
```

**Indicators**:

- `state` field is `"OPEN"`
- `closedAt` field is `null`

### Failure Scenarios

#### Scenario 1a: Issue Closed Recently

```json
{
  "state": "CLOSED",
  "title": "Issue description",
  "closedAt": "2026-02-14T15:30:00Z"
}
```

**Action**: STOP immediately
**Message**:

```markdown
❌ CRITICAL: Issue #<number> is CLOSED

Closed: 2026-02-14 (1 day ago)
Reason: Check PR/commit that closed it

Next steps:
1. Find closing PR: gh pr list --search "<number>" --state merged
2. Review PR to understand what was implemented
3. If work is incomplete, create new issue
4. DO NOT proceed with this issue number
```

**Exit Code**: 1 (failure)

---

#### Scenario 1b: Issue Closed Long Ago

```json
{
  "state": "CLOSED",
  "title": "Issue description",
  "closedAt": "2025-11-01T10:00:00Z"
}
```

**Action**: STOP immediately
**Message**:

```markdown
❌ CRITICAL: Issue #<number> is CLOSED

Closed: 2025-11-01 (3 months ago)
Status: Likely stale/resolved

Next steps:
1. Confirm this is the correct issue number
2. Check if issue was duplicated elsewhere
3. Verify you're not working from old assignment
4. DO NOT proceed - work is complete
```

**Exit Code**: 1 (failure)

---

#### Scenario 1c: Issue Not Found

```
Error: issue not found
```

**Action**: STOP immediately
**Message**:

```markdown
❌ CRITICAL: Issue #<number> not found

Possible causes:
1. Incorrect issue number
2. Issue in different repository
3. Private issue without access
4. Issue was deleted

Next steps:
1. Verify issue number: Check assignment/notification
2. Check repository: Confirm you're in correct repo
3. Check permissions: Ensure you have repo access
4. DO NOT proceed without valid issue
```

**Exit Code**: 1 (failure)

---

### Decision Logic

```python
def check_issue_state(issue_number: int) -> bool:
    """
    Check if issue is open and ready for work.

    Returns:
        True if issue is OPEN
        False if issue is CLOSED or not found
    """
    result = run(f"gh issue view {issue_number} --json state,closedAt")

    if result.returncode != 0:
        print(f"❌ CRITICAL: Issue #{issue_number} not found")
        return False

    data = json.loads(result.stdout)

    if data["state"] != "OPEN":
        closed_date = data["closedAt"]
        print(f"❌ CRITICAL: Issue #{issue_number} is CLOSED (closed: {closed_date})")
        return False

    print(f"✅ Issue #{issue_number} is OPEN")
    return True

# Usage
if not check_issue_state(686):
    exit(1)  # STOP - don't proceed to other checks
```

---

## Check 2: Git History Search

### Purpose

Find existing commits that may address this issue (even if not in a PR yet).

### Command

```bash
git log --all --oneline --grep="<number>" | head -5
```

### Timing

- **Typical**: 1.2s
- **Max**: 3.0s (large repos)
- **Network dependent**: No (local git)
- **Cache available**: Yes (git index)

### Success Criteria

```
(empty output - no commits found)
```

**Indicators**:

- No lines returned
- Exit code 0 (grep with no matches returns 1, but piped through head)

### Failure Scenarios

#### Scenario 2a: Recent Commits Found

```
abc1234 feat(metrics): Implement Cost-of-Pass calculation (#686)
def5678 test(metrics): Add tests for CoP metric (#686)
```

**Action**: WARN (don't stop, but inform user)
**Message**:

```markdown
⚠️ WARNING: Existing commits found for issue #686

Commits:
- abc1234 feat(metrics): Implement Cost-of-Pass calculation
- def5678 test(metrics): Add tests for CoP metric

Investigation required:
1. Check if commits are merged:
   git branch --contains abc1234

2. Check if commits are in open PR:
   gh pr list --search "686" --state open

3. Review commit content:
   git show abc1234

4. Determine if work is complete or partial

⚠️ Proceed with caution - may be duplicate work
```

**Exit Code**: 0 (warning, not failure)
**Continue**: Yes (proceed to Check 3)

---

#### Scenario 2b: Old Commits Found

```
xyz9012 wip: Started CoP implementation (#686) - 3 months ago
```

**Action**: WARN + INFO
**Message**:

```markdown
ℹ️ INFO: Old commits found for issue #686

Commits:
- xyz9012 wip: Started CoP implementation (3 months ago)

Likely scenario: Abandoned work

Investigation:
1. Check if branch still exists:
   git branch --list "*686*"

2. Check if commits were pushed:
   git branch -r | grep "686"

3. Review if work was resumed elsewhere:
   gh pr list --search "686" --state all

Recommendation: Treat as fresh start, but review old commits for context
```

**Exit Code**: 0
**Continue**: Yes

---

#### Scenario 2c: Many Commits Found (>5)

```
abc1234 feat(metrics): Implement Cost-of-Pass calculation (#686)
def5678 test(metrics): Add tests for CoP metric (#686)
ghi9012 fix(metrics): Correct CoP edge case (#686)
jkl3456 docs(metrics): Document CoP usage (#686)
mno7890 refactor(metrics): Optimize CoP calculation (#686)
... (more commits not shown due to head -5)
```

**Action**: WARN + INVESTIGATE
**Message**:

```markdown
⚠️ WARNING: Multiple commits found for issue #686 (5+ shown)

This suggests significant work already exists.

Critical checks:
1. Are these commits merged to main?
   git log main --oneline --grep="686"

2. Is there an open or merged PR?
   gh pr list --search "686" --state all

3. Why is issue still open?
   - May be epic/tracking issue
   - Work may be incomplete
   - Issue may need to be closed

⚠️ HIGH RISK - Investigate thoroughly before proceeding
```

**Exit Code**: 0 (warning)
**Continue**: Yes (but with high caution)

---

### Decision Logic

```python
def check_git_history(issue_number: int) -> str:
    """
    Check git history for existing commits.

    Returns:
        "safe" - No commits found
        "warn" - Commits found, investigate
        "stop" - Many commits found, high risk
    """
    result = run(f"git log --all --oneline --grep='{issue_number}' | head -5")
    commits = result.stdout.strip().split('\n')

    if not commits[0]:  # Empty output
        print(f"✅ No existing commits for issue #{issue_number}")
        return "safe"

    commit_count = len(commits)

    if commit_count >= 5:
        print(f"⚠️ WARNING: {commit_count}+ commits found - investigate thoroughly")
        for commit in commits:
            print(f"  - {commit}")
        return "stop"  # Don't actually stop, but flag for review
    else:
        print(f"⚠️ WARNING: {commit_count} commit(s) found")
        for commit in commits:
            print(f"  - {commit}")
        return "warn"

# Usage
history_status = check_git_history(686)
if history_status == "stop":
    print("\n🛑 Recommend manual review before proceeding")
```

---

## Check 3: PR Search

### Purpose

Find merged or open PRs that address this issue.

### Command

```bash
gh pr list --search "<number>" --state all --json number,title,state
```

### Timing

- **Typical**: 1.5s
- **Max**: 2.5s
- **Network dependent**: Yes
- **Cache available**: No (live GitHub API)

### Success Criteria

```json
[]
```

**Indicators**:

- Empty array
- No PRs found in any state

### Failure Scenarios

#### Scenario 3a: Merged PR Found (CRITICAL)

```json
[
  {
    "number": 685,
    "title": "feat(skills): Add issue pre-flight check",
    "state": "MERGED"
  }
]
```

**Action**: STOP immediately
**Message**:

```markdown
❌ CRITICAL: MERGED PR found for issue #686

PR #685: feat(skills): Add issue pre-flight check
State: MERGED

This issue should be closed automatically.

Critical actions:
1. Verify PR actually closes this issue:
   gh pr view 685 --json body | grep -i "closes #686"

2. Check if issue was auto-closed:
   gh issue view 686 --json state

3. If issue is still open, investigate:
   - May be epic/tracking issue (check for task list)
   - PR may not have used "Closes #686" syntax
   - Auto-close may have failed

❌ DO NOT PROCEED - Work is complete
```

**Exit Code**: 1 (critical failure)
**Continue**: NO (STOP)

---

#### Scenario 3b: Open PR Found

```json
[
  {
    "number": 687,
    "title": "feat(skills): Add issue pre-flight check",
    "state": "OPEN"
  }
]
```

**Action**: WARN (coordination needed)
**Message**:

```markdown
⚠️ WARNING: OPEN PR found for issue #686

PR #687: feat(skills): Add issue pre-flight check
State: OPEN

Someone may already be working on this.

Investigation required:
1. Check PR status and age:
   gh pr view 687 --json createdAt,updatedAt,author

2. Review PR conversation:
   gh pr view 687 --comments

3. Check if PR is stale/abandoned:
   - Last updated > 7 days ago = likely stale
   - CI failing = may need help
   - Author inactive = may be abandoned

4. Coordinate with PR author:
   - Comment on PR before starting duplicate work
   - Offer to help/takeover if stale
   - Ask maintainers for guidance

⚠️ PROCEED WITH CAUTION - Coordinate first
```

**Exit Code**: 0 (warning, not critical)
**Continue**: YES (but coordinate first)

---

#### Scenario 3c: Closed (Not Merged) PR Found

```json
[
  {
    "number": 684,
    "title": "feat(skills): Add issue pre-flight check (initial attempt)",
    "state": "CLOSED"
  }
]
```

**Action**: INFO (learn from previous attempt)
**Message**:

```markdown
ℹ️ INFO: CLOSED PR found for issue #686

PR #684: feat(skills): Add issue pre-flight check (initial attempt)
State: CLOSED (not merged)

Previous attempt was not accepted.

Learn from failure:
1. Read PR conversation to understand why closed:
   gh pr view 684 --comments

2. Check CI failures:
   gh pr checks 684

3. Review feedback from maintainers

4. Avoid same mistakes in new attempt

Common reasons for closed PRs:
- Failed CI/tests
- Did not meet requirements
- Superseded by different approach
- Stale/abandoned

✅ Safe to proceed - but learn from previous attempt
```

**Exit Code**: 0
**Continue**: YES

---

#### Scenario 3d: Multiple PRs Found

```json
[
  {
    "number": 684,
    "title": "feat(skills): Add issue pre-flight check (v1)",
    "state": "CLOSED"
  },
  {
    "number": 687,
    "title": "feat(skills): Add issue pre-flight check (v2)",
    "state": "OPEN"
  },
  {
    "number": 690,
    "title": "feat(skills): Pre-flight checklist skill",
    "state": "MERGED"
  }
]
```

**Action**: STOP + INVESTIGATE
**Message**:

```markdown
❌ CRITICAL: Multiple PRs found for issue #686

PRs:
- #684: CLOSED (v1 - failed attempt)
- #687: OPEN (v2 - current attempt)
- #690: MERGED (v3 - accepted)

Merged PR exists - issue should be closed.

Critical investigation:
1. If MERGED PR exists, work is complete:
   gh pr view 690 --json mergedAt,body

2. Verify merged PR closes this issue:
   gh pr view 690 --json body | grep -i "closes #686"

3. Check if issue was auto-closed:
   gh issue view 686 --json state

4. If issue still open, ask maintainer why:
   - May be epic with multiple PRs
   - PR may not have used close syntax
   - Issue may need manual closing

❌ DO NOT PROCEED - Work likely complete
```

**Exit Code**: 1 (critical if merged PR exists)
**Continue**: NO (if merged), YES (if only open/closed)

---

### Decision Logic

```python
def check_pr_search(issue_number: int) -> bool:
    """
    Check for existing PRs (merged, open, closed).

    Returns:
        True if safe to proceed
        False if merged PR found (critical stop)
    """
    result = run(f"gh pr list --search '{issue_number}' --state all --json number,title,state")
    prs = json.loads(result.stdout)

    if not prs:
        print(f"✅ No PRs found for issue #{issue_number}")
        return True

    # Check for merged PRs (critical)
    merged_prs = [pr for pr in prs if pr["state"] == "MERGED"]
    if merged_prs:
        print(f"❌ CRITICAL: MERGED PR(s) found for issue #{issue_number}")
        for pr in merged_prs:
            print(f"  PR #{pr['number']}: {pr['title']}")
        return False  # STOP

    # Check for open PRs (warning)
    open_prs = [pr for pr in prs if pr["state"] == "OPEN"]
    if open_prs:
        print(f"⚠️ WARNING: OPEN PR(s) found for issue #{issue_number}")
        for pr in open_prs:
            print(f"  PR #{pr['number']}: {pr['title']}")
        print("⚠️ Coordinate with PR author before proceeding")

    # Closed (not merged) PRs are informational
    closed_prs = [pr for pr in prs if pr["state"] == "CLOSED"]
    if closed_prs:
        print(f"ℹ️ INFO: CLOSED PR(s) found for issue #{issue_number}")
        for pr in closed_prs:
            print(f"  PR #{pr['number']}: {pr['title']}")
        print("Review previous attempts to avoid same mistakes")

    return True  # Continue (with warnings)

# Usage
if not check_pr_search(686):
    exit(1)  # STOP - merged PR found
```

---

## Check 4: Worktree Conflict Detection

### Purpose

Detect if issue branch is already checked out in a worktree (prevents collision).

### Command

```bash
git worktree list | grep "<number>"
```

### Timing

- **Typical**: 0.3s
- **Max**: 0.8s
- **Network dependent**: No (local filesystem)
- **Cache available**: No (live filesystem query)

### Success Criteria

```
(empty output - no worktree found)
```

**Indicators**:

- grep returns no matches
- Exit code 1 (grep not finding match)

### Failure Scenarios

#### Scenario 4a: Active Worktree Found

```
/home/user/ProjectScylla/.worktrees/issue-686  abc1234 [686-auto-impl]
```

**Action**: STOP (critical conflict)
**Message**:

```markdown
❌ CRITICAL: Worktree exists for issue #686

Location: /home/user/ProjectScylla/.worktrees/issue-686
Branch: 686-auto-impl
Commit: abc1234

Worktree is actively checked out.

Actions:
1. Navigate to existing worktree:
   cd /home/user/ProjectScylla/.worktrees/issue-686

2. Check status:
   git status
   git log -3

3. Decide:
   - If work in progress: Resume there
   - If work complete: Cleanup worktree
   - If work abandoned: Review before deleting

❌ DO NOT create new worktree - use existing or cleanup first
```

**Exit Code**: 1 (critical failure)
**Continue**: NO (STOP)

---

#### Scenario 4b: Multiple Worktrees Found

```
/home/user/ProjectScylla/.worktrees/issue-686-v1  abc1234 [686-initial]
/home/user/ProjectScylla/.worktrees/issue-686-v2  def5678 [686-revised]
```

**Action**: STOP (investigate conflicts)
**Message**:

```markdown
❌ CRITICAL: Multiple worktrees found for issue #686

Worktrees:
1. .worktrees/issue-686-v1 [686-initial]
2. .worktrees/issue-686-v2 [686-revised]

Multiple parallel attempts detected.

Critical investigation:
1. Check each worktree status:
   cd .worktrees/issue-686-v1 && git status
   cd .worktrees/issue-686-v2 && git status

2. Identify which is current:
   - Most recent commits
   - Clean vs dirty status
   - Pushed vs local-only

3. Cleanup old worktrees:
   git worktree remove .worktrees/issue-686-v1

4. Consolidate work if needed

❌ DO NOT proceed until worktrees are consolidated
```

**Exit Code**: 1 (critical)
**Continue**: NO

---

#### Scenario 4c: Stale Worktree (Branch Merged)

```
/home/user/ProjectScylla/.worktrees/issue-685  xyz9012 [685-description]
# (Branch 685-description was merged 2 days ago)
```

**Action**: CLEANUP (automated or manual)
**Message**:

```markdown
🧹 CLEANUP: Stale worktree found for issue #685

Location: .worktrees/issue-685
Branch: 685-description
Status: Merged to main

Cleanup steps:
1. Verify branch is merged:
   git branch --merged main | grep "685"

2. Remove worktree:
   git worktree remove .worktrees/issue-685

3. Delete local branch:
   git branch -d 685-description

4. Delete remote branch (if exists):
   git push origin --delete 685-description

✅ Safe to cleanup - work is merged
```

**Exit Code**: 0 (not critical for current issue)
**Continue**: YES (different issue number)

---

### Decision Logic

```python
def check_worktree_conflicts(issue_number: int) -> bool:
    """
    Check for existing worktrees for this issue.

    Returns:
        True if no worktree exists
        False if worktree conflict detected
    """
    result = run(f"git worktree list | grep '{issue_number}'")

    if result.returncode != 0:  # grep found nothing
        print(f"✅ No worktree conflicts for issue #{issue_number}")
        return True

    worktrees = result.stdout.strip().split('\n')

    if len(worktrees) > 1:
        print(f"❌ CRITICAL: Multiple worktrees found for issue #{issue_number}")
        for wt in worktrees:
            print(f"  - {wt}")
        return False

    worktree_path = worktrees[0].split()[0]
    print(f"❌ CRITICAL: Worktree exists at {worktree_path}")
    print(f"\nNavigate to existing worktree:")
    print(f"  cd {worktree_path}")
    print(f"\nOr remove if stale:")
    print(f"  git worktree remove {worktree_path}")

    return False

# Usage
if not check_worktree_conflicts(686):
    exit(1)  # STOP - worktree conflict
```

---

## Check 5: Branch State Verification

### Purpose

Find orphaned branches from previous work attempts.

### Command

```bash
git branch --list "*<number>*"
```

### Timing

- **Typical**: 0.2s
- **Max**: 0.5s
- **Network dependent**: No (local git)
- **Cache available**: Yes

### Success Criteria

```
(empty output - no branches found)
```

### Failure Scenarios

#### Scenario 5a: Merged Branch Found

```
  686-description
```

```bash
# Check if merged
$ git branch --merged main | grep "686"
  686-description
```

**Action**: CLEANUP (safe to delete)
**Message**:

```markdown
🧹 INFO: Merged branch found for issue #686

Branch: 686-description
Status: Merged to main

Cleanup:
1. Verify merge:
   git branch --merged main | grep "686"

2. Delete local branch:
   git branch -d 686-description

3. Check remote:
   git branch -r | grep "686"

4. Delete remote if exists:
   git push origin --delete 686-description

✅ Safe to cleanup and proceed
```

**Exit Code**: 0 (info)
**Continue**: YES (after cleanup)

---

#### Scenario 5b: Unmerged Local Branch

```
  686-initial-attempt
```

```bash
# Check if merged
$ git branch --merged main | grep "686"
(empty - not merged)
```

**Action**: WARN + BACKUP
**Message**:

```markdown
⚠️ WARNING: Unmerged branch found for issue #686

Branch: 686-initial-attempt
Status: NOT merged to main

Investigation required:
1. Check branch contents:
   git log 686-initial-attempt
   git diff main...686-initial-attempt

2. Determine if work is valuable:
   - Abandoned experiment: Can delete
   - Incomplete work: May want to resume
   - Alternative approach: Keep for reference

3. Backup before proceeding:
   git branch 686-backup-$(date +%Y%m%d) 686-initial-attempt

4. Decide:
   - Resume: git checkout 686-initial-attempt
   - Start fresh: Create new branch
   - Reference: Keep backup, create new

⚠️ PROCEED WITH CAUTION - may have unpushed work
```

**Exit Code**: 0 (warning)
**Continue**: YES (with caution)

---

#### Scenario 5c: Pushed Unmerged Branch

```
  686-feature-attempt
origin/686-feature-attempt
```

**Action**: INVESTIGATE (may be in PR)
**Message**:

```markdown
⚠️ WARNING: Pushed unmerged branch for issue #686

Branches:
- Local: 686-feature-attempt
- Remote: origin/686-feature-attempt

Status: Pushed but not merged

Investigation:
1. Check if branch has open PR:
   gh pr list --head 686-feature-attempt

2. Check remote branch status:
   git fetch origin
   git log main..origin/686-feature-attempt

3. Possible scenarios:
   - PR was closed without merge
   - PR is still open
   - Branch pushed but PR never created
   - Stale/abandoned work

4. Coordinate with team:
   - Check PR status
   - Ask if work should be resumed
   - Cleanup if truly abandoned

⚠️ HIGH CAUTION - coordinate before proceeding
```

**Exit Code**: 0 (warning)
**Continue**: YES (coordinate first)

---

### Decision Logic

```python
def check_branch_state(issue_number: int) -> str:
    """
    Check for existing branches for this issue.

    Returns:
        "safe" - No branches found
        "cleanup" - Merged branches found (safe to delete)
        "warn" - Unmerged branches found (investigate)
    """
    result = run(f"git branch --list '*{issue_number}*'")

    if not result.stdout.strip():
        print(f"✅ No existing branches for issue #{issue_number}")
        return "safe"

    branches = [b.strip().lstrip('* ') for b in result.stdout.strip().split('\n')]

    # Check which branches are merged
    merged_result = run(f"git branch --merged main | grep '{issue_number}'")
    merged_branches = [b.strip() for b in merged_result.stdout.strip().split('\n')] if merged_result.returncode == 0 else []

    unmerged_branches = [b for b in branches if b not in merged_branches]

    if merged_branches:
        print(f"🧹 INFO: Merged branch(es) found - safe to cleanup:")
        for b in merged_branches:
            print(f"  - {b}")
            print(f"    Cleanup: git branch -d {b}")

    if unmerged_branches:
        print(f"⚠️ WARNING: Unmerged branch(es) found:")
        for b in unmerged_branches:
            print(f"  - {b}")
            print(f"    Review: git log {b}")
            print(f"    Backup: git branch {b}-backup {b}")
        return "warn"

    return "cleanup" if merged_branches else "safe"

# Usage
branch_status = check_branch_state(686)
if branch_status == "warn":
    print("\n⚠️ Review unmerged branches before proceeding")
```

---

## Check 6: Context Gathering

### Purpose

Load full issue context including all comments and conversation history.

### Command

```bash
gh issue view <number> --comments
```

### Timing

- **Typical**: 1.0s
- **Max**: 5.0s (issues with many comments)
- **Network dependent**: Yes
- **Cache available**: No

### Success Criteria

```
Issue #<number>: <title>

[Issue body content]

--
author: user1
[Comment 1]

--
author: user2
[Comment 2]
```

**Indicators**:

- Issue body loaded
- All comments included
- Exit code 0

### Information Gathered

#### From Issue Body

- **Requirements**: What needs to be implemented
- **Success Criteria**: How to know when complete
- **Dependencies**: Other issues/PRs that must be done first
- **Deliverables**: Specific outputs required

#### From Comments

- **Clarifications**: Q&A about requirements
- **Approach Decisions**: Chosen implementation strategy
- **Blocker Updates**: New dependencies discovered
- **Scope Changes**: Modifications to original requirements
- **Implementation Notes**: Tips from maintainers/reviewers

### Critical: Always Use --comments Flag

**WRONG**:

```bash
gh issue view 686
# Only loads issue body - misses critical context
```

**RIGHT**:

```bash
gh issue view 686 --comments
# Loads body + all comments - full context
```

### Example Context from Comments

```markdown
Issue #686: Create pre-flight checklist skill

## Objective
Create pre-flight checklist before starting issue work...

[Original issue body]

--
author: maintainer
Comment 1:
Based on team discussion, this should extend #594 issue-completion-verification
rather than replacing it. Focus on adding worktree and branch conflict checks.

--
author: contributor
Comment 2:
Should we also check for stale worktrees from merged issues? I often forget
to cleanup after PR merge.

--
author: maintainer
Comment 3:
@contributor Good catch - yes, add cleanup detection. See git-worktree-workflow
skill for patterns.
```

**Key Insights from Comments**:

1. Extend #594, don't replace (architectural decision)
2. Add worktree conflict detection (new requirement)
3. Include stale worktree cleanup (enhancement)
4. Reference git-worktree-workflow skill (implementation hint)

**Without Comments**: Would miss 3 critical requirements and design decisions.

---

## Complete Sequence Example

### Scenario: Issue #686 (Fresh Start)

```bash
# ========================================
# Pre-Flight Check: Issue #686
# ========================================

# Step 1: Issue State (1s)
$ gh issue view 686 --json state,title,closedAt
{
  "state": "OPEN",
  "title": "Create pre-flight checklist skill for starting issue work",
  "closedAt": null
}
✅ Issue #686 is OPEN

# Step 2: Git History (2s)
$ git log --all --oneline --grep="686" | head -5
(empty)
✅ No existing commits for issue #686

# Step 3: PR Search (2s)
$ gh pr list --search "686" --state all --json number,title,state
[]
✅ No PRs found for issue #686

# Step 4: Worktree Check (1s)
$ git worktree list | grep "686"
(empty)
✅ No worktree conflicts for issue #686

# Step 5: Branch Check (<1s)
$ git branch --list "*686*"
(empty)
✅ No existing branches for issue #686

# Step 6: Context Gathering (variable)
$ gh issue view 686 --comments
[Full issue body and comments loaded]
✅ Context loaded with comments

# ========================================
# Result: ALL CHECKS PASSED
# ========================================

✅ SAFE TO PROCEED with issue #686

Summary:
✅ Issue is OPEN
✅ No existing commits
✅ No conflicting PRs
✅ No worktree conflicts
✅ No orphaned branches
✅ Full context loaded

Next steps:
1. Review issue requirements and comments
2. Create feature branch: git checkout -b 686-preflight-check
3. Begin implementation

Total time: ~6 seconds
```

---

## Automation Script

### Shell Function

```bash
#!/bin/bash
# Pre-flight check automation

preflight() {
  local issue_number=$1

  if [ -z "$issue_number" ]; then
    echo "Usage: preflight <issue-number>"
    return 1
  fi

  echo "========================================="
  echo "Pre-Flight Check: Issue #$issue_number"
  echo "========================================="
  echo

  # Check 1: Issue State
  echo "Check 1/6: Issue State..."
  if ! gh issue view "$issue_number" --json state,title,closedAt > /tmp/preflight_state.json 2>&1; then
    echo "❌ CRITICAL: Issue #$issue_number not found"
    return 1
  fi

  state=$(jq -r '.state' /tmp/preflight_state.json)
  if [ "$state" != "OPEN" ]; then
    echo "❌ CRITICAL: Issue #$issue_number is $state"
    return 1
  fi
  echo "✅ Issue #$issue_number is OPEN"
  echo

  # Check 2: Git History
  echo "Check 2/6: Git History..."
  commits=$(git log --all --oneline --grep="$issue_number" | head -5)
  if [ -n "$commits" ]; then
    echo "⚠️  WARNING: Existing commits found:"
    echo "$commits"
  else
    echo "✅ No existing commits"
  fi
  echo

  # Check 3: PR Search
  echo "Check 3/6: PR Search..."
  prs=$(gh pr list --search "$issue_number" --state all --json number,title,state)
  merged_count=$(echo "$prs" | jq '[.[] | select(.state=="MERGED")] | length')
  if [ "$merged_count" -gt 0 ]; then
    echo "❌ CRITICAL: MERGED PR found"
    echo "$prs" | jq '.[] | select(.state=="MERGED")'
    return 1
  fi

  open_count=$(echo "$prs" | jq '[.[] | select(.state=="OPEN")] | length')
  if [ "$open_count" -gt 0 ]; then
    echo "⚠️  WARNING: OPEN PR found"
    echo "$prs" | jq '.[] | select(.state=="OPEN")'
  else
    echo "✅ No conflicting PRs"
  fi
  echo

  # Check 4: Worktree
  echo "Check 4/6: Worktree Conflicts..."
  if git worktree list | grep -q "$issue_number"; then
    echo "❌ CRITICAL: Worktree exists"
    git worktree list | grep "$issue_number"
    return 1
  fi
  echo "✅ No worktree conflicts"
  echo

  # Check 5: Branches
  echo "Check 5/6: Branch State..."
  branches=$(git branch --list "*$issue_number*")
  if [ -n "$branches" ]; then
    echo "⚠️  WARNING: Existing branches:"
    echo "$branches"
  else
    echo "✅ No existing branches"
  fi
  echo

  # Check 6: Context
  echo "Check 6/6: Loading Context..."
  gh issue view "$issue_number" --comments > /tmp/preflight_context_$issue_number.md
  echo "✅ Context saved to /tmp/preflight_context_$issue_number.md"
  echo

  # Summary
  echo "========================================="
  echo "Pre-Flight Complete: Issue #$issue_number"
  echo "========================================="
  echo "✅ SAFE TO PROCEED"
  echo
  echo "Next steps:"
  echo "  1. Review context: cat /tmp/preflight_context_$issue_number.md"
  echo "  2. Create branch: git checkout -b $issue_number-description"
  echo "  3. Begin implementation"
  echo
}

# Usage: preflight 686
```

---

*This sequence is designed to be fast (6s), reliable (proven patterns), and safe (fast-fail on critical issues).*
