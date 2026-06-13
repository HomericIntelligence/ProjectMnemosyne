---
name: doc-comment-count-drift-verify-frozen-test
description: "When an issue reports 'doc says X but config says Y', trust neither — find the frozen test that enforces the canonical count. Use when: (1) issue claims doc/config count mismatch but actual code count differs from both, (2) multiple files repeat the same stale count and all need synchronizing, (3) a frozen allowlist or validation test is the real enforcer."
category: ci-cd
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: []
---

# doc-comment-count-drift: Verify Against Frozen Test

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Synchronize doc/comment count claims with the actual enforced module count |
| **Outcome** | CI passed first push; 20 tests passed across both test files |
| **Verification** | verified-ci |

## When to Use

- An issue reports "doc says X but config says Y" and neither X nor Y matches what you see in code
- Multiple files (README, ROADMAP, pyproject.toml comments, integration test docstrings) all carry the same stale count
- A frozen test (allowlist test, validation test) is the real enforcer — that is the ground truth
- You find yourself unsure which of two conflicting numbers is correct

## Verified Workflow

### Quick Reference

```bash
# 1. Find the frozen test that enforces the count
grep -r "omit\|allowlist\|excluded" tests/unit/validation/ --include="*.py" -l

# 2. Read the test to get the canonical count
# The test's list length IS the truth — count it

# 3. Update all stale locations to match
# Common locations: docs/ROADMAP.md, pyproject.toml (comments), integration test docstrings

# 4. Verify
pixi run pytest tests/unit/validation/test_omit_allowlist.py tests/integration/test_orchestration_smoke.py -v
```

### Detailed Steps

1. **Do not trust the issue framing.** An issue saying "doc claims X, config says Y" derives Y from the config comment, which may itself be stale. Neither X nor Y may be correct.

2. **Find the frozen/authoritative test.** Look in `tests/unit/validation/` or similar for a test that explicitly enumerates or counts the items. This test is the canonical source of truth because CI enforces it.

3. **Read the test and count.** The actual list in the test (e.g., `OMIT_ALLOWLIST`) gives the true count. In PR #1271 / issue #1191, the test enforced 12 modules while the doc said 6 and the config comment said 11.

4. **Grep all locations that carry the count.** Common places:
   - `docs/ROADMAP.md` — narrative description
   - `pyproject.toml` — inline comments in `[tool.coverage.report]` omit section
   - Integration test docstrings and inline comments
   - README or CONTRIBUTING.md

5. **Update all locations to the canonical count.** Make every reference agree with what the frozen test enforces.

6. **Run the test suite to confirm.** Both the frozen unit test and any integration tests that reference the count.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the issue's "11" | Implementer took the config comment count (11) at face value as the correct target | Config comment was itself stale; the real count was 12 | Always verify against the enforcing test, not against another stale comment |
| Trust the doc's "6" | The ROADMAP said 6 excluded modules — one might assume it was an older accurate count | The doc was simply out of date and wrong | Docs drift further than config comments; neither is reliable without a test to anchor them |
| Update only doc and config | A partial fix updating only `ROADMAP.md` + `pyproject.toml` comment | Integration test docstrings also carried the stale count and would have failed CI | Grep all locations; count-carrying strings appear in docstrings too, not just prose docs |

## Results & Parameters

**PR #1271 / Issue #1191 — ProjectHephaestus**

Files changed (4 locations across 3 files):
- `docs/ROADMAP.md:17` — `6` → `12`
- `pyproject.toml:244` comment — `"11 modules"` → `"12 modules"`
- `tests/integration/test_orchestration_smoke.py` docstring (×2) + inline comment — `11` → `12`

Canonical count source: `tests/unit/validation/test_omit_allowlist.py` — the `OMIT_ALLOWLIST` set contained 12 entries.

Verification command:
```bash
pixi run pytest tests/unit/validation/test_omit_allowlist.py tests/integration/test_orchestration_smoke.py -v
# Expected: 20 passed
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1271, issue #1191 — automation module omit count sync | CI passed first push; 20 tests passed |
