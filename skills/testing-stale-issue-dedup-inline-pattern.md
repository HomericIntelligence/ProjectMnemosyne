---
name: testing-stale-issue-dedup-inline-pattern
description: "When consolidating duplicate test helpers, inline direct calls rather than adding wrapper fixtures. Use when: (1) an issue asks to move a helper to conftest.py, (2) the helper is already importable from a shared module, (3) the helper is a pure function (not setup/teardown)."
category: testing
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Testing: Stale Issue Dedup — Inline Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Consolidate duplicate `_sign()` HMAC-SHA256 test helper across 4 files per issue #329 |
| **Outcome** | Successful — inlined 4 call sites in test_integration.py, tests pass |
| **Verification** | verified-local |

## When to Use

- An issue asks to consolidate a duplicate helper into `conftest.py`
- The helper is already defined in a shared module (e.g. `tests/helpers.py`)
- The helper is a pure function (bytes → str, not pytest setup/teardown)
- The function needs caller-supplied context (e.g. a per-module secret)
- Issue evidence list names files that may already be fixed by prior PRs

## Verified Workflow

### Quick Reference

```bash
# Before inlining: check current state of duplication
grep -rn "def _sign\|sign_body" tests/

# Confirm the shared helper exists and is importable
grep -n "def sign_body" tests/helpers.py

# Replace all wrapper calls with direct calls
# Edit: delete the wrapper function
# Edit: replace _sign(body_bytes) -> sign_body(body_bytes, MODULE_SECRET)

# Verify no residual wrapper definitions remain
grep -rn "def _sign" tests/

# Confirm tests collect cleanly (no NameError)
pytest tests/target_file.py --collect-only -q

# Lint and format
ruff check tests/target_file.py
ruff format --check tests/target_file.py
```

### Detailed Steps

1. **Grep for current state** — don't trust the issue body's "Evidence:" list; prior PRs may have already partially resolved the duplication
2. **Identify the canonical helper** — look for an existing shared module (`tests/helpers.py`, `conftest.py`) that already provides the function
3. **Check if the helper needs caller context** — if the function requires a per-module secret/config, a shared wrapper adds indirection without value; inline instead
4. **Delete the thin wrapper** — remove the one-liner that just delegates to the canonical helper
5. **Replace call sites** — use `replace_all=True` in Edit (all call sites are textually identical when the wrapper hid the secret)
6. **Run formatter** — the formatter may reflow surrounding long lines (acceptable, cosmetic)
7. **Verify collection** — `pytest --collect-only` catches NameError immediately without needing NATS/external services
8. **Commit and push** — if the remote branch has diverged with a different approach, rename branch and push as new rather than force-pushing

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Promote to conftest.py fixture | Add `@pytest.fixture` returning `sign_body(b, SECRET)` | pytest fixtures are for setup/teardown state, not pure functions; adds indirection with no benefit | Only use fixtures for stateful setup; importable pure functions should stay as functions |
| Force-push after remote diverged | `git push --force origin branch` | Remote had a different valid approach already committed; force-push would lose that work | Rename local branch and push as new; let the PR system sort out approaches |
| Trust the issue evidence list | Immediately edit the 4 files named in the issue | 3 of 4 files had already been fixed by a prior PR | Always grep first; issue bodies go stale as PRs land |

## Results & Parameters

```python
# Canonical shared helper (tests/helpers.py)
def sign_body(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

# Module-local secret (intentionally different from shared TEST_SECRET)
INTEGRATION_TEST_SECRET = "integration-test-secret-for-hermes-webhook"

# Inlined call site pattern (after removing wrapper)
headers = {
    "Content-Type": "application/json",
    "X-Webhook-Signature": sign_body(body_bytes, INTEGRATION_TEST_SECRET),
}
```

**Test result**: 327 tests pass after inlining (integration tests skip when NATS unavailable)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHermes | Issue #329 — dedup `_sign()` HMAC helper | PR #652 on HomericIntelligence/ProjectHermes |
