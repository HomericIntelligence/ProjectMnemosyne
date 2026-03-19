---
name: ruff-rule-set-expansion
description: Workflow for safely expanding ruff lint rule sets (B, SIM, C4, RUF) in
  an existing Python project
category: ci-cd
date: 2026-03-03
version: 1.0.0
---
# Ruff Rule Set Expansion

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-03 |
| **Objective** | Add B, SIM, C4, RUF rule sets to ruff configuration without breaking CI |
| **Outcome** | ✅ Success — 233 violations resolved, 0 remaining, all 3999 tests passing |
| **Project** | ProjectScylla |
| **PR** | #1375 |

## When to Use This Skill

Use this skill when:
- ✅ Adding new ruff rule sets (B, SIM, C4, RUF, or others) to an existing project
- ✅ You need to triage 50–500 new violations before deciding what to fix vs. ignore
- ✅ You want to apply fixes in the correct order (safe → unsafe → manual)
- ✅ You need explanatory `ignore` entries in `pyproject.toml`

Do NOT use this skill when:
- ❌ Fixing violations for already-enabled rules (see `fix-ruff-linting-errors`)
- ❌ Adding ruff to a project for the first time (greenfield setup)

## Verified Workflow

### Phase 1: Triage — Understand the Violation Landscape

```bash
# Count violations by rule BEFORE changing config
pixi run ruff check scylla/ scripts/ tests/ --select B,SIM,C4,RUF 2>&1 \
  | grep "^[A-Z][A-Z0-9]" | sort | uniq -c | sort -rn
```

**Interpret counts to decide: fix vs. ignore?**

| Volume | Approach |
|--------|----------|
| >30 violations | Consider ignoring if the rule has a legitimate exception pattern |
| Fixable (`[*]` in ruff output) | Apply auto-fix |
| Requires code restructure | Evaluate cost/benefit |

### Phase 2: Update `pyproject.toml`

Add rules to `select` and add `ignore` entries with **explanatory comments**:

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D", "UP", "S101", "B", "SIM", "C4", "RUF"]
ignore = [
    # ... existing ignores ...
    # B — flake8-bugbear
    "B017",  # Do not assert blind exception — inline comments name the actual type
    # SIM — flake8-simplify
    "SIM117",  # pytest.raises() must be the innermost context manager; cannot merge
    # RUF — ruff-specific
    "RUF001",  # Intentional Unicode (Greek letters, math notation) in strings/docstrings
    "RUF002",  # Intentional Unicode (en-dash, multiplication sign) in docstrings
    "RUF003",  # Intentional Unicode (en-dash, multiplication sign) in comments
]
```

### Phase 3: Apply Fixes in Order

```bash
# Step 1: Safe auto-fixes only
pixi run ruff check scylla/ scripts/ tests/ --fix

# Step 2: Unsafe auto-fixes (check the diff carefully)
pixi run ruff check scylla/ scripts/ tests/ --unsafe-fixes --fix

# Step 3: Check what remains
pixi run ruff check scylla/ scripts/ tests/ --output-format=concise
```

### Phase 4: Manual Fixes

Fix remaining violations by type:

#### RUF100 — Unused noqa directives

When adding `RUF` to `select`, existing `# noqa: C901` (or other non-enabled rules)
become violations. The auto-fixer removes them, but this **shortens lines that were
relying on the noqa comment for line length**.

