---
name: python-type-hints-and-mypy-patterns
description: "Canonical guide to Python type annotation and mypy compliance patterns. Use when: (1) mypy with implicit_reexport=false or disallow_untyped_defs raises errors after a module refactor, (2) annotating hundreds of unannotated test functions in tests/unit/ to satisfy mypy strict mode, (3) AI-generated type annotations are placed at call sites instead of function definitions causing CI failures, (4) a manager/proxy class needs correct Callable or TypeVar generics to preserve return types without ParamSpec violations, (5) adding PEP 561 py.typed marker to make a typed package discoverable by mypy/pyright, (6) Pydantic model field types diverge from function signatures causing implicit-reexport or attribute-export errors."
category: tooling
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: python-type-hints-and-mypy-patterns.history
tags:
  - python
  - mypy
  - type-hints
  - type-annotations
  - typing
  - callable
  - typevar
  - paramspec
  - pep-612
  - pep-561
  - py.typed
  - implicit_reexport
  - disallow_untyped_defs
  - pydantic
  - manager-proxy
  - bulk-annotation
  - ci-fix
---

# Python Type Hints and mypy Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Category** | tooling |
| **Objective** | Canonical reference for Python type annotation and mypy strict-mode compliance: bulk annotation, call-site error fixes, generic return preservation, manager-proxy hints, PEP 561 markers, and Pydantic/API alignment |
| **Outcome** | Consolidated from 6 skills covering bulk test annotation, call-site fixes, Callable/TypeVar generics, manager-proxy hints, py.typed packaging, and type-system/API alignment |
| **Verification** | verified-ci |
| **Toolchain** | mypy, ruff, Pydantic v2, hatchling, pixi |

## When to Use

- mypy with `disallow_untyped_defs` flags hundreds of unannotated test functions and you need to remove a `[[tool.mypy.overrides]]` suppress block
- AI-generated code placed type annotations at function **call sites** instead of definitions, causing `SyntaxError` during pytest collection or ruff `F821`
- A wrapper function must preserve the return type of a wrapped callable but interleaves keyword-only params between `*args`/`**kwargs` (ParamSpec/PEP 612 violation)
- A method returns a `multiprocessing.Manager()` proxy object (Semaphore/Queue) that cannot be annotated precisely
- A typed package needs a PEP 561 `py.typed` marker so mypy/pyright recognize it
- mypy with `implicit_reexport = false` raises "does not explicitly export attribute X" after a refactor
- Pydantic model field types diverge from function signatures, or `@dataclass` classes need migrating to `BaseModel`

## Verified Workflow

### Quick Reference

```python
# 1. Bulk-annotate test functions (mypy disallow_untyped_defs)
def test_something(self, my_fixture: Any, tmp_path: Any) -> None: ...
def my_fixture() -> Generator[Any, None, None]:  # yield-based fixture
    yield create_thing()

# 2. Call-site annotation is invalid Python — strip it
tier_order = derive_tier_order(sample_runs_df)   # NOT (sample_runs_df: pd.DataFrame)

# 3. Preserve generic return type (ParamSpec-incompatible wrapper)
R = TypeVar("R")
def retry_call(func: Callable[..., R], *args: Any, max_retries: int = 3, **kwargs: Any) -> R:
    return func(*args, **kwargs)   # type: R

# 4. Manager proxy return type — Any is the pragmatic, deliberate choice
def _setup_semaphore(self) -> Any:   # returns multiprocessing.Manager().Semaphore()
    ...

# 5. mypy explicit re-export (implicit_reexport = false)
from package.new_location import MySymbol as MySymbol  # noqa: PLC0414

# 6. Pydantic field_validator normalization chokepoint
@field_validator("models", mode="before")
@classmethod
def _normalize_models(cls, v: list[str]) -> list[str]:
    return [normalize_model_id(m) for m in v]
```

```bash
# PEP 561 py.typed marker (hatchling)
touch scylla/py.typed
# pyproject.toml -> [tool.hatch.build.targets.wheel.force-include]
#   "scylla/py.typed" = "scylla/py.typed"
pixi install   # refresh lock hash
```

```toml
# pyproject.toml — flags that trigger these patterns
[tool.mypy]
implicit_reexport = false
disallow_untyped_defs = true
```

### Detailed Steps

