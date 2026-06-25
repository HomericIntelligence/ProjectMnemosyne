---
name: python-testing-coverage-xml-gitignore
description: "Prevent generated pytest-cov artifacts from being committed. Use when: (1) coverage.xml appears in git status or PR diff, (2) htmlcov/ directory is tracked, (3) CI diff shows absolute developer paths in coverage reports."
category: ci-cd
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Python Testing: Exclude Coverage Artifacts from Git

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Prevent `coverage.xml` and `htmlcov/` from being committed to feature branches |
| **Outcome** | Successful — artifacts removed, `.gitignore` updated, pre-commit passed |
| **Verification** | verified-local (507 tests passed, pre-commit clean) |

## When to Use

- `coverage.xml` appears in `git status` or a PR diff
- `htmlcov/` directory is tracked by git
- PR review flags a committed coverage report with embedded absolute paths
- Setting up a new Python project using pytest-cov

## Verified Workflow

### Quick Reference

```bash
# Remove coverage artifact if committed
rm -f coverage.xml
rm -rf htmlcov/

# Add to .gitignore (add after .coverage entry)
echo "coverage.xml" >> .gitignore
echo "htmlcov/" >> .gitignore
```

### Detailed Steps

1. **Delete the committed artifact** from the working tree:
   ```bash
   rm -f coverage.xml
   rm -rf htmlcov/
   ```

2. **Add entries to `.gitignore`** — place them near the `.coverage` entry for logical grouping:
   ```
   .coverage
   coverage.xml
   htmlcov/
   ```

3. **Verify** the files are now ignored:
   ```bash
   git status  # coverage.xml and htmlcov/ should not appear
   git check-ignore -v coverage.xml  # should print the .gitignore rule
   ```

4. **Run pre-commit** to confirm no other hooks flag the change:
   ```bash
   pre-commit run --all-files
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| None | This is a straightforward gitignore fix | N/A | Add coverage artifacts to `.gitignore` at project setup time, not after the fact |

## Results & Parameters

**Typical `.gitignore` block for Python projects using pytest-cov:**

```gitignore
# Test / coverage artifacts
.coverage
coverage.xml
htmlcov/
.pytest_cache/
```

**Why `coverage.xml` is harmful when committed:**
- Embeds absolute developer paths (e.g., `/home/username/Projects/...`) — leaks environment details
- Changes on every test run — causes repeated merge conflicts
- 800+ lines of XML — bloats PR diffs and makes useful changes harder to review
- CI generates its own; developer-generated file is stale by the time CI runs

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHermes | PR #690 (issue #520) — coverage.xml committed on feature branch | Fix applied, pre-commit passed, 507 tests green |
