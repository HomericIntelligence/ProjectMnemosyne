---
name: error-message-consistency-optional-dependency-pola
description: "Resolve a POLA audit finding about a function that silently mishandles input — either the wrong-exception-message arm (collapse format-detection and dependency-availability) or the silently-ignores-invalid-input arm (raise vs document the existing fallback). Use when: (1) two public functions reach the same missing-dependency failure by different code paths and one already raises the right error; (2) a catch-all branch collapses 'unsupported format' and 'dependency missing' into one misleading message; (3) an audit says 'function X silently ignores invalid input — raise an error OR document the fallback' and you must decide which; (4) a sibling/related function already documents and TESTS the silent fallback as intended behavior; (5) you are tempted to add a discriminator enum or custom exception class for a one-line consistency fix; (6) the absent-dependency branch is only ever exercised via monkeypatch and could pass vacuously; (7) flipping an exception type (ValueError→RuntimeError) requires grepping callers for type-specific except handlers and potentially collapsing identical-body arms to a tuple."
category: architecture
date: 2026-06-27
version: "2.2.0"
user-invocable: false
verification: verified-local
history: error-message-consistency-optional-dependency-pola.history
tags:
  - pola
  - error-message
  - optional-dependency
  - exception-consistency
  - exception-type-flip
  - caller-reconciliation
  - silently-ignores-invalid-input
  - raise-vs-document-fallback
  - existing-test-as-contract
  - secondary-silent-fallthrough
  - dry
  - planning
  - yaml
  - monkeypatch
  - vacuous-test
  - yagni
  - kiss
  - runtime-error
  - value-error
---

# Resolving POLA Audit Findings on Functions That Silently Mishandle Input

This skill covers **two arms of the same POLA either/or** that recurs in "silently
mishandles input" audit findings:

