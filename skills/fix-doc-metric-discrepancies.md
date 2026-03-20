---
name: fix-doc-metric-discrepancies
description: Fix stale or incorrect metric values in documentation (test counts, coverage
  thresholds, command paths) that drift from actual codebase state. Use when a code
  audit reveals contradictions between docs and pyproject.toml, README, or CI config.
category: documentation
date: 2026-02-27
version: 1.0.0
user-invocable: true
---
# Fix Documentation Metric Discrepancies

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-27 |
| **Objective** | Fix four documentation discrepancies found during code audit: coverage threshold, test counts (x2), and `--cov` path typo |
| **Outcome** | All five fixes applied; 3,185 tests passed at 78.36% coverage; PR #1150 merged |
| **Related Issues** | ProjectScylla #1112 |

## When to Use This Skill

Use this skill when:

- Documentation states a metric (test count, coverage %, subtest count) that doesn't match the actual codebase
- A command in README or docs has a typo (e.g., doubled path component like `scylla/scylla`)
- CLAUDE.md and `pyproject.toml` contradict each other on thresholds
- A code audit issue lists specific files and line-level fixes needed

**Triggers:**

- Issue title contains "discrepancy", "typo", "stale", "mismatch", "fix docs"
- `fail_under` in `pyproject.toml` doesn't match the percentage stated in `CLAUDE.md`
- `pytest --cov=<path>` in README uses wrong path (doubled component, wrong module name)
- Test count claims are more than ~10% off from `pytest --collect-only -q | tail -1`

## Verified Workflow

### Phase 1: Audit Actual Values

```bash
# Actual test count
pixi run python -m pytest --collect-only -q tests/ 2>/dev/null | tail -3

# Actual test file count
find tests/ -name "test_*.py" | wc -l

# Actual coverage threshold in pyproject.toml
grep "fail_under" pyproject.toml

# Actual YAML subtest count (count files, not dirs)
find config/ -name "*.yaml" | wc -l   # adjust path to match project
```

### Phase 2: Cross-Reference Against Documentation

Check these locations for numeric claims:

| Location | What to Check |
|----------|--------------|
| `CLAUDE.md` | Coverage % in "Current Status" line; subtest counts in tier table |
| `README.md` | Test count badges/bullets; `--cov=<path>` in Running Tests section |
| `pyproject.toml` | `[tool.coverage.report] fail_under` |

### Phase 3: Apply Fixes (Minimal, Targeted)

Use `Edit` tool with exact string replacement — never rewrite whole sections.

**Coverage threshold:**
```
CLAUDE.md: "73%+ test coverage" → "75%+ test coverage"
```

**Subtest count (remove misleading `+` if count is exact):**
```
CLAUDE.md: "120+ YAML subtests" → "120 YAML subtests"
```

**Test counts in README (use round numbers with `+` suffix for forward-compatibility):**
```
"2026+ tests" → "3,000+ tests"
"115+ test files" → "127+ test files"
```

**`--cov` path typo:**
```
--cov=scylla/scylla  →  --cov=scylla
```

### Phase 4: Verify & Commit

```bash
# Confirm only the intended files changed
git diff --stat

# Run tests to confirm nothing broken (docs-only changes, but good hygiene)
pixi run python -m pytest tests/ -v --tb=short 2>&1 | tail -5

# Commit
git add README.md CLAUDE.md   # only the files that changed
git commit -m "docs(readme): fix test counts, file counts, and --cov path typo

- Update test count from N+ to M+ (actual: X)
- Update test file count from A+ to B+ (actual: B)
- Fix --cov=scylla/scylla typo → --cov=scylla

Closes #<issue>"

git push -u origin <branch>
gh pr create --title "[Docs] Fix documentation discrepancies" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Key Observations

1. **Worktree branches may already have partial fixes** — the issue description lists all problems, but the branch you're working on might have been created from a commit that already fixed some of them. Always read each file before editing to avoid re-applying changes or creating duplicates.

2. **Use `+` suffix for forward-compatibility on counts** — prefer `3,000+` over `3,016` for test counts in README. Exact numbers go stale; round numbers with `+` remain accurate through growth.

3. **Exact subtest counts should not have `+`** — if the count is deterministic (sum of tier table = 120), remove the `+` to avoid implying uncertainty. Dynamic counts (test functions) benefit from `+`.

4. **`--cov` path must match the installed package name** — `--cov=scylla/scylla` is wrong when the package is installed as `scylla`; `pixi run pytest --cov=scylla` is correct. Check `pyproject.toml [tool.setuptools.packages]` or `[project] name` to confirm.

5. **Pre-push hook runs full test suite** — the project's pre-push hook validates coverage before allowing push. This takes ~46 seconds for 3,185 tests. Account for this in timing expectations.

## Results

| File | Changes Applied |
|------|----------------|
| `README.md` | `2026+` → `3,000+` tests; `115+` → `127+` test files (×2 occurrences); `--cov=scylla/scylla` → `--cov=scylla` |
| `CLAUDE.md` | Already correct in worktree (prior commit had fixed `73%` → `75%` and `120+` → `120`) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1112, PR #1150 | 3,185 tests, 78.36% coverage, pre-push hook passed |
