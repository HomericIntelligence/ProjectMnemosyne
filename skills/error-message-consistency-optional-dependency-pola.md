---
name: error-message-consistency-optional-dependency-pola
description: "Plan a POLA fix that aligns one public entry point's missing-optional-dependency error to an existing sibling's actionable error instead of inventing a new exception. Use when: (1) two public functions reach the same missing-dependency failure by different code paths and one already raises the right error; (2) a catch-all branch collapses 'unsupported format' and 'dependency missing' into one misleading message; (3) you are tempted to add a discriminator enum or custom exception class for a one-line consistency fix; (4) the absent-dependency branch is only ever exercised via monkeypatch and could pass vacuously."
category: architecture
date: 2026-06-25
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - pola
  - error-message
  - optional-dependency
  - exception-consistency
  - planning
  - yaml
  - monkeypatch
  - vacuous-test
  - yagni
  - kiss
---

# Error-Message Consistency for Optional-Dependency Failures (POLA)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-25 |
| **Objective** | Plan ProjectHephaestus issue #1510 — `load_config()` raised a misleading `ValueError("Unsupported config format")` when PyYAML was absent for a `.yaml`/`.yml` file, instead of the actionable `RuntimeError("PyYAML is required for YAML config support")` that the sibling `load_yaml_config()` already raises. |
| **Outcome** | Plan written: split the collapsed `suffix in {...} and YAML_AVAILABLE` condition into (detect format) THEN (check dependency), and reuse the existing sibling error verbatim. NOT a discriminator-enum case. Plan unverified — never executed in CI. |
| **Verification** | unverified — planning session only; the one-liner and its tests were reasoned about but never run. |
| **History** | n/a (initial version) |

## When to Use

- Two public entry points can reach the **same** failure (a missing optional dependency such as PyYAML, `lxml`, `orjson`) by different code paths, and **one already raises the correct, actionable error** while the other collapses the case into a misleading catch-all.
- A single boolean condition collapses two distinct concerns — e.g. `if suffix in {".yaml", ".yml"} and YAML_AVAILABLE:` — so a missing dependency falls through to an "unsupported format" branch and reports the wrong cause.
- You are about to "fix" the inconsistency by inventing a **new exception class** or **discriminator enum** for what is a one-line consistency fix. (Reach for this skill to talk yourself out of that — see also `exception-discriminator-enums-state-machine-pola` for the *opposite* case where an enum IS warranted.)
- The missing-dependency branch is almost never exercised because the dependency is installed in every normal test/CI env, so the only coverage is a `monkeypatch.setattr(..., AVAILABLE_FLAG, False)`.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Find the sibling that ALREADY raises the right error — reuse its message verbatim.
grep -rn 'required for YAML\|YAML_AVAILABLE\|is required for' hephaestus/config/

# 2. THE TOP RISK: grep every caller that might catch the OLD exception type.
#    Changing ValueError -> RuntimeError silently breaks `except ValueError` handlers.
grep -rn 'load_config' hephaestus/ tests/ | grep -v 'def load_config'
grep -rn 'except ValueError' hephaestus/ tests/

# 3. Confirm the function reads the availability flag at CALL time (module-level),
#    so monkeypatching the module attribute actually takes effect.
grep -n 'YAML_AVAILABLE' hephaestus/config/utils.py
```

```python
# BEFORE (collapsed condition -> misleading error):
def load_config(config_path):
    suffix = config_path.suffix.lower()
    if suffix in {".json"}:
        return load_json_config(config_path)
    if suffix in {".yaml", ".yml"} and YAML_AVAILABLE:   # <-- two concerns in one test
        return load_yaml_config(config_path)
    raise ValueError(f"Unsupported config format: {config_path.suffix}")

# AFTER (split: detect format FIRST, then dependency; reuse sibling's error verbatim):
def load_config(config_path):
    suffix = config_path.suffix.lower()
    if suffix == ".json":
        return load_json_config(config_path)
    if suffix in {".yaml", ".yml"}:
        if not YAML_AVAILABLE:
            # Same RuntimeError text load_yaml_config() already raises — cross-entry-point consistency.
            raise RuntimeError("PyYAML is required for YAML config support")
        return load_yaml_config(config_path)
    raise ValueError(f"Unsupported config format: {config_path.suffix}")  # original-case suffix preserved
