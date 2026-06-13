---
name: coverage-omit-orchestration-pure-function-testing
description: "How to add behavioral test coverage for pure-function helpers in coverage-omitted orchestration modules (live CLI/TTY boundary). Use when: (1) modules are omitted from --cov due to live-session dependencies, (2) the omit list is frozen but pure helpers inside omitted modules have no behavioral tests, (3) a coverage audit flags untested orchestration logic."
category: testing
date: 2026-06-13
version: "1.1.0"
user-invocable: false
verification: unverified
tags: []
history: coverage-omit-orchestration-pure-function-testing.history
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
# Step 0: Verify actual filenames before adding any coverage.toml floor
ls hephaestus/automation/ | grep -i arming
grep -rn "class ArmingState" hephaestus/   # → arming_state.py:32

# Step 1: Run coverage to get actual XML and confirm path format
pixi run pytest tests/unit --cov=hephaestus --cov-report=xml:build/coverage.xml -q

# Step 2: Confirm path format from actual XML (no hephaestus/ prefix)
python3 -c "
import defusedxml.ElementTree as ET
tree = ET.parse('build/coverage.xml')
for c in list(tree.findall('.//class'))[:5]:
    print(c.get('filename'))
"
# Expected output: automation/models.py (NOT hephaestus/automation/models.py)

# Step 3: Check actual branch-rate values for target modules before setting floors
python3 -c "
import defusedxml.ElementTree as ET
tree = ET.parse('build/coverage.xml')
targets = {'automation/models.py', 'automation/dependency_resolver.py', 'automation/arming_state.py'}
for c in tree.findall('.//class'):
    if c.get('filename') in targets:
        print(c.get('filename'), 'line:', c.get('line-rate'), 'branch:', c.get('branch-rate'))
"

# Step 4: Set floors conservatively (70%) — CI enforcer uses branch_rate if > 0
# coverage.toml format (verified working):
# [coverage.modules]
# "automation/models.py" = { minimum = 70 }

