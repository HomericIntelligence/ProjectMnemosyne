---
name: bash-test-helper-captured-rc-pattern
description: "Replace `cmd || true` in bash test helpers with `_rc=0; cmd || _rc=$?; : $((_rc))`. Use when: (1) a test helper invokes a command whose exit code should NOT abort the test but SHOULD remain observable for debugging, (2) the `|| true` suppresses an exit code that the test transcript should still surface (`echo \"DEBUG: cmd rc=$_rc\"`), (3) a codebase enforces a forbid-`|| true` lint guard but the test-helper case was previously labeled 'intentional', (4) a test framework helper like `run_test`, `apply_agent`, `handle_unmanaged` is called with an expected-failure path and downstream assertions don't depend on $?, (5) needing to preserve 'don't assert on rc' semantics while complying with a no-silent-failures policy."
category: testing
date: 2026-05-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - bash
  - test-helpers
  - captured-rc
  - silent-failures
  - exit-code
  - bats
  - myrmidons
  - set-e
  - debugging-observability
---

# Bash Test Helper Captured-RC Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-10 |
| **Objective** | Refactor 11 test-helper sites in Myrmidons that previously used `\|\| true` to suppress exit codes during expected-failure paths, without losing the diagnostic value of seeing the rc in test output. |
| **Outcome** | All 83 bats + 51 stand-alone tests pass; the captured-rc pattern lets the lint guard run cleanly while preserving every test's existing behavior. |
| **Verification** | verified-ci |
| **PR** | HomericIntelligence/Myrmidons#711 |

## When to Use

- A test helper calls a command whose failure is expected on some paths and should NOT abort the test
- The test framework previously used `cmd || true` and the codebase is now adopting a forbid-`|| true` lint guard (see `ci-cd-forbid-suppressions-pygrep-lint-guard`)
- The test author wants to keep the exit code observable in transcripts/logs for regression debugging, not just discarded
- A repo's CLAUDE.md or comments label the existing `|| true` as "intentional exit-code suppression in test helpers" — that label conflicts with a no-silent-failures policy and the captured-rc pattern resolves the conflict

**Keyword triggers**: `|| true`, captured rc, bash test helper, expected-failure path, forbid suppressions, no-silent-failures, bats helper, `set -e`, exit code observability

## Verified Workflow

**Step 1: Replace the suppression with rc capture.** For a line that was `cmd || true`:

```bash
# Before (lint-guard violation):
some_test_helper "$arg" || true

# After (captured rc, no assertion):
_some_rc=0
some_test_helper "$arg" || _some_rc=$?
: $((_some_rc))  # explicit no-op; rc is captured in $_some_rc for inspection
```

The `: $((_some_rc))` line is a deliberate no-op that asserts to readers "we are aware of the rc and choosing not to act on it." If subsequent debug logging refers to `$_some_rc`, drop the `:` line.

**Step 2: For `output=$(cmd) && true || true` (capturing both stdout and rc):**

```bash
# Before:
output=$(_agamemnon_curl_retry "$url" ) && true || true

# After:
_retry_rc=0
output=$(_agamemnon_curl_retry "$url") || _retry_rc=$?
echo "DEBUG: curl rc=$_retry_rc"  # optional but recommended for test transcripts
```

**Step 3: Optional debug surface.** Where the helper's behavior is part of what the test investigates, add an `if` to surface the rc to the transcript:

```bash
_apply_rc=0
apply_agent "$config" || _apply_rc=$?
if [[ "$_apply_rc" -ne 0 ]]; then
    echo "DEBUG: apply_agent returned $_apply_rc for config '$config' (test continues)" >&2
fi
```

This is the meaningful upgrade over `|| true` — the test transcript now contains a breadcrumb when the helper failed, even though the test itself does not abort.

### Quick Reference

```bash
# Pattern 1: just capture rc, no debug surface
_rc=0; cmd || _rc=$?; : $((_rc))

# Pattern 2: capture rc + output
_rc=0; output=$(cmd) || _rc=$?

# Pattern 3: capture + debug log
_rc=0; cmd || _rc=$?
if (( _rc != 0 )); then echo "DEBUG: cmd failed rc=$_rc" >&2; fi
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| 1 | Original codebase used `cmd \|\| true` and CLAUDE.md labeled it "intentional exit-code suppression in test helpers" | Conflicts with the ecosystem's no-silent-failures policy (see `ci-cd-forbid-suppressions-pygrep-lint-guard`). The "intentional" label hid genuine debugging value behind a discarded exit code. | "Intentional suppression" is not a legitimate label. Capture the rc; suppress only the abort. |
| 2 | Tried `cmd \|\| :` as a cosmetic alternative | `:` is functionally identical to `true`, so the same lint guard catches it (or should, if widened). | Don't paper over the policy with synonyms — refactor the structure. |
| 3 | Tried `set +e; cmd; rc=$?; set -e` to temporarily disable abort | Works but is much more verbose and requires careful scoping. The `_rc=0; cmd \|\| _rc=$?` form keeps `set -e` intact and is one line shorter. | Use `\|\| _rc=$?` capture; reserve `set +e` brackets for cases where multiple commands need un-trapped behavior. |
| 4 | Tried `output=$(cmd) && true \|\| true` (chained both branches) | Doesn't actually capture the rc — both branches just discard it. The `&& true` is a no-op when `cmd` succeeds; the `\|\| true` swallows the failure. | Pattern is meaningless; use `output=$(cmd) \|\| _rc=$?` to capture once. |
| 5 | Considered just deleting the suppression entirely and letting tests abort on the expected-failure path | Several test cases (`test-api-retry.sh`, `test-apply-cache.sh`, `test-prune-settle.sh`) deliberately exercise error paths and rely on subsequent assertions over the captured rc/output. Hard-aborting would skip the assertions. | The "don't assert on $?" intent is real and valid; only the suppression mechanism needs to change. |

## Results & Parameters

11 test-helper sites refactored in Myrmidons PR #711:

- `tests/test-api-retry.sh:292,313,334,342` — `_curl_rc=0; ... || _curl_rc=$?` and `_retry_rc=0; ... || _retry_rc=$?`
- `tests/test-apply-cache.sh:181,217,251,299` — `_apply_rc=0; apply_agent ... || _apply_rc=$?` with `if`-guarded debug echo
- `tests/test-prune-settle.sh:178,225` — `_hu_rc=0; handle_unmanaged ... || _hu_rc=$?`
- `tests/test-export-default-owner.sh:61` — special case: `unset VAR 2>/dev/null || true` → bare `unset` (the suppression was unnecessary — `unset` doesn't fail on a non-existent var under `set -u` because `unset -v` accepts undefined names)

Test results post-refactor:

- bats: 83/83 passing (test_reconcile, test_export_default_owner, test_apply_args, test_apply_error, test_unmanaged)
- Stand-alone: 51/51 passing (test-api-retry.sh, test-apply-cache.sh, test-prune-settle.sh, test-export-default-owner.sh)

## Verified On

| Project | Context | Details |
|---|---|---|
| HomericIntelligence/Myrmidons | PR #711 — refactored 11 test-helper sites previously labeled "intentional \|\| true" in CLAUDE.md | All bats + stand-alone tests pass; lint guard `forbid-or-true` passes; Myrmidons CLAUDE.md flagged for follow-up doc rewrite |
