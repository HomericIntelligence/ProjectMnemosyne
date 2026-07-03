---
name: testing-env-gated-live-broker-gtest-suite
description: "Pattern for adding a live-broker (NATS/JetStream via docker-compose) gtest integration suite alongside unit tests without destabilizing default presets: tests GTEST_SKIP when the gating env var (e.g. NESTOR_LIVE_NATS_URL) is unset and HARD-FAIL when it is set (no silent pass in CI); a dedicated gtest_discover_tests pass assigns a ctest label (live-nats) with RUN_SERIAL + generous TIMEOUT and the unit-pass negative filter excludes the live suite; the compose file exposes host ports as ${VAR:-default} so it coexists with a developer's local broker. Use when: (1) adding integration tests that need a real broker/server container to cover connect/reconnect/provisioning happy paths excluded from unit coverage, (2) writing broker-bounce (stop/start) tests for disconnect/reconnect callbacks, (3) a bounce test's RAII restore guard runs `docker compose start` — which returns BEFORE the service accepts connections — so the guard must poll readiness (fresh throwaway client connect per attempt) before returning, because CTest schedules by recorded cost, NOT declaration order (RUN_SERIAL prevents overlap, not reordering), (4) choosing stop+start over restart to get a deterministic disconnected window, (5) using first-publish-success as the provisioning-readiness probe when provisioning and publish serialize on one mutex."
category: testing
date: 2026-07-03
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [integration-tests, gtest, ctest-labels, docker-compose, nats, jetstream, env-gated, skip-when-unset, hard-fail-when-set, broker-bounce, run-serial, ctest-scheduling, readiness-polling, raii-guard, port-collision, ci-job]
---

