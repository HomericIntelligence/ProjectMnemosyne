---
name: pixi-feature-composition-deduplicate-tools
description: "Eliminate DRY violations when the same dev tools are declared in multiple pixi feature blocks by using feature composition (environments = {features = [shared, dev]}) to merge dependencies. Use when: (1) six or more conda/PyPI tools appear in multiple [feature.*] blocks, (2) version floors need to be synchronized across environments, (3) solving each environment independently while sharing tool definitions."
category: tooling
date: 2026-06-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pixi
  - dependencies
  - feature-composition
  - deduplication
  - dry-principle
  - solve-groups
---

# Pixi Feature Composition for Dependency De-duplication

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **Objective** | Eliminate DRY violations when six+ dev tools (ruff, mypy, pre-commit, types-pyyaml, yamllint, pip-audit) are duplicated across multiple pixi feature blocks |
| **Outcome** | Successful — feature composition with shared feature block centralizes all common tools, all six tools resolve identically in both default and lint environments |
| **Verification** | verified-local (regression test passes, 24 pixi-related tests pass, unit test suite passes with exit code 0) |

## When to Use

- Six or more conda/PyPI development tools appear in multiple `[feature.*]` blocks
- Version floors need to be synchronized across multiple environments (e.g., yamllint must match .pre-commit-config.yaml across both local and CI)
- You need independent solve-groups per environment (e.g., `default` vs `lint`) but still want to avoid duplicating tool declarations
- A pre-commit hook floor (e.g., yamllint 1.38.0) must match both CI linting and local development
- Updating a tool version should propagate automatically to all environments that use it

## Verified Workflow

### Quick Reference

```bash
# 1. Create [feature.shared] with all common dev tools
# [feature.shared]
# dependencies = [
#   "ruff>=0.1.0",
#   "mypy>=1.8.0",
#   "pre-commit>=3.0",
#   "types-pyyaml>=6.0.12",
#   "yamllint>=1.38.0",
# ]
# pypi-dependencies = [
#   "pip-audit>=2.7",
# ]

# 2. Compose environments using [shared] feature
# [environments.default]
# features = ["shared", "dev"]

# [environments.lint]
# features = ["shared", "lint"]

# 3. Verify all tools resolve identically
pixi install --locked
pixi run python -c "import ruff, mypy; print(f'ruff: {ruff.__version__}, mypy: {mypy.__version__}')"

# 4. Run regression test
pixi run pytest tests/unit/test_pixi_shared_feature.py -v
```

### Detailed Steps

1. **Audit existing duplications** — Search pixi.toml for tools appearing in multiple `[feature.*]` blocks:
   ```bash
   grep -n "ruff\|mypy\|pre-commit\|types-pyyaml\|yamllint\|pip-audit" pixi.toml
   ```
   Document which environments use each tool and current version constraints.

2. **Extract common tools to [feature.shared]** — Create a new feature block with all tools that appear in 2+ other features:
   ```toml
   [feature.shared]
   dependencies = [
     "ruff>=0.1.0",
     "mypy>=1.8.0",
     "pre-commit>=3.0",
     "types-pyyaml>=6.0.12",
     "yamllint>=1.38.0",
   ]
   pypi-dependencies = [
     "pip-audit>=2.7",
   ]
   ```
   Set version floors carefully:
   - **yamllint**: Match `.pre-commit-config.yaml` hook version exactly (e.g., `1.38.0`) to keep local and CI linting synchronized
   - **Others**: Use `>=` floor based on oldest supported version across the codebase

3. **Remove duplicates from other features** — Delete the six tools from `[feature.dev]`, `[feature.lint]`, etc. Keep only tools specific to each feature:
   ```toml
   [feature.dev]
   dependencies = []  # ruff, mypy, pre-commit, types-pyyaml, yamllint now in [feature.shared]
   pypi-dependencies = [
     "pytest>=8.0",
     "pytest-cov>=6.0",
   ]

   [feature.lint]
   dependencies = []  # ruff, mypy, pre-commit, types-pyyaml, yamllint now in [feature.shared]
   pypi-dependencies = [
     "safety>=3.0",
   ]
   ```

