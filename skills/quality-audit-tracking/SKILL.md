# Quality Audit Tracking Skill

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-09 |
| **Objective** | Convert comprehensive code quality audit findings into tracked GitHub issues with epic tracking |
| **Outcome** | ✅ 24 issues created (#400-421), tracking issue (#403), arXiv build fix committed |
| **Category** | workflow |
| **Estimated Time** | 30-45 minutes for 24 issues |

## When to Use This Skill

Use this skill when:
- You have completed a comprehensive code quality audit with 15+ findings
- Findings are categorized by priority (P0/P1/P2) and development principles (KISS, YAGNI, TDD, etc.)
- You need to convert findings into trackable GitHub issues with proper organization
- You want to create an epic/tracking issue for multi-phase work
- Issues need proper labeling, effort estimates, and phase grouping

**Trigger phrases:**
- "Create GitHub issues from audit findings"
- "File all the audit issues"
- "Convert the audit plan to tracked issues"
- "Implement the audit plan with GitHub issues"

## Verified Workflow

### Phase 1: Check Available Labels

**CRITICAL FIRST STEP** - Always validate labels before creating issues:

```bash
# Check what labels exist in the repository
gh label list --limit 100
```

**Why:** Using non-existent labels causes issue creation to fail. This happened when we tried to use 'tooling' label which didn't exist.

### Phase 2: Create First Issues Manually

Start by creating 2-3 issues manually to verify the workflow:

```bash
gh issue create \
  --title "[P0] Issue title" \
  --label "P0,documentation,bug" \
  --body "$(cat <<'EOF'
## Objective
Clear statement of what needs fixing

## Problem
Detailed description of the issue

## Deliverables
- [ ] Task 1
- [ ] Task 2

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Principles
Which principle this addresses (KISS, YAGNI, TDD, DRY, SOLID, POLA)

**Estimated Effort**: 2h
**Phase**: 1 (Phase name)
EOF
)"
```

### Phase 3: Create Tracking/Epic Issue

Create the master tracking issue BEFORE batch creating remaining issues:

```bash
# Create tracking issue body in temp file
cat > /tmp/tracking_issue_body.md <<'EOF'
# Project Name Code Quality Audit - Tracking Issue

## Overview
Brief description of the audit scope

## Executive Summary
| Priority | Count | Description | Estimated Effort |
|----------|-------|-------------|------------------|
| P0 | 3 | Critical issues | 4.5h |
| P1 | 12 | High priority | 23.5h |
| P2 | 9 | Cleanup | 3.5h |
| Total | 24 | All issues | 31.5h |

## Phase 1: [Phase Name] (~Xh, Y issues)
- [ ] #400 - Issue description (effort)
- [ ] #401 - Issue description (effort)

[Repeat for each phase]

## Verification Steps
[List common verification steps for all issues]
EOF

# Create the tracking issue
gh issue create \
  --title "[TRACKING] Code Quality Audit: 24 Issues Across 4 Phases" \
  --label "epic,tech-debt" \
  --body "$(cat /tmp/tracking_issue_body.md)"
```

### Phase 4: Generate Batch Creation Script

Create a shell script for remaining issues:

```bash
cat > /tmp/create_issues.sh <<'SCRIPT'
#!/bin/bash
set -e

echo "Creating issue #4: Brief description (P1)"
gh issue create \
  --title "[P1] Full issue title" \
  --label "P1,category,type" \
  --body "$(cat <<'EOF'
## Objective
...

## Problem
...

## Deliverables
- [ ] Task 1

## Success Criteria
- [ ] Criterion 1

## Principles
[Principle name]

**Estimated Effort**: Xh
**Phase**: Y
EOF
)"

# Repeat for each remaining issue

echo ""
echo "All issues created successfully!"
SCRIPT

chmod +x /tmp/create_issues.sh
```

**Key points:**
- Use `set -e` to exit on first error
- Echo progress for each issue
- Use heredoc (`<<'EOF'`) for multi-line bodies
- Single-quote the outer EOF to prevent variable expansion

### Phase 5: Execute Batch Creation

```bash
/tmp/create_issues.sh 2>&1
```

Monitor output to ensure all issues are created successfully.

### Phase 6: Verify Issue Creation

```bash
# List all issues from the audit
gh issue list --label tech-debt --label epic

# Check specific issue
gh issue view 400

# Verify count matches expected
gh issue list --label P0 | wc -l  # Should match P0 count
gh issue list --label P1 | wc -l  # Should match P1 count
gh issue list --label P2 | wc -l  # Should match P2 count
```

## Failed Attempts & Lessons Learned

### ❌ Attempt 1: Parallel Issue Creation with Unknown Labels

**What we tried:**
```bash
# Attempted to create all 20 issues in parallel
gh issue create --label "P1,bug,tooling" ...  # FAILED
```

**Why it failed:**
- Used label 'tooling' which doesn't exist in repository
- Parallel execution means all subsequent calls failed due to sibling error
- No label validation before attempting creation

**Lesson:** Always run `gh label list` first and validate labels exist

### ❌ Attempt 2: Continuing After First Failure

**What we tried:**
- Continued with remaining issue creation calls after first failure
- All calls showed `<tool_use_error>Sibling tool call errored</tool_use_error>`

**Why it failed:**
- Once one parallel tool call fails, siblings are cancelled
- No recovery mechanism in parallel execution

**Lesson:** Use sequential script execution for batch operations where one failure shouldn't block others

### ✅ Solution: Sequential Shell Script

**What worked:**
1. Created first 3 issues manually to verify labels work
2. Generated shell script with sequential `gh issue create` calls
3. Each issue creation independent (one failure doesn't block others)
4. Progress echoed for each issue
5. Script completion summary at end

**Key insight:** Batch operations with external dependencies (GitHub API, labels) should be sequential, not parallel.

## Results & Parameters

### Session Outcome

**Issues Created:** 24 total
- P0: #400, #401, #402 (critical - data correctness)
- P1: #404-408, #413-414, #418-421 (high priority)
- P2: #409-412, #415-417 (cleanup)
- Tracking: #403 (epic)

**Time Breakdown:**
- Label validation: 2 minutes
- Manual issue creation (first 3): 5 minutes
- Tracking issue creation: 3 minutes
- Script generation: 8 minutes
- Script execution: 15 minutes
- Verification: 5 minutes
- **Total: ~38 minutes**

### Issue Template Structure

```markdown
## Objective
[One sentence: what needs fixing]

## Problem
[2-4 paragraphs explaining the issue with code references]

## Deliverables
- [ ] Specific deliverable 1
- [ ] Specific deliverable 2

## Success Criteria
- [ ] Measurable criterion 1
- [ ] Measurable criterion 2

## Principles
[KISS | YAGNI | TDD | DRY | SOLID | POLA | Modularity]

**Estimated Effort**: [Xh | Xm]
**Phase**: [Phase number and name]
```

### Label Strategy

| Label Type | Options | Usage |
|------------|---------|-------|
| Priority | P0, P1, P2, P3 | One required per issue |
| Category | documentation, testing, refactoring, config, etc. | 1-2 per issue |
| Type | bug, epic, tech-debt, enhancement | 0-1 per issue |
| Component | core, adapter, metrics, judge, etc. | 0-1 for component-specific |

### Tracking Issue Format

**Essential sections:**
1. Overview - One paragraph summary
2. Executive Summary - Table with priority breakdown
3. Phase-by-phase breakdown - Grouped issues with checkboxes
4. Verification steps - Common to all issues
5. Principles applied - Counts by principle
6. Progress tracking - Updated as work completes

## Common Pitfalls

### 1. Label Typos/Non-existence
**Symptom:** `could not add label: 'X' not found`
**Fix:** Run `gh label list` first, use exact label names

### 2. Heredoc Variable Expansion
**Symptom:** Variables in issue body get expanded
**Fix:** Use `<<'EOF'` (single-quoted) not `<<EOF`

### 3. Tracking Issue Created Last
**Symptom:** Issue numbers in tracking issue are TBD
**Fix:** Create tracking issue AFTER first batch, before final batch

### 4. Missing Co-Author
**Symptom:** Commits don't credit Claude
**Fix:** Always include in commit message:
```
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## Integration Points

### Before This Skill
- Complete code quality audit (use code review/analysis skills)
- Categorize findings by priority and principle
- Estimate effort for each finding
- Group findings into logical phases

### After This Skill
- Start working on P0 issues first
- Create PRs using `/commit` and PR creation workflows
- Update tracking issue checkboxes as issues close
- Monitor progress via `gh issue list --label epic`

### Related Skills
- `pr-workflow` - Creating PRs for issue fixes
- `github-issue-workflow` - Reading/commenting on issues
- `code-review` - Generating audit findings
- `/commit` - Committing fixes

## Example Usage

```bash
# User has completed audit, wants to file all issues
user: "Implement the audit plan - create all 24 GitHub issues"

# Claude workflow:
# 1. Check labels exist
gh label list --limit 100

# 2. Create first 2-3 manually (verify workflow)
gh issue create --title "[P0] First issue" --label "P0,bug" --body "..."

# 3. Create tracking issue
gh issue create --title "[TRACKING] Audit" --label "epic" --body "..."

# 4. Generate batch script
cat > /tmp/create_issues.sh <<'SCRIPT'
...
SCRIPT

# 5. Execute script
/tmp/create_issues.sh

# 6. Verify all created
gh issue list --label epic
```

## Metrics

**Success Indicators:**
- All planned issues created without errors
- Issue numbers sequential (no gaps from failures)
- All issues properly labeled
- Tracking issue has correct issue numbers
- Time: 30-45 minutes for 20-30 issues

**Failure Indicators:**
- Missing issues (gaps in numbering)
- Issues with missing/wrong labels
- Tracking issue created before batch (wrong numbers)
- Time: >60 minutes (indicates rework from errors)

## Notes

- **Template reuse:** Save issue templates to temp files for consistency
- **Batch size:** 20-30 issues is optimal for one script
- **Error handling:** Sequential execution allows recovery from individual failures
- **Documentation:** Include links to principles in tracking issue
- **Estimation:** Conservative effort estimates better than optimistic
- **Phases:** Group by logical dependency/priority, not arbitrary size

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-09 | Initial skill from ProjectScylla audit session |
