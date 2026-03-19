---
name: pixi-pypi-upper-bounds
description: Add explicit upper version bounds to pixi.toml [pypi-dependencies]. Use
  when auditing or hardening dependency version constraints to prevent silent breakage
  on major releases.
category: tooling
date: '2026-03-19'
version: 1.0.0
mcp_fallback: none
tier: 2
---
# Pixi PyPI Upper Bounds

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-27 |
| Objective | Add `<next-major>` upper bounds to all unbounded `[pypi-dependencies]` entries in `pixi.toml` to prevent silent breakage on major releases |
| Outcome | Successful — all 11 packages bounded, 3209 tests passing, 78.36% coverage |
| Issue | ProjectScylla #1119 |

## When to Use

- Auditing `pixi.toml` for missing upper bounds on PyPI dependencies
- After a quality audit flags unbounded scientific computing packages
- Before adding a new PyPI dependency (establish bounds from the start)
- When a CI break is caused by an unexpected major version upgrade

## Key Insight: Match Upper Bound to Installed Version's Major

**The critical rule**: set the upper bound to `<(installed_major + 1)`, NOT to `<(installed_major)`.

Setting `<installed_major` will **downgrade** the package, which can silently introduce
a different kind of breakage (the older minor may have its own Python-version incompatibilities).

Example that went wrong:
```
# altair 6.0.0 was installed and working on Python 3.14
altair = ">=5.0,<6"   # BAD — downgrades to 5.5.0 which breaks on Python 3.14
altair = ">=5.0,<7"   # GOOD — keeps 6.0.0
```

## Python Version Compatibility Pitfall

`altair 5.x` uses `TypedDict(closed=True)` which is not supported in Python 3.14:
```
TypeError: _TypedDictMeta.__new__() got an unexpected keyword argument 'closed'
```

When setting upper bounds, always verify the downgraded version is compatible with
the project's Python version. Run tests after `pixi install` to catch this.

## Verified Workflow

1. **Audit current bounds**: Read `pixi.toml` [pypi-dependencies] section — identify entries with no `<` constraint
2. **Check locked versions**: Run `grep "version:" pixi.lock | sort -u` or check `pixi.lock` for current installed versions
3. **Set bounds to `<(major+1)`**: For each package, use the currently-locked major version + 1 as the upper bound
4. **Handle special cases**: Check Python version compatibility before choosing the bound (see altair pitfall above)
5. **Run `pixi update <pkg>`**: After changing `pixi.toml`, `pixi lock` may say "already up-to-date" — use `pixi update <pkg>` to force re-resolution
6. **Run `pixi install`**: Reinstall the environment to pick up updated lock
7. **Run full test suite**: `pixi run python -m pytest tests/ -v` — ensure no new failures
8. **Add regression test**: Write a test that reads `pixi.toml` with `tomllib` and asserts `<` is present in each targeted package's constraint

## Regression Test Pattern

Use `tomllib` (stdlib in Python 3.11+) to parse `pixi.toml` and enforce upper bounds:

```python
import tomllib
from pathlib import Path
import pytest

PACKAGES_REQUIRING_UPPER_BOUND = ["numpy", "pandas", "scipy", "matplotlib", ...]
_PIXI_TOML = Path(__file__).parents[3] / "pixi.toml"  # adjust depth to project root

def _load_pypi_deps() -> dict[str, str]:
    with _PIXI_TOML.open("rb") as fh:
        data = tomllib.load(fh)
    raw = data.get("pypi-dependencies", {})
    return {name: spec for name, spec in raw.items() if isinstance(spec, str)}

@pytest.mark.parametrize("package", PACKAGES_REQUIRING_UPPER_BOUND)
def test_upper_bound_present(package: str) -> None:
    deps = _load_pypi_deps()
    spec = deps.get(package, "")
    assert "<" in spec, f"'{package}' has no upper bound: {spec!r}"
```

**Path depth**: `parents[N]` where N is the number of directories from the test file
to the project root. Verify with:
```python
from pathlib import Path
p = Path("/path/to/tests/unit/config/test_pixi.py")
[print(i, p.parents[i]) for i in range(6)]  # find which index = project root
```

## `pixi lock` vs `pixi update` Gotcha

After editing `pixi.toml`:
- `pixi lock` reports "already up-to-date" if the new constraint is still satisfied by the current locked version
- But if you *tightened* the bound (e.g., `<6` now excludes the locked `6.0.0`), you need `pixi update <package>` to force re-resolution
- Always run `pixi install` after lock changes to apply them to the active environment

## Reference Bounds Applied (ProjectScylla, 2026-02-27)

```toml
[pypi-dependencies]
matplotlib = ">=3.8,<4"
numpy = ">=1.24,<3"
pandas = ">=2.0,<3"
seaborn = ">=0.13,<1"
scipy = ">=1.11,<2"
altair = ">=5.0,<7"          # <7 not <6 — altair 5.x breaks on Python 3.14
vl-convert-python = ">=1.0,<2"
krippendorff = ">=0.6.0,<1"
statsmodels = ">=0.14,<1"
jsonschema = ">=4.0,<5"
defusedxml = ">=0.7,<1"
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| `altair = ">=5.0,<6"` | Downgraded altair 6.0.0 → 5.5.0; altair 5.x uses `TypedDict(closed=True)` unsupported in Python 3.14 | Always check Python version compatibility before tightening bounds |
| `pixi lock` after editing toml | Reported "already up-to-date" even when the effective constraint changed | Use `pixi update <pkg>` to force re-resolution, then `pixi install` |
| `parents[4]` path for test file | Resolved to wrong directory in a git worktree (`.worktrees/` parent) | Always verify `Path(__file__).parents[N]` with a quick Python snippet |
