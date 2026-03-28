---
name: tooling-python-codebase-symbol-rename
description: "Rename Python symbols (functions, classes, constants, CLI flags, enum variants, filenames) across an entire Python codebase. Use when: (1) renaming a concept across src/, tests/, and scripts/ Python files, (2) renaming a CLI flag with dashes to match a new convention, (3) renaming enum variants to match a renamed operation phase."
category: tooling
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - rename
  - python
  - refactor
  - symbol-rename
  - file-rename
  - enum
  - cli
---

# Python Codebase Symbol Rename

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-28 |
| **Objective** | Rename `retrospective` concept to `learn` across ProjectScylla's Python automation pipeline |
| **Outcome** | All Python symbols renamed, files renamed with `git mv`, PR HomericIntelligence/ProjectScylla#1734 created |
| **Verification** | verified-precommit (pre-commit hooks pass; CI pending at time of capture) |

> **Note:** This skill covers renaming Python-level symbols. For renaming plugin directories,
> slash commands, and markdown-based skill references, see
> [tooling-plugin-command-codebase-rename](tooling-plugin-command-codebase-rename.md).

## When to Use

- Renaming a concept across multiple Python files in `src/`, `tests/`, `scripts/`
- Renaming function names (e.g., `run_retrospective()` → `run_learn()`)
- Renaming constants (e.g., `RETROSPECTIVE_TIMEOUT` → `LEARN_TIMEOUT`)
- Renaming enum variants (e.g., `ImplementationPhase.RETROSPECTIVE` → `LEARN`)
- Renaming CLI flags (e.g., `--no-retrospective` → `--no-learn`)
- Renaming module files (e.g., `retrospective.py` → `learn.py`) while preserving git history
- Distinguishing "symbol renames" (change code) from "prose renames" (leave natural language as-is)

## Verified Workflow

### Quick Reference

```bash
# 1. Discover all affected files
grep -rn "<old_name>" src/ tests/ scripts/ --include="*.py" -l

# 2. File renames — use git mv to preserve history
git mv src/pkg/automation/old_name.py src/pkg/automation/new_name.py
git mv tests/unit/automation/test_old_name.py tests/unit/automation/test_new_name.py

# 3. Symbol renames in each file — use replace_all: true in Edit tool
#    (or sed -i for each pattern if working in bash)
for f in src/ tests/ scripts/; do
  sed -i 's/old_symbol_name/new_symbol_name/g' $(grep -rl "old_symbol_name" $f --include="*.py")
done

# 4. Verify only prose remains (natural language comments are OK to leave)
grep -rn "old_name" src/ tests/ scripts/ --include="*.py"
# Expected: only comments/docstrings with natural language ("run a retrospective")

# 5. Stage and commit
git add src/ tests/ scripts/
git status  # Confirm renames show as R  old.py -> new.py
git commit -m "refactor: rename <old> to <new> across Python codebase"
git push -u origin <branch>
gh pr create --repo <org>/<repo> ...
```

### Detailed Steps

**Phase 1: Discover all affected files**

1. Find all Python files containing the old name (symbols only — check both snake_case and
   UPPER_CASE and kebab-case for CLI flags):

   ```bash
   grep -rn "retrospective\|RETROSPECTIVE" src/ tests/ scripts/ --include="*.py" -l
   ```

2. Review each hit to distinguish:
   - **Symbol references** (function calls, class names, constants, enum variants, imports,
     CLI flags, log file names) → MUST rename
   - **Prose comments/docstrings** ("run a retrospective", "the retrospective phase") → OK to leave

**Phase 2: Rename files with `git mv`**

Use `git mv` for file renames — git detects rename by content similarity (~50% threshold),
so the rename appears in `git log --follow` and `git diff` as `R  old.py -> new.py`:

```bash
git mv src/pkg/automation/retrospective.py src/pkg/automation/learn.py
git mv tests/unit/automation/test_retrospective.py tests/unit/automation/test_learn.py
```

After `git mv`, the old filename is staged for deletion and the new filename is staged as
added. No separate `git add` or `git rm` needed for the renamed files.

**Phase 3: Edit file contents**

For each renamed file and any file that imports/references the old symbols, use `replace_all: true`
on each distinct symbol pattern. Process symbols from most-specific to least-specific to avoid
partial replacements:

