---
name: shell-script-integration-test-tier-coverage
description: "Pattern for ensuring integration tests cover all preference tiers in shell scripts with N-tier fallback logic. Use when: (1) a shell script has N-tier fallback/preference logic but tests only cover the first N-1 tiers, (2) adding a test for a bash script that uses bash-function-override injection (export a mock `gh` function), (3) reviewing test coverage gaps in `scripts/choose_merge_flag.sh` or similar tiered-preference scripts, (4) constructing JSON bodies for each tier of a jq-driven preference selector."
category: testing
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - shell
  - bash
  - integration-test
  - mock
  - choose_merge_flag
  - tier-coverage
  - jq
  - bash-function-override
---

# Shell Script Integration Test Tier Coverage

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Add missing integration test for the `--merge` fallback path in `scripts/choose_merge_flag.sh` (ProjectHephaestus issue #1277) |
| **Outcome** | Plan produced; test designed but not run |
| **Verification** | unverified — planning session only, tests not executed |

## When to Use

Trigger this skill when:

1. A shell script uses an if-elif/case chain with N preference tiers and tests only cover N-1 of them
2. The uncovered tier is a fallback (the "last resort" branch hit when all higher-priority conditions are false)
3. The existing test file uses a `_run_with_mock_gh(json_body)` helper that injects `gh` as a bash function override
4. You need to construct a JSON body that targets a specific branch in `choose_merge_flag.sh` by setting boolean flags
5. You encounter the pattern: `if rebaseMergeAllowed → --rebase; elif squashMergeAllowed → --squash; else → --merge`
6. Auditing test coverage for any script that dispatches on GitHub's `mergeCommitAllowed` / `squashMergeAllowed` / `rebaseMergeAllowed` fields

## Verified Workflow

> **Warning:** This workflow is unverified — it was designed in a planning session but not run. Treat as a hypothesis until CI confirms.

### 1. Enumerate all branches in the script under test

Read the script (e.g., `scripts/choose_merge_flag.sh`) and list every branch:

```
Tier 1 (~line 20): if rebaseMergeAllowed   → output "--rebase"
Tier 2 (~line 26): elif squashMergeAllowed → output "--squash"
Tier 3 (~line 32): else                    → output "--merge"
```

Count the branches, then count the existing test functions. Missing tiers = add one test per gap.

### 2. Check the existing test file for the `_run_with_mock_gh` helper

In `tests/integration/test_choose_merge_flag.sh` (or equivalent), locate `_run_with_mock_gh`:

```bash
_run_with_mock_gh() {
    local json_body="$1"
    # Injects gh as a bash function that echoes the fixed JSON body,
    # then sources/runs the script under test
    gh() { echo "$json_body"; }
    export -f gh
    bash scripts/choose_merge_flag.sh
}
```

No new infrastructure is needed — just add a new test function that calls this helper with a different JSON body.

### 3. Construct the JSON body for the missing tier

Toggle the three boolean flags to route execution into the desired branch:

```json
// Tier 1: rebase only — rebaseMergeAllowed: true, others false
{"data":{"repository":{"pullRequest":{"mergeStateStatus":"CLEAN","baseRepository":{"mergeCommitAllowed":false,"squashMergeAllowed":false,"rebaseMergeAllowed":true}}}}}

// Tier 2: squash only — squashMergeAllowed: true, rebase false
{"data":{"repository":{"pullRequest":{"mergeStateStatus":"CLEAN","baseRepository":{"mergeCommitAllowed":false,"squashMergeAllowed":true,"rebaseMergeAllowed":false}}}}}

// Tier 3: merge only — mergeCommitAllowed: true, rebase+squash false
{"data":{"repository":{"pullRequest":{"mergeStateStatus":"CLEAN","baseRepository":{"mergeCommitAllowed":true,"squashMergeAllowed":false,"rebaseMergeAllowed":false}}}}}
```

### 4. Add one test function per missing tier

Follow the exact shape of existing test functions — no scaffolding changes required:

```bash
test_merge_fallback() {
    local json_body='{"data":{"repository":{"pullRequest":{"mergeStateStatus":"CLEAN","baseRepository":{"mergeCommitAllowed":true,"squashMergeAllowed":false,"rebaseMergeAllowed":false}}}}}'
    result=$(_run_with_mock_gh "$json_body")
    assert_equals "--merge" "$result" "merge fallback tier"
}
```

Register it in the test runner (if the file has an explicit list of test functions to call).

### 5. Verify CI gating before assuming the test blocks merge

Check `.github/workflows/` to confirm whether `pixi run pytest tests/integration/` (or equivalent) is a **required** CI job:

```bash
grep -r "tests/integration\|pytest.*integration\|integration.*pytest" .github/workflows/
```

If integration tests are advisory-only, the new test won't block a broken PR automatically.

### Quick Reference

| Goal | What to do |
|------|------------|
| Find uncovered tiers | Read script + count if/elif/else branches; count existing test functions |
| Target Tier 1 (rebase) | `rebaseMergeAllowed: true`, others false |
| Target Tier 2 (squash) | `squashMergeAllowed: true`, rebase false |
| Target Tier 3 (merge) | `mergeCommitAllowed: true`, rebase+squash false |
| Add test | One new function; reuse `_run_with_mock_gh` helper — no new infra |
| No script changes | New tier test is test-only; the script under test is untouched |
| CI gating | Grep `.github/workflows/` — integration tests may be advisory not required |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| (none yet) | Plan only — no attempts run | N/A | Skill is unverified; update when the test is actually executed |

## Results & Parameters

### Known fragility: single quotes in JSON inside bash here-docs

The `_run_with_mock_gh` helper passes a JSON body as a bash string. If the JSON body ever contains single quotes (e.g., a string value with an apostrophe), single-quote shell interpolation will break. For fixed payloads with boolean values this is not a risk, but it is a latent fragility to watch if the JSON schema changes.

**Mitigation**: use a temporary file for the JSON body if it must contain single quotes:

```bash
_tmpfile=$(mktemp)
printf '%s' "$json_body" > "$_tmpfile"
# pass file path instead of inline string
```

### CI environment assumptions (unverified)

- `bash` and `jq` must be available in CI (assumed from existing tests passing — not independently verified)
- The bash function override injection pattern (`export -f gh`) must work consistently across bash versions in CI
- Whether `pixi run pytest tests/integration/` is a required CI gate is unverified — check `.github/workflows/` before assuming the new test blocks merge

### Pattern generalisation

This pattern applies to any shell script with N-tier preference logic and a `_run_with_mock_<tool>` injection helper:

1. Enumerate all branches
2. Map each branch to the JSON/env-var configuration that routes into it
3. Add one test function per uncovered branch, reusing the existing helper
4. Verify CI gating independently

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning session for issue #1277 (2026-06-13) | Plan only; test designed but not run; skill is unverified |
