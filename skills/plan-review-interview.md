---
name: plan-review-interview
description: Structured interview workflow for reviewing implementation plans and
  capturing decisions
category: evaluation
date: 2025-12-30
version: 1.0.0
---
# Plan Review Interview

Systematically review implementation plans, identify gaps, and capture decisions through structured interviews.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Review plan, identify gaps, interview stakeholder for decisions | 11 key decisions captured, 4 new issues created, 6 existing issues updated |

## When to Use

- (1) You have a draft implementation plan that needs stakeholder validation
- (2) There are ambiguous requirements or multiple valid approaches
- (3) GitHub issues exist but lack key decision details
- (4) You need to systematically identify gaps before implementation begins
- (5) You want to document decisions alongside the issues they affect

## Verified Workflow

### Phase 1: Prepare Context

1. Read all existing plan documents
2. List all GitHub issues with `gh issue list --limit 50`
3. Group issues by phase/category
4. Create a review prompt document with issue references

### Phase 2: Conduct Structured Interview

1. **Batch questions by topic** (3-4 questions per batch):
   - Core execution model
   - Configuration specifics
   - Judge/evaluation system
   - Scope and audience

2. **For each question**:
   - State the gap clearly
   - Reference affected GitHub issues
   - Propose 2-3 solutions
   - Record user's decision

3. Use `AskUserQuestion` tool with multiple related questions per batch

### Phase 3: Update Artifacts

1. Update plan document with decisions table at top
2. Add comments to GitHub issues:
   ```bash
   gh issue comment <number> --body "## Decision Update

   - **Key decision**: value
   - **Rationale**: reason"
   ```
3. Create new issues for gaps discovered:
   ```bash
   gh issue create --title "[Category] Title" --body "..." --label "category"
   ```
4. Transform review prompt into decisions document

### Phase 4: Commit and Document

1. Create feature branch
2. Commit all updated files
3. Create PR with summary of decisions

## Results

### Decision Table Format

```markdown
## Decisions Summary

| Question | Decision |
|----------|----------|
| API Key Handling | Environment Variables (docker -e flags) |
| Runs per Tier | **9 runs** (standardized) |
| Docker Fallback | **Fail with error** (Docker is required) |
```

### Issue Reference Pattern

```markdown
### 1. Test Execution Model

**Reference Issues**: #7, #8, #9, #35

| Question | Decision |
|----------|----------|
| How are API keys passed? | **Environment variables** via docker -e flags |
```

### Batched Interview Example

```
Batch 1: Core Execution (API keys, Docker, runs per tier)
Batch 2: Configuration (T0 definition, tier relationships)
Batch 3: Judge System (location, disagreement handling)
Batch 4: Scope (audience, first test scope)
```

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Session Statistics

| Metric | Value |
|--------|-------|
| Questions asked | 11 batched topics |
| Decisions captured | 11 key decisions |
| Issues updated | 6 |
| New issues created | 4 |
| Documents updated | 2 |

## Key Configuration

```yaml
# Interview batch size
questions_per_batch: 3-4

# Output format
decisions_format: "markdown table at top"
issue_updates: "comments (not body edits)"
new_issues: "create for discovered gaps"

# Required sections in decisions document
sections:
  - decisions_summary_table
  - resolved_questions_by_topic
  - new_issues_created
  - completed_actions
```

## Error Handling

| Problem | Solution |
|---------|----------|
| Too many questions | Batch by topic, max 4 per batch |
| Lost issue context | Use comments instead of body edits |
| Missing traceability | Always reference issue numbers |
| Decisions buried | Add summary table at document top |

## References

- See `/advise` for searching existing knowledge
- See `/learn` for capturing session learnings
