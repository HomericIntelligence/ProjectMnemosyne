---
name: bulk-issue-filing
description: "Bulk create GitHub issues from code markers (TODO/FIXME/DEPRECATED/NOTE)"
category: tooling
date: 2026-01-01
---

# Bulk Issue Filing

File GitHub issues in bulk from code markers (TODO, FIXME, DEPRECATED, NOTE).

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-01 |
| Objective | Create GitHub issues for 357+ code markers across a codebase |
| Outcome | Successfully filed 36 issues with proper categorization and linking |
| Source | ProjectOdyssey cleanup initiative |

## When to Use

- You have many TODO/FIXME/DEPRECATED/NOTE markers to track
- You want to systematically address technical debt
- You need to create a master tracking issue with child issues
- You're cleaning up a codebase and want GitHub visibility

## Verified Workflow

### Step 1: Discover All Markers

```bash
# Find all code markers
grep -rn "TODO\|FIXME\|DEPRECATED\|NOTE" --include="*.mojo" --include="*.py" .

# Count by type
grep -rn "TODO" --include="*.mojo" . | wc -l
grep -rn "FIXME" --include="*.mojo" . | wc -l
grep -rn "DEPRECATED" --include="*.mojo" . | wc -l
grep -rn "NOTE" --include="*.mojo" . | wc -l
```

### Step 2: Categorize Markers

Organize markers into batches:

| Batch | Type | Action |
|-------|------|--------|
| DEPRECATED | Files/aliases to delete | File deletion issues |
| Blocked TODOs | Depend on other issues | Create tracking issues |
| Already tracked | Reference existing issues | Skip |
| Templates | Intentional placeholders | Document, don't track |
| NOTEs | Informational | Convert to docstrings or keep |
| Actionable TODOs | Need implementation | Create individual issues |

### Step 3: Check Available Labels

```bash
# CRITICAL: Verify labels exist before using
gh label list

# Common labels to use:
# cleanup, testing, documentation, enhancement, bug
```

### Step 4: Create Master Tracking Issue

```bash
gh issue create \
  --title "[Cleanup] Master: Code marker cleanup tracking" \
  --body "$(cat <<'EOF'
## Objective
Track all code marker cleanup issues.

## Scope
- 357+ code markers (TODO, FIXME, DEPRECATED, NOTE)
- Categorized into logical batches

## Child Issues
<!-- Add links as issues are created -->

## Labels
cleanup
EOF
)" \
  --label cleanup
```

### Step 5: Batch Create Issues

Use heredoc for proper formatting:

```bash
gh issue create \
  --title "[Cleanup] Delete deprecated schedulers.mojo" \
  --body "$(cat <<'EOF'
## Objective
Delete deprecated scheduler file.

## Context
- **File**: `shared/training/schedulers.mojo`
- **Marker**: `DEPRECATED`
- **Original Text**: `# DEPRECATED: Use shared/training/lr_scheduler.mojo instead`

## Deliverables
- [ ] Verify no imports reference this file
- [ ] Delete the file
- [ ] Update any __init__.mojo exports

## Success Criteria
- [ ] File deleted
- [ ] Tests pass
- [ ] Pre-commit passes

## Parent Issue
Part of #<master-issue-number>
EOF
)" \
  --label cleanup
```

### Step 6: Batch Pattern for Multiple Issues

```bash
# Create multiple issues efficiently with a loop
for file in file1.mojo file2.mojo file3.mojo; do
  gh issue create \
    --title "[Cleanup] Delete deprecated ${file}" \
    --body "..." \
    --label cleanup
  sleep 1  # Avoid rate limiting
done
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Used non-existent labels | `could not add label: 'deprecated' not found` | Always run `gh label list` first |
| Created issues without parent reference | Issues orphaned, hard to track | Always link to master tracking issue |
| Mixed implementation with issue filing | Scope creep, couldn't finish | Separate issue filing from implementation |
| Filed issues for template placeholders | Created noise | Skip intentional placeholders |
| Filed issues for already-tracked items | Duplicated effort | Check if TODO references existing issue |
| No categorization | 357+ undifferentiated issues | Batch by type first |

## Results & Parameters

### Issue Template

```markdown
## Objective
[Brief description - what needs to be done]

## Context
- **File**: `[path/to/file.ext]`
- **Line(s)**: [line numbers]
- **Marker**: `[TODO|FIXME|DEPRECATED|NOTE]`
- **Original Text**: `[exact marker content]`

## Deliverables
- [ ] [Specific change 1]
- [ ] [Specific change 2]

## Success Criteria
- [ ] Marker addressed
- [ ] Tests pass
- [ ] Pre-commit passes

## Parent Issue
Part of #[master-issue-number]
```

### Batch Statistics from Session

| Category | Count | Issues Created |
|----------|-------|----------------|
| DEPRECATED files | 7 | #3060-#3066 |
| Blocked TODOs | 32 | #3067-#3069, #3077-#3079 |
| Template placeholders | 30 | #3070, #3080 (tracking only) |
| NOTE cleanup | 36 | #3071-#3076 |
| Actionable TODOs | 50 | #3081-#3094 |
| **Total** | **155** | **36 issues** |

### Key Commands

```bash
# Check available labels
gh label list

# Create issue with heredoc
gh issue create --title "..." --body "$(cat <<'EOF'
...
EOF
)" --label cleanup

# View created issues
gh issue list --label cleanup

# Link issues
# Use "Part of #<number>" in body
# Use "Closes #<number>" for PRs
```

## Platform Notes

- GitHub CLI (`gh`) must be authenticated: `gh auth status`
- Rate limiting: Add `sleep 1` between bulk creates
- Labels must exist before use - create with `gh label create` if needed
- Maximum body length is 65536 characters
- Heredoc syntax requires `'EOF'` (quoted) to prevent variable expansion

## References

- Master tracking issue: #3059
- GitHub CLI docs: https://cli.github.com/manual/gh_issue_create
- ProjectOdyssey: https://github.com/mvillmow/ProjectOdyssey
