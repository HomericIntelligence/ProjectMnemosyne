---
name: batch-pr-conflict-resolution-and-merge
description: "Use when: (1) 2-10 stale branches with closed or unmerged PRs need rebasing onto main after main advanced significantly, (2) conflict resolution requires understanding whether main already subsumes the branch's changes vs. integrating complementary work, (3) each branch has 1-3 commits and the decision is subsume vs. integrate (not mechanical rebase), (4) pre-commit/lint failures block auto-merge after rebase, (5) targeted module-level tests must verify resolution without running the full suite."
category: ci-cd
date: 2026-04-05
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: []
---
# Batch PR Conflict Resolution and Merge

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-05 |
| **Objective** | Rebase 3 stale issue branches (29, 31, 32) with closed PRs onto main, resolve conflicts intelligently, and create + merge 6 PRs total |
| **Outcome** | All 3 branches resolved and merged; 6 PRs created and merged with CI passing |

## When to Use

- Small batch (2–10) of stale issue branches where main advanced significantly (100+ commits)
- Each branch has 1–3 commits and conflicts exist because main evolved the same code
- The key question per branch is: **does main already subsume this fix, or is this complementary work?**
- Branches had original PRs that were closed (not merged) and need fresh PRs
- Pre-commit or lint failures block auto-merge after rebase
- You need targeted module-level tests — not the full suite — to verify each conflict resolution

**Common trigger phrases:**
- "Rebase these old branches and create PRs"
- "These old PRs were closed, rebase and re-open"
- "These branches conflict, figure out what to keep"
- "Batch merge these stale branches"

## Verified Workflow

### Quick Reference

```bash
# For each branch: examine conflict, decide subsume vs. integrate, resolve, test, push, PR
git fetch origin
git checkout -b temp-N origin/BRANCH_NAME

# Understand what main did vs. what branch did
git log --oneline origin/main..HEAD    # branch-only commits
git diff origin/main...HEAD            # branch's net diff vs. merge-base

# Rebase
git rebase origin/main
# On conflict — examine both sides before resolving
git diff HEAD                          # see unmerged

# Run targeted tests (not full suite)
pixi run pytest tests/unit/module_under_change/ -v

# Push and create PR
git push --force-with-lease origin temp-N:BRANCH_NAME
gh pr create --title "fix(module): description" --body "Closes #ISSUE"
gh pr merge PR_NUM --auto --rebase
```

### Phase 1: Triage Branches — Classify Before Touching Anything

Before rebasing, classify each branch:

```bash
git fetch origin

for branch in BRANCH_1 BRANCH_2 BRANCH_3; do
  ahead=$(git rev-list --count origin/main..origin/$branch 2>/dev/null)
  behind=$(git rev-list --count origin/$branch..origin/main 2>/dev/null)
  echo "$branch: $ahead ahead, $behind behind"
  git log --oneline origin/main..origin/$branch
done
```

**Classification outputs:**
- `0 ahead` → already in main, skip
- `N ahead, M behind` → has unique commits, needs rebase and conflict analysis

### Phase 2: Understand the Intent of Each Branch

For each branch that needs work, examine what it was trying to do:

```bash
# What did the branch commit(s) do?
git log --oneline origin/main..origin/BRANCH
git show origin/BRANCH                 # full diff of single-commit branches

# What does main look like in the same area now?
git show origin/main:path/to/affected/file.py

# Does main already contain the fix?
git diff origin/main...origin/BRANCH   # net diff from common ancestor
```

**Decision framework — subsume vs. integrate:**

| Signal | Decision |
|--------|----------|
| Main's implementation is a complete superset (same fix + more) | Take main's version; integrate any unique tests from branch |
| Branch adds logic not in main (e.g., new parser, unique validation) | Integrate branch's approach into main's structure |
| Branch and main both modified the same function differently | Semantic merge: keep main's structure + branch's unique additions |
| Branch's changes are line-for-line already in main | Close branch as superseded (empty diff after rebase) |

### Phase 3: Resolve Conflicts Semantically

**Never use blind `--theirs` or `--ours`.** Read both sides:

