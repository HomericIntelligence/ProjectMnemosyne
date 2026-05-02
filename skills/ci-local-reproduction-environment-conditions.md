---
name: ci-local-reproduction-environment-conditions
description: "Reproduce CI-only test failures locally by replicating all three CI environment conditions simultaneously: cold pixi cache, UID mismatch, and no-TTY. Use when: (1) tests pass locally 100% but fail in CI, (2) you've ruled out code-level differences, (3) CI uses Podman with pixi and named volumes."
category: ci-cd
date: 2026-04-11
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - ci
  - debugging
  - flakiness
  - podman
  - docker
  - reproduction
  - uid
  - tty
  - pixi
---

# CI Local Reproduction: Environment Conditions

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-11 |
| **Objective** | Reproduce CI-only test failures locally by replicating CI environment conditions |
| **Outcome** | Success — crash previously declared "non-reproducible locally" reproduced immediately, 100% deterministic, by combining all three CI conditions |
| **Verification** | verified-local |

## When to Use

- Tests pass locally 100% of the time but fail consistently in CI
- You've been told the failure is "non-deterministic" or "JIT flakiness" but haven't tried replicating CI conditions
- CI uses Podman containers with pixi for dependency management and named volumes for caching
- The failure involves permission errors, cache misses, or TTY-dependent behavior
- An issue document incorrectly concluded the crash is non-reproducible

## Verified Workflow

### Quick Reference

```bash
# Step 1: Delete ALL named volumes (simulate cold pixi cache)
podman compose down -v

# Step 2: Start container with CI runner UID
USER_ID=1001 GROUP_ID=1001 podman compose up -d

# Step 3: Run test with no-TTY flag (same as CI)
USER_ID=1001 GROUP_ID=1001 podman compose exec -T projectodyssey-dev bash -c \
  "cd /workspace && mojo run tests/path/to/test.mojo"
```

### Detailed Steps

1. **Identify the three CI-specific conditions** that differ from your local environment:
   - **Cold pixi cache**: CI creates fresh named volumes every run; locally volumes persist
   - **UID mismatch**: CI runner typically uses UID 1001, but container image is built with UID 1000
   - **No TTY**: CI uses `podman compose exec -T` (the `-T` flag disables TTY allocation)

2. **Verify your CI configuration** to confirm the exact values:

   ```bash
   # Check what UID the CI runner uses (look in your CI workflow YAML)
   grep -r "USER_ID\|GROUP_ID\|uid\|user:" .github/workflows/
   # Check compose exec calls
   grep -r "exec -T\|compose exec" .github/workflows/ justfile
   ```

3. **Delete all named volumes** to simulate cold cache:

   ```bash
   podman compose down -v
   # Verify volumes are gone
   podman volume ls
   ```

4. **Start container with CI UID** (not your local UID):

   ```bash
   USER_ID=1001 GROUP_ID=1001 podman compose up -d
   # Wait for container to be healthy
   podman compose ps
   ```

5. **Run the failing test with no-TTY** (the `-T` flag):

   ```bash
   USER_ID=1001 GROUP_ID=1001 podman compose exec -T <service-name> bash -c \
     "cd /workspace && <test command>"
   ```

6. **If still not reproducing**, check for additional differences:
   - Environment variables set in CI but not locally (`CI=true`, `GITHUB_ACTIONS=true`)
   - GitHub Actions runner resource limits (memory, CPU)
   - Filesystem differences (overlay vs native)

   ```bash
   # Add CI env vars explicitly
   USER_ID=1001 GROUP_ID=1001 podman compose exec -T <service-name> bash -c \
     "export CI=true GITHUB_ACTIONS=true && cd /workspace && <test command>"
   ```

7. **Read the full stack trace**, not just the error summary:
   - `execution crashed` is a symptom, not a cause
   - The actual cause (permission error, missing file, segfault) appears in the stack trace
   - `fortify_fail_abort` or `__fortify_fail` in the trace indicates a buffer overflow or permission violation

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Run tests with warm cache + UID 1000 | 10 parallel agents ran the same test commands locally | All passed because agents used warm pixi cache and matching UID — not replicating CI | Never declare a test "passes locally" without verifying you're running under identical conditions |
| Conclude "non-deterministic JIT flakiness" | Read only the `execution crashed` message, not full stack trace | The error message is the symptom; the real cause (permission error) was in the stack trace | Always read the complete stack trace before forming a hypothesis |
| Declare crash "non-reproducible locally" | Filed issue doc concluding the crash couldn't be reproduced | Cold cache + UID mismatch + no-TTY was never tried simultaneously | Don't conclude non-reproducible until you've replicated ALL CI conditions at once |
| Fix one condition at a time | Tried only cold cache, or only UID mismatch | Each condition alone may not trigger the crash; all three together are required | Replicate ALL differing conditions simultaneously, not one at a time |

## Results & Parameters

### CI Environment Variables (Podman-based CI with pixi)

```bash
# Typical CI configuration
USER_ID=1001          # CI runner UID (differs from container build UID 1000)
GROUP_ID=1001         # CI runner GID
# Named volumes for pixi cache are fresh on each run (created with `docker compose up`)
# compose exec uses -T flag (no TTY)
```

### Expected Behavior

When all three conditions are correctly replicated:
- A previously "non-reproducible" crash reproduces immediately and 100% deterministically
- The full stack trace reveals the actual root cause (permission errors, missing cache dirs, etc.)
- `fortify_fail_abort` in the stack trace points to a buffer overflow or permission violation from UID mismatch

### Verification Approach That Confirmed the Method

```bash
# WRONG: Warm cache + UID 1000 + TTY (your local defaults)
podman compose exec projectodyssey-dev bash -c "mojo run tests/failing_test.mojo"
# Result: PASSES — false confidence

# RIGHT: Cold cache + UID 1001 + no TTY (CI conditions)
podman compose down -v
USER_ID=1001 GROUP_ID=1001 podman compose up -d
USER_ID=1001 GROUP_ID=1001 podman compose exec -T projectodyssey-dev bash -c \
  "cd /workspace && mojo run tests/failing_test.mojo"
# Result: CRASHES — reproducible, now debuggable
```

### Environment Condition Checklist

| Condition | Local Default | CI Default | How to Replicate Locally |
| ----------- | -------------- | ------------ | -------------------------- |
| Pixi cache | Warm (persistent volumes) | Cold (fresh volumes each run) | `podman compose down -v` before starting |
| Container UID | 1000 (matches image build UID) | 1001 (CI runner UID) | `USER_ID=1001 GROUP_ID=1001 podman compose up -d` |
| TTY allocation | TTY present | No TTY (`-T` flag) | Use `podman compose exec -T` instead of `exec` |
| CI env vars | Not set | `CI=true`, `GITHUB_ACTIONS=true` | Add to exec command if needed |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Reproducing `fortify_fail_abort` crash declared non-reproducible in `jit-fortify-buffer-overflow.md` | Cold cache + UID 1001 + `-T` flag combined triggered crash 100% deterministically |
