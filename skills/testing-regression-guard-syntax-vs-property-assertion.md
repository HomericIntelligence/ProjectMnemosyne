---
name: testing-regression-guard-syntax-vs-property-assertion
description: "Refactor regression-guard tests that assert on the exact literal text of a suppression mechanism (`continue-on-error: true`, `|| true`, etc.) to instead assert the underlying property. Use when: (1) running an ecosystem sweep that changes the syntax of a known idiom while preserving its semantics, (2) CI tests fail with `assert \"continue-on-error: true\" in step_text` even though the property the test guards is preserved, (3) meta-tests / smoke tests / workflow-property tests pin to literal strings instead of behavioral predicates, (4) preparing a codebase for a forbid-suppressions or forbid-deprecated-API sweep — fix these meta-tests BEFORE the sweep, not after."
category: testing
date: 2026-05-11
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - meta-tests
  - regression-guard
  - syntax-pinning
  - property-assertion
  - ecosystem-sweep
  - smoke-tests
  - workflow-tests
  - test-broadening
---

# Testing: Regression-Guard Tests — Syntax vs Property Assertion

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-11 |
| **Objective** | Identify and refactor regression-guard tests that pin to the literal syntax of a suppression mechanism, so an ecosystem sweep replacing the syntax (while preserving the property) doesn't trip the tests on every PR. |
| **Outcome** | Broadened 2 categories of meta-tests across 2 repos. All affected tests now assert the underlying property (step non-blocking, audit step preserves fail-on-zero semantics, mojo-format step is fail-fast). 4 bats + 6 smoke tests pass. |
| **Verification** | verified-ci |

## When to Use

- Planning an ecosystem sweep that replaces a known suppression syntax (e.g., `continue-on-error: true` → in-script `if !` wrapper, or `|| true` → captured-rc pattern). Run the grep FIRST and fix meta-tests BEFORE the sweep.
- CI breaks on a sweep PR with assertion errors like `assert "continue-on-error: true" in step_text` — the property is preserved but the literal is gone.
- A workflow-property smoke test in `tests/smoke/test_*.py` or `.github/workflows/workflow-smoke-test.yml` pins to a literal string.
- Reviewing a sweep PR and noticing meta-test failures that are *not* real regressions.

## Verified Workflow

### Quick Reference

```bash
# Find meta-tests pinned to suppression syntax BEFORE running a sweep:
grep -rn "continue-on-error\|or-true\|::warning::" tests/ .github/ \
  --include="*.py" --include="*.sh" --include="*.bash" --include="*.bats" \
  --include="*.yml" --include="*.yaml"
```

### Step 1: Find the meta-tests pinned to suppression syntax

Run BEFORE the sweep:

```bash
# Generic pinning patterns: literal "continue-on-error: true", "|| true", etc.
grep -rn "continue-on-error\|or-true\|::warning::" tests/ \
  --include="*.py" --include="*.sh" --include="*.bash" --include="*.bats"

# Also workflow-level smoke-tests that grep workflow YAML for literals:
grep -rn "grep.*continue-on-error\|grep.*|| true" .github/ tests/ \
  --include="*.yml" --include="*.yaml" --include="*.sh"
```

If any hits → fix them BEFORE the sweep. Otherwise, your sweep PR will fail meta-tests on every commit.

### Step 2: Broaden the assertion from syntax to property

Anti-pattern (pinned to literal):

```python
def test_npm_audit_is_non_blocking():
    assert "continue-on-error: true" in step_text
```

Broadened (accepts either syntax form):

```python
def test_npm_audit_is_non_blocking():
    """Property: the npm-audit step must NOT fail the workflow on audit findings."""
    legacy = "continue-on-error: true" in step_text
    in_script_capture = (
        "|| AUDIT_EXIT=$?" in step_text
        and "AUDIT_EXIT:-0" in step_text
    )
    assert legacy or in_script_capture, "audit step must be non-blocking"
```

Even more strict (post-Bucket F per `ci-cd-forbid-suppressions-pygrep-lint-guard` v2.0.0 — both `continue-on-error: true` and the in-script `if !`+`::warning::` wrapper are now banned):

```python
def test_npm_audit_is_fail_fast():
    """Property (Bucket F): no suppression mechanism allowed in the audit step body."""
    forbidden = ["continue-on-error: true", "|| true", "::warning::",
                 "--exit-code 0", "--exit-zero"]
    for pat in forbidden:
        assert pat not in step_text, f"audit step contains forbidden pattern: {pat}"
```

