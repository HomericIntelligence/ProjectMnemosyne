---
name: review-pr-changes
description: "Review PR changes with structured checklist for Python/JS quality and standards compliance."
category: review
user-invocable: false
---

# Review PR Changes

Perform structured review of PR changes against project quality standards.

## When to Use

- Code review before approving PR
- Checking standards compliance (Python, JavaScript)
- Verifying test coverage

## Quick Reference

```bash
# Get PR files changed
gh pr diff <pr> --name-only

# View full diff
gh pr diff <pr>

# Get PR review status
gh pr view <pr> --json reviews
```

## Review Checklist

**Code Quality**:

- [ ] Code is readable and well-structured
- [ ] Functions have clear purposes
- [ ] Variable names are descriptive
- [ ] No code duplication (DRY principle)

**Python-Specific**:

- [ ] Type hints on function signatures
- [ ] Docstrings for public APIs
- [ ] No `[] or DEFAULT` pattern (use `if X is None`)
- [ ] AES negative IDs handled correctly

**JavaScript-Specific**:

- [ ] CDN-only (no npm imports, no build tools)
- [ ] All 4 game status values handled (final/in_progress/scheduled/conditional)
- [ ] Conditional game rendering correct (opponent_text, dashed border)
- [ ] Mobile-first responsive design maintained

**Testing**:

- [ ] Tests present for new functionality
- [ ] Tests passing (CI green)
- [ ] Edge cases covered
- [ ] Inline fixtures used (no external fixture files for unit tests)

**Security**:

- [ ] No hardcoded secrets/tokens
- [ ] Input validation present
- [ ] API calls use proper headers

**Git**:

- [ ] PR linked to issue
- [ ] Conventional commit messages
- [ ] No unintended files included

## Output Format

1. **Summary** - Overall assessment
2. **Issues Found** - Problems that must be fixed
3. **Suggestions** - Optional improvements
4. **Verdict** - Approve/Request Changes/Comment

## References

- See CLAUDE.md for project standards
- See verify-pr-ready for merge readiness