- **Arm A — change the exception (verified-local, #1510):** a function reports the
  *wrong cause* for a failure (collapsed format/dependency condition); fix by raising
  the sibling's actionable error verbatim. This is the original skill content.
- **Arm B — document the fallback, do NOT raise (verified-local, #1509):** an audit
  says "function X silently ignores invalid input — raise an error OR document the
  fallback". The correct first move is **not** to default to "raise". Grep ALL callers
  AND grep existing tests first: a sibling may already document AND test the fallback as
  an intended contract, and every caller may pass only valid literals — in which case the
  non-breaking POLA fix is to **document the fallback + add a regression test**, not raise.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-27 |
| **Objective** | (Arm A, #1510) Fix `load_config()` raising a misleading `ValueError("Unsupported config format")` when PyYAML was absent, instead of the actionable `RuntimeError` the sibling `load_yaml_config()` already raises. (Arm B, #1509) Plan the fix for an `[audit][S14 API Design]` finding that `format_output()` (`hephaestus/cli/utils.py:368`) and `format_system_info()` (`hephaestus/system/info.py:237-239`) silently ignore an invalid `format_type` — "raise OR document the fallback". |
| **Outcome** | (Arm A) Implemented and verified locally for #1510 — split condition, reconciled the one `except ValueError` caller, DRY tuple-collapse; 140 tests local, PR #1608. (Arm B) Executed and verified locally for #1509: do NOT raise — `format_system_info`'s text fallback is already documented AND asserted by an existing test (`tests/unit/system/test_info.py:167 test_invalid_format_falls_back_to_text`), so raising would break a tested contract; ~25 callers all pass `"json"`/`"text"` literals; resolution = document the fallback in the under-documented sibling + add regression tests for both the named fallback AND a secondary unnamed one (`"table"` on a dict). 77 tests passing locally; PR pending. |
| **Verification** | **verified-local** for the #1509 (Arm B) content (v2.2.0) — docstring expanded, two regression tests added, all 77 tests passing locally; CI pending. The #1510 (Arm A) content remains **verified-local** (140 tests local; CI pending). |
| **History** | [changelog](./error-message-consistency-optional-dependency-pola.history) — v1.0.0 (2026-06-25) planning only; v2.0.0 (2026-06-25) #1510 verified-local; v2.1.0 (2026-06-27) adds the #1509 "document the fallback, do NOT raise" arm (unverified planning); v2.2.0 (2026-06-27) upgrades Arm B to verified-local after executing the plan. |

## When to Use

- Two public entry points can reach the **same** failure (a missing optional dependency such as PyYAML, `lxml`, `orjson`) by different code paths, and **one already raises the correct, actionable error** while the other collapses the case into a misleading catch-all.
- A single boolean condition collapses two distinct concerns — e.g. `if suffix in {".yaml", ".yml"} and YAML_AVAILABLE:` — so a missing dependency falls through to an "unsupported format" branch and reports the wrong cause.
- You are about to "fix" the inconsistency by inventing a **new exception class** or **discriminator enum** for what is a one-line consistency fix. (Reach for this skill to talk yourself out of that — see also `exception-discriminator-enums-state-machine-pola` for the *opposite* case where an enum IS warranted.)
- The missing-dependency branch is almost never exercised because the dependency is installed in every normal test/CI env, so the only coverage is a `monkeypatch.setattr(..., AVAILABLE_FLAG, False)`.
- You are about to flip an exception type (e.g. `ValueError` → `RuntimeError`) in a public function and need to find all callers that had type-specific `except` handlers to update them.
- After adding a new `except` arm to a caller, you notice multiple arms now have byte-identical bodies and can be collapsed to a tuple for DRY.

### When to Use — Arm B (silently-ignores-invalid-input: raise vs document the fallback)

- An **audit finding** is phrased as an either/or: *"function X silently ignores an invalid input value — raise an error OR document the fallback."* Do **not** default to "raise"; this skill exists to make you grep first.
- A **sibling or related function** already documents the same silent fallback in its docstring **and** has an **existing test** that asserts the fallback as intended behavior. That existing test is decisive evidence the fallback is a tested **contract**, not a bug — so raising would break it. (In #1509: `format_system_info` documented the text fallback at `info.py:237-239` and `tests/unit/system/test_info.py:167 test_invalid_format_falls_back_to_text` asserted it.)
- **Every caller passes only valid string literals** (`"json"`/`"text"`), none passes a runtime variable or relies on rejection. With no caller depending on the function raising, raising adds risk for zero benefit (YAGNI/KISS) → document the fallback to reach parity with the already-documented sibling.
- The change would be **docstring-only + tests-only** (no logic change). Beware: such tests encode *current* behavior rather than driving new behavior, so they can pass **vacuously** — confirm each new test would FAIL if the fallback branch were deleted.
- You suspect a **secondary silent fallthrough the audit did NOT name** in the same function (e.g. `format_output`'s `format_type == "table" and isinstance(data, (list, tuple))` — a `"table"` request on a *dict* silently falls through to text). Document and test that one too.

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

### Arm B — "silently ignores invalid input: raise OR document the fallback" decision procedure (#1509)

> **Verified Locally (v2.2.0):** This arm was executed for issue #1509 — docstring expanded at `hephaestus/cli/utils.py:355-373` and two regression tests added to `tests/unit/cli/test_utils.py:328-356`. All 77 tests passing locally. CI pending.

When the audit phrases the finding as *"function X silently ignores an invalid value — raise an error OR document the fallback"*, run this BEFORE writing any code:

```bash
# 1. Grep EVERY caller. Do callers pass literals, or a runtime variable?
grep -rn "format_output\|format_system_info" hephaestus/ tests/ scripts/
#    In #1509: ~25 call sites, ALL pass "json"/"text" string literals; none passes a
#    variable or relies on the function rejecting bad input. (CAVEAT below.)

# 2. Grep the EXISTING tests. Does a sibling already ASSERT the silent fallback?
grep -rn "falls_back\|invalid_format\|format_type" tests/
#    In #1509: tests/unit/system/test_info.py:167 test_invalid_format_falls_back_to_text
#    explicitly asserts format_system_info() falls back to text on a bogus format_type.
#    An EXISTING passing test on the fallback == the fallback is an INTENTIONAL CONTRACT.

# 3. Read the sibling's docstring. Is the fallback already documented there?
#    In #1509: format_system_info (info.py:237-239) documents the text fallback;
#    format_output (cli/utils.py:368) does NOT — so the gap is documentation parity,
#    not a missing exception.
```

Then **decide raise-vs-document** with this rule:

| Condition (all observed) | Resolution |
|---|---|
| A sibling already **documents AND tests** the fallback as intended, **and** every caller passes a valid literal | **Document the fallback + add a regression test.** Do NOT raise — raising breaks a tested contract for zero caller benefit (YAGNI/KISS). Achieve parity by documenting the under-documented sibling. |
| No documented/tested fallback exists, callers pass runtime values, and a wrong value should fail loudly | Raise (and then this is Arm A — reuse a sibling's actionable message, grep callers for `except`). |

Hunt for **secondary silent fallthroughs the audit did not name.** In #1509 `format_output` has a second one: `format_type == "table" and isinstance(data, (list, tuple))` means a `"table"` request on a **dict** silently falls through to text. Document and test that too — the audit only named one.

**Make the docstring-only/tests-only change non-vacuous.** Because there is no logic change, a new test could pass whether or not the fallback exists. For each new test, confirm it would **FAIL if the fallback branch were removed** (e.g. mentally delete the `else: return text` arm and check the assertion breaks). State this explicitly so the reviewer can verify it.

**Top residual risks to hand the reviewer (the most uncertain assumptions):**

1. The "every one of ~25 callers passes a valid literal" claim came from a single `grep` over `hephaestus/ tests/ scripts/`. The grep showed visible call sites use literals; it did **not** prove no caller builds `format_type` from a runtime **variable** (argparse `choices`, a config value). A dynamic caller is the residual risk if anyone later switches to raising.
2. The plan documents **different** contracts for the two siblings: `format_output`'s match is **case-sensitive** (`cli/utils.py:366` `format_type == "json"` → `"JSON"` falls back to text) while `format_system_info` is **case-insensitive** (`info.py:245` `format_type.lower() == "json"`). The new test `for bogus in (..., "JSON")` depends on `format_output` staying case-sensitive. Reviewer must confirm the asymmetry is **real in the code and intended**, not accidentally "fixed" to match.
3. The change is docstring-only + tests-only, so the new tests encode current behavior rather than driving it (not true RED-GREEN). Reviewer must confirm each new test would FAIL if the fallback branch were removed (i.e. it is not vacuous).

## Verified Workflow

This section documents the implementation as actually executed for issue #1510 / PR #1608 (verified-local: 140 tests passing).

### Step 1 — Split the collapsed branch

```python
# BEFORE — collapsed: missing PyYAML falls through to ValueError("Unsupported config format")
with open(config_path) as f:
    if config_path.suffix.lower() in [".yml", ".yaml"] and YAML_AVAILABLE:
        return cast(dict[str, Any], yaml.safe_load(f) or {})
    elif config_path.suffix.lower() == ".json":
        return cast(dict[str, Any], json.load(f))
    else:
        raise ValueError(f"Unsupported config format: {config_path.suffix}")

# AFTER — split: detect format first, check availability inside the branch
suffix = config_path.suffix.lower()
with open(config_path) as f:
    if suffix in (".yml", ".yaml"):
        if not YAML_AVAILABLE:
            raise RuntimeError("PyYAML is required for YAML config support")
        return cast(dict[str, Any], yaml.safe_load(f) or {})
    elif suffix == ".json":
        return cast(dict[str, Any], json.load(f))
    else:
        raise ValueError(f"Unsupported config format: {config_path.suffix}")
```

Key decisions:
- Extract `suffix = config_path.suffix.lower()` to avoid computing it twice.
- Keep `config_path.suffix` (original case) in the `ValueError` message — existing tests assert the original-case extension.
- The `RuntimeError` message is verbatim from `load_yaml_config()` — cross-entry-point consistency.

### Step 2 — Grep callers for type-specific except handlers

```bash
# Find all call sites (before the type flip)
grep -rn "load_config(" hephaestus/ tests/ | grep -v "def load_config\|#"
# Find all type-specific except handlers around those call sites
grep -n "except ValueError\|except FileNotFoundError\|except RuntimeError" hephaestus/github/fleet_sync.py
```

In this case `fleet_sync.py:_load_fleet_config` had:

```python
# BEFORE — two separate arms, no RuntimeError arm
except FileNotFoundError as e:
    raise RuntimeError(f"Failed to load fleet config from {config_path}: {e}") from e
except ValueError as e:
    raise RuntimeError(f"Failed to load fleet config from {config_path}: {e}") from e
```

### Step 3 — Add the missing arm, then collapse identical-body arms to a tuple (DRY)

```python
# AFTER — add RuntimeError arm, then observe all three bodies are identical → collapse
except (FileNotFoundError, ValueError, RuntimeError) as e:
    raise RuntimeError(f"Failed to load fleet config from {config_path}: {e}") from e
```

Do this in ONE commit: adding the new arm and collapsing to a tuple is a single atomic DRY fix.

### Step 4 — Update the docstring Raises: section

```python
def load_config(config_path: Path, ...) -> dict[str, Any]:
    """...
    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the file extension is not a supported format.
        RuntimeError: If the file is YAML but PyYAML is not installed.
    """
```

### Step 5 — Add tests for both the fix and regression

```python
# New test: missing-dependency path raises RuntimeError (not ValueError)
def test_load_yaml_without_pyyaml_raises_runtime_error(self, tmp_path, monkeypatch):
    monkeypatch.setattr("hephaestus.config.utils.YAML_AVAILABLE", False)
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("key: value\n")
    with pytest.raises(RuntimeError, match="PyYAML is required for YAML config support"):
        load_config(yaml_file)

# New test: .yml variant also raises RuntimeError (not just .yaml)
def test_load_yml_without_pyyaml_raises_runtime_error(self, tmp_path, monkeypatch):
    monkeypatch.setattr("hephaestus.config.utils.YAML_AVAILABLE", False)
    yml_file = tmp_path / "config.yml"
    yml_file.write_text("key: value\n")
    with pytest.raises(RuntimeError, match="PyYAML is required for YAML config support"):
        load_config(yml_file)

# Regression: unsupported format still raises ValueError
def test_load_unsupported_format_raises(self, tmp_path):
    toml_file = tmp_path / "config.toml"
    toml_file.write_text("[section]\nkey = 'value'\n")
    with pytest.raises(ValueError, match="Unsupported config format"):
        load_config(toml_file)

# Caller test: context wrapper preserved for YAML-missing case
def test_load_fleet_config_yaml_missing_dep_raises_with_context(self, tmp_path, monkeypatch):
    monkeypatch.setattr("hephaestus.config.utils.YAML_AVAILABLE", False)
    fleet_file = tmp_path / "fleet.yml"
    fleet_file.write_text("repos: []\n")
    with pytest.raises(RuntimeError, match=r"Failed to load fleet config from .*fleet\.yml"):
        _load_fleet_config(fleet_file)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Reached for a custom exception class / discriminator enum to distinguish "unsupported format" from "PyYAML missing". | Two already-distinct exception **types** (`ValueError` vs `RuntimeError`) carry the semantic difference for free; an enum/subclass adds public-API surface and migration burden for a one-line fix — YAGNI/KISS. | A discriminator enum is overkill when separate exception types already encode the distinction. Save enums for same-type-multiple-states recovery (see `exception-discriminator-enums-state-machine-pola`). |
| 2 | Invented a NEW error message for `load_config`'s missing-PyYAML path. | A caller (or test) that branches on the message behaves differently depending on which entry point it hit — defeats the whole point of the consistency fix. | Reuse the sibling's existing message verbatim; do not paraphrase. |
| 3 | Left the collapsed condition `if suffix in {".yaml",".yml"} and YAML_AVAILABLE:` and just changed the trailing `ValueError`. | The missing-dependency case still falls through to the catch-all; you cannot raise the right error without splitting format-detection from availability. | Split the boolean: detect format FIRST, then check dependency inside the branch. |
| 4 | Changed `ValueError` -> `RuntimeError` without grepping callers. | Any existing `except ValueError:` around `load_config()` for the YAML-missing case silently breaks — a public-contract change shipped unverified. | TOP RISK: grep `load_config` callers and `except ValueError` before changing the raised type. |
| 5 | Shipped a malformed intermediate test in the plan: `with pytest.warns(None) if False else contextlib_nullcontext():` referencing an undefined `contextlib_nullcontext`, then "simplified" it. | A plan that contains a broken-then-corrected code block invites a reviewer to copy the wrong version; `contextlib_nullcontext` is undefined and the `pytest.warns(None)` form is deprecated. | Plans must emit only the FINAL form of code. Reviewers: ignore discarded drafts; check only the final test. |
| 6 | Assumed `monkeypatch.setattr(..., "YAML_AVAILABLE", False)` exercises the branch without confirming the flag is read at call time. | If the function captured the flag into a local or another module import-bound the value, the patch silently no-ops and the test passes vacuously without entering the missing-PyYAML branch. | Verify the flag is read module-level at call time; assert the exact error AND that the real branch was taken; remember the branch is only ever reachable via the patch. |
| 7 | Added `except RuntimeError` as a third separate arm alongside existing `FileNotFoundError` and `ValueError` arms in the caller. | Technically correct but left three arms with byte-identical bodies — DRY violation flagged in review. | Collapse all three to a tuple in the same commit as adding the new arm. |
| 8 | Used `except Exception` to catch all load errors in the caller. | Too broad — catches programmer errors unrelated to `load_config`. | Only catch the specific exception types that `load_config` can actually raise; use the tuple form. |
| 9 (Arm B, #1509) | On a "silently ignores invalid input — raise OR document" audit finding, **defaulted to "raise `ValueError`"** without grepping callers or existing tests. | A sibling (`format_system_info`) already documented the silent text fallback AND an existing test (`test_info.py:167 test_invalid_format_falls_back_to_text`) asserted it as intended — raising would have **broken a documented, tested contract**; and all ~25 callers pass valid literals, so rejection benefits no one. | When the audit offers "raise OR document", do NOT pick raise by default. Grep ALL callers AND existing tests first; an existing test on the fallback is decisive proof it is an intentional contract → document it, don't raise. |
| 10 (Arm B, #1509) | Fixed only the one silent fallthrough the audit **named**, missing a second one in the same function. | `format_output` has a secondary silent fallthrough the audit did not call out: `format_type == "table" and isinstance(data, (list, tuple))` means a `"table"` request on a **dict** silently falls through to text — left undocumented and untested. | Audit findings name the symptom they noticed, not every instance. Scan the whole function for SECONDARY silent fallthroughs and document/test those too. |
| 11 (Arm B, #1509) | Shipped docstring-only + tests-only changes whose new tests **pass vacuously** (they assert current behavior with no logic change, so they would still pass if the fallback branch were deleted). | A test that does not fail when the behavior is removed is not protecting anything — it is not RED-GREEN; it can give false confidence that the contract is guarded. | For a no-logic-change documentation fix, prove each new test would FAIL if the fallback branch were removed; also verify case-sensitivity asymmetries (e.g. `format_output` case-sensitive vs `format_system_info` `.lower()`) are real and intended, not accidentally normalized. |

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

### Exception contract after fix

| Input | `YAML_AVAILABLE` | Exception Type | Message |
|-------|-----------------|----------------|---------|
| `.yaml` / `.yml` | `True` | — (success) | — |
| `.yaml` / `.yml` | `False` | `RuntimeError` | `"PyYAML is required for YAML config support"` |
| `.json` | any | — (success) | — |
| `.toml` / other | any | `ValueError` | `"Unsupported config format: .toml"` (original-case suffix) |
| missing file | any | `FileNotFoundError` | `"Configuration file not found: ..."` |

### Caller tuple pattern (verified DRY collapse)

```python
# Any call site that had separate arms for each exception type
# and all arms had the same body → collapse to a tuple
except (FileNotFoundError, ValueError, RuntimeError) as e:
    raise RuntimeError(f"Failed to load config from {path}: {e}") from e
```

### Reviewer checklist (most-uncertain assumptions, ranked)

| # | Assumption to verify | How to check |
|---|----------------------|--------------|
| 1 (top) | No existing caller catches `ValueError` from `load_config` for the YAML-missing case. | `grep -rn 'load_config' hephaestus/ tests/`; `grep -rn 'except ValueError'`; the plan did NOT do this. |
| 2 | The `ValueError` message still interpolates the **original-case** suffix despite the lowercased `suffix` var. | Diff against `test_load_unsupported_format_raises`. |
| 3 | `monkeypatch.setattr(..., "YAML_AVAILABLE", False)` actually flips the branch. | Confirm `load_config` reads the module-level flag at call time, not a captured local. |
| 4 | The new tests are not vacuous. | PyYAML is always installed; branch reachable only via patch — assert exact message/type and that the loader was not called. |

### Outcome (verified locally)

- `load_config("x.yaml")` with PyYAML absent → `RuntimeError("PyYAML is required for YAML config support")` (was: misleading `ValueError`).
- `load_config("x.toml")` → `ValueError("Unsupported config format: .toml")` unchanged.
- Zero new public types; the two existing exception types encode the distinction.
- One caller updated: `fleet_sync.py:_load_fleet_config` — three separate `except` arms collapsed to a tuple.

### Arm B — #1509 fallback-contract reference (verified locally, v2.2.0)

> **Verified Locally (v2.2.0):** The #1509 plan was executed — docstring expanded at `hephaestus/cli/utils.py:355-373` and two regression tests added at `tests/unit/cli/test_utils.py:328-356`. All 77 tests passing locally. CI pending. The tables below describe the documented and tested contract.

The two siblings' `format_type` contracts (to be documented; NOT changed):

| Function | Location | Invalid `format_type` behavior | Case sensitivity |
|----------|----------|--------------------------------|------------------|
| `format_system_info` | `hephaestus/system/info.py:237-239`, `:245` | Already documented + tested (`test_info.py:167`): falls back to text | **case-insensitive** (`format_type.lower() == "json"`) |
| `format_output` (primary) | `hephaestus/cli/utils.py:366,368` | **Under-documented** silent fallback to text on unknown `format_type` | **case-sensitive** (`format_type == "json"` → `"JSON"` falls back to text) |
| `format_output` (secondary, audit did NOT name) | `hephaestus/cli/utils.py:368` | `"table"` requested on a **dict** (not list/tuple) silently falls through to text | n/a |

Planned resolution (parity, no logic change): document both `format_output` fallbacks in its docstring to match the already-documented sibling, and add regression tests — one over bogus values including `"JSON"` (depends on `format_output` staying case-sensitive), and one asserting `"table"` on a dict yields text. Each test must be confirmed to FAIL if its fallback branch were removed (non-vacuous).

Residual reviewer risks for #1509 (ranked): (1) the "all ~25 callers pass valid literals" claim came from a single literal-scan grep — it does NOT prove no caller builds `format_type` from a runtime variable; (2) confirm the case-sensitivity asymmetry between the two siblings is real and intended, not accidentally normalized; (3) confirm the docstring-only/tests-only new tests are non-vacuous.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1510 / PR #1608 — `load_config()` misleading missing-PyYAML error | v1.0.0: Planning session only; plan unverified, not executed in CI. v2.0.0: Implementation complete; 140 tests passing locally; CI pending. Sibling `load_yaml_config()` already raised the target `RuntimeError`; caller `fleet_sync.py:_load_fleet_config` had `except ValueError` updated to `except (FileNotFoundError, ValueError, RuntimeError)` tuple. |
| ProjectHephaestus | Issue #1509 — `format_output()` / `format_system_info()` silently ignore invalid `format_type` (POLA, S14 API Design) | v2.1.0 (unverified planning): plan produced, NOT executed, no code run, no CI. Decision = document the existing text fallback + add regression tests, do NOT raise — the fallback is already documented in `format_system_info` (`info.py:237-239`) and asserted by `tests/unit/system/test_info.py:167 test_invalid_format_falls_back_to_text`, and all ~25 callers pass `"json"`/`"text"` literals. Also covers a secondary unnamed fallthrough: `"table"` on a dict in `format_output` (`cli/utils.py:368`). |
| ProjectHephaestus | Issue #1509 / PR pending — `format_output()` document-the-fallback arm executed | v2.2.0: Arm B verified-local; 77 tests passing locally. Docstring expanded at `hephaestus/cli/utils.py:355-373`; two regression tests added at `tests/unit/cli/test_utils.py:328-356` (`test_invalid_format_falls_back_to_text` and `test_table_format_on_dict_falls_back_to_text`). No logic change. CI pending. |
