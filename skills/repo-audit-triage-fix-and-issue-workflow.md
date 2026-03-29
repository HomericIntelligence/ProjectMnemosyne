---
name: repo-audit-triage-fix-and-issue-workflow
description: "Full workflow for strict repo audit triage: run audit, classify findings by complexity, batch-fix simple items in one PR, file GitHub issues for complex work. Use when: (1) running a comprehensive repository quality audit and acting on all findings, (2) needing to triage audit results into immediate fixes vs tracked issues, (3) remediating dead code, stale docs, broken CI, or missing requirements files."
category: tooling
date: 2026-03-28
version: "1.0.0"
user-invocable: false
tags: [audit, triage, remediation, github-issues, dead-code, ci, requirements, parallel-execution]
---

# Repo Audit: Triage, Fix, and Issue Workflow

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-28 |
| **Objective** | Run a strict repo audit on ProjectMnemosyne, triage all findings by complexity, fix simple/medium items directly, and file GitHub issues for complex work |
| **Outcome** | Successful. Audit scored C+ (77%). 10 simple fixes applied in one PR (14 files changed, -1,280 net lines). 6 GitHub issues filed (#1105–#1110). 9/9 tests passing after fixes. |

## When to Use

- You have just run `/repo-analyze-strict` and have a list of graded findings
- You want to separate work that fits in one PR from work that needs its own branch/epic
- You need to clear dead migration scripts, duplicate files, or stale changelog entries
- CI tests are partially broken and you need to scope the test runner to the working subset
- You suspect some test failures are pre-existing (not caused by your changes) and need to verify

## Verified Workflow

### Quick Reference

```bash
# Step 1: Run strict audit
/repo-analyze-strict

# Step 2: Triage findings (see decision criteria below)
# fix-now: <1 hour, no design decisions, self-contained
# file-as-issue: requires design, cross-repo impact, or multi-session work

# Step 3: Batch all independent fixes in parallel tool calls

# Step 4: Verify pre-existing test failures before attributing to your changes
git stash
python3 -m pytest tests/ -v 2>&1 | grep -E "PASSED|FAILED|ERROR"
git stash pop

# Step 5: Scope CI to working test files only (if needed)
# In workflow YAML, change:
#   run: pytest tests/
# to:
#   run: pytest tests/test_generate_marketplace.py -v

# Step 6: Validate skill files
python3 scripts/validate_plugins.py

# Step 7: Commit, push, open PR with auto-merge
```

### Detailed Steps

#### Phase 1: Run the Audit

Run `/repo-analyze-strict`. This produces a graded report across 15 dimensions. Record:
- Overall score (letter grade + %)
- Per-section grades
- All findings classified as Critical / Major / Minor / Nitpick

#### Phase 2: Triage Findings

Use these criteria to decide between **fix-now** and **file-as-issue**:

| Criteria | Fix Now | File as Issue |
|----------|---------|---------------|
| Time estimate | < 1 hour | > 1 hour |
| Design decisions required | None | Yes |
| Cross-repo or multi-file refactor | No | Yes |
| Requires running tests suite changes | Minor scope | Major restructure |
| Impact if deferred | Low (hygiene) | Low–Medium (can track) |
| Concrete fix known | Yes | Needs investigation |

**Fix-now categories (typical)**:
- Dead scripts / migration artifacts with no callers
- Duplicate files left from refactors
- Missing `requirements.txt` / `requirements-dev.txt`
- Stale `[Unreleased]` changelog sections
- Incorrect CLI usage in docs
- Missing test fixture fields
- `.gitignore` gaps for local config files
- Wrong metadata in `.claude-plugin/plugin.json`

**File-as-issue categories (typical)**:
- Broken test files importing non-existent modules (requires module creation or deletion + test rewrite)
- Missing type annotations throughout a codebase
- Security hardening (e.g., input validation, sandboxing)
- Major CI matrix expansion
- Architectural restructuring (e.g., monorepo layout changes)

#### Phase 3: Batch-Execute Simple Fixes

Group all independent fix-now items and execute them in parallel tool calls within a single message. This dramatically reduces round-trips:

```
Parallel batch example:
- Edit .gitignore              (independent)
- Delete dead_script_1.py      (independent)
- Delete dead_script_2.py      (independent)
- Edit CONTRIBUTING.md         (independent)
- Edit CHANGELOG.md            (independent)
- Write requirements.txt       (independent)
- Write requirements-dev.txt   (independent)
- Edit tests/conftest.py       (independent)
- Edit .github/workflows/*.yml (independent — but verify test scope first)
```

Only serialize operations that have data dependencies (e.g., read a file before editing it).

#### Phase 4: Verify Pre-Existing Test Failures

Before attributing test failures to your changes, always verify they existed before your edits:

```bash
# Stash your changes
git stash

# Run the full test suite on the unmodified codebase
python3 -m pytest tests/ -v 2>&1 | grep -E "PASSED|FAILED|ERROR|ImportError"

# Restore your changes
git stash pop
```

If failures exist on the stashed (original) codebase, they are pre-existing. Document this in the PR description and scope CI to skip the broken test files.

**Pattern for broken test files that import non-existent modules**:

```bash
# Identify the broken imports
python3 -c "import tests.test_broken_file" 2>&1

# Scope CI to only the working tests
pytest tests/test_working_file.py -v
# Do NOT run: pytest tests/  (picks up broken files)
```

File a GitHub issue for the broken test files rather than deleting them (they may contain valuable test logic once the missing module is created).

#### Phase 5: File GitHub Issues for Complex Items

For each file-as-issue item, create a GitHub issue with:
- Clear title stating the problem
- Background: what the audit found
- Acceptance criteria: what "done" looks like
- Relevant file paths and error messages
- Label: `technical-debt`, `testing`, `ci-cd`, etc.

```bash
gh issue create \
  --title "Fix broken test files importing non-existent module" \
  --body "$(cat <<'EOF'
## Background
Two test files import `fix_remaining_warnings` which does not exist...

## Acceptance Criteria
- [ ] Module created or test files deleted and rewritten
- [ ] `pytest tests/` runs clean with no ImportError

## Files Affected
- tests/test_fix_remaining_warnings.py
- tests/test_quick_reference_transform.py
EOF
)" \
  --label "technical-debt,testing"
```

#### Phase 6: Validate and Commit

```bash
# Validate skill/plugin files if any were modified
python3 scripts/validate_plugins.py

# Run scoped tests
python3 -m pytest tests/test_generate_marketplace.py -v

# Check git diff for accidental deletions
git diff --stat

# Commit
git add <specific-files>
git commit -m "fix: apply audit remediation (dead code, CI, docs, requirements)"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run `pytest tests/` in CI | Pointed the CI workflow test step at the full `tests/` directory | Two test files import a non-existent module (`fix_remaining_warnings`), causing `ImportError` collection failure | Always verify full test suite runs clean before setting CI to `tests/`; scope to working subset and file issues for broken files |
| Attribute test failures to own changes | Assumed `ImportError` failures in `test_fix_remaining_warnings.py` were caused by the deletion of migration scripts | Git stash + re-run proved the failures pre-existed | Always stash and re-run before concluding test failures are your fault |
| Fix broken test files in same PR | Tried to fix the broken test imports as part of the cleanup PR | The missing module `fix_remaining_warnings` doesn't exist and creating it is a design decision requiring its own scope | Keep the cleanup PR focused; file a dedicated issue for the broken tests |

## Results & Parameters

### Audit Score Baseline (ProjectMnemosyne, 2026-03-28)

| Section | Grade | Key Findings |
|---------|-------|--------------|
| Documentation | B+ | Good README/CHANGELOG, missing ADRs |
| AI Agent Tooling | B+ | Skills marketplace functional |
| Planning/Compliance | B | Issues filed but no roadmap doc |
| Testing | C | 2 broken test files, no coverage enforcement |
| Dependencies | D | No requirements.txt (fixed in this session) |
| Safety | D | No input validation, no sandboxing |

### Changes Applied (10 fix-now items)

| Change | Type | Net Lines |
|--------|------|-----------|
| Fix `.claude-plugin/plugin.json` metadata | Edit | +10 / -10 |
| Create `requirements.txt` | New file | +2 |
| Create `requirements-dev.txt` | New file | +3 |
| Update CI to use `requirements-dev.txt` + scoped pytest | Edit | +5 / -3 |
| Delete 5 dead migration scripts | Delete | -1,100 |
| Delete 2 duplicate plugin scripts | Delete | -180 |
| Delete duplicate `learn-trigger.py` | Delete | -35 |
| Fix `CONTRIBUTING.md` CLI usage | Edit | +1 / -1 |
| Fix `tests/conftest.py` missing fixture field | Edit | +1 |
| Add `.claude/settings.local.json` to `.gitignore` | Edit | +1 |
| Clear stale `[Unreleased]` CHANGELOG section | Edit | +2 / -8 |

**Total**: 14 files changed, ~1,280 net lines deleted

### GitHub Issues Filed (Complex Work)

| Issue | Title | Label |
|-------|-------|-------|
| #1105 | Fix broken test files (`fix_remaining_warnings`) | testing, technical-debt |
| #1106 | Add type annotations throughout codebase | code-quality |
| #1107 | Security hardening: input validation + sandboxing | security |
| #1108 | Expand CI matrix (Python versions, OS) | ci-cd |
| #1109 | Add ADR directory and document key decisions | documentation |
| #1110 | Enforce test coverage threshold in CI | testing, ci-cd |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | Strict audit + triage + 10-item cleanup PR (March 2026) | 9/9 tests passing, 6 issues filed (#1105–#1110) |

## References

- Related skill: [audit-driven-remediation](./audit-driven-remediation.md) — implementing audit findings systematically (focuses on CI/source/test changes, not triage)
- Related skill: [issue-triage-wave-parallel-execution](./issue-triage-wave-parallel-execution.md) — parallel batching of independent fixes
- Related skill: [pre-existing-ci-failure-triage](./pre-existing-ci-failure-triage.md) — diagnosing failures that existed before your changes
- Related skill: [preexisting-ci-failure-triage](./preexisting-ci-failure-triage.md) — alternate entry for same pattern
