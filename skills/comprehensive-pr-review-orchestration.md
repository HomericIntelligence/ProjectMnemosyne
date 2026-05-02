---
name: comprehensive-pr-review-orchestration
description: Orchestrate comprehensive PR reviews using specialized sub-reviewers.
  Use when reviewing complex PRs.
category: ci-cd
date: 2026-01-23
version: 1.0.0
user-invocable: false
---
# Skill: Comprehensive PR Review Orchestration

| Property | Value |
| ---------- | ------- |
| **Date** | 2026-01-23 |
| **Objective** | Conduct comprehensive PR review using code-review-orchestrator to coordinate multiple specialized reviewers |
| **Outcome** | ✅ Successfully identified 3 blocking issues, posted structured review comments to PR and issue |
| **Context** | PR #3109 needed comprehensive review for alignment with issue #3033 and repository architecture |

## When to Use This Skill

Use this skill when:
- Need to conduct a thorough, multi-dimensional PR review
- PR must align with specific issue requirements and repository architecture
- Want structured, prioritized feedback across multiple review dimensions
- Need actionable review comments posted as GitHub review for engineer to address

**Key Indicators**:
- User asks to "review PR comprehensively"
- Review must check alignment with original issue requirements
- Need to verify adherence to repository architecture/patterns
- Want review comments filed for others to fix (not implement fixes directly)

## Verified Workflow

### 1. Use Code Review Orchestrator Agent

**Launch with clear requirements:**
```markdown
Use the Task tool with subagent_type="code-review-orchestrator"

Prompt should include:
1. PR number and URL
2. Related issue number for alignment verification
3. Requirement to check repository architecture/design adherence
4. Request to coordinate multiple specialized reviewers
```

**Example:**
```markdown
Review PR #3109 (https://github.com/user/repo/pull/3109) comprehensively.

Key requirements:
1. Verify alignment with issue #3033 (improve import test robustness)
2. Check adherence to repository architecture and design patterns from CLAUDE.md
3. Route to appropriate specialist reviewers based on the changes

Please:
- First, fetch the PR details and understand what changed
- Read issue #3033 to understand the requirements
- Identify which specialist reviewers are needed based on the changes
- Coordinate reviews across all applicable dimensions
- Provide an aggregated summary with prioritized findings
```

### 2. Orchestrator Routes to Specialist Reviewers

The orchestrator analyzes changes and routes to appropriate specialists:

**Common specialists for Mojo projects:**
- **Test Review Specialist** - Test coverage, quality, assertions
- **Mojo Language Review Specialist** - Mojo-specific idioms, syntax, patterns
- **Implementation Review Specialist** - General code quality, logic correctness
- **Documentation Review Specialist** - Documentation clarity, completeness
- **Memory Safety Review Specialist** - Memory management, ownership
- **Algorithm Review Specialist** - Mathematical correctness (ML code)

**Routing decision based on changes:**
- Test files changed → Test Review Specialist
- Mojo language features used → Mojo Language Review Specialist
- Documentation added/modified → Documentation Review Specialist
- Algorithm implementation → Algorithm Review Specialist

### 3. Review Output Structure

The orchestrator provides:

**A. Specialist Findings** - Organized by reviewer:
```markdown
### 1. Test Review Specialist
✅ Strengths: [What's good]
⚠️ Important Issues: [Priority issues with file:line references]
📝 Minor Issues: [Nice-to-have improvements]

### 2. Mojo Language Review Specialist
[Same structure]
```

**B. Consolidated Report** - Aggregated across all specialists:
```markdown
### Priority 1: Blocking Issues (Must Fix Before Merge)
1. Issue description [file:line] - Specialist name

### Priority 2: Important Improvements (Should Fix)
[Same structure]

### Priority 3: Nice to Have (Consider for Future)
[Same structure]
```

**C. Alignment Assessment:**
```markdown
**Issue Goal Alignment:** ✅/⚠️/❌
**Repository Architecture:** ✅/⚠️/❌
**Predicted CI Status:** ✅/❌
```

### 4. File Review Comments for Engineer

**Post comprehensive review:**
```bash
gh api \
  repos/OWNER/REPO/pulls/PR_NUMBER/reviews \
  -X POST \
  -f event='COMMENT' \
  -f body="[Full review with Priority 1/2/3 sections, testing instructions, alignment assessment]"
```

**Post line-specific issues:**
```bash
gh pr comment PR_NUMBER --body "$(cat <<'EOF'
## 📍 Line-Specific Issues

### file.mojo:263
🚫 **BLOCKING:** Issue description
Fix: [code example]

### file.mojo:284
⚠️ **IMPORTANT:** Issue description
Fix: [code example]
EOF
)"
```

**Update tracking issue:**
```bash
gh issue comment ISSUE_NUMBER --body "$(cat <<'EOF'
## PR #XXX Review Complete - Changes Requested

### Status: ⚠️ Changes Requested

**N blocking issues** identified:
1. Issue summary
2. Issue summary

### Review Details
Full review: [PR review link]
Line-specific: [PR comment link]

### Next Steps
Engineer should:
1. Apply fixes
2. Run local tests
3. Push updates
EOF
)"
```

