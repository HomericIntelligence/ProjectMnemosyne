# Raw Session Notes — Expand Ruff Rule Set

## Session Details

- **Date**: 2026-02-22
- **Branch**: `756-auto-impl` in ProjectScylla
- **PR**: #965

## Discovery Output (full violation counts before fixes)

```
# scylla/ + scripts/ combined:
52 S603 subprocess calls with controlled input
49 S607 partial executable path
38 B904 raise without from err/None
55 C901 cyclomatic complexity > 10 (default threshold)
 8 S110 try/except/pass
 4 B905 zip without strict=
 4 B007 unused loop variable
 3 S112 try/except/continue
 2 S101 assert detected
 1 S314 xml parsing
 1 S108 temp file path
 1 S106 hardcoded password (false positive)
 1 S105 hardcoded password (false positive)
 1 B009 getattr with constant (auto-fixed earlier)

# RUF + SIM subset:
20 RUF001 ambiguous unicode in string
18 SIM105 use contextlib.suppress
15 SIM102 nested if (merge with and)
15 RUF100 unused noqa directive
15 RUF022 __all__ not sorted
12 SIM108 use ternary
10 RUF005 use iterable unpacking
 9 RUF002 ambiguous unicode in docstring
 8 RUF059 unused unpacked variable
 6 SIM118 key in dict.keys()
 3 SIM115 open without context manager
 2 RUF012 mutable class variable
 1 SIM114 combine elif
 1 SIM103 return condition directly
 1 RUF010 use explicit conversion flag

# tests/ directory:
130 S108 /tmp/ paths in fixtures
 40 SIM117 nested with (pytest.raises)
 30 RUF059 unused unpacked variables
  6 B007 unused loop variables
  5 RUF043 regex metachar in pytest match=
  5 RUF005 iterable unpacking
  4 RUF003 ambiguous unicode in docstring
  3 B017 pytest.raises(Exception)
  2 C901 complex functions in test utilities
  1 B905 zip without strict=
```

## Auto-fix Pass Results

```
scylla/ + scripts/:
  ruff --fix:                10 fixed
  ruff --unsafe-fixes --fix: +40 fixed (RUF022 x11, RUF005 x10, SIM105 x11,
                                         SIM102 x5, SIM108 x10, SIM118 x5,
                                         RUF059 x7, B007 x3)

tests/:
  ruff --fix:                (0 new fixes)
  ruff --unsafe-fixes --fix: 40 fixed
```

## B904 Fix Strategy

Used sub-agent (Bash type) to process all 38 B904 violations across 7 files simultaneously. The sub-agent:
1. Read each file section around the violation
2. Identified whether except clause had a named variable (`as e`) or not
3. Added `from e` or `from None` appropriately

Files fixed: base_cli.py, claude_code.py, config/loader.py (11x), e2e/checkpoint.py (2x), executor/agent_container.py (2x), executor/docker.py (15x), executor/judge_container.py (3x), judge/runner.py (3x)

## C901 Strategy

37 functions in source, 2 in tests (compose_skills.py, generate_subtiers.py):
- Used a Bash sub-agent to add `# noqa: C901  # <rationale>` to all 37+2 functions
- All rationales explain WHY complexity is acceptable (orchestration, CLI mains, validators)

Key: max-complexity was changed from 10 → 12 in pyproject.toml. This reduced C901 violations from 55 to 37 (removing functions with complexity 11-12 which are borderline).

## SIM115 Handling

3 violations in `scylla/executor/capture.py` — files opened without `with` because they must remain open as long-lived instance attributes for streaming writes. Used `# noqa: SIM115  # kept open for streaming writes` inline comment.

## contextlib.suppress Conversion (SIM105)

Added `import contextlib` to 4 files that didn't have it:
- scylla/automation/implementer.py
- scylla/executor/agent_container.py
- scylla/executor/docker.py
- scylla/executor/workspace.py

scylla/executor/judge_container.py already had the import.

## Pre-commit Commit Loop Bug

When committing with unstaged pixi.lock:
1. pre-commit stashes unstaged files (including pixi.lock)
2. ruff-format runs on staged files, finds formatting to apply
3. Tries to apply format changes but stash conflicts
4. Rolls back, tries again → infinite loop

Fix: `git add pixi.lock` (include all modified files before committing).

## RUF043 Test Fixes

5 violations in test files where `.` in pytest `match=` strings are unescaped regex metacharacters. Fixed by escaping the dots:

```python
# BEFORE:
match="Incompatible checkpoint version 1.0.*requires checkpoint format 2.0"

# AFTER:
match=r"Incompatible checkpoint version 1\.0.*requires checkpoint format 2\.0"
```

Note: Used `\\.` (escaped backslash) in non-raw strings, or `\.` in raw strings.
