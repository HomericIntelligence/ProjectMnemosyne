# Bulk Issue Filing - Raw Session Notes

## Session Context

- **Date**: 2026-01-01
- **Repository**: mvillmow/ProjectOdyssey
- **Branch**: cleanup/44-implement-visualization-tests
- **Duration**: ~2 hours

## Problem Statement

ProjectOdyssey had 357+ code markers (TODO, FIXME, DEPRECATED, NOTE) scattered across the codebase with no systematic tracking. Goal was to file GitHub issues for all markers to enable proper prioritization and tracking.

## Discovery Phase

### Marker Counts Found

```text
Category                    Count
----------------------------------
TODO markers                372+
FIXME markers               4
DEPRECATED markers          11
NOTE markers                50+
GitHub issue references     100+
```

### File Distribution

Most markers concentrated in:

- `tests/` directory - Test TODOs and blocked tests
- `shared/core/` - Implementation notes
- `shared/training/` - Deprecated files

## Categorization Strategy

### Batch 1: DEPRECATED Items (7 issues)

Files and aliases marked for deletion:

```text
/shared/training/schedulers.mojo - DEPRECATED file
/tests/helpers/gradient_checking.mojo - DEPRECATED file
/tests/shared/fixtures/mock_models.mojo - DEPRECATED file
/benchmarks/__init__.mojo - DEPRECATED file
.claude/skills/plan-validate-structure/ - DEPRECATED skill
.claude/skills/plan-create-component/ - DEPRECATED skill
.claude/skills/plan-regenerate-issues/ - DEPRECATED skill
/shared/core/conv.mojo:26-44 - 6 deprecated aliases
/shared/core/linear.mojo:15-22 - 2 deprecated aliases
```

### Batch 2: Blocked TODOs (6 issues)

TODOs blocked by other issues:

```text
#1538 - Integration components: 17 TODOs
#3013 - Data loader: 10 TODOs
#2724 - Gradient computation: 5 TODOs
```

### Batch 3: Template Placeholders (2 issues)

Intentional placeholders not needing implementation:

```text
.templates/*.mojo - 20 placeholders
.claude/skills/phase-test-tdd/templates/* - 10 placeholders
```

### Batch 4: NOTE Cleanup (6 issues)

Informational notes to convert or document:

```text
Mojo language limitations - 8 NOTEs
Implementation constraints - 12 NOTEs
Temporary workarounds - 6 NOTEs
Reference notes - 10 NOTEs
FP16 SIMD blockers - 2 NOTEs
Python interop blockers - 3 NOTEs
```

### Batch 5: Actionable TODOs (14 issues)

Specific implementation work needed.

## Issue Filing Workflow

### Step 1: Check Labels

```bash
gh label list
# Found: cleanup, testing, documentation, enhancement, bug, core
# NOT found: deprecated (had to use 'cleanup' instead)
```

### Step 2: Create Master Issue

```bash
gh issue create \
  --title "[Cleanup] Master: FIXME/TODO code marker cleanup" \
  --body "..." \
  --label cleanup
# Created: #3059
```

### Step 3: Create Child Issues

Used consistent template:

```markdown
## Objective
[Brief description]

## Context
- **File**: `[path]`
- **Line(s)**: [numbers]
- **Marker**: `[type]`
- **Original Text**: `[content]`

## Deliverables
- [ ] [Change 1]

## Success Criteria
- [ ] Marker addressed
- [ ] Tests pass

## Parent Issue
Part of #3059
```

## Issues Created

### Batch 1: DEPRECATED

- #3060 - Delete deprecated schedulers.mojo
- #3061 - Delete deprecated gradient_checking.mojo
- #3062 - Delete deprecated mock_models.mojo
- #3063 - Delete deprecated plan-* skill directories
- #3064 - Remove deprecated Conv backward result aliases
- #3065 - Remove deprecated Linear backward result aliases
- #3066 - Delete deprecated benchmarks/__init__.mojo

### Batch 2: Blocked TODOs

- #3067 - Track TODOs blocked by #1538
- #3068 - Track TODOs blocked by #3013
- #3069 - Track TODOs blocked by #2724
- #3077 - Track disabled test TODOs (#1538)
- #3078 - Track data loader TODOs (#3013)
- #3079 - Track gradient TODOs (#2724)

### Batch 3: Templates

- #3070 - Track template TODO placeholders
- #3080 - Document intentional template placeholders

### Batch 4: NOTEs

- #3071 - Document Mojo language limitation NOTEs
- #3072 - Convert implementation constraint NOTEs
- #3073 - Track temporary workaround NOTEs
- #3074 - Review miscellaneous reference NOTEs
- #3075 - Clean up FP16 SIMD blocker NOTEs
- #3076 - Clean up Python interop blocker NOTEs

### Batch 5: Specific Markers

- #3081-#3094 - Various actionable TODOs

## Errors Encountered

### Label Not Found

```text
Error: could not add label: 'deprecated' not found
```

**Fix**: Used `gh label list` to check available labels, then used `cleanup` instead.

### Rate Limiting Consideration

Added `sleep 1` between issue creations to avoid hitting GitHub API rate limits.

## Commands Reference

```bash
# Discovery
grep -rn "TODO\|FIXME" --include="*.mojo" .
grep -rn "DEPRECATED" --include="*.mojo" .
grep -rn "NOTE:" --include="*.mojo" .

# Check labels
gh label list

# Create issue
gh issue create \
  --title "[Cleanup] ..." \
  --body "$(cat <<'EOF'
## Objective
...
EOF
)" \
  --label cleanup

# View issues
gh issue list --label cleanup --limit 50
gh issue view 3059
```

## Lessons Learned

1. **Check labels first** - `gh label list` before bulk filing
2. **Separate filing from implementation** - Don't mix planning with doing
3. **Use master tracking issue** - Link all child issues to parent
4. **Skip already-tracked items** - Check if TODO references existing issue
5. **Categorize before filing** - Group similar markers for efficiency
6. **Use consistent templates** - Copy-paste friendly format
7. **Include context** - File path, line number, exact marker text
8. **Rate limit awareness** - Add delays for bulk operations

## Statistics

- Total markers found: 357+
- Issues created: 36
- Time spent: ~2 hours
- Efficiency: ~6 minutes per issue (including categorization)
