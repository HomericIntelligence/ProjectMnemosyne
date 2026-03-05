# Session Notes: Tighten `except Exception` Clauses

**Date**: 2026-03-03
**Issue**: ProjectScylla #1355
**PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/1374

## Raw Counts

- Initial: 128 `except Exception` clauses across 42 files
- Worst offenders: `implementer.py` (18), `llm_judge.py` (8), `runner.py` (7)
- After: 111 broad catches (17 tightened)

## Categorization Detail

### implementer.py (18 → 9 broad)

| Line | Action | Reason |
|------|--------|--------|
| 116 | Tighten → `CyclicDependencyError` | `detect_cycles()` only raises this |
| 176 | Keep | network + API + JSON all possible |
| 194,201,208,218 | Tighten → `(CalledProcessError, FileNotFoundError, OSError)` | health check `run()` calls |
| 249 | Tighten → `CyclicDependencyError` | `topological_sort()` only raises this |
| 288 | Keep | thread pool wait() can raise various internal errors |
| 312 | Keep | `future.result()` re-raises worker exceptions |
| 522 | Keep | top-level worker boundary |
| 563 | Tighten → `(SubprocessError, json.JSONDecodeError, OSError)` | `_has_plan` gh CLI + JSON |
| 708,720 | Keep | GitHub API boundary |
| 727 | Keep | follow-up top-level, non-blocking |
| 761 | Tighten → `OSError` | `log_file.read_text()` only |
| 872 | Keep | external claude process, non-blocking |
| 1130 | Keep | gh CLI + JSON; fallback is to create PR |
| 1187 | Tighten → `(json.JSONDecodeError, ValueError, OSError)` | state file load |

### llm_judge.py (8 → 0 broad)

| Line | Action | Reason |
|------|--------|--------|
| 430 | Tighten → `(OSError, SubprocessError)` | subprocess execution |
| 432 | Tighten → `OSError` | Python script finding (glob/file ops) |
| 644 | Tighten → `(SubprocessError, OSError)` | git status |
| 712 | Tighten → `(SubprocessError, OSError)` | git diff |
| 742 | Tighten → `(SubprocessError, OSError)` | git deleted files |
| 761 | Tighten → `OSError` | reference patch read |
| 835 | Tighten → `OSError` | rubric read |
| 1351 | Tighten → `OSError` | MODEL.md write |

### runner.py (7 → 7 broad, all annotated)

All 7 are genuine system boundaries:
- L365: checkpoint resume failure (JSON/IO/state errors all possible)
- L455: experiment baseline (non-critical; build/git/IO all fail)
- L460: worktree cleanup (cleanup must not raise)
- L487: interrupt handler (must not mask interrupt)
- L787: top-level `run()` boundary (re-raises after logging)
- L1166: checkpoint merge at completion (fallback pattern)
- L1193: `run_experiment()` public API boundary (rate-limit diagnostics)

## Pre-commit Gotchas

1. First commit attempt always fails because `ruff-format` modifies files
2. Long inline comments (> ~60 chars) trigger E501
3. `ruff-format` wraps `except (Exception) as e:  # long comment` to next line,
   which can still fail E501 if comment is too long
4. Fix: shorten comments + re-add + re-commit (2-3 rounds typical)

## Key Import Added

```python
from .dependency_resolver import CyclicDependencyError, DependencyResolver
```

`CyclicDependencyError` is a custom exception defined in `dependency_resolver.py` that
`detect_cycles()` and `topological_sort()` raise. Was being caught as broad `Exception`.