# Step 5: Verify enforcement by running the actual CLI (not hand-rolled XML parse)
pip install -e ".[xml]"
hephaestus-check-coverage --coverage-file build/coverage.xml --config coverage.toml
# Must exit 0 before committing floors
```

### Detailed Steps

1. **Verify actual filenames before touching coverage.toml** — `ls hephaestus/automation/` and grep for the class name. Modules get renamed (e.g., `arming_state_store.py` → `arming_state.py` in commit cb33b509); any path in `[coverage.modules]` that is missing from the XML causes a hard CI fail (coverage.py:250-257).

2. **Read actual function signatures** for every function you plan to test — do NOT assume from name alone. Key risk areas:
   - `ci_driver._pr_is_failing`: checks `isDraft` first (line 85), then `mergeStateStatus == "BLOCKED"` (line 87), then rollup conclusions (line 89-90)
   - `loop_runner._parse_repo_list`: empty string returns `[]` (not raises) per docstring at loop_runner.py:126
   - `loop_runner._validate_phases`: raises `SystemExit`; valid phases are `{"plan", "implement", "drive-green"}` (`ALL_SELECTABLE` at loop_runner.py:108)
   - `github_api._assert_body_has_closes`: raises `ValueError` exactly (github_api.py:541)
   - `audit_reviewer._parse_coordinator_results`: returns `[]` on empty/whitespace (docstring at audit_reviewer.py:40-43); skips malformed JSON blocks without raising (audit_reviewer.py:44-48)

3. **Create `tests/unit/automation/test_orchestration_pure_functions.py`** with one class per module, importing each pure helper directly:
   ```python
   from hephaestus.automation.loop_runner import _parse_repo_list
   ```
   Tests run fine even though the source is in the omit list — they exercise the logic and prove behavioral correctness; they just do not add to the coverage denominator.

4. **Extend `coverage.toml`** with per-module floors for non-omitted automation modules. Set floors conservatively against branch-rate (CI enforcer uses `branch_rate if branch_rate > 0 else line_rate` — coverage.py:262). Verify via `hephaestus-check-coverage` CLI, not a hand-rolled XML parser.

5. **Fix any docstring count discrepancies** in `tests/integration/test_orchestration_smoke.py` if the module comment says "4 console scripts" but 5 are listed.

## Verified Workflow

> This workflow is **unverified** — it has not been run end-to-end through CI. The steps below are the intended approach based on planning analysis of ProjectHephaestus issue #1197 (R1 iteration). Update this section to "verified" once the implementation passes CI.

1. Verify filenames: `ls hephaestus/automation/` + `grep -rn "class <TargetClass>" hephaestus/` — confirm the exact `.py` filename before adding any floor.
2. Read actual function signatures for each pure helper (grep `^def _` in the target module; read the docstring and body, not just the name).
3. Create `tests/unit/automation/test_orchestration_pure_functions.py` with one class per omitted module; import helpers directly.
4. Run the new test file in isolation (`pixi run pytest tests/unit/automation/test_orchestration_pure_functions.py -v`) — confirm all pass.
5. Confirm the omit allowlist test still passes (`pixi run pytest tests/unit/validation/test_omit_allowlist.py -v`).
6. Generate a Cobertura XML report (`pixi run pytest tests/unit --cov=hephaestus --cov-report=xml:build/coverage.xml`) and inspect `filename` attributes to confirm path format is `automation/<name>.py` (no `hephaestus/` prefix).
7. Check branch-rate values for target modules from the XML before setting floors (CI enforcer uses branch-rate preferentially).
8. Add per-module floors to `coverage.toml`; verify via `hephaestus-check-coverage --coverage-file build/coverage.xml --config coverage.toml` (exit 0). Set one test floor to 99% on a known-below-99% module → confirm exit 1 → restore real floor.
9. Push and confirm CI green.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed `_pr_is_failing` dict shape | Wrote tests using `{"statusCheckRollup": [...]}` without reading source | Dict key or nesting may differ — tests would fail immediately | Always read the function body, not just the name, before writing assertions |
| Assumed `_parse_repo_list("")` raises | Wrote `pytest.raises((ValueError, SystemExit))` for empty input | Docstring at loop_runner.py:126 states "Empty input returns an empty list" — function returns `[]` not raise | Read the function docstring/body before writing edge-case assertions; empty-string behavior is often intentionally lenient |
| Used full path in coverage.toml floors | `"hephaestus/automation/models.py" = { minimum = 80 }` | Cobertura XML uses relative paths without `hephaestus/` prefix; mismatch silently skips the floor check | Verify path format against actual XML output before committing floors |
| Included `_evaluate_run_result` in approach but not tests | Identified it as pure at ci_driver.py:3224 but omitted from test class | Complex signature requires reading before stubbing; silently dropped | Either test it or explicitly note it as deferred in the plan |
| Used `arming_state_store.py` as module path in coverage.toml | Prior plan added floor for `"automation/arming_state_store.py"` | File was renamed to `arming_state.py` by commit cb33b509 (extract ArmingStateStore from CIDriver) — causes hard CI fail (coverage.py:250-257: missing module fails loud) | Always verify filename against actual `ls hephaestus/automation/` before adding a floor; grep for class name: `grep -rn "class ArmingState" hephaestus/` |
| Verified floors against line-rate in verification step | Plan's Criterion 5 used `xml.etree.ElementTree` to read line-rate from XML | CI enforcer (`_required.yml:592`) uses `hephaestus-check-coverage` which applies `branch_rate if branch_rate > 0 else line_rate` (coverage.py:262) — floor set vs line-rate could silently pass while branch-rate fails | Always verify floor enforcement by running the actual `hephaestus-check-coverage` CLI, not a hand-rolled XML parser |
| Assumed `_parse_repo_list("")` raises on empty | Test used `pytest.raises((ValueError, SystemExit))` for empty string | Docstring at loop_runner.py:126 states "Empty input returns an empty list" — function returns `[]` not raise | Read the function docstring/body before writing edge-case assertions; empty-string behavior is often intentionally lenient |
| Used shotgun exception tuples `raises((ValueError, SystemExit, AssertionError))` | Test accepted any of three unrelated exception types | Accepting three unrelated exception types is not a behavior contract — it's a guess wrapper (POLA violation) | Read the source to confirm the exact exception type; each `raises()` call must specify exactly one type |

## Results & Parameters

**Confirmed path format from live coverage run:**
- XML `filename` attribute format: `automation/models.py` (no `hephaestus/` prefix) — verified via `pixi run pytest tests/unit/automation/test_models.py --cov=hephaestus --cov-report=xml:build/coverage_sample.xml`

**Coverage floor safety invariants (verified R1):**

1. **Path format**: `automation/<name>.py` — no `hephaestus/` prefix (confirmed from live XML)
2. **Missing module = hard CI fail**: `coverage.py:250-257` — any path in `[coverage.modules]` missing from XML fails loudly; verify XML presence before committing a floor
3. **Metric used**: `branch_rate if branch_rate > 0 else line_rate` (`coverage.py:262`) — floor values must be safe vs branch-rate, which is typically lower than line-rate
4. **CI invocation**: `hephaestus-check-coverage --coverage-file coverage.xml --config coverage.toml` (`_required.yml:592`) — always verify via this CLI, not custom XML parsing
5. **Verify floor enforcement**: Set test floor to 99% on a known-uncovered module → confirm exit 1 → restore real floor

**Coverage.toml per-module floor format (verified path prefix):**
```toml
[coverage.modules]
"automation/models.py" = { minimum = 70 }
"automation/dependency_resolver.py" = { minimum = 70 }
"automation/arming_state.py" = { minimum = 70 }   # not arming_state_store.py
```

**Confirmed function behaviors (R1, verified against source):**

| Function | Module | Behavior | Source Location |
|----------|--------|----------|-----------------|
| `_validate_phases` | loop_runner.py | Raises `SystemExit`; valid phases: `{"plan", "implement", "drive-green"}` | loop_runner.py:537; `ALL_SELECTABLE` at loop_runner.py:108 |
| `_assert_body_has_closes` | github_api.py | Raises `ValueError` exactly (not AssertionError or SystemExit) | github_api.py:541 |
| `_parse_repo_list("")` | loop_runner.py | Returns `[]` not raises | docstring at loop_runner.py:126 |
| `_parse_coordinator_results` | audit_reviewer.py | Returns `[]` on empty/whitespace; skips malformed JSON without raising | audit_reviewer.py:40-48 |
| `_pr_is_failing` | ci_driver.py | Checks `isDraft` first (line 85), then `mergeStateStatus == "BLOCKED"` (line 87), then rollup conclusions (line 89-90) | ci_driver.py:85-90 |

**Omit list is frozen by `test_omit_allowlist.py` — any addition fails CI:**
- Do NOT add new modules to the omit list without updating the allowlist test
- Tests for omitted modules can be written and run; they just don't count toward the denominator

**Recommended test structure for omitted-module pure helpers:**
```python
class TestLoopRunnerPureFunctions:
    def test_parse_repo_list_comma_separated(self) -> None:
        from hephaestus.automation.loop_runner import _parse_repo_list
        assert _parse_repo_list("a,b,c") == ["a", "b", "c"]

    def test_parse_repo_list_empty_returns_empty_list(self) -> None:
        from hephaestus.automation.loop_runner import _parse_repo_list
        # Empty string returns [] not raises (confirmed loop_runner.py:126)
        assert _parse_repo_list("") == []

    def test_validate_phases_invalid_raises_system_exit(self) -> None:
        from hephaestus.automation.loop_runner import _validate_phases
        with pytest.raises(SystemExit):  # NOT ValueError or AssertionError
            _validate_phases(["nonexistent"])
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1197 planning R0 (2026-06-13) | Plan written; implementation pending |
| ProjectHephaestus | Issue #1197 planning R1 (2026-06-13) | Second planning iteration; verified filenames, metrics, and function behaviors against source files |
