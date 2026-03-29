---
name: quality-audit-workflow
description: "Use when: (1) implementing findings from a comprehensive code quality audit by creating tracking issues and fixing HIGH priority items, (2) converting audit findings into tracked GitHub issues with epics, (3) a quality audit flags a module docstring as a sentence fragment but the docstring is grammatically complete"
category: tooling
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: unverified
tags: []
---
# Quality Audit Workflow

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-29 |
| Objective | Consolidated workflow for conducting code quality audits: converting findings to GitHub issues, implementing HIGH priority mechanical fixes, and handling docstring false positives |
| Outcome | Merged from 3 source skills |
| Verification | unverified |

## When to Use

- You have a completed code quality audit with actionable findings categorized by priority (HIGH/MEDIUM/LOW or P0/P1/P2)
- You need to create GitHub tracking issues for systematic implementation
- You want to implement mechanical fixes while deferring complex refactoring
- A quality audit flags a module docstring as "garbled" or "sentence fragment" but on inspection it is grammatically complete — just wrapped across lines
- The false-positive docstring issue has recurred across multiple audit cycles

## Verified Workflow

### Quick Reference

**Label check before any issue creation**:
```bash
gh label list --limit 100
```

**Issue number extraction from URL**:
```bash
issue_url=$(gh issue create ...)
issue_num=$(echo "$issue_url" | grep -oP '\d+$')
```

**Docstring false positive fix** — restructure to remove visual ambiguity:
```python
# BEFORE (line N+1 looks like a fragment)
"""This module provides the Foo class that does X
across multiple Y."""

# AFTER (relative clause makes completeness clear)
"""This module provides the Foo class, which does X
across multiple Y."""
```

### Phase 1: Check Available Labels

**CRITICAL FIRST STEP** — always validate labels before creating issues:
```bash
gh label list --limit 100
```

Using non-existent labels causes `gh issue create` to fail. Common missing labels: `tooling`, `tech-debt`, `epic`.

### Phase 2: Check Existing Infrastructure

Before implementing, verify what is already done:
```bash
# Check pre-commit hooks
grep -A 5 "mypy" .pre-commit-config.yaml

# Check for existing files
ls -la .env.example CONTRIBUTING.md

# Check pyproject.toml for existing configs
grep -A 10 "\[tool.pytest" pyproject.toml
grep -A 10 "\[tool.coverage" pyproject.toml

# Verify CODEOWNERS paths (stale entries are silent — no errors)
while IFS= read -r line; do
  path=$(echo "$line" | grep -oP '^/[^ ]+')
  [ -n "$path" ] && [ ! -e ".$path" ] && echo "STALE: $path"
done < .github/CODEOWNERS
```

Only implement what is actually missing or needs fixing.

### Phase 3: Create Tracking Issues

**Triage decision — direct fix vs. issue**:
- Change is < 5 lines AND has no design ambiguity → fix directly in same PR
- Change requires thought/review/architecture → file issue only

**Create first 2–3 issues manually** to verify labels and workflow work before batch creation.

**Issue template structure**:
```markdown
## Objective
Brief description (2-3 sentences)

## Deliverables
- [ ] Deliverable 1
- [ ] Deliverable 2

## Success Criteria
- Criterion 1
- Criterion 2

## Priority
HIGH/MEDIUM/LOW - Impact description

## Estimated Effort
X hours

## Verification
```bash
# Commands to verify fix
```

## Context
From [Audit Name] (#ISSUE-NUMBER)
```

**Create tracking/epic issue** before batch-creating remaining issues (so issue numbers are known):
```bash
gh issue create \
  --title "[TRACKING] Code Quality Audit: N Issues Across X Phases" \
  --label "epic,tech-debt" \
  --body "$(cat <<'EOF'
## Overview
Brief description

## Executive Summary
| Priority | Count | Estimated Effort |
|----------|-------|-----------------|
| P0 | 3 | 4.5h |
| P1 | 12 | 23.5h |

## Phase 1: [Name] (~Xh, Y issues)
- [ ] #400 - Description (effort)

## Verification Steps
[Common verification steps]
EOF
)"
```

**Generate batch creation script** for remaining issues:
```bash
cat > /tmp/create_issues.sh <<'SCRIPT'
#!/bin/bash
set -e

echo "Creating issue: Brief description"
gh issue create \
  --title "[P1] Full issue title" \
  --label "P1,documentation" \
  --body "$(cat <<'EOF'
## Objective
...

## Deliverables
- [ ] Task 1

## Success Criteria
- [ ] Criterion 1

**Estimated Effort**: Xh
**Phase**: 1
EOF
)"

echo "All issues created successfully!"
SCRIPT
chmod +x /tmp/create_issues.sh
/tmp/create_issues.sh 2>&1
```

