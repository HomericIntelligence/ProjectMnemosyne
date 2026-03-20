---

---

name: "Skill: Dockerfile/pyproject.toml Version Guard Tests"
description: "Pattern for extending Dockerfile pin regression tests to cross-validate against pyproject.toml constraints, preventing silent version drift"
category: testing
date: 2026-03-02
user-invocable: false
---
# Skill: Dockerfile/pyproject.toml Version Guard Tests

## Overview

| Item | Details |
|------|---------|
| **Date** | 2026-03-02 |
| **Objective** | Extend Dockerfile pin regression tests to assert the pinned version satisfies the `pyproject.toml` `[build-system].requires` constraint |
| **Context** | Issue #1208 — follow-up from #1141; `test_dockerfile.py` only checked `==` was present, not that the version was in range |
| **Outcome** | ✅ 2 new tests added, all 5 tests pass, pre-commit clean |
| **PR** | #1308 |

## When to Use This Skill

Use this pattern when:

1. **Dockerfile pins a package also declared in `pyproject.toml`** — e.g. `hatchling`, `pip`, `setuptools`
2. **You want a regression guard against silent drift** — i.e. Dockerfile is updated but `pyproject.toml` constraint is not (or vice versa)
3. **Existing test only checks `==` presence** — a stronger guard parses the actual version and validates the range
4. **Multiple files must agree on a version** — any two source-of-truth files (Dockerfile, `pyproject.toml`, `pixi.toml`) declaring the same package

**Trigger phrases:**
- "assert pinned version matches pyproject.toml"
- "prevent Dockerfile from drifting out of sync with pyproject.toml"
- "cross-validate version between Dockerfile and build config"

## Verified Workflow

### Step 1: Identify the version constraint in `pyproject.toml`

```toml
# pyproject.toml
[build-system]
requires = ["hatchling>=1.27.0,<2"]
build-backend = "hatchling.build"
```

The specifier string is `hatchling>=1.27.0,<2`. Extract it programmatically.

### Step 2: Add tomllib import with Python 3.10 backport

```python
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib   # no type: ignore needed — mypy resolves correctly

PYPROJECT_TOML = Path(__file__).parents[3] / "pyproject.toml"
```

**Note:** Do NOT add `# type: ignore[no-redef]` — mypy on Python ≥3.11 flags it as
`unused-ignore`. The bare `import tomli as tomllib` in the else-branch is sufficient;
mypy only type-checks the branch it can reach.

### Step 3: Add helper functions (stdlib-only, no new deps)

```python
def _parse_hatchling_specifier(requires: list[str]) -> str | None:
    """Return the hatchling specifier string from build-system.requires, or None."""
    for req in requires:
        if req.lower().startswith("hatchling"):
            return req
    return None


def _version_tuple(v: str) -> tuple[int, ...]:
    """Convert '1.29.0' to (1, 29, 0)."""
    return tuple(int(p) for p in v.split("."))
```

`_version_tuple` uses only stdlib — no `packaging` dependency required for simple
`>=` / `<` comparisons on X.Y.Z versions.

### Step 4: Add the two new test methods

```python
def test_pyproject_hatchling_requirement_parseable(self) -> None:
    """pyproject.toml [build-system].requires must include a hatchling entry."""
    with PYPROJECT_TOML.open("rb") as f:
        data = tomllib.load(f)
    requires: list[str] = data.get("build-system", {}).get("requires", [])
    spec = _parse_hatchling_specifier(requires)
    assert spec is not None, (
        "hatchling not found in [build-system].requires in pyproject.toml"
    )

def test_hatchling_version_matches_pyproject(self) -> None:
    """Dockerfile hatchling pin must satisfy the constraint in pyproject.toml."""
    with PYPROJECT_TOML.open("rb") as f:
        data = tomllib.load(f)
    requires: list[str] = data.get("build-system", {}).get("requires", [])
    spec = _parse_hatchling_specifier(requires)
    assert spec is not None, "hatchling not in pyproject.toml [build-system].requires"

    content = DOCKERFILE.read_text()
    pin_match = re.search(r"pip install.*?hatchling==(\d+\.\d+\.\d+)", content)
    assert pin_match is not None, "Could not find hatchling==X.Y.Z in Dockerfile"
    pinned = pin_match.group(1)
    pinned_t = _version_tuple(pinned)

    lower_match = re.search(r">=(\d+\.\d+\.\d+)", spec)
    assert lower_match is not None, (
        f"No >= lower bound found in pyproject.toml specifier: {spec!r}"
    )
    lower_t = _version_tuple(lower_match.group(1))

    upper_match = re.search(r"<(\d+(?:\.\d+)*)", spec)
    upper_t = _version_tuple(upper_match.group(1)) if upper_match else None

    assert pinned_t >= lower_t, (
        f"Dockerfile hatchling=={pinned} is below pyproject.toml lower bound "
        f"{lower_match.group(1)} (from {spec!r})"
    )
    if upper_t is not None:
        assert pinned_t < upper_t, (
            f"Dockerfile hatchling=={pinned} violates pyproject.toml upper bound "
            f"(from {spec!r})"
        )
```

**Design decisions:**
- Two tests, not one — separates "pyproject.toml is parseable" from "versions agree"
- `lower_match` re-used in the assertion message (already asserted non-None above)
- Upper bound is optional — if `pyproject.toml` has no `<` bound, upper check is skipped
- Regex `<(\d+(?:\.\d+)*)` handles both `<2` and `<2.0.0`

### Step 5: Verify and commit

```bash
# Run only the affected file (fast check)
pixi run python -m pytest tests/unit/e2e/test_dockerfile.py -v --no-cov

# Run pre-commit on modified file
pre-commit run --files tests/unit/e2e/test_dockerfile.py
```

Expected: 5 tests pass, all hooks green.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Test counts

| File | Tests Before | Tests After | Delta |
|------|-------------|-------------|-------|
| `tests/unit/e2e/test_dockerfile.py` | 3 | 5 | +2 |

### Pre-commit status

All hooks pass: `ruff-format`, `ruff-check`, `mypy`, `check-unit-test-structure`.

### Version validation logic

```
pyproject.toml: hatchling>=1.27.0,<2
Dockerfile:     hatchling==1.29.0

pinned_t  = (1, 29, 0)
lower_t   = (1, 27, 0)   →  (1,29,0) >= (1,27,0) ✅
upper_t   = (2,)          →  (1,29,0) <  (2,)     ✅
```

Tuple comparison in Python handles mixed-length tuples correctly for major-version
upper bounds (e.g. `(1, 29, 0) < (2,)` is `True`).

## Key Takeaways

1. **Always split "parseable" from "correct"** — two tests give clearer failure messages.
2. **stdlib `tomllib` (3.11+) + `tomli` backport (3.10)** is the canonical pattern in this codebase — no `# type: ignore` needed.
3. **`_version_tuple` + tuple comparison** is sufficient for `>=`/`<` checks — no `packaging` import needed.
4. **Run `pre-commit run --files <file>` before committing** — catches ruff format changes and mypy issues early.

## Related Skills

- `testing/generate-tests` — general test generation patterns
- `testing/run-tests` — running tests with pixi
- `ci-cd/fix-ci-test-failures` — debugging CI failures

## References

- Issue #1208: Extend test_dockerfile.py to assert pinned version matches pyproject.toml
- Issue #1141: Original hatchling pin regression test
- PR #1308: Implementation
