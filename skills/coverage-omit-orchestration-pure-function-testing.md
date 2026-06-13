---
name: coverage-omit-orchestration-pure-function-testing
description: "How to add behavioral test coverage for pure-function helpers in coverage-omitted orchestration modules (live CLI/TTY boundary). Use when: (1) modules are omitted from --cov due to live-session dependencies, (2) the omit list is frozen but pure helpers inside omitted modules have no behavioral tests, (3) a coverage audit flags untested orchestration logic."
category: testing
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Coverage-Omit Orchestration Pure-Function Testing

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Add behavioral test coverage for pure-function helpers inside coverage-omitted orchestration modules without removing modules from the omit list |
| **Outcome** | Plan written (not yet implemented) |
| **Verification** | unverified |

## When to Use

- Orchestration modules are omitted from `--cov` due to live `claude`/`gh` CLI or real TTY dependencies
- A coverage audit flags that the 80% gate measures a reduced denominator
- Pure helpers inside omitted modules (parsers, formatters, predicates) have no behavioral tests
- You want to tighten the coverage gate without removing the omit entries

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Read the actual function signatures BEFORE writing tests
# (function names and dict shapes must be verified against source, not assumed)
grep -n "^def _" hephaestus/automation/ci_driver.py | head -20
grep -n "^def _" hephaestus/automation/loop_runner.py | head -30

# 2. Run the new tests in isolation first
pixi run pytest tests/unit/automation/test_orchestration_pure_functions.py -v

# 3. Verify the omit list guard still passes (nothing was added to omit list)
pixi run pytest tests/unit/validation/test_omit_allowlist.py -v

# 4. Verify coverage.toml path format matches Cobertura XML
pixi run pytest tests/unit --cov=hephaestus --cov-report=xml:build/coverage.xml
python3 -c "
import defusedxml.ElementTree as ET
tree = ET.parse('build/coverage.xml')
for c in list(tree.findall('.//class'))[:5]:
    print(c.get('filename'))
"
# If output is 'hephaestus/automation/models.py' → use that full path in coverage.toml
# If output is 'automation/models.py' → use the short form
```

### Detailed Steps

1. **Read actual function signatures** for every function you plan to test — do NOT assume from name alone. Key risk areas:
   - `ci_driver._pr_is_failing`: verify the input dict key (`statusCheckRollup` vs another key)
   - `loop_runner._parse_repo_list`: verify empty-string behavior (raises vs returns [])
   - `loop_runner._validate_phases`: verify the valid phase set (what strings are accepted)
   - `github_api._parse_issue_number`: verify input format (URL? numeric string? both?)

2. **Create `tests/unit/automation/test_orchestration_pure_functions.py`** with one class per module, importing each pure helper directly:
   ```python
   from hephaestus.automation.loop_runner import _parse_repo_list
   ```
   Tests run fine even though the source is in the omit list — they exercise the logic and prove behavioral correctness; they just do not add to the coverage denominator.

3. **Extend `coverage.toml`** with per-module floors for non-omitted automation modules. Verify the path format matches the Cobertura XML `filename` attribute before committing floors (mismatch silently skips enforcement).

4. **Fix any docstring count discrepancies** in `tests/integration/test_orchestration_smoke.py` if the module comment says "4 console scripts" but 5 are listed.

## Verified Workflow

> This workflow is **unverified** — it has not been run end-to-end through CI. The steps below are the intended approach based on planning analysis of ProjectHephaestus issue #1197. Update this section to "verified" once the implementation passes CI.

1. Read actual function signatures for each pure helper (grep `^def _` in the target module).
2. Create `tests/unit/automation/test_orchestration_pure_functions.py` with one class per omitted module; import helpers directly.
3. Run the new test file in isolation (`pixi run pytest tests/unit/automation/test_orchestration_pure_functions.py -v`) — confirm all pass.
4. Confirm the omit allowlist test still passes (`pixi run pytest tests/unit/validation/test_omit_allowlist.py -v`).
5. Generate a Cobertura XML report and inspect the `filename` attribute to determine the correct path prefix for `coverage.toml` floors.
6. Add per-module floors to `coverage.toml` using the verified path format; set one floor to 99% on a known-below-99% module, confirm exit 1, then restore.
7. Push and confirm CI green.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed `_pr_is_failing` dict shape | Wrote tests using `{"statusCheckRollup": [...]}` without reading source | Dict key or nesting may differ — tests would fail immediately | Always read the function body, not just the name, before writing assertions |
| Assumed `_parse_repo_list("")` raises | Wrote `pytest.raises((ValueError, SystemExit))` for empty input | Argparse-type validators often return `[]` on empty, not raise | Read the function body or run it interactively before asserting exception type |
| Used full path in coverage.toml floors | `"hephaestus/automation/models.py" = { minimum = 80 }` | Cobertura XML may use relative paths; mismatch silently skips the floor check | Verify path format against actual XML output before committing floors |
| Included `_evaluate_run_result` in approach but not tests | Identified it as pure at ci_driver.py:3224 but omitted from test class | Complex signature requires reading before stubbing; silently dropped | Either test it or explicitly note it as deferred in the plan |

## Results & Parameters

**Coverage.toml per-module floor format (verify path prefix first):**
```toml
[coverage.modules]
"automation/models.py" = { minimum = 80 }          # short form if XML uses this
"hephaestus/automation/models.py" = { minimum = 80 } # full form if XML uses this
```

**Verification that floor enforcement works:**
```bash
# Set a floor to 99% on a module you know is below 99% → confirm exit 1
# Then restore the real floor
```

**Omit list is frozen by `test_omit_allowlist.py` — any addition fails CI:**
- Do NOT add new modules to the omit list without updating the allowlist test
- Tests for omitted modules can be written and run; they just don't count toward the denominator

**Recommended test structure for omitted-module pure helpers:**
```python
class TestLoopRunnerPureFunctions:
    def test_parse_repo_list_comma_separated(self) -> None:
        from hephaestus.automation.loop_runner import _parse_repo_list
        assert _parse_repo_list("a,b,c") == ["a", "b", "c"]
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1197 planning (2026-06-13) | Plan written; implementation pending |
