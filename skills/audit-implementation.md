---
name: audit-implementation
description: 'Implements repository audit findings as concrete fixes via PRs. Use
  when: audit report needs actionable implementation, triage of findings into fix
  vs defer.'
category: tooling
date: 2026-03-17
version: 1.0.0
user-invocable: false
---
# Audit Implementation

## Overview

| Field | Value |
|-------|-------|
| Skill | audit-implementation |
| Category | tooling |
| Complexity | Medium |
| Prerequisites | Completed audit report with findings |

Translates repository audit findings into concrete, shippable fixes via feature branches and PRs. Key insight: most audit findings fall into three buckets — quick fixes (duplicate configs, stale counts), pragmatic improvements (adding warnings vs removing safety nets), and deferred items (large refactors, blocked by external tools). Efficient implementation focuses on the first two buckets.

## When to Use

- After running `/repo-analyze-strict` or similar audit and receiving a findings report
- When triaging Major/Minor/Nitpick findings into actionable work
- When multiple small fixes can be batched into a single PR
- When audit findings need verification before implementation (e.g., "missing file" that actually exists)

## Verified Workflow

### Quick Reference

```text
1. Read audit report → extract actionable findings
2. Verify each finding (some may be incorrect)
3. Create feature branch
4. Batch compatible fixes into one commit
5. Run pre-commit hooks
6. Create PR with auto-merge
7. Document deferred items separately
```

### Step 1: Triage Findings

Categorize each finding before touching any code:

| Category | Action | Example |
|----------|--------|---------|
| Quick fix | Include in batch PR | Duplicate hook, stale badge count |
| Pragmatic improvement | Include if safe | Add CI warning annotation |
| Verify first | Check before acting | "Missing CODE_OF_CONDUCT.md" — may already exist |
| Needs separate PR | Defer with note | 4,278-line script decomposition |
| External blocker | Document only | Mojo compiler limitation |
| Admin setting | Not a code change | Branch protection review count |

### Step 2: Verify Before Implementing

Critical lesson: **always verify audit findings**. Automated audits can report false positives:

- "Missing file X" — run `find` or `glob` to check
- "Stale count" — run the validation script to get actual numbers
- "Unused dependency" — grep for actual usage before removing

### Step 3: Batch Compatible Fixes

Group fixes that:
- Touch different files (no merge conflicts)
- Are independently correct (reverting one doesn't break others)
- Share a common theme (audit findings)

### Step 4: Handle Continue-on-Error Pragmatically

When audit flags `continue-on-error: true` in CI:

- **Don't** just remove it — understand WHY it's there
- Semgrep returns non-zero on findings; removing continue-on-error breaks SARIF upload
- **Better**: Add a warning annotation step that surfaces findings without blocking
- Pattern: keep `continue-on-error`, add `id:` to step, add downstream `if: steps.X.outcome == 'failure'` warning

### Step 5: Document Deferred Items in PR Body

List what was NOT implemented and why, so the audit trail is complete.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Remove Semgrep continue-on-error outright | Simply deleting `continue-on-error: true` from security.yml | Would break SARIF upload to GitHub Security tab — Semgrep exits non-zero when it finds issues | Add warning annotations downstream instead of removing safety mechanisms |
| Trust audit finding about missing CODE_OF_CONDUCT.md | Planned to create new file | File already existed — audit was incorrect | Always verify findings with filesystem checks before implementing |
| Update README test count to exact number (540) | Considered updating badge to exact file count | Badge script uses "N+" format and has 10% drift tolerance | Match existing convention (498+) rather than switching to exact counts |

## Results & Parameters

### PR Template for Audit Fixes

```markdown
## Summary

- **Fix 1**: [What changed] ([audit section reference])
- **Fix 2**: [What changed] ([audit section reference])

## Not Implemented (Deferred)

- [Finding] — [reason for deferral]

## Test plan

- [x] Pre-commit hooks pass locally
- [ ] CI workflows pass on this PR
```

### Triage Decision Matrix

```yaml
# Include in batch PR if ALL true:
include_criteria:
  - change_is_under_20_lines: true
  - no_behavior_change_risk: true
  - independently_reversible: true
  - pre_commit_hooks_validate: true

# Defer to separate PR if ANY true:
defer_criteria:
  - requires_large_refactor: true  # e.g., 4000-line script split
  - blocked_by_external_tool: true  # e.g., Mojo coverage tooling
  - requires_admin_settings: true   # e.g., branch protection rules
  - needs_stakeholder_input: true   # e.g., dependency removal
```
