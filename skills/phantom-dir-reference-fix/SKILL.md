# Skill: phantom-dir-reference-fix

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-22 |
| Objective | Remove phantom `tests/integration/` directory references from README.md and CONTRIBUTING.md |
| Outcome | Success — all phantom references removed, PR #954 created and auto-merge enabled |
| Category | docs |

## When to Use

Use this skill when:
- A quality audit identifies documentation referencing directories that do not exist in the repository
- `grep -r "tests/integration" docs/ README.md CONTRIBUTING.md` returns hits in user-facing docs
- Contributors are misled by stale test-category descriptions or nonexistent pytest invocation paths
- You need to correct test counts or category descriptions after test restructuring

## Verified Workflow

### 1. Identify all phantom references

```bash
grep -rn "tests/integration" docs/ README.md CONTRIBUTING.md
```

Check which hits are in user-facing documentation (README.md, CONTRIBUTING.md, docs/) vs. archived snapshots (docs/arxiv/ dryrun workspaces) — archived snapshots are out of scope.

### 2. Fix README.md — test category bullets

Remove the phantom category bullet and fold its count into the parent category:

**Before:**
```markdown
- **Unit Tests** (67+ files): Analysis, adapters, config, executors, judges, metrics, reporting
- **Integration Tests** (2 files): End-to-end workflow testing
```

**After:**
```markdown
- **Unit Tests** (70+ files): Analysis (incl. integration-style tests), adapters, config, executors, judges, metrics, reporting
```

Key: update the unit test count to absorb the integration-style tests (they live in `tests/unit/analysis/` as `test_integration.py`, `test_cop_integration.py`, `test_duration_integration.py`).

### 3. Fix README.md — running tests code block

Remove the nonexistent invocation:

**Before:**
```bash
# Integration tests
pixi run pytest tests/integration/ -v

# Coverage analysis
```

**After:**
```bash
# Coverage analysis
```

### 4. Fix CONTRIBUTING.md — write tests comment

**Before:**
```bash
# Create tests in tests/unit/ or tests/integration/
```

**After:**
```bash
# Create tests in tests/unit/
```

### 5. Fix CONTRIBUTING.md — running tests section

Replace the phantom invocation with the actual location of integration-style tests:

**Before:**
```bash
pixi run pytest tests/unit/ -v          # Unit tests only
pixi run pytest tests/integration/ -v   # Integration tests
```

**After:**
```bash
pixi run pytest tests/unit/ -v          # Unit tests only
pixi run pytest tests/unit/analysis/ -v # Includes integration-style tests
```

### 6. Verify clean

```bash
grep -r "tests/integration" docs/ README.md CONTRIBUTING.md
# Should return no results
```

### 7. Commit and PR

```bash
git add README.md CONTRIBUTING.md
git commit -m "fix(docs): Remove phantom tests/integration/ references"
git push -u origin 848-auto-impl
gh pr create --title "fix(docs): Remove phantom tests/integration/ references" --body "Closes #848"
gh pr merge --auto --rebase
```

## Failed Attempts

None — the task was a straight documentation edit with no code changes required, so no approaches failed. The only subtlety was confirming that `docs/arxiv/` dryrun snapshot references were out of scope before declaring the grep clean.

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Files changed | `README.md`, `CONTRIBUTING.md` |
| Lines removed | 7 |
| Lines added | 3 |
| Pre-commit hooks | All passed (markdown lint, trailing whitespace, end-of-file) |
| PR | https://github.com/HomericIntelligence/ProjectScylla/pull/954 |
| Issue | #848 |
| Branch | `848-auto-impl` |

## Key Insight

Integration-style tests in ProjectScylla live inside `tests/unit/analysis/` under names like `test_integration.py`, `test_cop_integration.py`, and `test_duration_integration.py`. There is **no** dedicated `tests/integration/` directory. When documenting test categories, fold these into the unit test count with a clarifying note rather than listing them as a separate category.
