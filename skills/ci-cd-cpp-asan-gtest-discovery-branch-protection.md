---
name: ci-cd-cpp-asan-gtest-discovery-branch-protection
description: "C++ CI repair patterns for ASAN/UBSAN test discovery failures and GitHub branch protection drift. Use when: (1) gtest_discover_tests() aborts at CMake configure time with ASan runtime error, (2) branch ruleset required_approving_review_count resets to 0 causing daily audit CI failures, (3) upgrading peter-evans/create-pull-request from v6 to v8, (4) upgrading gitleaks/gitleaks-action from v2 to v3."
category: ci-cd
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - asan
  - ubsan
  - sanitizer
  - gtest
  - cmake
  - gtest_discover_tests
  - branch-protection
  - ruleset
  - required-reviewers
  - peter-evans-create-pull-request
  - gitleaks
---

# C++ CI Repair: ASAN Test Discovery + Branch Protection Drift

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Fix recurring C++ CI failures: ASAN-linked test binaries crashing at CMake configure time, and GitHub ruleset required_approving_review_count silently resetting to 0 |
| **Outcome** | Both fixes verified in CI via PRs to ProjectNestor (#111) and ProjectCharybdis (#263) |
| **Verification** | verified-ci |

## When to Use

1. `gtest_discover_tests()` in CMake causes CI failure with `ASan runtime does not come first in initial library list` at configure time
2. A daily ruleset-audit CI job is failing with `required_approving_review_count is 0, expected >= 1`
3. Upgrading `peter-evans/create-pull-request` from v6 to v8 — need to know what inputs break
4. Upgrading `gitleaks/gitleaks-action` from v2 to v3 — need to know what breaks

## Verified Workflow

### Quick Reference

```bash
# Fix 1: ASAN gtest discovery — add DISCOVERY_MODE PRE_TEST
# In CMakeLists.txt:
gtest_discover_tests(my_test_target DISCOVERY_MODE PRE_TEST)

# Fix 2: Branch protection reset — run existing script if present
bash scripts/apply-branch-protection.sh

# Fix 2 alternative — patch via API
RULESET_ID=15556497  # find with: gh api repos/ORG/REPO/rulesets
RULES=$(gh api repos/ORG/REPO/rulesets/$RULESET_ID | jq '.rules | map(if .type == "pull_request" then .parameters.required_approving_review_count = 1 else . end)')
gh api --method PATCH repos/ORG/REPO/rulesets/$RULESET_ID --field enforcement=active --field "rules=$RULES"
```

### Detailed Steps

#### Fix 1: ASAN/UBSAN + gtest_discover_tests

**Root cause:** `gtest_discover_tests()` default mode (`POST_BUILD`) runs the test binary at CMake configure/build time to enumerate tests via `--gtest_list_tests`. When the binary is linked with `-fsanitize=address`, the ASan runtime `.so` must be the first shared library loaded. In the non-test GitHub Actions environment, LD_PRELOAD is not set, causing the immediate abort:
```
==XXXXX==ASan runtime does not come first in initial library list; you should either link runtime to your application or manually preload it with LD_PRELOAD.
CMake Error at .../GoogleTestAddTests.cmake:132: Error running test executable.
```

**Fix:** Add `DISCOVERY_MODE PRE_TEST` to every `gtest_discover_tests()` call:

```cmake
# Before (broken with ASAN):
gtest_discover_tests(nestor_tests)
gtest_discover_tests(nestor_tests PROPERTIES TIMEOUT 120)

# After (ASAN-safe):
gtest_discover_tests(nestor_tests DISCOVERY_MODE PRE_TEST)
gtest_discover_tests(nestor_tests DISCOVERY_MODE PRE_TEST PROPERTIES TIMEOUT 120)
```

`DISCOVERY_MODE PRE_TEST` defers the `--gtest_list_tests` invocation to actual test runtime when `ctest` sets up the proper sanitizer environment.

Find all affected targets:
```bash
grep -rn "gtest_discover_tests" . --include="CMakeLists.txt"
```

#### Fix 2: Branch protection required_approving_review_count reset

**Root cause:** GitHub's rulesets API can reset `required_approving_review_count` to 0 after certain operations (push events, API calls by other tools). A daily audit workflow checking this will fail until fixed.

**Step 1:** Check if the repair script exists:
```bash
ls scripts/apply-branch-protection.sh 2>/dev/null
```

**Step 2a:** If script exists, run it:
```bash
bash scripts/apply-branch-protection.sh
# Should output: OK: required_approving_review_count=1 confirmed on 'homeric-main-baseline'
```

**Step 2b:** If no script, patch directly:
```bash
# Find your ruleset ID
gh api repos/ORG/REPO/rulesets | jq '.[] | {id, name}'

# Patch — preserves all other rules, only sets reviewer count
RULESET_ID=<id>
RULES=$(gh api repos/ORG/REPO/rulesets/$RULESET_ID \
  | jq '.rules | map(if .type == "pull_request" then .parameters.required_approving_review_count = 1 else . end)')
gh api --method PATCH repos/ORG/REPO/rulesets/$RULESET_ID \
  --field enforcement=active \
  --field "rules=$RULES"
```

#### Fix 3: peter-evans/create-pull-request v6 to v8 upgrade

The `author`/`committer` format changed in v7+. Safe upgrade if the workflow does NOT use `author:` or `committer:` inputs. Repos using only `commit-message`, `title`, `body`, `branch`, `delete-branch` can upgrade transparently.

```yaml
# This upgrade is safe — no author/committer inputs used:
- uses: peter-evans/create-pull-request@5f6978faf089d4d20b00c7766989d076bb2fc7f1  # v8.1.1
  with:
    commit-message: "chore: update vendored schema"
    title: "Update vendored JSON schema"
    body: "Automated update"
    branch: update-schema
    delete-branch: true
```

#### Fix 4: gitleaks/gitleaks-action v2 to v3 upgrade

No breaking input changes for standard usage. Direct SHA swap:
```yaml
# Before:
uses: gitleaks/gitleaks-action@ff98106e4c7b2bc287b24eaf42907196329070c7  # v2

# After:
uses: gitleaks/gitleaks-action@e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e  # v3.0.0
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Set `LD_PRELOAD` in gtest step env to force ASan preload | Env var on the CMake configure step doesn't propagate to child processes spawned by GoogleTestAddTests.cmake during test discovery | `DISCOVERY_MODE PRE_TEST` is the canonical CMake solution — don't fight the discovery phase |
| 2 | Added PROPERTIES ENVIRONMENT "LD_PRELOAD=..." to gtest_discover_tests | PROPERTIES keyword applies to test properties, not the discovery invocation itself | Use DISCOVERY_MODE PRE_TEST instead; it completely skips the binary invocation at configure time |
| 3 | Used `gh api --method PATCH` with a JSON-encoded `rules` string | The PATCH endpoint requires `rules` as a JSON array object, not a JSON-encoded string | Use `--field "rules=$RULES"` where `$RULES` is the raw jq output (array), not a quoted string |

## Results & Parameters

### ASAN gtest discovery fix — verified in ProjectNestor

- Affected: `test/CMakeLists.txt` with 3 `gtest_discover_tests()` calls
- PR: HomericIntelligence/ProjectNestor#111
- Outcome: CodeQL and Required Checks now passing on PR

### Branch protection fix — verified in ProjectCharybdis

- Ruleset: `homeric-main-baseline` (id=15556497)
- Script: `scripts/apply-branch-protection.sh` (existed and worked)
- PR: HomericIntelligence/ProjectCharybdis#263
- Outcome: Daily ruleset-audit workflow now passes

### Action version SHAs (2026-06-13)

| Action | Version | SHA |
|--------|---------|-----|
| `peter-evans/create-pull-request` | v8.1.1 | `5f6978faf089d4d20b00c7766989d076bb2fc7f1` |
| `gitleaks/gitleaks-action` | v3.0.0 | `e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectNestor | CodeQL ASAN failure fix 2026-06-13 | PR #111 — 3 gtest_discover_tests calls fixed |
| ProjectCharybdis | Daily ruleset-audit failure fix 2026-06-13 | PR #263 — apply-branch-protection.sh ran successfully |
