---
name: ci-cd-gated-debug-instrumentation-workflow-dispatch
description: "Use when: (1) you have debug-only CI instrumentation (gdb wrapper, valgrind, strace, coredump capture, verbose tracing) that adds latency or noise to every PR/push run, (2) you want to preserve the ability to capture debug data on demand for an upstream bug repro without changing the underlying test runner script, (3) the instrumentation is already gated on an env var inside the runner (e.g. MOJO_TEST_UNDER_GDB) and you need to flip that env var off by default but keep an opt-in path, (4) you want a manual one-click toggle in the GitHub Actions UI (workflow_dispatch input) that drives behavior without touching repo source on every PR, (5) you need an opt-in (default false) rather than opt-out (default true) for cost/noise control, (6) the same env var must propagate to every step in a job (build, exec, container shell-out) — gate at job-level env not step-level if:."
category: ci-cd
date: 2026-05-17
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [workflow_dispatch, github-actions, ci-gating, debug-instrumentation, gdb, opt-in, env-var, manual-trigger, upstream-bug-repro, coredump]
---

# Gated Debug Instrumentation via workflow_dispatch Input

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-17 |
| **Objective** | Disable always-on debug CI instrumentation (gdb -batch wrapper capturing ELF cores for libKGEN JIT crashes — modular/modular#6413) on routine PR/push runs while preserving the ability to manually re-enable it for upstream bug repros |
| **Outcome** | Successful — ProjectOdyssey PR #5411 (commit 71a6323f) gated 6 CI jobs behind a `workflow_dispatch` input defaulting to `false`. Normal PR/push runs revert to `pixi run mojo` (faster, no gdb noise); manual `gh workflow run ... -f enable_gdb_cores=true` still captures cores when needed. |
| **Verification** | verified-ci — applied to ProjectOdyssey PR #5411; CI ran with gate disabled, confirming gdb wrapper is no longer invoked on routine runs |

## When to Use

- Adding debug-only instrumentation (gdb, valgrind, strace, coredump capture, verbose logging) to existing CI that's already enabled and now slows every run
- Need to keep instrumentation available for manual debugging without slowing every PR/push
- Want zero changes to the underlying test runner script — gate purely at the workflow YAML level via env var
- Investigating an upstream bug (e.g. compiler crash) where you occasionally need fresh repro data on demand
- The test runner / justfile / shell script already branches on an env var (e.g. `MOJO_TEST_UNDER_GDB=1`)
- You want default-off (opt-in) behavior — every PR is fast, only manual dispatch is slow
- Multiple jobs in the same workflow need the same gate — job-level `env:` is the right scope

## Verified Workflow

### Quick Reference

```yaml
# In .github/workflows/<workflow>.yml — declare workflow_dispatch input alongside pull_request/push
on:
  workflow_dispatch:
    inputs:
      enable_gdb_cores:
        description: 'Capture gdb core dumps for libKGEN JIT crashes (modular/modular#6413)'
        required: false
        default: false
        type: boolean
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  comprehensive-mojo-tests:
    runs-on: ubuntu-latest
    # Job-level env: every step in this job sees MOJO_TEST_UNDER_GDB
    env:
      MOJO_TEST_UNDER_GDB: ${{ (github.event_name == 'workflow_dispatch' && inputs.enable_gdb_cores) && '1' || '0' }}
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: just test-mojo  # Reads MOJO_TEST_UNDER_GDB internally
```

```bash
# Runner-side gate (justfile recipe, shell script, etc.) — already in place, unchanged
if [ "${MOJO_TEST_UNDER_GDB:-0}" = "1" ]; then
    bash "$REPO_ROOT/scripts/mojo-under-gdb.sh" "$@"
else
    pixi run mojo "$@"
fi
```

```bash
# Manually trigger with gdb capture enabled
gh workflow run comprehensive-tests.yml -f enable_gdb_cores=true --ref <branch>

# Normal PR/push: enable_gdb_cores is null/false, gate evaluates to '0', wrapper not invoked
```

### Step-by-Step

1. **Identify the runner-side gate.** Confirm the test runner (justfile, shell wrapper, pytest conftest) already branches on a known env var. If it doesn't, add that gate to the runner *first* — this skill is about driving an existing env var, not creating one.

2. **Add `workflow_dispatch` to the workflow's `on:` block.** If the workflow already has `pull_request` / `push`, add a sibling `workflow_dispatch` entry. Declare a single typed boolean input with `default: false` and a description that references the upstream bug or rationale.

3. **Wire the input into job-level `env:`.** Place the env var at the *job* level (not the step level) so every step — checkout, build, exec, container shell-out — sees the same value. Use the defensive ternary:

   ```yaml
   env:
     MOJO_TEST_UNDER_GDB: ${{ (github.event_name == 'workflow_dispatch' && inputs.enable_gdb_cores) && '1' || '0' }}
   ```

   The `github.event_name == 'workflow_dispatch'` guard is critical: on `pull_request` and `push`, `inputs.enable_gdb_cores` is null, and older GitHub Actions runner versions evaluated `null && '1' || '0'` ambiguously.

4. **Repeat for every job that runs the instrumented runner.** In ProjectOdyssey this was 6 jobs: Comprehensive Mojo Tests, Configs, Benchmarks, Core Layers, Gradient Checking Tests, Data Utilities Test Suite. The input declaration is shared (one block in `on:`); only the job-level `env:` is per-job.

5. **Verify with a normal PR.** Push the change. The gate should evaluate to `'0'`; the runner should fall through to the non-instrumented branch. Confirm in CI logs that the gdb wrapper is not invoked.

6. **Verify the manual path.** Run `gh workflow run <name> -f enable_gdb_cores=true --ref <branch>`. Confirm the gate evaluates to `'1'` and the wrapper is invoked.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Gate composite action usages | Initially assumed the PR used a `coredump-capture` composite action and went to gate 12 step usages | The branch had no such action — the gdb wrapper was invoked via `MOJO_TEST_UNDER_GDB` env var at job level, not a composite action | Re-read the actual diff before designing the gate; do not assume implementation from memory of earlier commits |
| Gate at step level with `if:` | Considered adding `if: github.event_name == 'workflow_dispatch' && inputs.enable_gdb_cores` to each step that ran gdb | Step-level gates duplicate logic 6× per job, miss the env-var flow into the container, and only block the step from running — they cannot toggle behavior inside a step that always runs | Gate at the highest scope the value is consumed. For env-var-driven runners, that is job-level `env:` |
| Use bare `inputs.X` ternary | Tried `${{ inputs.enable_gdb_cores && '1' || '0' }}` without the event-name guard | On `pull_request` / `push` triggers, `inputs.enable_gdb_cores` is null; the `&&` short-circuit was ambiguous in some runner versions and could produce `''` instead of `'0'` | Always pair `inputs.X` with `github.event_name == 'workflow_dispatch'` to make the expression total over all trigger types |
| Default to `true` for safety | Briefly considered keeping the default `true` so we still got cores during the libKGEN investigation | Defeats the entire purpose — every PR would still pay the gdb cost. The user's explicit request was opt-in, not opt-out | Debug instrumentation gates should be opt-in (`default: false`). If you need cores, dispatch manually; do not impose the cost on every contributor |

## Results & Parameters

- **Applied to:** ProjectOdyssey PR #5411 (commit `71a6323f`)
- **Jobs gated (6 total):**
  - Comprehensive Mojo Tests
  - Configs
  - Benchmarks
  - Core Layers
  - Gradient Checking Tests
  - Data Utilities Test Suite
- **Default behavior (PR/push):** `enable_gdb_cores=false` → `MOJO_TEST_UNDER_GDB=0` → runner uses `pixi run mojo` directly. gdb wrapper is not invoked.
- **Opt-in behavior (`gh workflow run ... -f enable_gdb_cores=true`):** input is true → env evaluates to `'1'` → runner invokes `scripts/mojo-under-gdb.sh` and captures ELF cores for libKGEN JIT crashes.
- **Upstream tracking:** modular/modular#6413 (libKGEN JIT crash — reason debug instrumentation exists)
- **Related rule:** The debug script `scripts/mojo-under-gdb.sh` itself belongs in ProjectHephaestus per the project memory rule (general CI debugging scripts → Hephaestus, not the consumer repo). This skill covers the workflow-level gating pattern, not the script's location.

### Key Design Rules (recap)

1. `default: false` — opt-in, never opt-out
2. Always combine `github.event_name == 'workflow_dispatch'` with `inputs.X` in the ternary
3. Place the env var at job-level `env:`, not step-level — this propagates to all steps including container exec
4. Do not modify the test runner — it should already gate on the env var; this skill only flips the env var
5. One input declaration in `on:` covers all jobs in the workflow; per-job `env:` consumes it