# Testing: Env-Gated Live-Broker GTest Suite

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-03 |
| **Objective** | Add a live NATS+JetStream integration suite covering the broker-dependent regions of a C++ NATS client (connect success, reconnect loop, callbacks, stream provisioning, publish paths) as a separate CI job outside the unit coverage gate (ProjectNestor issue #119 / PR #120) |
| **Outcome** | 8-test suite green locally under ASan/UBSan across repeated runs; default presets unaffected (tests skip without env); separate CI job folded into the canonical test aggregate; three review-flagged flake/UB hazards fixed |
| **Verification** | verified-local — repeated local runs green in both env configurations; CI validation pending on ProjectNestor PR #120 |

## When to Use

- Adding integration tests that require a real broker/server container (NATS, Kafka, Redis...) to exercise connect/reconnect/provisioning paths that unit tests exclude from coverage.
- Writing broker-bounce tests (stop/start mid-test) for disconnect/reconnect callback coverage.
- A bounce test restores the broker via an RAII guard and other tests connect single-shot — ordering hazard (see Step 6).
- Deciding between docker-compose, GitHub `services:`, and testcontainers for a C++ repo that already runs docker in CI.

## Verified Workflow

### Quick Reference

```yaml
# compose: overridable host ports so it coexists with a local broker
services:
  nats:
    image: nats:2.12-alpine
    command: ["-js", "-m", "8222"]
    ports:
      - "${NESTOR_NATS_TEST_PORT:-4222}:4222"
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "-", "http://127.0.0.1:8222/healthz"]
      interval: 2s
      timeout: 2s
      retries: 15
# docker compose -f test/docker/docker-compose.nats.yml up -d --wait
```

```cmake
# unit pass: append *NatsClientLive* to the negative filter
# extra discovery pass for the live label:
gtest_discover_tests(${PROJECT_NAME}_tests
  DISCOVERY_MODE PRE_TEST
  TEST_FILTER "*NatsClientLive*"
  TEST_PREFIX "live."
  PROPERTIES LABELS "live-nats" TIMEOUT 180 RUN_SERIAL TRUE
)
```

```bash
# CI job (separate from unit coverage gate):
ctest --output-on-failure -L live-nats --no-tests=error   # label typo must fail, not pass
```

### Detailed Steps

1. **Gating semantics: skip-when-unset, hard-fail-when-set.** Every test starts by checking the env var (`NESTOR_LIVE_NATS_URL`); unset → `GTEST_SKIP()` (default presets stay green for developers without docker). The CI job SETS the var, so an unreachable broker is a hard failure — no silent pass. Put the skip check directly in each TEST body, never in a fixture helper (GTEST_SKIP only aborts the current function).
2. **Compose over testcontainers/`services:`.** A checked-in compose file gives one identical command locally and in CI (`up -d --wait` blocks on the healthcheck); testcontainers-cpp would add a vendored dependency for no benefit. Expose host ports as `${VAR:-default}` — a fixed 4222 collided with the developer machine's local NATS on first run.
3. **Fourth discovery pass for the label.** Extend the unit pass's negative gtest filter to exclude the live suite, then add a `gtest_discover_tests` pass with `TEST_FILTER "*NatsClientLive*"`, `LABELS "live-nats"`, `TIMEOUT 180`, `RUN_SERIAL TRUE`. RUN_SERIAL stops `ctest -j N` interleaving bounce tests with other live tests on the shared broker.
4. **Provisioning-readiness probe = first successful publish.** When background provisioning (jsCtx + streams + subscription) and `publish()` serialize on one mutex, `wait_for([&]{ return client.publish(probe_subject, ...); }, 30s)` proves the whole provisioning chain completed — no test hooks needed. Subject uniqueness per call (timestamp+rng suffix) keeps runs collision-free on a persistent broker.
5. **Bounce with stop+start, not restart.** `docker compose restart` races the disconnect observation (client may reconnect before the observing poll). `stop` → assert disconnected (deterministic: no broker to reconnect to) → `start` → assert reconnected → assert publish recovers (re-provisioning).
6. **Restore guard must poll readiness — CTest order is NOT declaration order.** CTest schedules by recorded test cost from prior runs, so a bounce test can run FIRST locally; RUN_SERIAL prevents overlap, not reordering. `docker compose start` returns before the broker accepts connections, so an RAII restore guard that just runs `start` leaks an unready broker into whatever single-shot-connect test runs next. In the guard destructor, after `start` succeeds, poll with a fresh throwaway client per attempt (`connect()` then `close()` to reap the client's background retry thread) under a generous `wait_for` (60s); `ADD_FAILURE` if never ready.
7. **Handler assertions filter by unique subject.** A wildcard subscription (`hi.research.>`) also receives the readiness-probe publishes — assert on the uid-suffixed subject, never on first-received message.
8. **Separate CI job, aggregated.** New job mirrors existing test sub-jobs (Release build, compose up --wait, `ctest -L live-nats --no-tests=error`, `if: always()` compose down), added to the canonical `test` aggregate's `needs` + result loop — gating without touching branch protection, and explicitly outside the unit coverage gate.
9. **Verify both configurations locally.** With broker + env: all live tests pass, twice (second run proves bounce tests restored broker state). Without env: full default suite green, live tests report Skipped, zero live tests under the unit label (`ctest -L unit -N | grep -c Live` → 0).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fixed host ports in compose | `"4222:4222"` hard-coded | Collided with the developer machine's local NATS on the very first `up` | Expose host ports as `${VAR:-default}`; defaults keep CI unchanged |
| `docker compose restart` for bounce | Single restart command around the disconnect assertion | Restart window races the 100 ms `is_connected` poll; client can reconnect before the disconnect is observed | Use stop → assert disconnected → start → assert reconnected: each phase is deterministic |
| Restore guard returning right after `compose start` | RAII guard destructor ran `start` and returned | `start` (unlike `up --wait`) returns before the broker accepts connections; CTest cost-based scheduling can put a single-shot 500 ms-timeout connect test immediately after → flake | Poll readiness in the guard (fresh client connect per attempt, 60s budget) so scheduling order is irrelevant |
| Relying on declaration order to run bounce tests last | Bounce tests declared last in the file | CTest schedules by recorded cost from prior runs, not declaration order; RUN_SERIAL only prevents overlap | Never encode ordering assumptions; make every test tolerate running after a bounce |
| Asserting on first handler-received message | Handler test assumed first delivery was the test message | Wildcard subscription also receives readiness-probe publishes | Filter received messages by uid-suffixed subject |

## Results & Parameters

| Parameter | Verified Value |
|-----------|----------------|
| Broker image | `nats:2.12-alpine`, `command: ["-js", "-m", "8222"]`, wget healthz healthcheck (2s interval, 15 retries) |
| Gating env vars | `NESTOR_LIVE_NATS_URL` (suite), `NESTOR_LIVE_NATS_COMPOSE` (bounce tests only; extra skip) |
| ctest wiring | label `live-nats`, prefix `live.`, `TIMEOUT 180`, `RUN_SERIAL TRUE`; unit filter appends `:*NatsClientLive*` |
| CI invocation | `ctest --output-on-failure -L live-nats --no-tests=error` after `docker compose up -d --wait`; `down -v` under `if: always()` |
| Readiness probes | provisioning: first publish success (30s wait_for); broker restore: throwaway client connect/close per attempt (60s) |
| Poll helper | `wait_for(pred, timeout)` at 100 ms interval |
| Suite runtime | ~14-17s for 8 tests (bounce tests ~7-9s each); rest sub-second |
| Local verification | 8/8 green under ASan/UBSan debug preset, repeated runs; 181/181 default suite with live tests Skipped when env unset |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectNestor | Issue #119, PR #120 | Live NATS+JetStream suite; three review-flagged hazards (skip-in-helper, null getenv, restore-guard readiness) fixed and re-verified locally; CI pending |
