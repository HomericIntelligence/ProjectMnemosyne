---
name: tighten-except-exception-clauses
description: "Audit and tighten broad except Exception clauses in Python \u2014 replacing\
  \ with specific types where feasible and annotating legitimate broad catches with\
  \ justification comments"
category: architecture
date: 2026-03-03
version: 1.0.0
user-invocable: false
tags:
- python
- exceptions
- refactoring
- code-quality
- ruff
- pre-commit
- subprocess
- OSError
- json
---
# Tighten Broad `except Exception` Clauses

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-03 |
| **Objective** | Audit 33 `except Exception` clauses across 3 worst offenders in `scylla/` and replace with specific types where feasible |
| **Outcome** | ✅ 17 clauses tightened, 23 annotated, net reduction 128 → 111 project-wide |
| **Project** | ProjectScylla |
| **PR** | [#1374](https://github.com/HomericIntelligence/ProjectScylla/pull/1374) |

## When to Use

Use this skill when:

- Static analysis (ruff `BLE001` or similar) reports broad `except Exception` clauses
- A code quality audit asks to tighten exception handling in specific worst-offender files
- You need to categorize each `except Exception` as "Keep" vs "Tighten" before making changes

## The Core Decision Framework

For each `except Exception` clause, answer:

1. **Is this a top-level system boundary?** (thread pool worker, `run_experiment()`, main loop error recovery, graceful shutdown handler) → **Keep** with justification comment
2. **Is this a non-blocking fire-and-forget handler?** (follow-up actions that must never propagate errors) → **Keep** with justification comment
3. **Does the try block call only subprocess functions?** → Tighten to `(subprocess.CalledProcessError, FileNotFoundError, OSError)` or `subprocess.SubprocessError`
4. **Does the try block call only file I/O?** → Tighten to `OSError`
5. **Does the try block call only JSON parsing?** → Tighten to `json.JSONDecodeError`
6. **Does the try block call a domain-specific function that raises a known exception?** → Import and use the specific exception class
7. **Does the try block mix multiple different error sources?** → Use a tuple of specific types, or keep broad with comment

## Verified Workflow

### 1. Locate All `except Exception` Clauses

```bash
grep -rn "except Exception" scylla/ | wc -l           # baseline count
grep -n "except Exception" scylla/path/to/file.py      # per-file locations
```

### 2. Read Context Around Each Clause

For each occurrence, read ~15 lines before to understand what the `try` block does:

```bash
awk 'NR>=LINE-10 && NR<=LINE+5' scylla/path/to/file.py
```

### 3. Categorize: Keep vs Tighten

| Category | Typical Pattern | Action |
|----------|----------------|--------|
| **Keep** | Thread pool catch-all, top-level `run()`, interrupt handler | Add `# broad catch: <reason>` inline comment |
| **Tighten** | `subprocess.run()` call only | `(subprocess.CalledProcessError, FileNotFoundError, OSError)` |
| **Tighten** | File read/write only | `OSError` |
| **Tighten** | `json.loads()` only | `json.JSONDecodeError` |
| **Tighten** | Domain-specific function | Import + use specific exception class |
| **Tighten** | `subprocess.run()` + file I/O | `(subprocess.SubprocessError, OSError)` |
| **Tighten** | JSON parse + file I/O + subprocess | `(subprocess.SubprocessError, json.JSONDecodeError, OSError)` |

### 4. Import Required Exception Classes

If tightening to a domain-specific exception (e.g., `CyclicDependencyError`), import it:

```python
# BEFORE:
from .dependency_resolver import DependencyResolver

# AFTER:
from .dependency_resolver import CyclicDependencyError, DependencyResolver
```

### 5. Apply Changes

Replace the `except Exception` clauses with specific types. For kept clauses, add an inline comment:

```python
# Tightened example:
except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
    logger.error(f"Command failed: {e}")

# Kept with justification:
except Exception as e:  # broad catch: top-level worker boundary, must not crash thread pool
    logger.error(f"Unexpected {type(e).__name__}: {e}")
```

### 6. Run Tests + Pre-commit

```bash
pixi run python -m pytest tests/unit/ -x -q
pre-commit run --all-files
```

**Critical**: Pre-commit may fail on the first commit attempt because `ruff-format` reformats inline comments that exceed the 100-character line length. The formatter wraps them to the next line automatically. Just re-stage and commit again:

```bash
git add <modified files>
git commit -m "..."   # round 1: formatter modifies files, commit fails
git add <modified files>
git commit -m "..."   # round 2: formatter passes, commit succeeds
```

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Exception Type Reference for ProjectScylla

| Operation | Specific Exception Types |
|-----------|--------------------------|
| `subprocess.run()` / `run()` wrapper | `(subprocess.CalledProcessError, FileNotFoundError, OSError)` |
| Any subprocess operation | `subprocess.SubprocessError` (base class) |
| File read/write | `OSError` (covers `IOError`, `FileNotFoundError`, `PermissionError`) |
| `json.loads()` / `json.load()` | `json.JSONDecodeError` |
| Pydantic `.model_validate_json()` | `(json.JSONDecodeError, ValueError)` |
| `DependencyResolver.detect_cycles()` | `CyclicDependencyError` (import from `.dependency_resolver`) |
| Mixed subprocess + file I/O | `(subprocess.SubprocessError, OSError)` |
| State file load (JSON + file + Pydantic) | `(json.JSONDecodeError, ValueError, OSError)` |

## Justification Comment Patterns

Keep these comments short (< 60 chars after `#`) to avoid E501:

```python
# broad catch: top-level worker boundary, must not crash thread pool
# broad catch: worker threads can raise any exception
# broad catch: network errors, API failures, JSON parsing all possible
# broad catch: thread pool can raise various internal errors
# broad catch: GitHub API can fail in many ways; continue with others
# broad catch: external claude process; non-blocking, must not propagate
# broad catch: top-level follow-up boundary; non-blocking, must not propagate
# broad catch: gh CLI + JSON parsing; fallback is to create PR
# broad catch: resume can fail from JSON/IO/state errors
# broad catch: pipeline baseline is non-critical; build/git/IO can all fail
# broad catch: cleanup must not raise; any error is non-fatal
# broad catch: interrupt handler; must not mask interrupt
# broad catch: top-level experiment boundary; re-raised after logging
# broad catch: checkpoint merge at completion; fallback to in-memory copy
# broad catch: public API boundary; provides rate-limit diagnostics before re-raising
```

## Pre-commit Line-Length Trap

**Problem**: Ruff enforces E501 (line > 100 chars). Inline comments on `except` lines are counted:

```python
# This line is 121 chars — FAILS E501:
except Exception as e:  # broad catch: checkpoint can fail due to JSON errors, IO errors, or state corruption
```

**Fix**: Keep inline comments under ~60 characters after the `#`:

```python
# This passes (95 chars total):
except Exception as e:  # broad catch: resume can fail from JSON/IO/state errors
```

**Also**: `ruff-format` will reformat multi-line `except (Exception) as e:` blocks. When the formatter wraps lines, the comment moves to a new line, which may still trigger E501. Just shorten the comment and re-commit.

## Results Summary (ProjectScylla Issue #1355)

| File | Before | Tightened | Kept (annotated) | After |
|------|--------|-----------|------------------|-------|
| `automation/implementer.py` | 18 | 9 | 9 | 9 broad |
| `e2e/llm_judge.py` | 8 | 8 | 0 | 0 broad |
| `e2e/runner.py` | 7 | 0 | 7 | 7 broad |
| **Project total** | **128** | **17** | **23** | **111** |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1355 — March 2026 quality audit (10/14) | [notes.md](../../references/notes.md) |