**Pattern**: Function def line had `# noqa: C901  # descriptive comment`
- After RUF100 fix: line is still long because the descriptive comment remains
- Fix: remove the inline descriptive comment (it's redundant with the docstring)

```python
# BEFORE (was passing via noqa: C901 which also masked E501)
def my_func(arg: str) -> int:  # noqa: C901  # complex function with many branches

# AFTER RUF100 removes the noqa (line becomes E501)
def my_func(arg: str) -> int:  # complex function with many branches  # E501!

# FIX: remove the inline comment entirely
def my_func(arg: str) -> int:
```

#### SIM102 — Nested `if` merge

```python
# BEFORE
if condition_a:
    if condition_b:
        do_thing()

# AFTER
if condition_a and condition_b:
    do_thing()
```

**Watch out**: If the merged line exceeds 100 chars, extract a variable:

```python
# If merged condition is too long:
has_incomplete = self._subtest_has_incomplete_runs(tier_id_str, sub_id)
if sub_state in ("aggregated", "runs_complete") and has_incomplete:
    ...
```

#### SIM103 — Return condition directly

```python
# BEFORE
if call_count[0] == 1:
    return False
return True

# AFTER
return call_count[0] != 1
```

#### SIM105 — Replace try/except/pass with contextlib.suppress

```python
# BEFORE
try:
    runner._run_tier(TierID.T0, None, None)
except Exception:
    pass  # May fail — we just check the call

# AFTER
with contextlib.suppress(Exception):
    runner._run_tier(TierID.T0, None, None)
    # May fail — we just check the call
```

**Note**: Add `import contextlib` if not already present.

#### B023 — Loop variable not bound in closure

```python
# BEFORE — late binding bug: _pending_runs always uses last subtest_id
for subtest_id in subtest_ids:
    def _pending_runs() -> None:
        use(subtest_id)  # captures by reference!

# AFTER — bind at definition time via default arg
for subtest_id in subtest_ids:
    def _pending_runs(_sid: str = subtest_id) -> None:
        use(_sid)
```

#### RUF012 — Mutable class attribute needs ClassVar

```python
# BEFORE
class MyTest:
    _PATCHES = [("path", "value")]  # RUF012

# AFTER
from typing import ClassVar

class MyTest:
    _PATCHES: ClassVar[list[tuple[str, Any]]] = [("path", "value")]
```

### Phase 5: Verify

```bash
# Should show "All checks passed!"
pixi run ruff check scylla/ scripts/ tests/

# Run full pre-commit
SKIP=audit-doc-policy pre-commit run --all-files

# Run tests
pixi run python -m pytest tests/unit/ -x -q
```

## Rule Set Reference

### What to Ignore vs. Fix

| Rule | Default Decision | Rationale |
|------|-----------------|-----------|
| **SIM117** | **IGNORE** | `pytest.raises()` must be innermost context manager — merging breaks pytest |
| **B017** | **IGNORE** if comments name type | `pytest.raises(Exception)` acceptable when comment identifies expected type |
| **RUF001/002/003** | **IGNORE** if intentional Unicode | Greek letters (α, ρ, σ), math symbols (×, –) in scientific code |
| **B023** | **FIX** | Real late-binding closure bug — can cause test failures |
| **RUF100** | **FIX** | Unused noqa for non-enabled rules (C901, BLE001, N817, etc.) |
| **SIM105** | **FIX** (auto) | `try/except/pass` → `contextlib.suppress()` |
| **SIM102** | **FIX** (auto) | Nested `if` merge |
| **C4xx** | **FIX** (auto) | Comprehension simplifications |
| **RUF022** | **FIX** (auto) | Unsorted `__all__` |
| **RUF059** | **FIX** (auto) | Unused unpacked variables → prefix with `_` |

### Violation Count Expectations (ProjectScylla baseline)

After adding B, SIM, C4, RUF to a mature Python codebase (~18K lines):

| Rule | Count | Action |
|------|-------|--------|
| SIM117 | 59 | Ignored |
| RUF100 | 51 | Auto-fixed |
| RUF001/002/003 | 27 | Ignored |
| RUF059 | 12 | Auto-fixed |
| SIM105 | 5 | Auto-fixed |
| B017 | 3 | Ignored |
| SIM102/103 | 5 | Manual fix |
| C4xx | 6 | Auto-fixed |
| B023 | 1 | Manual fix |
| RUF012 | 1 | Manual fix |
| **Total** | **233** | **0 remaining** |

## Failed Attempts

### Attempting to fix SIM117 in pytest tests

SIM117 suggests merging nested `with` statements. For pytest, this breaks because
`pytest.raises()` **must** be the innermost context manager. Attempting to merge:

```python
# BROKEN — pytest.raises() must be innermost
with mock.patch("sys.argv", [...]), pytest.raises(SystemExit) as exc_info:
    main()
# exc_info.value.code would fail — raises() needs to be innermost
```

**Resolution**: Add `"SIM117"` to the global `ignore` list in `pyproject.toml`.

### Using `--unsafe-fixes` without reviewing changes

The unsafe fixes include SIM105 (`try/except/pass` → `contextlib.suppress`) which
sometimes applies in ways that lose important contextual comments. Always review
the diff after `--unsafe-fixes --fix`.

### Trying to keep `# noqa: C901` after RUF100 cleanup

When RUF100 removes `# noqa: C901` directives (because C901 is not enabled), those
same lines may become E501 violations if the `# noqa: C901  # description` was long.
You cannot keep the noqa directive (RUF100 will re-flag it next run).
**Correct fix**: Remove the entire inline comment; the information belongs in the docstring.

## Key Configuration

```toml
# pyproject.toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D", "UP", "S101", "B", "SIM", "C4", "RUF"]
ignore = [
    # ... existing rules ...
    "B017",    # Blind exception — inline comments name the actual type
    "SIM117",  # pytest.raises() must be innermost context manager
    "RUF001",  # Intentional Unicode in strings
    "RUF002",  # Intentional Unicode in docstrings
    "RUF003",  # Intentional Unicode in comments
]
```
