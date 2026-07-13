---
name: inference360-haproxy-stream-reload-validation
description: "Validate Inference360 HAProxy graceful reloads with a loopback in-flight stream harness. Use when: (1) proving stream-safe route reload behavior, (2) adding Warden/gateway reload integration coverage, (3) fixing HAProxy validation cleanup, timeout, or review-gate issues."
category: testing
date: 2026-07-08
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [inference360, haproxy, stream-safe-reload, warden, gateway, validation, pytest, strict-review]
---

# Inference360 HAProxy Stream Reload Validation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-08 |
| **Objective** | Implement LLM360/Inference360 issue #372 by adding integration coverage that proves HAProxy graceful reloads preserve an existing streaming response while new traffic routes to the updated backend. |
| **Outcome** | Successful: PR #382 merged after local/container validation, GitHub CI, and final `/review-pr-strict` unconditional GO on head `ad433fb08cdbcce8070f1adf170e03bffc94a340`. |
| **Verification** | verified-ci |
| **Related skills** | `inference360-warden-autoscaling-boundaries.md`, `inference360-validation-sqsh-harden-wrapper.md`, `pr-rebase-conflict-resolution-patterns.md` |

## When to Use

- An Inference360 Warden, gateway, or HAProxy change claims stream-safe reload behavior.
- Unit tests only verify `haproxy -sf <old-pid>` command shape, but no test holds a real in-flight stream through reload.
- A local host may not have HAProxy installed, so pytest should skip the live integration path while a validation container provides the non-skipped evidence.
- Review or merge automation needs a hard gate: do not merge or enable auto-merge until `/review-pr-strict` returns unconditional GO, not conditional GO.
- HAProxy startup, config validation, or stream harness tests need deterministic cleanup and typed monkeypatch-safe subprocess/socket replacement.

## Verified Workflow

### Quick Reference

```bash
# Real non-skipped harness evidence, run where HAProxy is available.
scripts/run_validation_container.sh -- \
  env UV_CACHE_DIR=/tmp/uv-cache \
  uv run python scripts/validate_haproxy_stream_reload.py --haproxy-bin haproxy

# Focused host tests may skip the real integration path when HAProxy is absent.
env UV_CACHE_DIR=/tmp/uv-cache \
  uv run pytest tests/test_haproxy_stream_reload_validation.py -q

# Full repository gate used before merge.
env UV_CACHE_DIR=/tmp/uv-cache just validate
```

### Detailed Steps

1. Keep the validation harness loopback-only and deterministic. Use two local Python HTTP backends, one named `backend-a` and one named `backend-b`, and bind HAProxy only to loopback addresses.

2. Start HAProxy with real master-worker graceful reload semantics:

   ```text
   haproxy -W -db -S <master-socket>,mode,600,level,admin -f <cfg> -p <pid>
   ```

   Use explicit argv subprocess calls. Do not use `shell=True`.

3. Route the initial HAProxy config to `backend-a`. Open `/stream` through HAProxy, read the first chunk, and hold the response open through a backend server event.

4. Rewrite the HAProxy config to route to `backend-b`, then reload by launching the new HAProxy process with:

   ```text
   -sf <old-pid>
   ```

5. Verify new traffic after reload reaches `backend-b` by calling `/who` and checking the response body.

6. Release the original stream and verify every stream chunk still came from `backend-a`, for example:

   ```text
   backend-a:chunk-0
   backend-a:chunk-1
   backend-a:chunk-2
   backend-a:chunk-3
   ```

7. Clean up both HAProxy processes and both backend servers in a `finally` block. If HAProxy startup readiness times out, terminate the spawned process before raising.

8. Wrap HAProxy config validation failures in a domain `ValidationError` that includes stdout/stderr context instead of leaking a raw `subprocess.CalledProcessError`.

9. Test both the harness and failure behavior:
   - missing HAProxy binary skips or reports cleanly;
   - rendered loopback config is deterministic;
   - HAProxy startup timeout terminates the spawned process;
   - config validation errors are wrapped with useful context;
   - the real integration path runs when HAProxy and loopback sockets are available.

10. Document the operator validation command in the Warden lifecycle debugging runbook, operator script contracts runbook, and design contract when this harness becomes part of the platform validation surface.