| Order | Pattern | Example |
|-------|---------|---------|
| 1 | Private helper function | `_run_retrospective` → `_run_learn` |
| 2 | Private check function | `_retrospective_needs_rerun` → `_learn_needs_rerun` |
| 3 | Public function | `run_retrospective` → `run_learn` |
| 4 | Public check function | `retrospective_needs_rerun` → `learn_needs_rerun` |
| 5 | Enum variant | `ImplementationPhase.RETROSPECTIVE` → `ImplementationPhase.LEARN` |
| 6 | Enum definition | `.RETROSPECTIVE` → `.LEARN` |
| 7 | Boolean flag field | `enable_retrospective` → `enable_learn` |
| 8 | CLI flag (dashes) | `--no-retrospective` → `--no-learn` |
| 9 | Log filename pattern | `retrospective-{n}.log` → `learn-{n}.log` |
| 10 | Import name | `from .retrospective import` → `from .learn import` |
| 11 | Module constant | `RETROSPECTIVE_TIMEOUT` → `LEARN_TIMEOUT` |

**Phase 4: Verify only prose remains**

```bash
grep -rn "retrospective" src/ tests/ scripts/ --include="*.py"
```

Every remaining hit should be a natural-language comment or docstring, e.g.:

```python
# This runs a retrospective to capture session learnings  ← OK to leave
"""Run a retrospective on the session."""                  ← OK to leave
```

If any symbol references remain, fix them before proceeding.

**Phase 5: Stage, commit, and push**

```bash
# Stage all changed files (git mv files are already staged)
git add src/ tests/ scripts/

# Verify staging looks correct
git status
# Should show: R  src/pkg/automation/retrospective.py -> src/pkg/automation/learn.py
# Should show: M  src/pkg/other_file.py (for files with content edits only)

# Commit
git commit -m "refactor: rename retrospective to learn across Python codebase

- Renamed retrospective.py → learn.py and test_retrospective.py → test_learn.py
- Renamed all public/private functions, constants, enum variants, CLI flags
- Prose comments left unchanged (natural language)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push -u origin <branch>
gh pr create --repo <org>/<repo> --title "refactor: rename retrospective to learn" ...
```

### Important: Do git operations in main context

If a sub-agent makes the file edits, it may return to the main context without completing
git operations. Always run `git add`, `git commit`, `git push`, and `gh pr create` in the
main context after any sub-agent returns.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Sub-agent with worktree isolation | Delegated all code changes + git workflow to a sub-agent | Agent made all file edits correctly but returned without committing, pushing, or creating a PR | Sub-agents may not complete git workflows — run add/commit/push/PR in main context after agent returns |
| Renaming all occurrences of "retrospective" | Tried replacing every occurrence including prose | Over-replaced prose comments/docstrings ("run a retrospective") | Only rename symbol references, not natural language prose |

## Results & Parameters

### Rename Scope (ProjectScylla)

```yaml
files_renamed:
  - src/scylla/automation/retrospective.py → learn.py
  - tests/unit/automation/test_retrospective.py → test_learn.py

symbols_renamed:
  functions:
    - run_retrospective() → run_learn()
    - retrospective_needs_rerun() → learn_needs_rerun()
    - _run_retrospective() → _run_learn()
    - _retrospective_needs_rerun() → _learn_needs_rerun()
  enums:
    - ImplementationPhase.RETROSPECTIVE → LEARN
    - ReviewPhase.RETROSPECTIVE → LEARN
  fields:
    - enable_retrospective → enable_learn
  cli_flags:
    - --no-retrospective → --no-learn
  constants:
    - RETROSPECTIVE_TIMEOUT → LEARN_TIMEOUT
  log_patterns:
    - retrospective-{n}.log → learn-{n}.log

prose_left_unchanged: true  # natural language comments
```

### Symbol Categories Reference

| Category | Python Pattern | Rename Strategy |
|----------|---------------|----------------|
| Public function | `def run_retrospective(` | Rename definition + all call sites |
| Private function | `def _run_retrospective(` | Rename definition + all call sites |
| Enum variant | `RETROSPECTIVE = auto()` | Rename definition + all references |
| Class field | `enable_retrospective: bool` | Rename definition + all attribute accesses |
| CLI flag | `add_argument("--no-retrospective")` | Rename the string + dest parameter |
| Module constant | `RETROSPECTIVE_TIMEOUT = 300` | Rename definition + all references |
| Log filename | `f"retrospective-{n}.log"` | Rename the string template |
| Import | `from .retrospective import` | Rename after file rename |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1734, rename retrospective → learn in Python automation pipeline | 2026-03-28 session |
