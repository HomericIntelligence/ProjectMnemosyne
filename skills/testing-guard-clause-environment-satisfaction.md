---
name: testing-guard-clause-environment-satisfaction
description: "When writing unit tests that mock internal functions, the test environment must satisfy ALL prerequisite guards that execute BEFORE the mock is reached. Guard clauses in entry points check prerequisites (env vars, files, config) before internal logic executes. If the test only satisfies partial prerequisites, the guard will exit early, preventing the mocked code from being reached. This pattern ensures mocked tests reach their target code instead of failing at guard-time."
category: testing
date: 2026-06-27
version: "1.0.0"
verification: verified-ci
tags:
  - unit-tests
  - test-environment
  - guard-clauses
  - monkeypatch
  - entry-point-validation
  - mocking
  - pytest
---

# Testing: Guard Clause Environment Satisfaction

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-27 |
| **Objective** | Ensure unit tests mocking internal functions satisfy ALL prerequisite guards before those mocks are reached |
| **Outcome** | Success — fixed test_reports_pi_runtime_contract_error by adding missing HEPH_PI_PROVIDER environment variable; all 4 related tests now mirror consistent guard-satisfaction setup |
| **Verification** | verified-ci (CI passed after fix) |

## When to Use

Apply this pattern when:

- Tests fail with unexpected return codes when mocking internal functions
- A test expects RuntimeError (code 1) but gets exit code 2 (guard failure)
- A test mocks subprocess/agent calls but fails at entry point validation
- Multiple related tests need consistent guard-clause satisfaction
- Guard clauses check prerequisites (env vars, files, config) before main logic
- The test environment is incomplete relative to what entry-point guards require

## Verified Workflow

> Verification level: **verified-ci**. Issue #1580/#1595: CI passed after applying the fix.

### Quick Reference

**The Problem:**
```python
# Before (FAILS — guard clause prevents reaching mock):
def test_reports_pi_runtime_contract_error(monkeypatch, mocker):
    monkeypatch.setenv("HEPH_PI_MODEL", "test-model-alias")
    # Missing: HEPH_PI_PROVIDER
    mocker.patch("run_pi_session", side_effect=RuntimeError("contract error"))
    result = main([...])  # Returns 2 (guard failure), not 1 (RuntimeError)
    # Test expected exit code 1, got 2 — guard clause exits early
```

**The Fix:**
```python
# After (PASSES — guard clause satisfied, mock is reached):
def test_reports_pi_runtime_contract_error(monkeypatch, mocker):
    monkeypatch.setenv("HEPH_PI_MODEL", "test-model-alias")
    monkeypatch.setenv("HEPH_PI_PROVIDER", "private-provider-alias")  # NEW
    mocker.patch("run_pi_session", side_effect=RuntimeError("contract error"))
    result = main([...])  # Returns 1 (RuntimeError), test passes
    # Guard clause satisfied, mock is reached, contract validation works
```

### Detailed Steps

1. **Audit the entry point's guard clauses.** Read the entry point function (typically `main()`) and identify ALL prerequisite checks that run BEFORE the code-under-test is called. These include:
   - Environment variable validation (e.g. `if not (HEPH_PI_MODEL and HEPH_PI_PROVIDER): return 2`)
   - File existence checks (e.g. `if not Path(config_path).exists(): return 3`)
   - Configuration validation (e.g. `if not validate_config(cfg): return 4`)
   - Any `sys.exit()`, `return <code>`, or exception that happens BEFORE the mocked function

   Document these guards explicitly as a comment in the test or in the test's docstring.

2. **Identify which guards your test must satisfy.** When you mock a function at depth (e.g. `run_pi_session`), that function call is DEEP in the call stack, AFTER all entry-point guards. The test environment MUST satisfy every guard that executes before the mock is reached.

   Example: if `main()` has guards for BOTH HEPH_PI_MODEL and HEPH_PI_PROVIDER, and only the first is set, the second guard will fail BEFORE the mocked `run_pi_session()` is ever invoked.

3. **Set all required environment variables, files, and config in the test.** Use monkeypatch (preferred in pytest) or other test fixtures to satisfy EVERY prerequisite. Do not assume a guard is "probably optional" — audit the entry point to confirm.

   ```python
   def test_example(monkeypatch, mocker):
       # Satisfy ALL guards that run before the mock:
       monkeypatch.setenv("REQUIRED_VAR_1", "value1")
       monkeypatch.setenv("REQUIRED_VAR_2", "value2")
       # Optionally create required files, apply config patches, etc.

       # THEN mock the internal function:
       mocker.patch("module.internal_function", side_effect=MyException())

       # NOW call the entry point:
       result = main([...])
   ```