### 5. Verify Review Posted Successfully

```bash
# Check review was posted
gh pr view PR_NUMBER --json reviews --jq '.reviews[-1]'

# Check comments were posted
gh pr view PR_NUMBER --json comments --jq '.comments[-1]'

# Check issue comment was posted
gh issue view ISSUE_NUMBER --json comments --jq '.comments[-1]'
```

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | YYYY-MM-DD |
| **Objective** | Skill objective |
| **Outcome** | Success/Operational |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Agent Configuration

**Agent Type**: `code-review-orchestrator`
**Model**: Default (inherited from parent, likely Sonnet)
**Mode**: Default (no special permissions needed)

**Prompt Structure**:
```markdown
Review PR #[NUMBER] ([URL]) comprehensively.

Key requirements:
1. Verify alignment with issue #[NUMBER] ([description])
2. Check adherence to repository architecture and design patterns
3. Route to appropriate specialist reviewers

Please:
- Fetch PR details
- Read related issue
- Identify needed specialists
- Coordinate reviews
- Provide aggregated summary with prioritized findings
```

### Review Output Example

**PR #3109 Review Results:**

**Specialists Engaged**: 4
- Test Review Specialist
- Mojo Language Review Specialist
- Implementation Review Specialist
- Documentation Review Specialist

**Findings**:
- 3 blocking issues (Priority 1)
- 2 important improvements (Priority 2)
- 2 nice-to-have suggestions (Priority 3)

**Blocking Issues Identified**:
1. Missing AUTHOR and LICENSE constants (import failure)
2. Undefined `int()` function (compilation error)
3. Missing exports in `shared/__init__.mojo` (import failure)

**Review Comments Posted**:
- Main review: https://github.com/.../pull/3109#pullrequestreview-3698599863
- Line-specific: https://github.com/.../pull/3109#issuecomment-3791264504
- Issue tracking: https://github.com/.../issues/3033#issuecomment-3791265854

### GitHub API Commands Used

```bash
# Post comprehensive review summary
gh api repos/OWNER/REPO/pulls/3109/reviews \
  -X POST \
  -f event='COMMENT' \
  -f body="[Full markdown review]"

# Post line-specific issues as PR comment
gh pr comment 3109 --body "$(cat <<'EOF'
## 📍 Line-Specific Issues
[Formatted issues with file:line references]
EOF
)"

# Update tracking issue
gh issue comment 3033 --body "$(cat <<'EOF'
## PR #3109 Review Complete - Changes Requested
[Status summary and next steps]
EOF
)"
```

### Testing Commands

**Recommended for engineer to verify fixes:**
```bash
# Test compilation
pixi run mojo build tests/shared/test_imports.mojo

# Test execution
pixi run mojo test tests/shared/test_imports.mojo

# Verify exports
pixi run mojo build shared/__init__.mojo

# Run full test group
just test-group tests/shared "test_imports.mojo"
```

## Key Takeaways

1. **Use code-review-orchestrator for comprehensive reviews** - Coordinates multiple specialists automatically
2. **Be explicit about requirements** - Specify issue alignment, architecture adherence in prompt
3. **Let orchestrator route to specialists** - Don't manually specify which reviewers to use
4. **Prioritize findings** - P1 (blocking) → P2 (important) → P3 (nice-to-have)
5. **Use simple PR comments, not inline review comments** - Inline API is complex, simple comments work
6. **Post three locations** - Main review (PR), line-specific (PR comment), tracking (issue comment)
7. **Include testing instructions** - Help engineer verify fixes locally
8. **Estimate fix time** - Sets expectations (e.g., "15-30 minutes")
9. **Don't implement fixes when asked to file comments** - Maintain clear ownership

## Cross-Project Applicability

This skill applies to any project with:
- ✅ Pull request workflow on GitHub
- ✅ Hierarchical agent system (orchestrator + specialists)
- ✅ Code review requirements before merge
- ✅ Issue tracking for feature work

**Adaptation notes**:
- Specialist selection depends on project language (Mojo, Python, TypeScript, etc.)
- Priority levels may vary by project standards
- Testing commands are project-specific

## Related Skills

- `verify-issue-before-work` - Check issue requirements before starting implementation
- `fix-ci-test-failures` - Fix tests that fail in CI but pass locally
- `grading-consolidation` - Multi-agent orchestration pattern for complex analysis

## Port to Other Projects

This skill is already in ProjectMnemosyne (team knowledge base). To apply to specific projects:

```bash
# Reference in project CLAUDE.md
echo "See ProjectMnemosyne/skills/ci-cd/comprehensive-pr-review-orchestration" >> CLAUDE.md

# Or create project-specific adaptation
cp -r ProjectMnemosyne/skills/ci-cd/comprehensive-pr-review-orchestration \
  YourProject/.claude/skills/
```
