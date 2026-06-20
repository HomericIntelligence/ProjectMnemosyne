---
name: testing-verification-gate-zero-test-false-pass
description: "A verification gate that selects ZERO tests still exits 0 (green) and silently gates nothing — a FALSE PASS. Happens when a plan says 'wrap existing test X in pytest.warns' but X never existed, or uses `pytest -k <expr>` that matches no tests. Net-new code (e.g. a deprecation shim) then ships untested. Use when: (1) a plan modifies/wraps an 'existing' test, (2) a verification step relies on `pytest -k`/selection, (3) you add net-new code and want a real gate, (4) you must enforce a DeprecationWarning rather than just allow it."
category: testing
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [testing, pytest, verification-gate, false-pass, deprecation-warning, test-count, collect-only, planning]
---

# Verification Gate: Zero-Test False Pass

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-06-20 |
| Objective | Validate the test gate in the R1 plan that "verifies" a new deprecation shim added while moving code ProjectKeystone → ProjectAgamemnon |
| Outcome | Planning-only (R1 re-plan after NOGO). Found the planned gate was a false pass: it wrapped phantom tests and used `pytest -k config` which matched 0 tests yet exited 0. Replaced with grep-confirmed test existence, a net-new test for net-new code, an asserted pass COUNT, and `-W error::DeprecationWarning` enforcement |
| Verification | unverified — gate not executed; no CI ran |

## When to Use

- A plan or issue says "wrap the existing `LegacyClass(...)` test in `pytest.warns`" or "modify test X" — before trusting it, confirm X actually exists.
- A verification step relies on `pytest -k <expr>` or any test SELECTION to gate a change.
- You are adding **net-new** code (a deprecation shim, a new module) and want a gate that actually exercises it.
- You need a DeprecationWarning to be **enforced** (failing the build if it regresses), not merely permitted.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

The trap: `pytest -k config` (or `pytest.warns` wrapped around a non-existent call) returns exit code 0 when it collects **zero** matching tests. Green build, nothing tested. The fix is to (a) prove the tests you intend to modify exist, (b) give net-new code a net-new test, (c) assert an explicit pass COUNT and collection parity so a missing test can't hide, and (d) promote the warning to an error so it's enforced.

1. **Before writing "wrap/modify existing test X":** grep-confirm X exists. If the grep returns nothing, the assertions you planned to wrap are phantom.
2. **Net-new code gets a NET-NEW test** — not a wrapper around a phantom assertion. A deprecation shim that ships without its own test is untested code.
3. **Never let a selection gate pass on zero tests.** Assert the expected pass count (e.g. `... | grep -q "4 passed"`), so a zero-match run (which prints `no tests ran` / `0 selected`) fails the gate.
4. **Enforce the warning** with `-W error::DeprecationWarning` so the deprecation path is actually triggered and a regression fails the build.
5. **Check collection parity:** `pytest --collect-only -q | tail -1` must equal `baseline + N-new`, so a net-new test cannot be silently absent.

### Quick Reference

```bash
# 1. BEFORE planning "wrap existing test X": confirm the assertions/tests exist.
grep -rnE 'setenv|os\.environ|KEYSTONE_|monkeypatch' tests/*.py
# If this prints NOTHING and tests/test_config.py does not exist, the "existing test
# to wrap" is PHANTOM. Net-new code needs a NET-NEW test, not a wrapped phantom.

# 2. FALSE PASS to avoid — selects 0 tests, exits 0, gates nothing:
pytest -k config            # "no tests ran" but exit code 0  → green, untested

# 3. REAL gate — assert the expected COUNT and enforce the warning:
pytest tests/test_config_deprecation.py -W error::DeprecationWarning -q \
  | tee /tmp/out.txt
grep -q "4 passed" /tmp/out.txt || { echo "FALSE PASS: expected 4 tests"; exit 1; }

# 4. Collection parity — net-new test cannot be silently absent:
pytest --collect-only -q | tail -1   # must equal baseline + N-new
```

## Verified Workflow

_Not applicable_ — unverified; no workflow was executed. Captured during an R1 re-planning session; the gate above is a hypothesis to be confirmed by CI/execution.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Plan: "wrap each legacy-var assertion in `pytest.warns`" to verify the new deprecation shim | `grep -rnE 'setenv\|os.environ\|KEYSTONE_\|monkeypatch' tests/*.py` returned nothing and no `test_config.py` existed — the assertions to wrap were phantom | Before writing "wrap/modify existing test X", grep-confirm X exists; net-new code needs a NET-NEW test, not a wrapped phantom |
| 2 | `pytest -k config` as the verification gate for the change | It matched 0 tests, exited 0 (green), and gated nothing — a FALSE PASS; net-new shim shipped untested | A `pytest -k` gate matching zero tests is a false pass; assert the expected pass COUNT (e.g. `grep -q "4 passed"`) so a zero-match run fails |
| 3 | Allowed the DeprecationWarning to merely fire (default filter) | A merely-allowed warning never fails the build, so a regression on the deprecation path would pass silently | Run with `-W error::DeprecationWarning` to enforce the warning, and use `--collect-only` count parity (baseline + N-new) so a missing test can't hide |

## Results & Parameters

- **False-pass command:** `pytest -k config` → "no tests ran", exit 0.
- **Phantom-detection grep:** `grep -rnE 'setenv|os\.environ|KEYSTONE_|monkeypatch' tests/*.py` (empty result ⇒ no test to wrap).
- **Real gate:** `pytest <net-new-test> -W error::DeprecationWarning -q` AND `grep -q "<N> passed"` on the output.
- **Collection parity:** `pytest --collect-only -q | tail -1` == baseline + N-new.
- **Rules:** (1) grep-confirm a test exists before "wrapping" it; (2) net-new code → net-new test; (3) assert pass count, not just exit code; (4) enforce warnings as errors.
- **Status:** unverified (planning-only); gate not executed, no CI run.

## Verified On

| Item | Value |
|------|-------|
| Migration | ProjectKeystone → ProjectAgamemnon |
| Meta-repo | Odysseus |
| Issue | #143 (R1 planning) |
| Verification | unverified — not executed |