**Post summary to tracking issue** after batch creation:
```bash
gh issue comment <tracking-number> --body "$(cat <<EOF
## GitHub Issues Created

### HIGH Priority
- #<num> - Description

### MEDIUM Priority
- #<num> - Description
EOF
)"
```

### Phase 4: Implement HIGH Priority Mechanical Fixes

**Only implement mechanical/automated fixes**:

```bash
# Example: Update coverage threshold
sed -i 's/fail_under = 70/fail_under = 80/' pyproject.toml

# Example: Remove backup files
find . -name "*.orig" -type f -delete
echo "*.orig" >> .gitignore
echo "*.bak" >> .gitignore

# Example: Fix model config naming inconsistency
# Edit config/models/<file>.yaml to align name with file name
```

**DO NOT implement**: complex refactoring, architectural changes, or anything requiring design decisions.

### Phase 5: Handle Docstring False Positives

Quality audit tools often parse line-by-line. A line starting with a lowercase continuation word triggers a fragment heuristic.

**Identify the ambiguity**: a line break mid-sentence where line N+1 looks like a fragment without line N context.

**Apply the minimal fix** — restructure with a relative clause or reflow to avoid mid-clause line endings:
```python
# BEFORE (visually ambiguous)
"""Module summary line.

This module provides the Foo class that does X
across multiple Y, with support for
Z and W.
"""

# AFTER (unambiguous — relative clause)
"""Module summary line.

This module provides the Foo class, which does X
across multiple Y, with support for
Z and W.
"""
```

Check the issue for any suggested replacement text: `gh issue view <number> --comments`

Run pre-commit on the file only:
```bash
pre-commit run --files <module>.py
```

### Phase 6: Verify and Create PR

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Verify specific changes
grep "fail_under" pyproject.toml
grep -E "\.orig|\.bak" .gitignore

# Review diff
git diff
```

Commit and create PR:
```bash
git add <changed-files>
git commit -m "feat(quality): Implement code quality audit findings from #<issue>

Implements HIGH priority fixes:
1. Created <N> GitHub tracking issues (#X-Y)
2. [Each HIGH priority fix]

Closes #<tracking-issue>"

git push -u origin <branch-name>
gh pr create \
  --title "Implement Code Quality Audit Findings" \
  --body "Closes #<tracking-issue>" \
  --label "refactor,testing,documentation"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `--json` flag with `gh issue create` | `issue_num=$(gh issue create ... --json number --jq .number)` | `--json` flag not available in all gh CLI versions | Extract issue number from URL: `echo "$issue_url" \| grep -oP '\d+$'` |
| Assuming all fixes need implementation | Created tasks for mypy, YAML linting, .env.example, CONTRIBUTING.md | Many items were already implemented | Check existing infrastructure FIRST before planning implementation |
| Parallel issue creation with unknown labels | Attempted to create all issues in parallel with label 'tooling' | Label didn't exist; parallel execution means all siblings failed | Always validate labels with `gh label list` first; use sequential scripts |
| Continuing after first parallel failure | Continued with remaining calls after first failed | `<tool_use_error>Sibling tool call errored</tool_use_error>` cancelled all | Use sequential shell script for batch operations |
| Tracking issue created last | Created tracking issue after all batch issues | Issue numbers in tracking body were TBD | Create tracking issue after first batch, before final batch |
| Skipping existing-skill check | Created new retrospective without checking for existing skill | Duplicate skill created instead of updating existing one | Always check `skills/` for matching skill name before creating new one |

## Results & Parameters

### Issue Creation Timing (38 min for 24 issues)

| Activity | Time |
|----------|------|
| Label validation | 2 min |
| Manual issue creation (first 3) | 5 min |
| Tracking issue creation | 3 min |
| Script generation | 8 min |
| Script execution | 15 min |
| Verification | 5 min |

### Configuration Change Patterns

```toml
# pyproject.toml coverage threshold
[tool.coverage.report]
fail_under = 80  # Changed from 70
```

```text
# .gitignore additions
*.orig
*.bak
```

### Verification Commands

```bash
# Confirm sub-test counts
ls tests/<path>/subtests/ | wc -l

# Confirm coverage threshold
grep "fail_under" pyproject.toml

# Confirm integration tests exist
ls tests/integration/

# Confirm integration tests are in CI matrix
grep "integration" .github/workflows/test.yml
```

### Label Strategy

| Label Type | Options | Usage |
|------------|---------|-------|
| Priority | P0, P1, P2 | One required per issue |
| Category | documentation, testing, refactoring, config | 1-2 per issue |
| Type | bug, epic, tech-debt, enhancement | 0-1 per issue |

### Success Indicators

- All audit findings have tracking issues (or are fixed directly if trivial)
- P0/P1 mechanical fixes are implemented in the same PR as issue filing
- Pre-commit hooks pass on all changed files
- PR created with auto-merge enabled
- Existing skill updated rather than duplicated
