---
name: repo-hygiene-audit-implementation
description: 'Workflow for implementing repository hygiene audit fixes. Use when:
  (1) an automated audit surfaces actionable code quality issues, (2) migrating Pydantic
  to_dict() to model_dump(), (3) adding debug logging to silent exception catches.'
category: architecture
date: 2026-03-13
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | repo-hygiene-audit-implementation |
| **Category** | architecture |
| **Source** | ProjectScylla 2026-03-13 post-audit hygiene sprint |
| **Trigger** | Automated repository audit surfaces actionable fixes |

This skill captures the verified workflow for triaging and implementing repository hygiene
fixes following an automated code quality audit. It covers the triage step (distinguishing
real issues from false positives), safe Pydantic `model_dump()` migration, exception
logging patterns, and the multi-PR git workflow with ProjectScylla-specific gotchas.

## When to Use

- An automated audit (e.g. GitHub code scanning, internal audit script) scores the repo and
  lists findings
- You need to decide which `to_dict()` methods can safely be replaced with `model_dump()`
- You have bare `except ... pass` blocks that should emit debug log lines
- You need to fix metadata in `pyproject.toml` (URLs, authors) or add security policy files

## Verified Workflow

### Quick Reference

```bash
# Triage: verify each audit finding against actual code before acting
grep -n "to_dict" scylla/e2e/models.py
grep -n "except.*:" scylla/e2e/checkpoint.py | grep -v logger

# model_dump() candidacy check: safe only when fields map 1:1 to serialized keys
# and no Path→str, Enum→value, computed properties, or nested to_dict() calls needed

# Exception logging pattern (debug for non-fatal fallbacks)
except (OSError, json.JSONDecodeError) as e:
    logger.debug("Disk read failed, falling back: %s", e)

# Push branches one at a time (HomericIntelligence repo limits to 2 ref updates per push)
git push -u origin branch-1
git push -u origin branch-2
```

### Step 1: Triage audit findings

Before writing any code, verify each finding against the actual codebase. Audits often
report issues that have already been fixed or don't exist:

```bash
# Confirm claimed missing files
git status --short | grep "??"          # untracked (e.g. SECURITY.md exists but untracked)
ls -la <path>                           # claimed-empty dirs

# Confirm claimed code patterns
grep -rn "to_dict" scylla/ scripts/     # manual to_dict() methods
grep -n "except.*:" scylla/e2e/*.py | grep "pass$"  # silent catches
grep -n "mvillmow" pyproject.toml      # URL mismatches
```

Build a verified issue table:

| Audit Finding | Actual Status |
| --- | --- |
| SECURITY.md missing | NOT missing — exists but untracked |
| 11 manual to_dict() | CONFIRMED in models.py |
| 6 silent except catches | CONFIRMED (6 locations) |
| pyproject.toml URL mismatch | CONFIRMED |

### Step 2: Assess model_dump() migration safety

For each `to_dict()` method, check candidacy:

**Safe to replace with `model_dump()`** — fields map 1:1 to output dict, no custom transforms:

```python
# BEFORE (manual, error-prone)
def to_dict(self) -> dict[str, Any]:
    return {
        "input_tokens": self.input_tokens,
        "output_tokens": self.output_tokens,
        "cache_creation_tokens": self.cache_creation_tokens,
        "cache_read_tokens": self.cache_read_tokens,
    }

# AFTER (idiomatic, maintained automatically)
def to_dict(self) -> dict[str, Any]:
    return self.model_dump()
```

**NOT safe — keep custom implementation** if any of these apply:
- `Path` fields that need `str()` coercion: `"path": str(self.path)`
- `Enum` fields that need `.value`: `"tier_id": self.tier_id.value`
- Computed/property fields: `"cost_of_pass": self.cost_of_pass`
- Nested `to_dict()` calls: `"runs": [r.to_dict() for r in self.runs]`
- Fields that must be excluded (ephemeral runtime state)

> **Rule**: If the method body is `return {field: getattr(self, field) for ...}` with no
> transforms, use `model_dump()`. Otherwise keep custom logic.

### Step 3: Add exception logging

Replace silent `except` blocks with `logger.debug()`. Use `debug` (not `warning`) for
expected non-fatal fallbacks:

