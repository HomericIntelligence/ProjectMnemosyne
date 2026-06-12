---
name: mypy-shutil-which-optional-narrowing
description: "mypy cannot narrow Optional through pytest.skip(), so shutil.which() results stay str|None and fail list-item/arg type checks. Use when: (1) a [list-item] or [arg-type] mypy error appears after a pytest.skip() guard, (2) passing a shutil.which() / os.environ.get() result into subprocess.run() or a path API, (3) the lint and pre-commit CI checks both fail on one identical mypy error."
category: ci-cd
date: 2026-06-11
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# mypy Cannot Narrow Optional Through pytest.skip()

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-11 |
| **Category** | ci-cd |
| **Objective** | Fix a `[list-item]` / `[arg-type]` mypy error where a `shutil.which()` result remains `str | None` after a `pytest.skip()` guard, failing both the `lint` and `pre-commit` required CI checks |
| **Outcome** | Added a single `assert binary is not None` after the skip guard to narrow `Optional[str]` → `str`; mypy clean (314 source files), all pre-commit hooks pass, full suite green (3516 passed, 18 skipped, 84.93% coverage) |
| **Verification** | verified-local — confirmed via `pixi run --environment lint mypy`, `pre-commit run --all-files`, and the full pytest suite locally |
| **Toolchain** | mypy, pytest, pre-commit, pixi |

## When to Use

- A `[list-item]` or `[arg-type]` mypy error appears **after** a `pytest.skip()` guard that you expected to narrow an `Optional`.
- You pass a `shutil.which()`, `os.environ.get()`, or `dict.get()` result (all `str | None` / `T | None`) into `subprocess.run([...])`, a path API, or any function expecting a non-Optional type.
- ONE identical mypy error fails **both** the `lint` and `pre-commit` required CI checks — they share the same mypy invocation, so fix it once.
- The repo enforces a `forbid-suppressions` gate, so `# type: ignore[...]` is not an acceptable fix.

## Verified Workflow

> **Verification level:** verified-local — the fix was confirmed locally via `pixi run --environment lint mypy`, `pre-commit run --all-files`, and the full pytest suite. A remote CI re-run was not observed within the session.

### Root cause

`shutil.which("hephaestus-automation-loop")` returns `str | None`. A test guards the
absent case with `pytest.skip(...)` and then uses the value in an argv list:

```python
binary = shutil.which("hephaestus-automation-loop")
if binary is None:
    pytest.skip("hephaestus-automation-loop not on PATH")

result = subprocess.run([binary, "--max-workers", "0"], ...)  # mypy: binary is still str | None
```

mypy does **not** know `pytest.skip()` is `NoReturn`. Even though `pytest.skip` raises
`Skipped` at runtime, mypy's plugin does not annotate it as `NoReturn` by default, so the
`if binary is None:` branch is **not** treated as terminating. `binary` therefore remains
`str | None` when placed in the list, producing:

```text
tests/integration/test_cli_entry_points.py:158: error: List item 0 has incompatible type "str | None"; expected "str | bytes | PathLike[str] | PathLike[bytes]"  [list-item]
```

Because `lint` and `pre-commit` both run the same mypy, the **single** error fails both
required checks.

### The fix (one line, no rule disabled)

Add an explicit `assert` immediately after the `pytest.skip()` guard so mypy can narrow
`Optional[str]` → `str`:

```python
binary = shutil.which("hephaestus-automation-loop")
if binary is None:
    pytest.skip("hephaestus-automation-loop not on PATH")
assert binary is not None  # narrow Optional[str] for mypy

result = subprocess.run([binary, "--max-workers", "0"], ...)
```

### Quick Reference

```python
# Pattern: any Optional-returning lookup used after an early-exit guard mypy can't see through.
x = shutil.which("tool")          # str | None
# (also applies to os.environ.get(...), dict.get(...), re.match(...), etc.)
if x is None:
    pytest.skip("tool not on PATH")   # mypy does NOT treat skip() as NoReturn
assert x is not None                  # <-- minimal, intent-revealing narrowing
subprocess.run([x, "..."], ...)       # now x is str
```

```bash
# One mypy error fails BOTH required checks — fix once, verify with the shared invocation:
pixi run --environment lint mypy      # -> Success: no issues found in 314 source files
pre-commit run --all-files            # -> Mypy Type Check Python ... Passed
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Relied on the `if binary is None: pytest.skip(...)` guard alone to narrow `binary` to `str` | mypy does not treat `pytest.skip()` as `NoReturn`, so it never narrows the post-guard type — `binary` stays `str | None` | A runtime-raising helper is not a type-checker `NoReturn` unless declared as such; mypy needs an explicit narrowing statement |
| 2 | Adding `# type: ignore[list-item]` at the call site | The repo's `forbid-suppressions` gate rejects inline ignores, and it hides the genuine `Optional` rather than resolving it | Suppression masks the real defect and is blocked by policy; narrow the type instead of silencing the checker |
| 3 | Fixed only the `lint` check and assumed `pre-commit` was a separate, still-failing problem | Both checks run the **same** mypy invocation over the same single error; the one fix cleared both simultaneously | When one identical mypy error fails both `lint` and `pre-commit`, treat it as one fix, not two |
| 4 | Considered `raise pytest.skip.Exception(...)` or `assert binary, "..."` as the narrowing form | Both type-check correctly, but are heavier / less explicit than the intent of "this is not None here" | A plain `assert binary is not None` is the minimal, intent-revealing narrowing; prefer it over restructuring |

## Results & Parameters

### Exact error and fix

```text
# Before (fails lint AND pre-commit on one error):
tests/integration/test_cli_entry_points.py:158: error: List item 0 has incompatible type "str | None"; expected "str | bytes | PathLike[str] | PathLike[bytes]"  [list-item]
```

```python
# After — add one line after the skip guard, before subprocess.run:
assert binary is not None  # narrow Optional[str] for mypy
```

### Verification commands and outputs

| Command | Result |
|---------|--------|
| `pixi run --environment lint mypy` | `Success: no issues found in 314 source files` |
| `pre-commit run --all-files` | All hooks `Passed` (incl. `Mypy Type Check Python`) |
| `pixi run pytest tests` | 3516 passed, 18 skipped, coverage 84.93% |

### Context

- ProjectHephaestus PR #1016 (issue #723); file `tests/integration/test_cli_entry_points.py:158`.
- The Optional source was `binary = shutil.which("hephaestus-automation-loop")`.

### Generalizable lesson

- For any `shutil.which` / `os.environ.get` / `dict.get` result consumed after an
  early-exit guard mypy cannot see through (`pytest.skip`, custom `fail()` helpers,
  `sys.exit` wrappers), add an explicit `assert x is not None` to narrow it.
- When ONE mypy error fails both `lint` and `pre-commit`, they share the same mypy
  invocation — fix it once and re-run that shared invocation to confirm both clear.