```

### Detailed Steps (pre-planning + planning checklist)

1. **Find the sibling that already raises the right error and reuse its message byte-for-byte.** Do not paraphrase. Cross-entry-point consistency means a caller that branches on the message (or asserts on it in a test) behaves identically no matter which entry point it hit. In #1510, `load_yaml_config()` already raised `RuntimeError("PyYAML is required for YAML config support")`; `load_config()` must raise the *same* string.

2. **Split the collapsed condition into format-detection THEN dependency-availability.** `if suffix in {".yaml",".yml"} and YAML_AVAILABLE:` answers "is this a supported, loadable YAML file?" — but the failure modes differ. Detect the format first (so an unknown extension still hits `ValueError`), then check availability inside that branch (so a `.yaml` file with PyYAML absent raises the actionable `RuntimeError`).

3. **Reject a custom exception class / discriminator enum for a minor fix (YAGNI / KISS).** Two already-distinct exception **types** carry the semantic difference for free: `ValueError` = "I don't know this format", `RuntimeError` = "I know it but can't load it because a dependency is missing". An enum or subclass adds a public-API surface and migration burden for zero caller benefit. (Contrast: `exception-discriminator-enums-state-machine-pola` is for when the *same* exception type is raised from multiple states with different recovery strategies — that is NOT this situation.)

4. **TOP RISK — grep for callers that catch the OLD exception type.** Changing the missing-PyYAML path from `ValueError` to `RuntimeError` is a **public-contract change**. Any existing `except ValueError:` around `load_config()` that relied on the YAML-missing case now leaks a `RuntimeError`. The plan MUST grep `load_config` callers and `except ValueError` before committing to the change. The #1510 plan did NOT do this — flag it as the single most important reviewer check.

5. **Verify the case-preservation claim against the existing test.** The plan lowercases `suffix` for *comparisons* but the final `ValueError` message interpolates the **original-case** `config_path.suffix`. Confirm this matches `test_load_unsupported_format_raises` (or equivalent) so a `.YAML`/`.Yml` input still reports its original casing in the error.

6. **Confirm the availability flag is read at call time, then patch the right target.** The new test relies on `monkeypatch.setattr("hephaestus.config.utils.YAML_AVAILABLE", False)`. This only works if `load_config` reads the **module-level** flag inside the function body at call time, not a value captured into a local or an import-bound name in another module. Grep the flag's read site before trusting the patch.

7. **Treat the monkeypatched branch as vacuous-until-proven.** PyYAML is installed in every normal env, so the missing-PyYAML branch is *only* reachable via the patch. A wrong patch target makes the new test pass without ever entering the branch (the real code path is never exercised). Assert on the **exact** error message/type AND, if feasible, assert the branch was taken (e.g. the loader function was not called). There is no real-absence integration coverage, so the unit test is the only guard — make it strict.

8. **Emit only the FINAL form of any test in the plan.** Do not ship a broken-then-corrected draft (see Failed Attempts). A reviewer may copy the wrong version.

## Verified Workflow

_Not applicable._ This skill was captured from a planning session and is `unverified`: the one-line fix and its tests were reasoned about but never executed and no CI ran, so there is no verified workflow. The actionable, hypothesis-level methodology lives under **Proposed Workflow** above and must be treated as unvalidated until CI confirms it. (This placeholder section exists only because `scripts/validate_plugins.py` requires the literal `## Verified Workflow` heading; it intentionally makes no verification claim.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Reached for a custom exception class / discriminator enum to distinguish "unsupported format" from "PyYAML missing". | Two already-distinct exception **types** (`ValueError` vs `RuntimeError`) carry the semantic difference for free; an enum/subclass adds public-API surface and migration burden for a one-line fix — YAGNI/KISS. | A discriminator enum is overkill when separate exception types already encode the distinction. Save enums for same-type-multiple-states recovery (see `exception-discriminator-enums-state-machine-pola`). |
| 2 | Invented a NEW error message for `load_config`'s missing-PyYAML path. | A caller (or test) that branches on the message behaves differently depending on which entry point it hit — defeats the whole point of the consistency fix. | Reuse the sibling's existing message verbatim; do not paraphrase. |
| 3 | Left the collapsed condition `if suffix in {".yaml",".yml"} and YAML_AVAILABLE:` and just changed the trailing `ValueError`. | The missing-dependency case still falls through to the catch-all; you cannot raise the right error without splitting format-detection from availability. | Split the boolean: detect format FIRST, then check dependency inside the branch. |
| 4 | Changed `ValueError` -> `RuntimeError` without grepping callers. | Any existing `except ValueError:` around `load_config()` for the YAML-missing case silently breaks — a public-contract change shipped unverified. | TOP RISK: grep `load_config` callers and `except ValueError` before changing the raised type. |
| 5 | Shipped a malformed intermediate test in the plan: `with pytest.warns(None) if False else contextlib_nullcontext():` referencing an undefined `contextlib_nullcontext`, then "simplified" it. | A plan that contains a broken-then-corrected code block invites a reviewer to copy the wrong version; `contextlib_nullcontext` is undefined and the `pytest.warns(None)` form is deprecated. | Plans must emit only the FINAL form of code. Reviewers: ignore discarded drafts; check only the final test. |
| 6 | Assumed `monkeypatch.setattr(..., "YAML_AVAILABLE", False)` exercises the branch without confirming the flag is read at call time. | If the function captured the flag into a local or another module import-bound the value, the patch silently no-ops and the test passes vacuously without entering the missing-PyYAML branch. | Verify the flag is read module-level at call time; assert the exact error AND that the real branch was taken; remember the branch is only ever reachable via the patch. |