```python
# BEFORE — silent, undebuggable
except (OSError, json.JSONDecodeError, KeyError):
    pass  # Disk read failed — fall through and save as-is

# AFTER — debug-level, diagnosable
except (OSError, json.JSONDecodeError, KeyError) as e:
    logger.debug("Checkpoint disk-merge read failed, saving as-is: %s", e)
```

Use `logger.warning()` only for unexpected swallowed exceptions that indicate a bug.

**Do NOT add `# noqa: BLE001`** unless `BLE` is in your ruff `select` list. Check first:

```bash
grep "select" pyproject.toml  # look for "BLE" in the select list
```

In ProjectScylla, `select = ["E", "F", "W", "I", "N", "D", "UP", "S101", "B", "SIM", "C4", "C901", "RUF"]`
— `BLE` is NOT included, so `# noqa: BLE001` is unnecessary noise.

### Step 4: Fix metadata and add policy files

```toml
# pyproject.toml — fix org name in URLs
[project.urls]
Homepage = "https://github.com/HomericIntelligence/ProjectScylla"
Repository = "https://github.com/HomericIntelligence/ProjectScylla"
Issues = "https://github.com/HomericIntelligence/ProjectScylla/issues"
```

For untracked files like SECURITY.md: just `git add` them — no content changes needed.

### Step 5: Commit and push as separate PRs

Group changes into logical PRs (quick wins / exception logging / refactor):

```bash
# Create branch from main
git checkout -b hygiene-pr1-description

# Stage specific files only
git add pyproject.toml SECURITY.md

# IMPORTANT: stage pixi.lock BEFORE committing if pip-audit hook ran
# (pip-audit modifies pixi.lock; unstaged lock causes stash conflict failure)
git add pixi.lock

git commit -m "fix(pyproject): correct repository URLs; add SECURITY.md"

# Push ONE branch at a time (HomericIntelligence limits to 2 ref updates per push)
git push -u origin hygiene-pr1-description
```

**Critical gotcha**: The pip-audit pre-commit hook modifies `pixi.lock` as a side effect.
If `pixi.lock` is unstaged when the hook runs, pre-commit stashes it, the hook modifies it,
pre-commit tries to restore the stash → conflict → hook "fails" even though no vulnerabilities
were found. Fix: **always stage `pixi.lock` before committing** after pip-audit has run once.

### Step 6: Enable auto-merge

```bash
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Push all 3 branches at once | `git push -u origin branch1 branch2 branch3` | Remote rejected: "Pushes can not update more than 2 branches or tags" | Push branches one at a time in HomericIntelligence repos |
| Add `# noqa: BLE001` to broad except | Added noqa comment to suppress BLE001 | `BLE` not in ruff select — comment is unnecessary noise, ruff warns about unused ignores | Always check `pyproject.toml` select list before adding noqa comments |
| First commit attempt without staging pixi.lock | `git add pyproject.toml SECURITY.md && git commit` | pip-audit hook stash conflict: hook modifies pixi.lock mid-run but can't restore stash | Stage pixi.lock before committing whenever pip-audit hook has already run |
| Migrate all 11 to_dict() to model_dump() | Planned to replace all 11 methods | 10/11 have Path→str, Enum→value, computed properties, or nested calls — model_dump() would produce wrong output | Only migrate to_dict() when fields map 1:1 to output with no transforms |

## Results & Parameters

**Session outcome**: 3 PRs created, all passing CI

| PR | Branch | Change |
| ---- | -------- | -------- |
| #1482 | `hygiene-pr1-pyproject-security` | pyproject.toml URLs + SECURITY.md |
| #1483 | `hygiene-pr2-silent-exceptions` | 5 silent exception catches → logger.debug() |
| #1484 | `hygiene-pr3-tokenstats-model-dump` | TokenStats.to_dict() → model_dump() |

**Test results**: 1548 unit tests passed, all pre-commit hooks green.

**model_dump() migration rate**: 1/11 methods (9%) were safe to migrate.
The other 10 retain custom implementations with good reason.

**Exception logging level guide**:
- `logger.debug()` — expected fallback (disk read failed, version detection, timezone parse)
- `logger.warning()` — unexpected swallowed exception that might indicate a bug
- `logger.error()` — should not be silently caught; consider re-raising instead