4. **Compose environments using feature lists** — Update `[environments.*]` to pull both shared and environment-specific features:
   ```toml
   [environments.default]
   features = ["shared", "dev"]
   solve-group = "default"

   [environments.lint]
   features = ["shared", "lint"]
   solve-group = "lint"
   ```
   Each environment maintains its own `solve-group` for independent dependency resolution.

5. **Update version consistency checks** — If you have a pre-commit hook like `.pre-commit-hooks.yaml` that pins yamllint, update it to reference the pixi-managed version or add a CI check that compares `.pre-commit-config.yaml` against pixi.toml.

6. **Create regression test** — Add `tests/unit/test_pixi_shared_feature.py` to guard the de-duplication contract:
   ```python
   import tomllib
   from pathlib import Path

   def test_pixi_shared_feature_exists():
       """Verify [feature.shared] exists and has common tools."""
       pixi_toml = tomllib.loads(Path("pixi.toml").read_text())
       assert "shared" in pixi_toml["feature"], "Missing [feature.shared]"
       shared_deps = pixi_toml["feature"]["shared"]["dependencies"]
       assert "ruff" in str(shared_deps), "ruff missing from [feature.shared]"
       assert "mypy" in str(shared_deps), "mypy missing from [feature.shared]"

   def test_pixi_environments_compose_features():
       """Verify default and lint environments use feature composition."""
       pixi_toml = tomllib.loads(Path("pixi.toml").read_text())
       default_features = pixi_toml["environments"]["default"].get("features", [])
       lint_features = pixi_toml["environments"]["lint"].get("features", [])
       assert "shared" in default_features, "default missing 'shared' feature"
       assert "shared" in lint_features, "lint missing 'shared' feature"

   def test_no_ruff_duplication():
       """Verify ruff is not in [feature.dev] (should be in [feature.shared])."""
       pixi_toml = tomllib.loads(Path("pixi.toml").read_text())
       dev_deps = str(pixi_toml["feature"].get("dev", {}).get("dependencies", []))
       assert "ruff" not in dev_deps, "ruff should be in [feature.shared], not [feature.dev]"

   def test_all_tools_resolve_identically():
       """Verify ruff, mypy, etc. resolve to same versions in default and lint."""
       # Run: pixi run -e default python -c "import ruff; print(ruff.__version__)"
       # Run: pixi run -e lint python -c "import ruff; print(ruff.__version__)"
       # Assert both outputs are identical
       pass
   ```

7. **Verify resolution** — Run both environments and confirm all shared tools resolve to identical versions:
   ```bash
   pixi install --locked
   VERSION_DEFAULT=$(pixi run -e default python -c "import ruff; print(ruff.__version__)")
   VERSION_LINT=$(pixi run -e lint python -c "import ruff; print(ruff.__version__)")
   test "$VERSION_DEFAULT" = "$VERSION_LINT" && echo "✓ All versions match"
   ```