11. Run strict review before merge and wait for unconditional GO. A conditional GO is still a merge blocker for this workflow.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Command-shape-only coverage | Verified HAProxy process replacement arguments without holding an in-flight stream | `-sf <old-pid>` command shape alone does not prove client-observed stream continuity | Add a real loopback HAProxy harness that streams, reloads, routes new traffic, then finishes the old stream |
| Startup timeout without cleanup | Spawned HAProxy and raised on readiness timeout | The process could be left running after the exception | Call `_terminate_process(process)` before raising timeout errors and add regression coverage |
| Raw config validation exception | Let `subprocess.CalledProcessError` surface from HAProxy config validation | The operator saw a low-level subprocess failure without harness context | Wrap validation failures in `ValidationError` with stdout/stderr context |
| Dead stream gate event | Kept a `first_chunk_sent` event and hard-coded `10.0` timeout | The event was unused and the timeout ignored configured harness parameters | Propagate `stream_timeout_seconds` onto the backend server and remove dead synchronization |
| Object monkeypatches broke mypy | Monkeypatched `harness.subprocess` and `harness.socket` objects directly | The monkeypatch shape conflicted with static typing | Patch module-path strings such as `scripts.validate_haproxy_stream_reload.subprocess.Popen` |
| Cross-thread errors stored in a list | Shared stream errors through `list[str]` and commented around analysis-sensitive post-reload handling | Code Quality flagged the path as unreachable and the synchronization was less explicit | Use `SimpleQueue[str]` plus `_drain_stream_errors()` before reload and after stream join |
| Conditional strict-review GO treated as enough | Considered merge readiness before all review dimensions returned unconditional GO | Conditional GO still means known conditions remain before merge | Do not merge or auto-merge until `/review-pr-strict` returns unconditional GO across all dimensions |

## Results & Parameters

### Harness Command Shape

```text
haproxy -W -db -S <master-socket>,mode,600,level,admin -f <cfg> -p <pid>
haproxy -W -db -S <master-socket>,mode,600,level,admin -f <updated-cfg> -p <new-pid> -sf <old-pid>
```

### Verified Commands

```bash
scripts/run_validation_container.sh -- \
  env UV_CACHE_DIR=/tmp/uv-cache \
  uv run python scripts/validate_haproxy_stream_reload.py --haproxy-bin haproxy

env UV_CACHE_DIR=/tmp/uv-cache \
  uv run pytest tests/test_haproxy_stream_reload_validation.py -q

env UV_CACHE_DIR=/tmp/uv-cache just validate
```

### Observed Results

| Check | Result |
|-------|--------|
| Real validation-container harness | Passed with `initial_stream_lines` all `backend-a:chunk-0..3`, `new_response=backend-b`, `reloaded_backend=backend-b`, and changed HAProxy PID |
| Focused host pytest | `4 passed, 1 skipped`; the real integration path skipped locally when HAProxy was absent |
| Ruff | passed |
| Mypy | passed |
| `git diff --check` | passed |
| Full validation | `1275 passed, 10 skipped`, coverage `82.46%` |
| GitHub CI for PR #382 | passed: validate, pre-commit, secrets, sast, python-sca, and CodeQL |
| Strict review gate | Six dimensions returned unconditional GO on head `ad433fb08cdbcce8070f1adf170e03bffc94a340` |

### PR Evidence

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | Issue #372, PR #382 | PR merged at `2026-07-08T04:10:06Z` with merge commit `4c9f3571b4b140507dcffd8cb6772c6e2facadeb`, closing issue #372. |

### Operator Documentation Locations

```text
docs/runbooks/warden-lifecycle-debugging.md
docs/runbooks/operator-script-contracts.md
docs/inference360-design.md
```

Ordinary local pytest may skip the live HAProxy integration test when the HAProxy binary is absent. The non-skipped real harness evidence should come from the validation container or another environment with HAProxy and loopback sockets available.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | PR #382 for issue #372, verified-ci | Real HAProxy non-skipped harness verified in the validation container; focused local pytest skipped the live path on a host without HAProxy; full validation and GitHub CI passed before merge. |
