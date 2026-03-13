# Skill: wheel-only-build

## Overview

| Field     | Value                                                          |
|-----------|----------------------------------------------------------------|
| Date      | 2026-02-19                                                     |
| Issue     | #746                                                           |
| PR        | #804                                                           |
| Objective | Configure hatchling to produce wheel-only distributions        |
| Outcome   | Success — single 2-line addition resolved the issue            |
| Category  | tooling                                                        |

## When to Use

Trigger this skill when:

- A pyproject.toml using hatchling builds both sdist and wheel by default and you want wheel-only output
- Issue asks to "make distribution binary-only" or "exclude sdist from default build"
- `hatch build` produces both `.tar.gz` and `.whl` files and only `.whl` is desired
- You need to reduce distribution surface area or pre-compilation focus

## Verified Workflow

### 1. Identify the build backend

Confirm the project uses `hatchling`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 2. Add the `[tool.hatch.build]` targets restriction

Insert **above** the existing `[tool.hatch.build.targets.wheel]` section:

```toml
[tool.hatch.build]
targets = ["wheel"]

[tool.hatch.build.targets.wheel]
packages = ["scylla"]
```

The `targets` key tells hatchling which build targets to produce by default. Setting it to `["wheel"]` suppresses sdist generation unless explicitly requested.

### 3. Verify sdist is still accessible explicitly

```bash
hatch build -t sdist   # still works on demand
hatch build            # now produces only wheel
```

### 4. Run pre-commit and tests

```bash
pre-commit run --files pyproject.toml
pixi run python -m pytest tests/ -v
```

No test changes needed — this is a build configuration change only.

## Failed Attempts

None — the change was identified and applied correctly on the first attempt. The hatchling `targets` key was already documented behavior; no trial-and-error was required.

## Results & Parameters

### Minimal diff to `pyproject.toml`

```diff
+[tool.hatch.build]
+targets = ["wheel"]
+
 [tool.hatch.build.targets.wheel]
 packages = ["scylla"]
```

### Key facts

- **No Python code changes** — build config only
- **No test changes** — existing test suite unaffected
- **sdist preserved** — still producible with `hatch build -t sdist` for PyPI compliance if needed
- **Pre-commit hooks**: All pass (toml is checked by `Fix End of Files` / `Trim Trailing Whitespace` only; no TOML-specific linter)

## References

- [Hatchling build targets documentation](https://hatch.pypa.io/latest/config/build/#targets)
- PR #804: feat(build): configure hatchling to produce wheel-only distributions