#### 1. Bulk-annotate hundreds of test functions (disallow_untyped_defs)

Remove the override **before** running mypy so you see the real error count. Annotate in phases:

```python
# Phase 1: AST/regex-guided -> None on test functions
func_match = re.match(
    r'^( *)(def (?:test_\w+|setUp|tearDown|setup_method|teardown_method|'
    r'setup_class|teardown_class|setUpClass|tearDownClass)\s*\(.*\))(\s*):$',
    stripped,
)
if func_match and '->' not in func_match.group(2):
    new_line = f"{func_match.group(1)}{func_match.group(2)} -> None:\n"
```

Then check actual errors (don't guess) and fix the three cascade categories:

1. `[no-untyped-def]` — add `: Any` to fixture params and inner helpers (use `Any`, **not** `object` — `object` causes cascade errors).
2. `[return-value]` / `[func-returns-value]` — inner helpers/fixtures wrongly given `-> None` that actually return values: change to `-> Any`.
3. Generator fixtures (`yield`-based) need `-> Generator[Any, None, None]`.

**Import ordering is critical**: add `from typing import Any` *after* the module docstring and *after* any `from __future__ import annotations`. Wrong order causes E402 or `name-defined`. Then `ruff check <test-dir>/ --fix` and finally delete the override block.

```bash
<package-manager> run mypy <test-dir>/   # expect: Success: no issues found
```

#### 2. Fix AI-generated call-site annotations

Type annotations at function **call sites** are invalid Python (the #1 error in bulk refactors):

```python
# WRONG (call site — SyntaxError)
tier_order = derive_tier_order(sample_runs_df: pd.DataFrame)
# CORRECT
tier_order = derive_tier_order(sample_runs_df)
```

Related cascade fixes:
- **Misplaced imports**: AI moves module-level imports inside function bodies at col 0 — move them back to module level.
- **F821 undefined name**: a type used in annotations (e.g. `pd`) must be importable at module level — add `import pandas as pd`.
- **Fixtures**: `-> None` wrongly applied to value-returning fixtures → `-> Any`.
- **Mock patch paths**: bulk replace can retarget `patch()` to wrong modules. Always diff against `origin/main`:
  ```bash
  diff <(git show origin/main:tests/file.py | grep 'patch(') <(grep 'patch(' tests/file.py)
  ```
- **Stale API tests**: `grep -r "_old_api" src/` — empty means API gone; remove the test.

Always `ast.parse()` every modified file after automated edits.

#### 3. Preserve generic return type with Callable[..., R]

When a wrapper adds its own keyword-only parameters between `*args` and `**kwargs`, ParamSpec is illegal (PEP 612 requires `P.args`/`P.kwargs` to be consecutive). Use `Callable[..., R] + TypeVar`:

```python
from collections.abc import Callable   # prefer over typing.Callable
from typing import Any, TypeVar

R = TypeVar("R")

def resilient_call(
    func: Callable[..., R],
    *args: Any,
    max_retries: int = 3,   # interleaved wrapper param — fine here, illegal under ParamSpec
    backoff_factor: float = 2.0,
    **kwargs: Any,
) -> R:
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)   # type: R, preserved transparently
        except Exception:
            if attempt == max_retries - 1:
                raise
```

`Callable[..., R]` accepts any callable and preserves the return type `R`, so call sites keep precise types (`result["key"]` is checked) with **zero `# type: ignore`**. One `R` per module suffices — each call rebinds it. If mypy still complains, the error is real, not masked.

#### 4. Manager / proxy return types — explicit Any

`multiprocessing.Manager().Semaphore()` / `.Queue()` return runtime proxy wrappers whose types are not annotatable (`SyncManager.Semaphore` isn't a usable annotation; the raw `multiprocessing.synchronize.Semaphore` is the wrong type). Use `-> Any` with a docstring explaining *why*:

```python
def _setup_workspace_and_semaphore(self) -> Any:
    """Set up workspace manager and global semaphore for parallel execution.

    Returns:
        Manager-created Semaphore for limiting concurrent agents across
        all tiers. Type annotation is Any due to complexity of Manager
        proxy types (returns multiprocessing.Manager().Semaphore()).
    """
```

This converts an *implicit* `Any` (no annotation) into an *explicit, documented* `Any` — a deliberate architectural choice, not laziness. Prefer this over Protocols/SyncManager gymnastics (KISS). Verify:

```bash
pre-commit run mypy --all-files
python -c "import inspect; from pkg.mod import Cls; print(inspect.signature(Cls._setup_workspace_and_semaphore).return_annotation)"  # -> Any
```

#### 5. PEP 561 py.typed marker (hatchling)

Hatchling's `packages = ["scylla"]` includes only `.py` files; non-Python markers need `force-include`:

```toml
[tool.hatch.build.targets.wheel.force-include]
"scylla/py.typed" = "scylla/py.typed"
```

1. `touch <package>/py.typed` (must be empty per PEP 561).
2. Add the `force-include` entry above.
3. `pixi install` to refresh the SHA256 in the lock file.
4. Add regression tests (marker exists + present in `force-include`).
5. `pre-commit run --all-files` — mypy must still pass.

Verify the marker ships: `pip show -f scylla | grep py.typed`.

#### 6. mypy explicit re-export (implicit_reexport = false)

```python
# WRONG: from pkg.module import X        -> "does not explicitly export attribute X"
# RIGHT: from pkg.module import X as X   # noqa: PLC0414  — PEP 484 opt-in signal
```

Runtime behavior is identical (same binding in the module `__dict__`, so `mock.patch("a.b.X")` still works); only static analysis differs. `__all__` and explicit re-export are independent — you may need both.

#### 7. Pydantic / API alignment

- **field_validator normalization chokepoint** (legacy IDs in saved configs): put `normalize_model_id()` in a zero-import constants module + one `@field_validator(..., mode="before")`; don't scatter across call sites.
- **Base-class hierarchy**: when a domain model inherits `BaseModel` directly but siblings have `*Base` classes, extract a shared `*Base`. Pydantic config is **not** additive — a subtype with its own `model_config` must explicitly repeat `frozen=True`.
- **`@dataclass` → `BaseModel` migration**: `field(default_factory=...)` → `Field(default_factory=...)`; `__post_init__` → `@model_validator`; Pydantic v2 has no `.dict()`/`.to_dict()` — use `.model_dump()` (and `model_dump(mode="json")` for `Path`/`Enum`).
- **Redundant bool return**: a function that returns `True` on success and raises on failure should be `-> None` (POLA).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| ParamSpec with interleaved params | `def retry(func: Callable[P, R], *args: P.args, max_retries: int, **kwargs: P.kwargs) -> R:` | PEP 612 forbids parameters between `P.args` and `P.kwargs` | ParamSpec is for transparent forwarding only; when you add wrapper-specific params, use `Callable[..., R] + TypeVar` |
| `object`-typed signature for wrappers | `def retry(func: object, *args: object, **kwargs: object) -> object:` | Erases all type info; every call site needs `# type: ignore` | Even broad `Callable[..., R]` preserves return-type semantics; never erase to `object` |
| Add `: Any` via simple regex on multi-line signatures | Regex inserted `: Any` across multi-line `def`s and into multi-line imports | Corrupted signatures; inserted `from typing import Any` inside import statements | Use AST-based tools or fix manually; `ast.parse()` every file after automated edits |
| Use `object` instead of `Any` for untyped test params | Annotated fixture params `: object` | Caused a cascade of secondary mypy errors | Use `Any` for permissive test/fixture params; `object` is too strict |
| `-> None` on value-returning fixtures/helpers | Bulk-applied `-> None` to all functions | `[return-value]`/`[func-returns-value]` errors on functions that return values | Inner helpers and fixtures returning values need `-> Any` (or precise type) |
| `from typing import Any` placed wrong | Import landed before `from __future__` or inside the docstring | E402 / `name-defined` errors | Place typing imports after the docstring and after `from __future__ import annotations` |
| `replace_all` for mock patch paths | Edit with `replace_all=true` to retarget `patch()` calls | Changed correct occurrences in other test classes too | Each test class patches a different module; never `replace_all`; diff against `origin/main` |
| Plain import for re-export | `from pkg import X` (no `as`) under `implicit_reexport=false` | mypy: "does not explicitly export attribute X" | `from X import Y as Y` is the canonical opt-in re-export signal |
| `__all__` as re-export workaround | Added symbol to `__all__` without `as` import | `__all__` controls `import *`; mypy still needs the `as Y` form | They're independent — both may be needed |
| `SyncManager.Semaphore` / `multiprocessing.synchronize.Semaphore` for proxy type | Tried to annotate Manager proxy precisely | Not a resolvable annotation / wrong type (raw class vs proxy wrapper) | Manager proxies are runtime factories; use explicit, documented `-> Any` |
| Assumed mutation sites blocked `frozen=True` | Grepped `.field =` and assumed they blocked freezing | Mutations were on different dataclasses/models with same field names | Verify the *type* of the mutated object before ruling out `frozen=True` |
| Renaming model-ID constants without normalization | Updated constants + YAML to new naming | Old IDs baked into saved `experiment.json` survived | Add normalization at the deserialization boundary, not just at the constants |

## Results & Parameters

### Error categories from a real bulk refactor (ProjectScylla #1517)

| Error Category | Count | Fix |
| ---------------- | ------- | ----- |
| Call-site type annotations (SyntaxError) | 93 | Remove `: Type` from function calls |
| F821 undefined name (ruff) | 50 | Add module-level `import pandas as pd` |
| `[no-untyped-def]` (mypy) | 220 | Add `: Any` to unannotated params |
| `[return-value]`/`[func-returns-value]` | 37 | `-> None` → `-> Any` on fixtures |
| Wrong mock patch paths | 13 | Restore original module paths |
| Black/format (E501) | 26 | Run `ruff format` |

### Bulk annotation scale (ProjectScylla #1453)

- 62 test files; ~590 `-> None` + ~725 `: Any` annotations; 489 cascade errors resolved; 4455 tests still pass; override block deleted entirely.

### Copy-paste annotation patterns

```python
def test_with_fixture(self, my_fixture: Any, tmp_path: Any) -> None: ...
def mock_reset(checkpoint: Any, **kwargs: Any) -> Any:   # inner helper returns a value
    return 1
def my_fixture() -> Generator[Any, None, None]:           # yield-based fixture
    yield create_thing()
```

### PEP 561 regression test pattern

```python
def test_py_typed_marker_exists() -> None:
    assert (REPO_ROOT / "scylla" / "py.typed").is_file()

def test_py_typed_in_hatch_build_targets() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    fi = data["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert "scylla/py.typed" in fi
```

### Verification commands

```bash
# Syntax-check all modified files after automated edits
python3 -c "import ast,subprocess,os; \
[ast.parse(open(f).read()) for f in subprocess.run(['git','diff','--name-only','origin/main'],capture_output=True,text=True).stdout.split() if f.endswith('.py') and os.path.exists(f)]"

<package-manager> run mypy <path>/         # expect: Success: no issues found
<package-manager> run ruff check <path>/ --fix
pre-commit run --all-files
<package-manager> run python -m pytest tests/unit/ -q --no-cov
```

### Key rules

1. Use `Any` (not `object`) for permissive test/fixture params.
2. `Callable[..., R] + TypeVar` preserves return types when ParamSpec is illegal.
3. Manager-proxy returns get explicit, documented `-> Any`.
4. `from X import Y as Y` is the canonical mypy re-export signal; identical at runtime.
5. Place typing imports after the docstring and after `from __future__ import annotations`.
6. Always diff mock `patch()` paths against `origin/main`; never `replace_all`.
7. PEP 561 marker needs hatchling `force-include` (not just `packages`).

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PR #1453, issue #1379 — ~635 unannotated functions in tests/unit/ | bulk -> None + : Any; override removed; 4455 tests pass |
| ProjectScylla | PR #1517, issue #1379 — bulk type-annotation refactor | Fixed 400+ errors across 28 test files |
| ProjectScylla | PR #708, issue #641 — Manager proxy return type | `-> Any` on `_setup_workspace_and_semaphore`; mypy + tests pass |
| ProjectScylla | Issue #1530, PR #1559 — PEP 561 py.typed marker | pre-commit verified |
| ProjectScylla | Issues #679/#729/#799/#796/#1355, PR #1541 — type-alias/base-class/frozen/except/normalization | up to 4800 tests pass |
| ProjectHephaestus | Issue #757, PR #956 — Callable[..., R] + TypeVar | Replaced `object` signature; 124 tests pass in CI |
| ProjectHephaestus | PRs #308/#74/#88 — explicit re-export, bool→None, audit | mypy clean, all tests pass |
