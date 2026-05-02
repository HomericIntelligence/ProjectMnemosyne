---
name: mojo-transient-crash-rerun
description: 'Identify and clear transient Mojo runner crashes in CI by re-triggering
  failed jobs. Use when: CI fails with ''mojo: error: execution crashed'' with no
  repo stack frames, same test passes on main, and PR has no logic changes.'
category: ci-cd
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
# Mojo Transient Crash Rerun

Diagnose `mojo: error: execution crashed` CI failures as transient runner issues and clear
them by re-triggering the failed jobs — no code changes required.

## Overview

| Aspect | Details |
| -------- | --------- |
| **Date** | 2026-03-06 |
| **Objective** | Clear spurious CI failures on PR #3288 (ProjectOdyssey) |
| **Outcome** | Identified as transient crash; re-triggered CI with `--failed` flag |
| **Verified On** | PR #3288, issue #3074 — cosmetic comment-only changes |
| **Key Lesson** | `mojo: error: execution crashed` with only runtime library frames is always a transient runner issue, not a code regression |

## When to Use

Use this skill when ALL of the following are true:

1. CI fails with `mojo: error: execution crashed` (not an assertion error or compilation error)
2. The crash log shows no stack frames from your repo's code — only from `libKGENCompilerRTShared.so` or similar Mojo runtime libraries
3. The same test group passes on the `main` branch CI at roughly the same time
4. The PR contains no logic changes (comments, docs, formatting, NOTEs only)

Do NOT use when:
- The error is a test assertion failure (values don't match) — use `fix-ci-mojo-test-failure` instead
- The error is a compilation error — investigate the code change
- The crash appears on `main` as well — it may be a real regression

## Verified Workflow

### Phase 1: Confirm the Crash Is Transient (3 checks)

1. **Read the crash log** for stack frame origin:
   ```bash
   gh run view <RUN_ID> --log-failed 2>&1 | grep -A 20 "execution crashed"
   ```
   Transient signature — ONLY runtime library frames, no repo files:
   ```
   mojo: error: execution crashed
   libKGENCompilerRTShared.so ...
   ```
   Real crash signature — repo frames present:
   ```
   mojo: error: execution crashed
   shared/core/extensor.mojo:145 ...
   ```

2. **Check main CI at same date**:
   ```bash
   gh run list --branch main --repo <REPO> --limit 5
   gh run view <MAIN_RUN_ID> --repo <REPO>
   ```
   If main passes all groups at the same time, the PR failure is transient.

3. **Confirm PR has no logic changes**:
   ```bash
   git diff main...HEAD -- '*.mojo' | grep -v '^#' | grep -v '^[+-]\s*#'
   ```
   If only comment lines changed, no code regression is possible.

### Phase 2: Re-trigger Failed Jobs

```bash
# Re-run only the failed jobs (not the entire workflow)
gh run rerun <RUN_ID> --repo <REPO> --failed
```

The `--failed` flag limits re-runs to only the failing jobs, saving CI minutes.

### Phase 3: Verify

```bash
# Poll until complete
gh run view <NEW_RUN_ID> --repo <REPO>

# Expected: all groups pass, 0 failures
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Code fix | Looked for code to change that would fix the crash | No code caused the crash — stack frames were all in Mojo runtime | Check stack frames first; if no repo frames, skip code investigation entirely |
| Full workflow rerun | Would re-run all 32 test groups | Wastes CI minutes on passing jobs | Always use `--failed` flag to limit rerun to only failing jobs |

## Results & Parameters

### Key Command

```bash
# Re-trigger only failed jobs
gh run rerun <RUN_ID> --repo <OWNER>/<REPO> --failed
```

### Decision Tree

```text
CI job fails with "mojo: error: execution crashed"?
  |
  +-- Stack frames include repo files?
  |     YES --> Investigate code change, use fix-ci-mojo-test-failure skill
  |     NO  --> Likely transient
  |
  +-- Same test group passes on main CI (same date)?
  |     NO  --> May be a real regression, investigate further
  |     YES --> Definitely transient
  |
  +-- PR has logic changes?
        YES --> Still check stack frames; transient can occur alongside real PRs
        NO  --> Confirmed transient; re-trigger with --failed
```

### Evidence Markers for Transient Crashes

- Only `libKGENCompilerRTShared.so` or `libMojoRuntime.so` in stack trace
- Random test groups fail each run (not the same group every time)
- `main` branch has same crash pattern in recent history (different test group each time)
- Failure appears on cosmetic/comment-only PRs

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #3288 — Core Activations & Data Loaders crash, run 22734969748 | [notes.md](../../references/notes.md) |
