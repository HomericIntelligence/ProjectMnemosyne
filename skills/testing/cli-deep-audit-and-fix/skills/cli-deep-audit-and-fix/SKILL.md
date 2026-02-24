---
name: "Skill: CLI Deep Audit and Fix"
description: "Deep-audit CLI scripts across 8 dimensions (bugs, dead code, duplication, validation placement, error messaging, exception safety, test coverage gaps, argparse resolution) then fix in dependency order with complementary tests."
category: testing
date: 2026-02-24
user-invocable: false
---

# Skill: CLI Deep Audit and Fix

## Overview

| Item | Details |
|------|---------|
| **Date** | 2026-02-24 |
| **Objective** | Audit `manage_experiment.py` (CLI entry point for e2e experiment runs) across 8 dimensions and fix all confirmed issues |
| **Outcome** | ✅ 1 real bug fixed (argparse `default=3600` silently overriding YAML timeout), 5 code-quality concerns fixed, 12 new tests added |
| **Context** | CLI had grown over multiple refactors; single-mode and batch-mode code paths had diverged; early-validation was missing before `ThreadPoolExecutor` |

## When to Use This Skill

Use this skill when:

- A CLI script has grown organically over multiple sprints and may have accumulated inconsistencies
- Multiple code paths (e.g., single-mode vs batch-mode) risk diverging in validation, error messaging, or argument handling
- You need to verify that argparse default values don't silently override configuration-layer fallbacks
- A function has grown beyond a single responsibility and benefits from extraction/decomposition
- Test coverage exists for override paths but not for fallback/default paths

**Key Indicators**:

- `argparse` has `default=<non-None>` for an option that the config layer is also supposed to set
- Validation or file-existence checks happen inside a thread-pool lambda rather than before it
- `except Exception as e` blocks re-raise without wrapping in a domain-specific exception
- Tests all set the option explicitly; no test omits the flag to exercise the fallback

## Verified Workflow

### Phase 1: Read the Existing Plan / Issue

Read the GitHub issue or audit document before touching any code. Identify:

