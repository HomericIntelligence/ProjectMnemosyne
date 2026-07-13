---
name: inference360-warden-autoscaling-boundaries
description: "Plan Inference360 Warden autoscaling without creating a second scheduler or lifecycle owner. Use when: (1) adding per-model endpoint scale-out/scale-in policy, (2) deciding Warden, Registry, gateway, and Slurm ownership for autoscaling, (3) writing tests for draining and job-class isolation."
category: architecture
date: 2026-07-07
version: "1.1.0"
user-invocable: false
verification: unverified
history: inference360-warden-autoscaling-boundaries.history
tags:
  - inference360
  - warden
  - autoscaling
  - slurm
  - h200
  - registry
  - gateway
  - haproxy
  - stream-safe-reload
  - clock-boundary
  - job-class-isolation
  - lifecycle
---

# Inference360 Warden Autoscaling Boundaries

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-07 |
| **Objective** | Preserve Inference360's H200 Slurm lifecycle boundaries while planning Warden autoscaling for model endpoints: scale out when a model's endpoints stay at or above 80% usage for a sustained period, default 30 seconds; scale in when removing one endpoint would keep remaining endpoints below 50% usage. |
| **Outcome** | Architecture and test-planning guidance only. PR #365 review added concrete implementation guardrails for persisted release clocks, gateway readiness, and stream-safe HAProxy reload coverage. |
| **Verification** | unverified |
| **History** | [changelog](./inference360-warden-autoscaling-boundaries.history) |
| **Related skills** | `inference360-warden-lifecycle-gpt2-cleanup.md`, `inference360-module-scope-preserve-cli-boundaries.md`, `documentation-architecture-registry-gateway-warden-contracts.md` |

Inference360 is a manifest-driven internal H200 Slurm inference platform. Slurm remains the scheduler of record. Warden remains the lifecycle owner for Slurm-backed endpoints and route publication. Autoscaling should extend those contracts, not introduce Kubernetes, a separate autoscaler authority, or a second control plane.

## When to Use

- You are planning or implementing Warden autoscaling for model endpoints in Inference360.
- A design proposes scale-out or scale-in behavior based on endpoint utilization thresholds.
- Ownership between Warden, Registry, HAProxy/gateway, Scheduler/Slurm, manifests, and job classes is unclear.
- Tests need to prove sustained threshold timing, draining, route publication, and job-class isolation without depending on live Slurm.
- A review needs to reject designs where HAProxy owns lifecycle, Scheduler mutates routes, or autoscaling state crosses model/job-class boundaries.
- Autoscale code persists delayed release intent timestamps or exposes test clocks such as `now`.
- Gateway publication claims READY after HAProxy startup or reload without proving the operation succeeded.
- A stream-safe reload claim is backed only by HAProxy command-shape unit tests and not by an in-flight streaming validation.

<!-- Validator compatibility: ## Verified Workflow -->
## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until implementation and CI confirm it.

### Quick Reference

```text
Default scale-out:
- Per model/job class, if all routeable ready endpoints for that model are at >=80% usage
  for a sustained 30 seconds, Warden starts one more endpoint through existing
  allocate/start/register lifecycle paths and publishes routeable state when ready.

Default scale-in:
- Per model/job class, if removing one endpoint would keep the remaining routeable ready
  endpoints below 50% usage, Warden marks one endpoint non-routeable/draining, publishes
  updated routes, waits for active work to finish naturally, then stops and deallocates it
  through existing lifecycle paths.

Ownership:
- Warden decides lifecycle and publishes route state.
- Registry stores observed endpoint/runtime state.
- HAProxy/gateway consumes routeable backend state and load-balances ready endpoints.
- Slurm remains scheduler of record.
- Scheduler/Slurm must not mutate routes.

Implementation review gates:
- Keep monotonic threshold timing separate from persisted wall-clock release timestamps.
- Gateway READY must fail closed if initial HAProxy start or reload fails.
- Stream-safe reload claims need an integration harness with a live in-flight stream.
```

### Detailed Steps