Choose the strict fail-fast form when adopting the v2.0.0 policy.

### Step 3: Inline-shell smoke tests (workflow-smoke-test.yml)

The same principle applies to grep-based smoke tests in `.github/workflows/workflow-smoke-test.yml`. Replace:

```yaml
- name: smoke-test mojo-format is non-blocking
  run: grep -A 5 "Run mojo format" .github/workflows/pre-commit.yml | grep -q "continue-on-error: true"
```

with:

```yaml
- name: smoke-test mojo-format is fail-fast
  run: |
    # Property (Bucket F per HomericIntelligence/Odysseus#282): mojo-format
    # runs fail-fast; no advisory wrapper allowed.
    step=$(yq '.jobs.lint.steps[] | select(.name == "Run mojo format")' .github/workflows/pre-commit.yml)
    for pat in 'continue-on-error: true' '|| true' '::warning::' '--exit-code 0' '--exit-zero'; do
      if echo "$step" | grep -qF "$pat"; then
        echo "::error::mojo-format step contains forbidden pattern: $pat"
        exit 1
      fi
    done
```

NOTE: this smoke-test's `run:` block contains the literal `::warning::` string in its error message. The `forbid-advisory-warnings` hook (per `ci-cd-forbid-suppressions-pygrep-lint-guard` v2.0.0) will catch it unless you exclude this file via `exclude:` in `.pre-commit-config.yaml`. See the v2.0.0 lesson "Lint guards must self-exempt."

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| 1 | Ran the sweep first, fixed meta-tests in the same PR after CI broke | Every sweep PR's CI ran twice (once broken, once fixed). Inefficient and confusing — reviewers see "test_npm_audit_is_non_blocking failed" and assume the audit-step refactor is wrong. | Run the meta-test grep BEFORE the sweep, fix in a small predecessor PR. |
| 2 | Broadened the meta-test to accept the NEW syntax only (replaced `continue-on-error: true` with the new mechanism's literal) | Same problem on the NEXT sweep — when Bucket F banned the in-script wrapper, the meta-test broke again. | Assert the property (step is fail-fast / step is non-blocking), not a particular syntax. |
| 3 | Tested for the property by asserting the step's runtime behavior (`gh workflow run ... && check exit code`) | Way too slow for unit tests; defeats pre-merge fast-feedback. | Use static analysis: parse the workflow YAML, assert on the relevant `run:` block's text via property-based predicates. |
| 4 | Used Python `re.search()` over the raw workflow file text | False positives — matched `continue-on-error: true` inside a different step's commented-out code. | Parse the workflow YAML structurally (yq / PyYAML) and check the *specific* step under test. |
| 5 | Forgot that the smoke-test's own error message literally contains `::warning::` or `continue-on-error: true` | The forbid-suppressions / forbid-advisory-warnings hooks fire on the test file itself. | Self-exempt the smoke-test workflow file from those hooks via `exclude:`, OR construct the forbidden literal at runtime via string concatenation. |

## Results & Parameters

Broadened meta-tests (verified-ci):

| Repo | PR | Test file:test name | Before | After |
|---|---|---|---|---|
| HomericIntelligence/ProjectScylla | #1968 | `tests/unit/ci/test_npm_audit_step.py::test_npm_audit_is_non_blocking` | `assert "continue-on-error: true" in step_text` | accept either legacy `continue-on-error: true` OR in-script `\|\| AUDIT_EXIT=$?` + `AUDIT_EXIT:-0` |
| HomericIntelligence/ProjectOdyssey (research) | #5385 + #5387 | `tests/smoke/test_pre_commit_workflow_properties.py::test_mojo_format_step_is_fail_fast` + `.github/workflows/workflow-smoke-test.yml` `Check pre-commit mojo-format is fail-fast` | grep for literal `continue-on-error: true` | property check: no forbidden patterns in step body (post-Bucket F) |

## Verified On

| Project | Context | Details |
|---|---|---|
| HomericIntelligence/ProjectScylla | PR #1968 — silent-failures sweep + npm-audit meta-test broadening | 4 tests pass (bats + pytest), CI green |
| HomericIntelligence/ProjectOdyssey (research) | PR #5385 + #5387 — silent-failures + Bucket F sweep | 6 smoke tests pass; meta-test now asserts fail-fast contract per Bucket F |

## See also

- `ci-cd-forbid-suppressions-pygrep-lint-guard` v2.0.0 — the policy this skill supports
- `ci-cd-pip-audit-ignore-vuln-allowlist-with-tracking-issue` — sister skill for handling real findings surfaced after the sweep