## Results & Parameters

### The fix shape (copy-paste ready)

```python
def load_config(config_path: Path) -> dict:
    suffix = config_path.suffix.lower()           # lowercase ONLY for comparison
    if suffix == ".json":
        return load_json_config(config_path)
    if suffix in {".yaml", ".yml"}:
        if not YAML_AVAILABLE:
            raise RuntimeError("PyYAML is required for YAML config support")  # verbatim sibling message
        return load_yaml_config(config_path)
    # Original-case suffix preserved in the message:
    raise ValueError(f"Unsupported config format: {config_path.suffix}")
```

### The strict test (final form only — no draft)

```python
def test_load_config_yaml_without_pyyaml_raises_runtimeerror(tmp_path, monkeypatch):
    """Missing PyYAML on a .yaml file raises the same RuntimeError as load_yaml_config()."""
    # Patch the module-level flag the function reads at call time.
    monkeypatch.setattr("hephaestus.config.utils.YAML_AVAILABLE", False)
    cfg = tmp_path / "settings.yaml"
    cfg.write_text("key: value\n")
    with pytest.raises(RuntimeError, match="PyYAML is required for YAML config support"):
        load_config(cfg)


def test_load_unsupported_format_preserves_original_case(tmp_path):
    """Unknown extension still raises ValueError with original-case suffix."""
    cfg = tmp_path / "settings.TOML"
    cfg.write_text("")
    with pytest.raises(ValueError, match=r"Unsupported config format: \.TOML"):
        load_config(cfg)
```

### Reviewer checklist (most-uncertain assumptions, ranked)

| # | Assumption to verify | How to check |
|---|----------------------|--------------|
| 1 (top) | No existing caller catches `ValueError` from `load_config` for the YAML-missing case. | `grep -rn 'load_config' hephaestus/ tests/`; `grep -rn 'except ValueError'`; the plan did NOT do this. |
| 2 | The `ValueError` message still interpolates the **original-case** suffix despite the lowercased `suffix` var. | Diff against `test_load_unsupported_format_raises`. |
| 3 | `monkeypatch.setattr(..., "YAML_AVAILABLE", False)` actually flips the branch. | Confirm `load_config` reads the module-level flag at call time, not a captured local. |
| 4 | The new tests are not vacuous. | PyYAML is always installed; branch reachable only via patch — assert exact message/type and that the loader was not called. |

### Expected outcome

- `load_config("x.yaml")` with PyYAML absent → `RuntimeError("PyYAML is required for YAML config support")` (was: misleading `ValueError`).
- `load_config("x.toml")` → `ValueError("Unsupported config format: .toml")` unchanged.
- Zero new public types; the two existing exception types encode the distinction.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1510 — `load_config()` misleading missing-PyYAML error | Planning session only; plan unverified, not executed in CI. Sibling `load_yaml_config()` already raised the target `RuntimeError`. |