```bash
# During rebase conflict
git status                             # See which files are conflicted (UU = unmerged)
cat CONFLICTED_FILE                    # See conflict markers

# Understand conflict markers:
# <<<<<<< HEAD (main's version)
# =======
# >>>>>>> commit (branch's version)
```

**Resolution patterns by scenario:**

**Scenario A: Main's implementation subsumes the branch fix**
```bash
# Take main's implementation but integrate branch's unique test
git checkout --ours src/module.py      # Take main's impl
git add src/module.py
# Manually add branch's unique test to the test file
# Edit test file to merge in branch's test case
git add tests/unit/test_module.py
GIT_EDITOR=true git rebase --continue
```

**Scenario B: Branch adds genuine new value (new parser, new validation)**
```bash
# Read branch's implementation carefully
git show STASH_OR_BRANCH:path/file.py

# Apply branch's approach into main's current structure
# Edit the file to integrate branch's unique code
# (Don't blindly take --theirs; adapt to main's current API)
git add path/file.py
GIT_EDITOR=true git rebase --continue
```

**Scenario C: Both sides touched the same function**
```bash
# Keep main's function signature and structure (it's more evolved)
# Integrate the branch's logic/fix into the main's version
# Verify: grep for conflict markers after resolution
grep -c "<<<<<<\|>>>>>>" RESOLVED_FILE || echo "0 — clean"
```

**Key principle**: Use a Sonnet-tier agent for conflict analysis — Haiku is sufficient for mechanical rebases but misses integration nuances.

### Phase 4: Verify With Targeted Tests

After resolving conflicts for each branch, run targeted tests — not the full suite:

```bash
# Run only tests for the module that was changed
pixi run pytest tests/unit/path/to/module/ -v

# Example: if config/ was changed
pixi run pytest tests/unit/config/ -v

# Example: if utils/ was changed  
pixi run pytest tests/unit/utils/ -v
```

**Expected**: 39–66 tests per module, all passing. Do not run the full suite between branches — it wastes time and obscures which branch introduced a failure.

### Phase 5: Fix Pre-commit Failures Before Pushing

If pre-commit or lint hooks fail after rebase:

```bash
# Auto-fix all hooks
pre-commit run --all-files

# Check what changed
git status --short
git diff

# Stage only modified tracked files
git add -u
git commit -m "fix(lint): apply pre-commit auto-fixes after rebase"

# Then push
git push --force-with-lease origin BRANCH_NAME
```

**CRITICAL**: After any `git push --force-with-lease`, GitHub silently clears auto-merge. Always re-enable:

```bash
git push --force-with-lease origin BRANCH_NAME
gh pr merge PR_NUM --auto --rebase     # Re-enable after force-push
```

### Phase 6: Create PR and Enable Auto-merge

```bash
# Create PR for the rebased branch
gh pr create \
  --title "fix(module): description of fix" \
  --body "$(cat <<'EOF'
Closes #ISSUE_NUMBER

## Summary
- Brief description of what this PR does

## Conflict Resolution
- Describe how conflicts were resolved (subsume vs. integrate)
EOF
)"

# Enable auto-merge
gh pr merge PR_NUM --auto --rebase

# Verify auto-merge is active
gh pr view PR_NUM --json autoMergeRequest
# Should show mergeMethod: "rebase", NOT null
```

### Phase 7: Batch Pattern — Process Branches Sequentially

For 3–10 branches, process sequentially (not in parallel):

```bash
for branch in BRANCH_A BRANCH_B BRANCH_C; do
  # 1. Create temp tracking branch
  git checkout -b temp-$branch origin/$branch

  # 2. Attempt rebase
  git rebase origin/main || {
    # 3. Resolve conflicts (Phase 3)
    # 4. Continue rebase
    GIT_EDITOR=true git rebase --continue
  }

  # 5. Targeted tests (Phase 4)
  pixi run pytest tests/unit/relevant_module/ -v

  # 6. Pre-commit (Phase 5)
  pre-commit run --all-files && git add -u && git commit -m "fix: pre-commit" || true

  # 7. Push
  git push --force-with-lease origin temp-$branch:$branch

  # 8. PR and auto-merge (Phase 6)
  PR=$(gh pr create --title "..." --body "..." | tail -1 | grep -oP '\d+')
  gh pr merge $PR --auto --rebase

  # 9. Return to main
  git switch main
  git branch -d temp-$branch
done
```