1. Start from the Inference360 repo contract. Read `README.md`, `AGENTS.md`, and `docs/inference360-design.md`; for module-boundary planning also read `docs/issue-346-module-scope-plan.md`.

2. Model autoscaling as a Warden lifecycle extension. Warden should allocate, start, stop, and deallocate Slurm-backed endpoints using existing lifecycle paths. Do not add Kubernetes, a sidecar control plane, or an independent autoscaler authority.

3. Keep policy manifest/config driven. Define thresholds and windows through checked-in manifests, config files, or explicit CLI/config inputs. Do not add new repository-behavior environment variables for autoscaling policy.

4. Preserve component boundaries:

   | Component | Autoscaling responsibility |
   |-----------|----------------------------|
   | Warden | Owns lifecycle decisions, starts/stops endpoints, marks endpoints draining, publishes route state |
   | Registry | Stores observed endpoint readiness, lifecycle state, usage observations, and routeable/draining state |
   | HAProxy/gateway | Consumes routeable ready backend state and load-balances user traffic |
   | Slurm/Scheduler | Schedules and manages jobs as the scheduler of record |
   | Manifests/config | Define desired service shape and autoscaling policy |

5. Enforce job-class isolation before coding policy. Autoscaling decisions, endpoints, routes, ports, labels, metrics, dashboards, benchmark configuration, promotion gates, and runtime state must remain scoped per model/job class. A busy model must not cause another model or job class to scale.

6. Implement scale-out against sustained observations, not a single spike. For the default policy, only start one more endpoint when the model's current routeable ready endpoints have been at or above 80% usage for 30 seconds. Add cooldown or in-flight scaling guards only if the current lifecycle needs them to avoid duplicate starts.

7. Implement scale-in as drain-first lifecycle. Pick one endpoint for removal only when the remaining routeable ready endpoints would stay below 50% usage. Mark the chosen endpoint non-routeable/draining, publish updated routes so it receives no new work, preserve its lifecycle state while active work drains, then stop and deallocate it through Warden.

8. Write tests first with fakes. Use fake Warden/Registry/runner observations rather than live Slurm. Key tests:

   - sustained scale-out threshold with the default 30 second window;
   - no early scale-out before the sustained window completes;
   - scale-in only when remaining endpoints would stay below 50%;
   - draining endpoints are excluded from new routes while lifecycle state is preserved;
   - job-class isolation for observations, endpoints, routes, metrics, and policy state;
   - no cross-module boundary violations, especially HAProxy owning lifecycle or Scheduler mutating routes.

9. Separate timing domains before persisting autoscale release intent. Use a monotonic clock for sustained threshold windows and cooldown math. Use an explicit wall-clock timestamp for `release_after` and persisted audit state. Tests that inject `now=0`, `now=32`, or another monotonic value must either also inject `wall_time` or assert that persisted timestamps are real wall-clock times, not Unix-epoch artifacts.

10. Make gateway route publication fail closed. If `publish_gateway_routes` calls the HAProxy initial-start path and startup marks the gateway unavailable, do not later overwrite it with `status: running` or gateway health `READY`. Cover both no-existing-process and stale-process restart branches; command-shape coverage for `-sf` is not enough.

11. Prove stream-safe reloads at the right layer. Unit tests can check HAProxy master-worker command shape, stats aggregation, and old worker retention, but a claim that existing streams survive reload needs a real HAProxy or documented operator harness that holds an in-flight streaming response, reloads routes, and verifies the existing stream completes while new traffic uses the updated backend set.

