---
name: ci-cd-cross-repo-skill-maintenance
description: "Fix conflicting rename/refactor PRs and coordinate skill definition updates across repositories. Use when: (1) a rename PR shows CONFLICTING status after main advances, (2) a skill definition in repo A needs updating because of changes in repo B, (3) batch-resolving homogeneous conflicts in a refactor PR."
category: ci-cd
date: 2026-03-26
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - cross-repo
  - skill-maintenance
  - rename-refactor
  - conflict-resolution
  - coordinated-prs
---

# Cross-Repo Skill Maintenance

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-26 |
| **Objective** | Fix a conflicting rename PR in ProjectMnemosyne and coordinate a skill definition update in ProjectHephaestus |
| **Outcome** | PR #1061 rebased and MERGEABLE, skill definition PR #203 created in ProjectHephaestus |
| **Verification** | verified-local |

## When to Use

- A rename/refactor PR that touches many files shows CONFLICTING merge state after main advances
- All conflicts follow the same pattern (e.g., both sides changed the same text references being renamed)
- A skill definition in one repo (e.g., ProjectHephaestus) needs a coordinated update because of changes in another repo (e.g., ProjectMnemosyne)
- You need to validate a plugin repository after resolving conflicts to ensure no structural corruption

## Verified Workflow

### Quick Reference

```bash
# 1. Rebase conflicting rename PR
git fetch origin && git checkout <branch>
git rebase origin/main

# 2. Batch-resolve homogeneous conflicts with --theirs
for f in $(git diff --name-only --diff-filter=U); do
  git checkout --theirs "$f" && git add "$f"
done
git rebase --continue

# 3. Validate plugin repo integrity
python3 scripts/validate_plugins.py

# 4. Push and verify merge state
git push --force-with-lease
gh pr view <number> --json mergeStateStatus --jq '.mergeStateStatus'
```

### Detailed Steps

**Phase 1: Fix the conflicting rename PR**

1. Fetch latest main and check out the PR branch:
   ```bash
   git fetch origin
   git checkout <branch>
   git rebase origin/main
   ```

2. When rebase stops at a conflict, check if all conflicts follow the same pattern. For a rename PR, conflicts are almost always the same: both sides changed the text being renamed.

3. Batch-resolve with `--theirs` (the PR's version is the rename target):
   ```bash
   # List conflicting files
   git diff --name-only --diff-filter=U

   # Resolve all with --theirs (the rename is the PR's intent)
   for f in $(git diff --name-only --diff-filter=U); do
     git checkout --theirs "$f" && git add "$f"
   done
   git rebase --continue
   ```

4. Repeat for each rebase step if multiple commits conflict. The pattern is the same each time.

5. Validate and push:
   ```bash
   python3 scripts/validate_plugins.py  # e.g., 1059/1059 valid
   git push --force-with-lease
   ```

6. Verify PR is now MERGEABLE:
   ```bash
   gh pr view <number> --json mergeStateStatus --jq '.mergeStateStatus'
   # Expected: MERGEABLE
   ```

**Phase 2: Coordinate the skill definition update in the second repo**

1. Clone or update the skill-definition repo (e.g., ProjectHephaestus):
   ```bash
   gh repo clone HomericIntelligence/ProjectHephaestus /tmp/ProjectHephaestus
   cd /tmp/ProjectHephaestus
   git checkout -b update-skill-definition origin/main
   ```

2. Edit the skill definition to reflect the new behavior, naming, or execution model.

3. Commit, push, and create a PR linking to the original rename PR:
   ```bash
   git add <files>
   git commit -m "feat(skills): update <skill> definition for <change>"
   git push -u origin update-skill-definition
   gh pr create --title "Update <skill> definition" \
     --body "Coordinates with HomericIntelligence/ProjectMnemosyne#<number>"
   gh pr merge --auto --rebase
   ```

**Phase 3: Verify both PRs**

- Check that CI passes on both PRs independently
- Neither PR should block the other (they are independently mergeable)
- If the rename PR merges first, the skill definition PR may need a trivial rebase

### Decision: When to use --theirs vs manual merge

```text
Is the PR a rename/refactor where the intent is to change text references?
+-- YES: Are all conflicts in the renamed text (not structural changes)?
|   +-- YES -> Use --theirs for all conflicts (the rename IS the intent)
|   +-- NO  -> Manual merge for structural conflicts, --theirs for rename text
+-- NO -> Use standard conflict resolution (manual or --ours as appropriate)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked first try | N/A | Batch `--theirs` was correct because all 8 conflicts followed the identical rename pattern |

## Results & Parameters

### Conflict Resolution Stats

```yaml
pr_number: 1061
repo: HomericIntelligence/ProjectMnemosyne
branch: refactor/rename-to-mnemosyne-v2
conflicts_found: 8
resolution_strategy: "--theirs for all (homogeneous rename conflicts)"
validation_result: "1059/1059 plugins valid"
final_merge_state: MERGEABLE
```

### Cross-Repo Coordination

```yaml
primary_pr:
  repo: ProjectMnemosyne
  number: 1061
  change: "Rename retrospective -> learn across 41 files"

secondary_pr:
  repo: ProjectHephaestus
  number: 203
  change: "Add Execution Model section to /learn skill definition"

dependency: none  # PRs are independently mergeable
coordination: "Secondary PR references primary for context"
```

### Key Patterns

| Pattern | Description |
|---------|-------------|
| Homogeneous conflicts | All conflicts in a rename PR tend to be the same pattern -- safe to batch-resolve |
| `--theirs` for renames | The PR branch has the correct renamed text; main has the old text -- always take theirs |
| Validate after resolve | Always run the repo's validation script before pushing (e.g., `validate_plugins.py`) |
| Independent PRs | Cross-repo updates should not block each other -- file them as separate PRs |
| Link PRs for context | Reference the related PR in the body so reviewers understand the coordination |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | PR #1061, rename retrospective to learn (8 conflicts resolved) | 2026-03-26 session |
| ProjectHephaestus | PR #203, add Execution Model section to /learn skill | 2026-03-26 session |

## References

- [tooling-plugin-command-codebase-rename](tooling-plugin-command-codebase-rename.md) - The rename operation itself (41-file content changes)
- [mass-pr-rebase-conflict-resolution](mass-pr-rebase-conflict-resolution.md) - Batch-rebasing many PRs with diverse conflicts
- [pixi-lock-rebase-regenerate](pixi-lock-rebase-regenerate.md) - Related: lock file regeneration after rebase