**Wait for each PR to merge before starting the next** if branches touch overlapping files. If branches are fully independent (different modules), they can be pushed simultaneously.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Unguided rebase without examining main | Agent rebased and reported conflicts without analyzing whether main already had the fix | Produced incorrect resolutions (kept branch's inferior implementation, or missed unique tests) | Always read what main's implementation does before resolving — subsume vs. integrate decision first |
| Auto-merge blocking after pre-commit failure | PRs had pre-commit/lint failures; enabled auto-merge before fixing them | CI failed → auto-merge never triggered | Run `pre-commit run --all-files` and fix before pushing; after force-push, re-enable auto-merge |
| Using Haiku agent for conflict resolution | Delegated semantic conflict resolution to Haiku | Haiku missed integration nuances — took `--ours` blindly when branch had genuine new value (PEP 508 parser) | Use Sonnet for conflict analysis; Haiku only for mechanical fixes (format, lint) |
| Running full test suite after each branch | `pixi run pytest tests/` for every branch | Takes 10-15x longer than targeted tests; masks which branch introduced failures | Run targeted module-level tests only: `pytest tests/unit/changed_module/` |
| `--force` instead of `--force-with-lease` | Used `--force` on rebased branch | Unsafe; no protection against overwriting concurrent remote changes | Always use `--force-with-lease` — aborts if remote has changed since last fetch |

## Results & Parameters

### Scale Reference

| Scale | Method | Est. Time |
|-------|--------|-----------|
| 1–3 branches, 1 commit each | Sequential temp-branch rebase + semantic resolution | ~20-30 min/branch |
| 3–10 branches, 1–3 commits | Sequential with targeted tests per branch | ~1.5-3 hours total |
| 10+ branches | Use `batch-pr-rebase-conflict-resolution-workflow` with Myrmidon swarm | 30+ min |

### Key Commands Reference

```bash
# Examine branch intent before rebasing
git log --oneline origin/main..origin/BRANCH
git show origin/BRANCH
git diff origin/main...origin/BRANCH

# Rebase + resolve
git rebase origin/main
grep -c "<<<<<<\|>>>>>>" CONFLICTED_FILE  # Verify clean after resolution

# Targeted tests (not full suite)
pixi run pytest tests/unit/MODULE/ -v

# Pre-commit fix
pre-commit run --all-files && git add -u && git commit -m "fix: pre-commit" || true

# Force-push + re-enable auto-merge (always together)
git push --force-with-lease origin BRANCH
gh pr merge PR_NUM --auto --rebase

# Verify auto-merge
gh pr view PR_NUM --json autoMergeRequest
```

### Conflict Resolution Decision Tree

```
Branch conflicts with main on file X:
├── Does main's version already contain the fix this branch adds?
│   ├── YES → Take main's version (--ours for impl); integrate any unique branch tests
│   └── NO → Does the branch add something genuinely new?
│       ├── YES → Integrate branch's approach into main's current structure
│       └── BOTH sides differ → Keep main's structure + add branch's unique logic
│
└── After resolution: Does git diff origin/main show any unique content?
    ├── YES → Proceed with PR
    └── NO  → Branch is superseded; close without PR
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issues #29, #31, #32 — 3 stale branches, 125 commits behind main, 6 PRs created and merged, 2026-04-05 | verified-ci; all PRs merged with CI passing |

## References

- [batch-pr-rebase-conflict-resolution-workflow.md](./batch-pr-rebase-conflict-resolution-workflow.md) — Mass rebase for 10–160+ PRs with Myrmidon swarm
- [batch-pr-ci-fix-workflow.md](./batch-pr-ci-fix-workflow.md) — CI failure diagnosis and batch fix patterns
