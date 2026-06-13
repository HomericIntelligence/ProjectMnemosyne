---
name: pixi-pip-dep-floor-cap-pinning
description: "Use when: (1) pixi.toml has pip listed as `\"*\"` (unbounded) in [dependencies] while all other deps are pinned, (2) planning a floor/cap constraint for conda-managed pip to guard PEP 660 editable-install compatibility, (3) adding a regression test to ensure pip stays within a safe range after a version bump, (4) checking whether pixi.lock needs to be committed after constraining pip."
category: ci-cd
date: 2026-06-13
version: "1.2.0"
user-invocable: false
history: pixi-pip-dep-floor-cap-pinning.history
tags:
  - pixi
  - pip
  - dependency-pinning
  - floor-cap
  - pep-660
  - editable-install
  - pixi-lock
  - regression-test
  - dev-install
  - conda
---

# Pixi pip Dependency Floor/Cap Pinning

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-13 |
| **Objective** | Constrain the `pip` entry in `pixi.toml [dependencies]` from unbounded `"*"` to a `>=floor,<cap` range that guarantees PEP 660 editable-install compatibility while preventing silent breakage from major pip upgrades |
| **Outcome** | Proposed plan for GitHub issue #1202 — `pip = ">=23.0,<27"` — derived from the installed pip version (26.1.2) and the PEP 660 stable-support floor (23.0); regression test class `TestPipPinning` to be added to `tests/unit/scripts/test_dependency_floor_consistency.py` |
| **Verification** | verified-ci (PR #1295 — all CI gates green; pixi.lock unchanged; 9/9 tests passed) |

## When to Use

- `pixi.toml` contains `pip = "*"` in `[dependencies]` while every other dep has an explicit version constraint.
- You need to pick a floor for pip that guarantees the `dev-install = "pip install -e . --no-deps"` task works correctly with PEP 660 editable installs.
- You need to pick a `<cap` that blocks silent breakage from the next major pip release without over-constraining.
- You are adding or auditing a regression test for pip version bounds in the project's test suite.
- You are evaluating whether constraining pip triggers a lockfile re-solve that must be committed.

## Verified Workflow

> **VERIFIED**: This workflow was applied in ProjectHephaestus PR #1295 (merged 2026-06-13). All CI gates passed; pixi.lock was unchanged (pip 26.1.2 already satisfies `>=23.0,<27`). 9/9 tests passed.

### Quick Reference

```bash
# 1. Check installed pip version
pixi run python -c "import pip; print(pip.__version__)"
pixi list | grep "^pip "

# 2. Derive constraints
#    floor = 23.0  (first pip release with stable PEP 660 editable-install support)
#    cap   = installed_major + 1  (e.g. 26.x installed → cap = 27)

# 3. Apply to pixi.toml [dependencies]
#    pip = ">=23.0,<27"

# 4. Re-solve and check lockfile drift  ← MANDATORY EXPLICIT STEP
pixi install
git diff pixi.lock
git add pixi.lock   # ALWAYS add if pixi.lock changed — CI fails on dirty lockfile

# 5. Verify pip is importable at the constrained version
pixi run python -c "import pip; print(pip.__version__)"

# 6. Run the regression test
pixi run pytest tests/unit/scripts/test_dependency_floor_consistency.py -v
```

### Detailed Steps

#### 1. Identify the unbounded pip entry

```bash
grep -n '"pip"' pixi.toml
# Expected before fix:
# pip = "*"
```

All other deps in a well-maintained pixi.toml should already have explicit bounds. Unbounded `"*"` means any future pip version — including major breaks — will be silently accepted.

#### 2. Determine the floor

The floor is `>=23.0` because:

- pip 23.0 is the first stable release with full PEP 660 editable install support (`pip install -e . --no-deps` reliably without `--no-build-isolation` hacks).
- The `dev-install` pixi task (`pip install -e . --no-deps`) depends on this behavior.
- Community consensus places PEP 660 stable support at pip 23.0. **Note**: this claim has NOT been independently verified against the pip 23.0 changelog — it is reasonable community consensus. If the project later needs to lower the floor, cross-check against the actual pip 23.0 release notes.

#### 3. Determine the cap

```bash
pip_version=$(pixi run python -c "import pip; print(pip.__version__)")
installed_major=$(echo "$pip_version" | cut -d. -f1)
cap=$((installed_major + 1))
echo "pip = \">=23.0,<${cap}\""
```

The cap is `installed_major + 1`. This:
- Allows all current patch and minor releases of the installed major.
- Prevents silent adoption of the next major pip release (which may break the build system, deprecate flags, or change resolver behavior).
- Is conservative: the cap must be bumped intentionally in a future PR when the next major is tested.

For the #1202 session: pip 26.1.2 was installed → cap = 27 → `pip = ">=23.0,<27"`.

#### 4. Apply the change

Edit `pixi.toml`:

```toml
[dependencies]
# Before:
pip = "*"

# After:
pip = ">=23.0,<27"
```

#### 5. Re-solve and lockfile check — MANDATORY EXPLICIT STEP

This is the most common landability gap for pixi.toml edits. When any `[dependencies]` constraint changes, `pixi install` re-solves `pixi.lock`. The plan **must** include all three sub-steps:

```bash
# (a) Re-solve the environment
pixi install

# (b) Check if the lockfile changed
git diff pixi.lock

# (c) Stage the lockfile if it changed
git add pixi.lock
```

If `pixi.lock` changed and is omitted from the commit, CI fails on the locked-install check. This was the primary cause of the R0 plan receiving a NOGO. The lockfile re-solve is a side effect of `pixi install` — not an explicit file edit — so it is easy to forget. It must appear in both the **Files to Modify** list and the **Implementation Order** steps of any plan touching `pixi.toml`.

#### 6. Add a regression test

Add a `TestPipPinning` class to the **existing** test file:

```
tests/unit/scripts/test_dependency_floor_consistency.py
```

Do NOT create a new file. The existing file already exercises pixi.toml dependency constraints — `TestPipPinning` extends that coverage.

**Use the existing `_floor()` and `_upper_cap()` module-level helpers** — do not write substring checks inline. Every other class in the file delegates to these helpers. Using them is required for DRY compliance.

```python
class TestPipPinning:
    """Regression tests for pip version bounds in pixi.toml."""

    def test_pip_has_floor_and_cap(self, pixi_deps: dict[str, str]) -> None:
        """pip must have both a >= floor and a < cap."""
        spec = pixi_deps.get("pip", "")
        assert spec, "pip must appear in pixi.toml [dependencies]"
        # Delegate to module-level helpers (DRY — consistent with all other classes)
        floor = _floor(spec)   # raises AssertionError if >= clause absent
        cap = _upper_cap(spec) # raises AssertionError if < clause absent
        assert floor is not None, f"pip spec must have a >= floor, got: {spec!r}"
        assert cap is not None, f"pip spec must have a strict < cap, got: {spec!r}"

    def test_pip_floor_is_pep660_compatible(self, pixi_deps: dict[str, str]) -> None:
        """pip floor must be >= 23.0 (first stable PEP 660 release)."""
        from packaging.version import Version

        spec = pixi_deps.get("pip", "")
        floor = _floor(spec)
        assert floor >= Version("23.0"), (
            f"pip floor {floor} is below 23.0 (minimum for stable PEP 660 editable installs)"
        )

    def test_pip_cap_blocks_next_major_only(self, pixi_deps: dict[str, str]) -> None:
        """pip cap must block the next major (27) but not be a downgrade cap.

        Two-sided bound: Version("26") < cap <= Version("27")
        - Lower bound rejects a downgrade cap like <24 (which was the installed major).
        - Upper bound rejects an over-permissive cap like <28.
        # TODO: update lower bound to Version("27") when CI tests pip 27.x.
        """
        from packaging.version import Version

        spec = pixi_deps.get("pip", "")
        cap = _upper_cap(spec)
        assert Version("26") < cap <= Version("27"), (
            f"pip cap {cap} must be exactly <27 (two-sided: not a downgrade, not over-permissive); "
            "bump this test when the cap is intentionally raised"
        )
```

**Test design notes (R1 revision)**:
- `_floor(spec)` and `_upper_cap(spec)` are module-level helpers already present in `test_dependency_floor_consistency.py`. Always use them — do not write `"<" in spec` substring checks inline.
- The two-sided cap assertion `Version("26") < cap <= Version("27")` rejects both a downgrade cap (e.g., `<24`) and an over-permissive cap (e.g., `<28`). A one-sided `cap <= Version("27")` would silently accept `<24`. The lower bound must be the current installed major.
- The hardcoded `Version("26")` lower bound is a future maintenance burden: it must be updated to `Version("27")` when CI upgrades to pip 27.x. The test comment marks this explicitly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Adding `TestPipPinning` to a new test file | Considered `tests/unit/scripts/test_pip_pinning.py` | The existing `test_dependency_floor_consistency.py` already covers pixi dep constraints; a new file would duplicate infra | Always check the existing test file in `tests/unit/scripts/` before creating a new one — the right home is the closest existing file |
| Using `">=23,<27"` (integer floor) | Minor-version-only floor like `>=23` | Technically valid but inconsistent with the rest of the codebase which uses dotted floors like `>=23.0` | Use `>=MAJOR.MINOR` (dotted) for consistency with other dep specs in the project |
| Omitting `pixi.lock` from the PR (R0) | Changed only `pixi.toml` in Files to Modify; no `pixi install` step in Implementation Order | `pixi install` triggered a lockfile re-solve; CI `--locked` check failed because `pixi.lock` diverged | Whenever a `pixi.toml` dependency constraint changes, `pixi.lock` must appear in Files to Modify AND the plan must include: (a) `pixi install`, (b) `git diff pixi.lock`, (c) `git add pixi.lock`. This was the primary R0 NOGO cause. |
| Inline `"<" in spec` substring check in `test_pip_has_floor_and_cap` (R0) | Used `"<" in spec and not spec.startswith("<=")` directly instead of `_upper_cap()` | Reviewer flagged as DRY violation (existing helpers ignored) and fragile — a spec like `!=26.0,<27` passes even without a clean `<cap` clause | Always delegate to `_floor(spec)` / `_upper_cap(spec)` which raise AssertionError when the clause is absent; do not write inline substring checks |
| One-sided cap assertion `cap <= Version("27")` (R0) | Used upper bound only | Silently accepts a downgrade cap like `<24` (which is below the installed major); reviewer flagged as incomplete | Use two-sided bound: `Version("26") < cap <= Version("27")` — lower bound is the current installed major, upper bound is installed_major + 1 |

## Results & Parameters

### Constraint derivation formula

| Parameter | Value | Rationale |
| ----------- | ------- | ----------- |
| Floor | `>=23.0` | First pip release with stable PEP 660 editable-install support (community consensus; cross-check against pip 23.0 release notes before lowering) |
| Cap | `<installed_major + 1` | Blocks the next major version; requires an explicit bump when the new major is tested |
| Example (2026-06-13) | `>=23.0,<27` | pip 26.1.2 installed → cap = 27 |

### Implementation Order checklist (mandatory for any pixi.toml edit)

1. Edit `pixi.toml` — change `pip = "*"` to `pip = ">=23.0,<27"`
2. Run `pixi install` — re-solves `pixi.lock` as a side effect
3. Run `git diff pixi.lock` — check if lockfile changed
4. Run `git add pixi.lock` if changed — **must be in the same commit/PR**
5. Add `TestPipPinning` to `tests/unit/scripts/test_dependency_floor_consistency.py` using `_floor()` / `_upper_cap()` helpers
6. Run `pixi run pytest tests/unit/scripts/test_dependency_floor_consistency.py -v`

### Verification commands

```bash
# Confirm installed pip version
pixi run python -c "import pip; print(pip.__version__)"
pixi list | grep "^pip "

# Confirm constraint is applied
grep "pip" pixi.toml

# Confirm lockfile is current after constraint change
git diff pixi.lock   # should be empty after committing

# Run regression test
pixi run pytest tests/unit/scripts/test_dependency_floor_consistency.py::TestPipPinning -v
```

### Reviewer checklist (from the #1202 session, updated R1)

- Confirm `pixi install` completes cleanly after the constraint change.
- Check whether `pixi.lock` changed; if so, verify it is committed in the same PR.
- Verify that `test_pip_has_floor_and_cap` delegates to `_floor()` / `_upper_cap()` — not inline substring checks.
- Verify the two-sided cap assertion: `Version("26") < cap <= Version("27")`. The lower bound rejects downgrade caps; the upper bound rejects over-permissive caps.
- The hardcoded `Version("26")` lower bound in `test_pip_cap_blocks_next_major_only` must be updated to `Version("27")` when CI upgrades to pip 27.x.

### Uncertain assumptions (flag for future verification)

- **Floor `>=23.0`**: Based on PEP 660 stable-support community consensus, NOT independently cross-checked against the actual pip 23.0 release notes. If the project needs to lower the floor, verify against `https://pip.pypa.io/en/stable/news/`.
- **Lockfile re-solve**: Constraining pip MAY trigger a full lockfile re-solve depending on the current pixi version. Always check `git diff pixi.lock` before committing.
- **Hardcoded lower bound `Version("26")`** in `test_pip_cap_blocks_next_major_only`: This will need updating when pip 27.x lands in CI. The test comment flags this explicitly, but the hardcoded value remains a future maintenance burden.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #1202 — pip `"*"` → `">=23.0,<27"` (R0) | pip 26.1.2 confirmed via `pixi list`; R0 plan received NOGO (missing lockfile step, inline substring check, one-sided cap) |
| ProjectHephaestus | Issue #1202 — PR #1295 (merged 2026-06-13) | Lockfile step explicit, `_floor`/`_upper_cap` helpers used, two-sided cap assertion verified; all 9 CI tests passed; pixi.lock unchanged (pip 26.1.2 already in range) |