12. Keep verification honest. Until implementation and CI exist, describe this as architecture/planning guidance and keep verification `unverified`. If follow-up issues are filed instead of fixed, keep the skill as proposed guidance and cite the issue numbers in results rather than claiming validation.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Separate autoscaler authority | Treating autoscaling as a new scheduler/control-plane concept | It would split lifecycle ownership away from Warden and compete with Slurm as scheduler of record | Autoscaling belongs inside Warden lifecycle orchestration |
| HAProxy-owned lifecycle | Letting the gateway decide when to start or stop endpoints | HAProxy should consume routeable ready backend state; it must not allocate Slurm jobs or own lifecycle | Warden decides lifecycle and publishes route state; HAProxy load-balances ready endpoints |
| Scheduler mutates routes | Having Scheduler/Slurm update gateway route state directly | Scheduler is the job scheduler of record, not the route-policy owner | Warden publishes route state based on lifecycle and Registry observations |
| Environment-driven policy | Adding new repository-behavior environment variables for thresholds and timing | Repo guidance requires manifest/config driven lifecycle behavior with explicit inputs | Use manifests, config files, or explicit CLI/config inputs |
| Immediate scale-in shutdown | Stopping an endpoint as soon as policy says capacity can shrink | Active work could be interrupted and route state could point at a terminating backend | Mark draining/non-routeable first, publish routes, wait for natural drain, then stop |
| Cross-job-class pooling | Sharing endpoint, route, metric, or policy state across job classes | Inference360 requires strict job-class isolation | Keep decisions and runtime state scoped per model/job class |
| Reused monotonic test time as wall time | Passed `now` through both autoscale threshold logic and persisted `release_after` wall-clock construction | Tests that used `now=32` could persist timestamps near 1970 while still passing threshold assertions | Split monotonic timing from persisted wall-clock timestamps and assert persisted `release_after` |
| READY after failed initial HAProxy start | Let route publication call initial HAProxy startup, then unconditionally set gateway status to running and health to READY | A missing HAProxy binary or failed startup could be masked by later state updates | Treat startup/reload success as a precondition for READY and route-count publication |
| Stream safety proved by command shape only | Verified `haproxy -sf` command construction but did not hold a real in-flight stream through reload | Command shape does not prove client-observed stream continuity | Add live HAProxy/in-flight stream integration coverage or an explicit operator validation harness |

## Results & Parameters

### Default Policy Values

| Parameter | Proposed default | Notes |
|-----------|------------------|-------|
| Scale-out usage threshold | `>=80%` | Applies per model/job class to routeable ready endpoints |
| Scale-out sustained window | `30 seconds` | Must be sustained; a single spike is insufficient |
| Scale-in capacity threshold | `<50%` after removing one endpoint | Remove only when remaining endpoints would stay below threshold |
| Scale-in behavior | drain first, then stop | Exclude from new routes before lifecycle teardown |
| Policy source | manifest/config or explicit CLI/config input | Do not introduce repository-behavior environment variables |
| Test substrate | faked Warden/Registry/runner observations | Do not require live Slurm for unit behavior |

### Boundary Checklist

```text
- Slurm remains scheduler of record.
- Warden owns lifecycle: allocate/start/stop/deallocate and route publication.
- Registry stores observed lifecycle/readiness/usage/routeable state.
- HAProxy/gateway consumes routeable ready backend state only.
- Scheduler/Slurm does not mutate routes.
- No Kubernetes v1 requirement.
- No shared jobs, routes, ports, labels, metrics, dashboards, benchmark config,
  promotion gates, or runtime state across job classes.
- Scale-in marks non-routeable/draining before shutdown.
- Verification remains unverified until implementation and CI exist.
```

### PR #365 Review Follow-ups

| Issue | Review finding | Why it matters |
|-------|----------------|----------------|
| LLM360/Inference360#370 | Fix Warden gateway READY state after initial HAProxy start failure | Gateway readiness must fail closed when HAProxy cannot start |
| LLM360/Inference360#372 | Add integration coverage for stream-safe HAProxy reloads | Stream continuity is a behavioral property, not just a command-line property |
| LLM360/Inference360#373 | Separate autoscaling monotonic clock from persisted release wall time | Persisted release state must use real wall time and avoid Unix-epoch artifacts from test clocks |
| LLM360/Inference360#371 | Clean up minor Warden autoscaling audit findings from PR #365 | Keeps runbook, logging, and validation-preview details aligned |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | Warden autoscaling planning session on 2026-07-06 | Architecture/planning guidance only; not implemented or tested end-to-end. |
| LLM360/Inference360 | Strict review of PR #365 on 2026-07-07 | Follow-up issues #370, #371, #372, and #373 were filed. The implementation guardrails remain unverified until those issues land and pass CI. |
