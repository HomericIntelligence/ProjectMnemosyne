---
name: ci-cd-hatchling-force-include-sdist-wheel-break
description: "Fix hatchling CI build failures caused by force-include paths breaking the sdist→wheel two-step build. Use when: (1) CI build job fails with FileNotFoundError on a force-include path, (2) wheel builds from source work locally but fail in CI using python -m build --no-isolation, (3) hatchling force-include paths cannot be resolved inside an unpacked sdist directory."
category: ci-cd
date: 2026-05-03
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [hatchling, force-include, sdist, wheel, python-build, pyproject, packaging, ci-cd]
---

# Hatchling force-include Breaks sdist→Wheel Build

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-03 |
| **Objective** | Fix CI `build` job failure caused by `force-include` paths not resolving inside the unpacked sdist |
| **Outcome** | Success — removed `force-include` entirely; wheel build went from failure to success |
| **Verification** | verified-ci (Scylla PR #1905 merged; build job passed) |

## When to Use

- CI fails with `FileNotFoundError: Forced include not found: src/<pkg>/...`
- `python -m build --no-isolation` passes locally but fails in CI
- A `[tool.hatch.build.targets.wheel.force-include]` section exists in `pyproject.toml`
- The build uses the standard two-step sequence: sdist first, then wheel from the sdist
- Directories listed in `force-include` already live under a package path in `packages`

## Verified Workflow

### Quick Reference

```toml
# BEFORE (breaks sdist→wheel builds):
[tool.hatch.build.targets.wheel]
packages = ["src/scylla"]

[tool.hatch.build.targets.wheel.force-include]
"src/scylla/analysis/schemas" = "scylla/analysis/schemas"

# AFTER (correct — packages already includes all subdirs recursively):
[tool.hatch.build.targets.wheel]
packages = ["src/scylla"]
```

```bash
# Verify the fix locally before pushing
python -m build --no-isolation
ls dist/*.whl  # should exist and contain the previously-missing paths
```

### Detailed Steps

1. **Identify the error** — look for this pattern in CI logs:
   ```
   FileNotFoundError: Forced include not found: src/<pkg>/<subpath>
   ```

2. **Understand the build sequence** — `python -m build --no-isolation` runs:
   - Step 1: `python -m build --sdist` → produces `.tar.gz`
   - Step 2: builds wheel **from the unpacked sdist**, NOT from the repo root

3. **Recognize the path resolution mismatch** — hatchling resolves `force-include` paths relative
   to the directory where the build command runs. During the wheel-from-sdist step, that directory
   is the unpacked sdist, not the repo root. Paths like `src/scylla/analysis/schemas` do not exist
   there.

4. **Check if the path is already covered by `packages`** — `packages = ["src/scylla"]` causes
   hatchling to recursively include **all** contents of `src/scylla/`, including every
   subdirectory. If the `force-include` target lives inside a listed package, it is redundant.

5. **Remove the `force-include` section entirely** from `pyproject.toml`.

6. **Update any tests asserting `force-include` config** — if a packaging test checks for the
   `force-include` key, update it to check `packages` instead:
   ```python
   # Old (checks force-include):
   force_include = wheel.get("force-include", {})
   assert "src/scylla/py.typed" in force_include

   # New (checks packages):
   packages: list[str] = wheel.get("packages", [])
   assert any("scylla" in pkg for pkg in packages)
   ```

7. **Verify locally**:
   ```bash
   python -m build --no-isolation
   python -m zipfile -l dist/*.whl | grep "schemas\|py.typed"
   ```

8. **Push and confirm CI build job passes**.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add `force-include` for `py.typed` | Added `"src/scylla/py.typed" = "scylla/py.typed"` to `force-include` | Same `FileNotFoundError` — path resolution is relative to sdist directory, not repo root | `py.typed` is already included via `packages`; `force-include` is redundant AND breaks sdist→wheel |
| Use relative path in `force-include` | Changed `"src/scylla/analysis/schemas"` to `"analysis/schemas"` | Still fails — hatchling's working directory during wheel-from-sdist step is the sdist root, not the package directory | `force-include` paths cannot be made to work reliably in sdist→wheel builds regardless of path form |

## Results & Parameters

### Root Cause Explained

`python -m build --no-isolation` performs two steps:

```text
Step 1: build sdist → extracts to /tmp/pip-sdist-build-XXXX/projectname-0.1.0/
Step 2: build wheel from → /tmp/pip-sdist-build-XXXX/projectname-0.1.0/
```

During step 2, hatchling is invoked with CWD = the unpacked sdist directory. The path
`src/scylla/analysis/schemas` does not exist there (sdist layout preserves the directory
structure, but build artifacts like `force-include` source paths are not re-resolved from
the original repo root).

### What `packages` Already Covers

`packages = ["src/scylla"]` tells hatchling to include the entire `src/scylla/` tree recursively:

```
src/scylla/
├── __init__.py          ✓ included
├── py.typed             ✓ included
├── analysis/
│   ├── __init__.py      ✓ included
│   └── schemas/
│       ├── foo.json     ✓ included
│       └── bar.json     ✓ included
```

No `force-include` is needed for any path already within the package tree.

### Minimal pyproject.toml diff

```diff
 [tool.hatch.build.targets.wheel]
 packages = ["src/scylla"]
-
-[tool.hatch.build.targets.wheel.force-include]
-"src/scylla/analysis/schemas" = "scylla/analysis/schemas"
```

### Secondary: Transient CI Failure

A 502 Bad Gateway error during `pixi install` for `v8 v0.105.1` caused an unrelated job failure.
Fix: rerun only the failed jobs:

```bash
gh run rerun <run-id> --failed
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectScylla | PR #1905 (`fix/build-py-typed-sdist-signed`); `python -m build --no-isolation` in CI `build` job; 2026-05-03 | Build job went from failure to success after removing `force-include` |