- Which dimensions to audit (see dimensions table below)
- Which code paths are in scope (single-mode, batch-mode, shared helpers)
- Whether a plan already exists (avoid re-deriving what's already decided)

```bash
gh issue view <number> --comments
```

### Phase 2: Implement Fixes in Dependency Order

Fix issues in this order to avoid cascading breakage:

1. **Extract shared constants** — e.g., pull `MODEL_ALIASES` dict out of a function so it can be reused and tested independently
2. **Fix argparse defaults** — change `default=<value>` → `default=None` for any option that the config/YAML layer is also responsible for setting; add the fallback explicitly in the resolution function
3. **Move validation before thread pool** — any per-thread check that can be done once (path existence, alias resolution) belongs before `ThreadPoolExecutor(...)`
4. **Add path existence checks** — fail fast with a clear `FileNotFoundError` or `argparse.ArgumentTypeError` rather than letting the worker crash later
5. **Wrap exceptions** — `except Exception as e: raise SpecificError(...) from e` instead of bare re-raise or swallowing

### Phase 3: Run Existing Tests After Production Changes

**Do this before writing any new tests.**

```bash
pixi run python -m pytest tests/ -x -q 2>&1 | tail -20
```

Fix any tests broken by the production changes (e.g., tests asserting on the old default value).

### Phase 4: Write New Tests

Write tests that cover the gaps exposed by the audit:

- **Fallback tests** — omit the CLI flag entirely and assert the config-layer default is used
- **Override tests** — pass the flag explicitly and assert the override wins
- **Early-exit tests** — assert on return code (`sys.exit` captured via `pytest.raises(SystemExit)`) not on file side-effects
- **Extraction tests** — for any newly extracted constant/function, add a unit test directly

```python
# Pattern: test fallback (flag omitted)
def test_timeout_uses_yaml_default(tmp_path, monkeypatch):
    # Do NOT pass --timeout; verify config value flows through
    ...

# Pattern: test early-exit by return code
def test_missing_experiment_dir_exits(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        run_cli(["--experiment-dir", str(tmp_path / "nonexistent"), ...])
    assert exc_info.value.code != 0
```

### Phase 5: Pre-commit and Commit

```bash
pre-commit run --all-files
git add <files>
git commit -m "fix(cli): <description>"
```

## Audit Dimensions

| # | Dimension | What to Check |
|---|-----------|---------------|
| 1 | **Bugs** | Argparse defaults silently overriding config layer; off-by-one errors in range checks |
| 2 | **Dead code** | Unused imports, unreachable branches, obsolete helper functions |
| 3 | **Duplication** | Same dict/constant defined in multiple places; copy-paste validation logic |
| 4 | **Validation placement** | Checks that belong before `ThreadPoolExecutor` but are inside the thread lambda |
| 5 | **Error messaging** | Vague `Exception("something went wrong")` vs specific messages with context |
| 6 | **Exception safety** | Bare `raise` in wrong scope; swallowed exceptions; missing `from e` chaining |
| 7 | **Test coverage gaps** | Override tests exist but fallback tests are missing (or vice versa) |
| 8 | **Argparse resolution** | `default=None` + explicit fallback vs `default=<value>` competing with config layer |

## Key Fixes Applied

### Fix 1: argparse `default=None` Pattern

**Problem**: `parser.add_argument("--timeout", type=int, default=3600)` caused the argparse value
(3600) to always win over the YAML config fallback, even when the user never passed `--timeout`.

**Fix**:

```python
# Before
parser.add_argument("--timeout", type=int, default=3600)

# After
parser.add_argument("--timeout", type=int, default=None)
# ... then in resolution:
timeout = args.timeout if args.timeout is not None else config.get("timeout", 3600)
```

### Fix 2: Extract `MODEL_ALIASES` as Module-Level Constant

**Problem**: `MODEL_ALIASES` dict was defined inside `resolve_model()` — unreachable by tests and
redefined on every call.

**Fix**: Move to module level so unit tests can import and validate it directly.

### Fix 3: Move Validation Before `ThreadPoolExecutor`

**Problem**: Per-experiment path existence check lived inside the thread lambda, causing N identical
error messages if N threads all hit the same missing path.

**Fix**: Validate all paths once before submitting work to the pool.

### Fix 4: Path Existence Check

**Problem**: Missing `--config-file` caused a cryptic `FileNotFoundError` deep in the call stack.

**Fix**: Add explicit check with `argparse.ArgumentTypeError` containing the missing path.

### Fix 5: Exception Wrapping

**Problem**: `except Exception as e: raise RuntimeError("batch failed")` lost the original traceback.

**Fix**: `raise RuntimeError("batch failed") from e`

## Failed Attempts

| # | What Was Tried | Why It Failed | Correct Approach |
|---|----------------|---------------|-----------------|
| 1 | Wrote new tests before running full suite after production changes | New tests passed but 3 pre-existing tests were now broken by the changed default value — only caught at final pre-commit run | Always run `pytest -x -q` after production changes, before writing any new tests |
| 2 | Asserted on file side-effects (e.g., output file created) for early-exit test paths | Early-exit paths (`sys.exit`) never reach the file-write code; assertion always fails | Assert on `SystemExit.code` via `pytest.raises(SystemExit)` for early-exit paths; assert on file contents only for success paths |

## Results & Parameters

| Item | Value |
|------|-------|
| Files changed | 2 (production: `manage_experiment.py`; tests: `test_manage_experiment.py`) |
| New tests added | 12 |
| Bug fixed | 1 (argparse `default=3600` silently overriding YAML timeout) |
| Code-quality fixes | 5 (MODEL_ALIASES extraction, early validation, path check, exception wrapping, dead import removal) |
| Commit message prefix | `fix(cli): Deep audit fixes for manage_experiment.py` |
| Pre-commit hooks | All pass (black, ruff, mypy) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Branch `consolidate-run-command`, commit `554bfac` | [notes.md](../references/notes.md) |
