---
name: create-review-checklist
description: "Generate customized review checklists based on type of change"
category: testing
source: ProjectOdyssey
date: 2025-12-30
---

# Create Review Checklists

Generate customized review checklists based on type of change.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Tailored PR review checklists | Thorough, focused code reviews |

## When to Use

- (1) Starting PR review for unfamiliar change type
- (2) Need specific checklist for code vs tests vs docs
- (3) Large multi-type changes needing organized review
- (4) Ensuring consistent review quality

## Verified Workflow

1. **Analyze PR**: Determine file types changed
2. **Categorize**: Group changes by type
3. **Select templates**: Pick appropriate checklists
4. **Customize**: Adjust based on complexity/scope
5. **Prioritize**: Mark critical vs optional items
6. **Document**: Create checklist with explanations
7. **Use**: Apply during code review

## Results

Copy-paste ready commands:

```bash
# Detect change type from PR
gh pr diff <pr> --name-only | grep -E "\\.py$|\\.mojo$|\\.md$|test_"

# Categorize changes
gh pr diff <pr> | head -100 | grep "^[+-]" | wc -l  # Changed lines

# Get file counts by type
gh pr diff <pr> --name-only | sed 's/.*\.//' | sort | uniq -c
```

### Checklist Templates

**Python Code Checklist**:
- [ ] Follows PEP 8 style guide
- [ ] Type hints on all functions
- [ ] Docstrings present and clear
- [ ] Error handling appropriate
- [ ] No security vulnerabilities
- [ ] Tests cover new code
- [ ] Edge cases handled

**Test Code Checklist**:
- [ ] Test name describes what's tested
- [ ] Assertions are clear and specific
- [ ] Edge cases covered (boundaries, empty, null)
- [ ] Setup/teardown clean (no side effects)
- [ ] Not dependent on other tests
- [ ] Deterministic (no randomness/flakiness)

**Documentation Checklist**:
- [ ] Spelling and grammar correct
- [ ] Links validated and working
- [ ] Code examples complete and correct
- [ ] Instructions tested and accurate
- [ ] Markdown formatting valid

**Configuration Checklist**:
- [ ] Syntax is valid (YAML, TOML, JSON)
- [ ] No hardcoded secrets
- [ ] Consistent with project standards
- [ ] Required fields present

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Used single generic checklist for all PRs | Missed type-specific issues | Create tailored checklists per change type |
| Made checklist too long (50+ items) | Reviewers skipped items | Keep to 8-12 most important items per type |
| Didn't prioritize items | Critical issues missed | Mark items as Critical/High/Medium/Low |
| Forgot to update checklist for project | Outdated standards checked | Review and update templates periodically |

## Change Type Detection

**Code Implementation**: `.py`, `.mojo`
- Focus: Logic, patterns, performance

**Tests**: `test_*.py`, `test_*.mojo`
- Focus: Coverage, assertions, edge cases

**Documentation**: `*.md`, docstrings
- Focus: Clarity, accuracy, completeness

**Configuration**: `*.toml`, `*.yaml`, `*.json`
- Focus: Correctness, no secrets

## Priority Levels

**Critical** (must fix):
- Syntax errors, test failures, security issues

**High** (should fix):
- Code style, missing tests, performance

**Medium** (nice to have):
- Code cleanup, example improvements

**Low** (optional):
- Formatting polish, minor optimizations

## Error Handling

| Problem | Solution |
|---------|----------|
| Mixed change types | Create separate checklists for each |
| Unclear type | Inspect files to determine type |
| Complex change | Break into multiple checklists |
| Specialized domain | Add domain-specific items |

## References

- See gh-review-pr for PR review workflow
- See verify-pr-ready for merge readiness