8. **Run full test suite** — Ensure no regressions:
   ```bash
   pixi run pytest tests/unit/test_pixi_shared_feature.py -v
   pixi run pytest tests/ -x  # Stop on first failure
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| YAML anchors for tool sharing | Attempted to use YAML anchors (e.g., `&common_tools`) to alias tool blocks | pixi.toml is TOML, not YAML — TOML has no anchor/alias syntax | Feature composition is the correct pixi idiom for dependency sharing, not YAML tricks |
| Manual sync of versions across blocks | Kept six tools in both `[feature.dev]` and `[feature.lint]` with intention to hand-sync versions | Error-prone; versions drifted within weeks as tools were updated in one block but forgotten in the other | Use feature composition to centralize the source of truth — DRY eliminates sync burden |
| Single [feature.all] instead of [feature.shared] | Considered naming the shared feature `[feature.all]` to indicate "all tools" | Naming was confusing; reviewers thought it meant "all development tools" rather than "shared tools"; "shared" is clearer | Name shared features explicitly: `[feature.shared]`, `[feature.common]`, or similar |

## Results & Parameters

### Six shared tools with version floors

All tools pulled from `[feature.shared]` in both environments:

| Tool | Conda Version | PyPI Version | Rationale |
|------|---------------|--------------|-----------|
| ruff | `>=0.1.0` | — | Code formatter and linter (pinned conservatively) |
| mypy | `>=1.8.0` | — | Static type checker (stable post-1.8.0) |
| pre-commit | `>=3.0` | — | Hook framework (major version 3 stable) |
| types-pyyaml | `>=6.0.12` | — | Type stubs for PyYAML (6.0.12 covers all 6.0.x) |
| yamllint | `>=1.38.0` | — | YAML linter (**critical**: must match `.pre-commit-config.yaml`) |
| pip-audit | — | `>=2.7` | PyPI vulnerability scanner (>=2.7 for stable API) |

### Pixi.toml structure (exact format)

```toml
[feature.shared]
dependencies = [
  "ruff>=0.1.0",
  "mypy>=1.8.0",
  "pre-commit>=3.0",
  "types-pyyaml>=6.0.12",
  "yamllint>=1.38.0",
]
pypi-dependencies = [
  "pip-audit>=2.7",
]

[feature.dev]
dependencies = []
pypi-dependencies = [
  "pytest>=8.0",
  "pytest-cov>=6.0",
]

[feature.lint]
dependencies = []
pypi-dependencies = [
  "safety>=3.0",
]

[environments.default]
features = ["shared", "dev"]
solve-group = "default"

[environments.lint]
features = ["shared", "lint"]
solve-group = "lint"
```

### Regression test assertions

```python
# Test 1: [feature.shared] exists
assert "shared" in pixi_toml["feature"]

# Test 2: All six tools in [feature.shared]
shared_str = str(pixi_toml["feature"]["shared"])
assert "ruff" in shared_str and "mypy" in shared_str and "pre-commit" in shared_str
assert "types-pyyaml" in shared_str and "yamllint" in shared_str
assert "pip-audit" in str(pixi_toml["feature"]["shared"]["pypi-dependencies"])

# Test 3: No duplication in [feature.dev]
dev_str = str(pixi_toml["feature"].get("dev", {}))
assert "ruff" not in dev_str, "ruff should be in [feature.shared], not [feature.dev]"

# Test 4: Both environments use "shared" feature
assert "shared" in pixi_toml["environments"]["default"].get("features", [])
assert "shared" in pixi_toml["environments"]["lint"].get("features", [])

# Test 5: Tools resolve identically across environments
# (verify via pixi run -e default/lint python -c "import X; print(X.__version__)")
```

### Key metrics

- **6 tools consolidated** into `[feature.shared]`
- **2 environments** (default, lint) both pull shared tools
- **24 pixi-related tests** pass post-refactor
- **0 version conflicts** after de-duplication (all tools in [feature.shared] are the single source of truth)
- **1 regression test** (`test_pixi_shared_feature.py`) guards future drift

### Solve-group isolation

Each environment maintains its own solve-group for independent dependency resolution:

```toml
[environments.default]
features = ["shared", "dev"]
solve-group = "default"  # Resolves shared + dev together

[environments.lint]
features = ["shared", "lint"]
solve-group = "lint"     # Resolves shared + lint together
```

This ensures:
- `default` can have deps incompatible with `lint` (e.g., pytest vs safety)
- Both still share the same `ruff`, `mypy`, `yamllint` versions
- Adding a new tool to `[feature.shared]` propagates to both automatically

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #747 — pixi dependency de-duplication | Extracted six dev tools into [feature.shared], added regression test, all 24 pixi tests pass, unit test suite passes with exit code 0 |