4. **Test symmetry: ensure all related tests have consistent guard satisfaction.** When you fix one test to satisfy guards, audit sibling tests that mock the same function or entry point. They should all have the same guard-satisfaction setup (in the same order, with the same values), making it easy to audit that all 4 tests agree on prerequisites.

   Example from issue #1580: all 4 tests in `test_pi_smoke.py` that call `main()` now all set BOTH HEPH_PI_MODEL and HEPH_PI_PROVIDER at lines 37-38, 77-78, 103-104, 132-133, ensuring symmetry and making the guards visible at a glance.

5. **Verify that the mock is actually reached.** After fixing guard satisfaction, run the test and confirm:
   - The test now receives the expected return code / exception (not the guard-exit code)
   - The mock was actually invoked (use `assert mocker.patch(...).called` or check the side_effect was raised)
   - The test behavior matches what you expected from the code-under-test, not from an early guard

6. **Document the guard dependencies in the test or skill.** Add a comment explaining which guards are required. This prevents future edits from accidentally removing a monkeypatch that silently lets a guard pass.

   ```python
   def test_reports_pi_runtime_contract_error(monkeypatch, mocker):
       # Entry-point guards require BOTH aliases (hephaestus/scripts/run_pi_smoke.py:45-48):
       monkeypatch.setenv("HEPH_PI_MODEL", "test-model-alias")
       monkeypatch.setenv("HEPH_PI_PROVIDER", "private-provider-alias")
       mocker.patch("run_pi_session", side_effect=RuntimeError("contract error"))
       result = main([...])
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Set only HEPH_PI_MODEL | Assumed main() only checks one env var | Guard clause checks BOTH required aliases; entry point validations must be fully satisfied | Audit entry point for ALL guards before writing test setup; don't assume which guards exist |
| Mock earlier (before main()) | Tried to intercept at a different layer | Mocking interior functions doesn't bypass entry-point guards; guards execute BEFORE the mock call | Guards are structural, not mockable; satisfy them in test environment, not code |
| Use pytest.fixture for env setup | Tried to share env setup via a conftest fixture | Fixture-based setup was harder to audit — unclear which tests satisfy which guards | Direct monkeypatch in each test function makes guard satisfaction explicit and auditable |
| Ignore the guard-exit code discrepancy | Assumed "return 2 vs return 1" was just a different test result | Exit code 2 is the guard-failure code; exit code 1 is RuntimeError — the test is failing at a different layer entirely | Always audit unexpected exit codes against the entry point's return statements to find early guards |
| Skip adding comments | Assumed the guard setup was "obvious" from the code | Future maintainers removing a monkeypatch didn't know it was critical to reach the mock | Document guard dependencies explicitly in test comments; make prerequisites visible |

## Results & Parameters

**File**: `tests/unit/scripts/test_pi_smoke.py` lines 37-38, 77-78, 103-104, 132-133
**Required aliases**: `HEPH_PI_MODEL`, `HEPH_PI_PROVIDER` (both non-negotiable)
**Guard location**: `hephaestus/scripts/run_pi_smoke.py` main() lines ~45-48
**Return code on guard failure**: 2 (via `sys.exit(2)`)
**Return code on RuntimeError**: 1 (via exception handler)
**All 4 test functions now mirror this setup for symmetry**:
- `test_accepts_pi_model_alias` (line 37-38)
- `test_reports_missing_heph_environment_variable` (line 77-78)
- `test_accepts_heph_pi_provider_as_env_alias` (line 103-104)
- `test_reports_pi_runtime_contract_error` (line 132-133)

**CI Verification**: Passed after fix

## Generalization

This pattern applies to ANY entry point with prerequisite guards:

- **Env var validation**: require ALL checked vars, not just some
- **File existence checks**: create all required files, not just the ones being tested
- **Configuration validation**: satisfy all config predicates before the code-under-test
- **Argument parsing**: fulfill all `argparse` requirements before calling `main()`

The durable rule: **a unit test that mocks an internal function must satisfy ALL guards that execute BEFORE that mock is reached**. Guards are structural; they execute in order and cannot be mocked away. The test environment must be complete.

## Verified On

| Repository | Issue / PR | What was applied |
| ------------ | ------------ | ------------------ |
| ProjectHephaestus | issue #1580/#1595 | Fixed test_reports_pi_runtime_contract_error by adding monkeypatch.setenv("HEPH_PI_PROVIDER", "private-provider-alias"). Applied same fix symmetrically to all 4 related tests in test_pi_smoke.py. CI passed. |

## Tags

`#unit-tests` `#test-environment` `#guard-clauses` `#monkeypatch` `#entry-point-validation` `#mocking` `#pytest` `#hephaestus`
