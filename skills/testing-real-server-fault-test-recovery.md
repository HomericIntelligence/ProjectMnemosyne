---
name: testing-real-server-fault-test-recovery
description: "Plan a credible real-server fault-injection recovery test that can prove both failure and recovery. Use when: (1) replacing a placeholder chaos/resilience test that always passes, (2) kill/restart testing a broker or async service, (3) deciding dedicated-server isolation and skip-versus-fail behavior, (4) validating a reconnect loop through observable end-to-end recovery rather than configuration assertions, (5) reviewing unverified binary, client, lifecycle, or timeout assumptions."
category: testing
date: 2026-07-17
version: "1.0.0"
user-invocable: false
verification: unverified
tags: ["fault-injection", "chaos", "recovery", "real-server", "nats", "red-green", "placeholder-test", "reconnect", "integration-test"]
history: testing-real-server-fault-test-recovery.history
---

# Real-Server Fault-Test Recovery

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-17 |
| **Objective** | Replace false-pass fault tests with isolated kill/degrade/restart/recover tests that demonstrate real system behavior |
| **Outcome** | One planning workflow for placeholder remediation and real broker-recovery testing, with explicit assumption gates |
| **Verification** | unverified — source plans were reviewed but not executed end-to-end |
| **History** | [absorbed placeholder and real-server planning sources](./testing-real-server-fault-test-recovery.history) |

## When to Use

- A resilience or chaos test contains `pass`, `assert True`, or another path that cannot fail
- A test must hard-kill and restart a real broker, server, or process without disrupting the shared test environment
- Recovery needs to prove an async reconnect loop or client lifecycle through an observable effect
- A reviewer identifies unverified claims about client reconnect behavior, server flags, helper paths, retries, or timing

## Verified Workflow

> **Warning:** This is a planning-discipline workflow. Verify the target binary, client source, and actual test behavior before claiming end-to-end validation.

### Quick Reference

```text
1. Start a dedicated server on its own port and state directory.
2. Prove the baseline works, then kill it and observe degradation.
3. Keep a no-restart companion that must stay unhealthy (RED proof).
4. Restart the real server and prove a new end-to-end operation succeeds (GREEN proof).
5. Skip only when the fault cannot run; fail when recovery should occur but does not.
```

### Detailed Steps

1. Read the real client and server source before planning. Confirm reconnect behavior, supported server flags, public configuration overrides, launcher paths, and the test harness's lifecycle semantics.
2. Spawn a dedicated subprocess server with its own port and persistent state directory. Never kill a shared session broker or global test URL.
3. Configure a short reconnect interval through a supported settings or environment override; clear any settings cache that would otherwise silently ignore the override. Prefer this to monkeypatching private task fields.
4. Establish a working baseline, hard-kill the dedicated process, and observe an externally visible degraded state such as a health endpoint becoming non-200.
5. Add a companion that does not restart the server and asserts that recovery never occurs within the budget. A test that cannot go RED is still a placeholder.
6. Restart on the required port and state directory, tolerate the documented transient startup race if one exists, then prove recovery through a new end-to-end operation or health check—not by rereading settings or code.
7. Use a clean skip only when the binary or topology is structurally unavailable. A missing expected recovery is a failure, never a pass.
8. Derive one timeout budget from the configured reconnect interval and keep it in code as the single source of truth. Record any remaining assumptions explicitly for review.

### Worked Example — NATS/JetStream restart

For a NATS service, confirm the installed binary supports the planned `-js` and `-sd` flags with
`nats-server --help`. Start a fresh server on a test port with its own JetStream store. Set the
application's public reconnect-interval environment variable before constructing the client, and
clear the cached settings fixture so the override takes effect.

Kill the process, wait for `/health` to become unavailable, then restart it on the same port and
store directory. Retry startup briefly for a residual store-lock race and poll `/health` for 200.
The no-restart companion must remain unhealthy; a post-restart task lifecycle or health check must
succeed.

### Worked Example — Turning a false-pass placeholder into a real test

Replace the placeholder only after proving its replacement discriminates broken recovery from
working recovery. Temporarily omit restart or disable reconnect and observe a failure; restore the
real path and observe success. If an environment topology cannot exercise the fault, annotate a
clean skip with the specific limitation instead of returning success.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Keep a hardcoded pass | Left a placeholder success path | It cannot detect broken recovery | Every fault test needs a demonstrated RED path |
| Assert design intent | Re-read configuration or a code comment after restart | It proves documentation, not behavior | Assert an observable end-to-end effect |
| Kill the shared broker | Reused the session-wide test service | It destabilized unrelated tests | Use a dedicated process and isolated state |
| Patch private reconnect internals | Replaced tasks or events directly | The test coupled to changing implementation details | Prefer a public settings override and real reconnect loop |
| Treat a free port as a store-ready guarantee | Polled only TCP availability before restart | Persistent-store locks can outlive the socket | Handle documented startup races separately |
| Pass when inapplicable | Converted unavailable topology into green success | It reproduced the false-pass defect | Skip unavailable faults; fail expected recovery failures |

## Results & Parameters

### Review gates

- Binary flags and client reconnect behavior were read from the actual installed/source version.
- The dedicated server, port allocation, state directory, and launcher path are verified.
- Both no-restart RED and restart GREEN scenarios have observable assertions.
- The recovery budget is derived once and the settings override actually reaches the created client.
- Remaining uncertainty, including port TOCTOU and persistent-store races, is explicit rather than hidden in prose.

### Outcome semantics

| Situation | Test result |
|-----------|-------------|
| Required binary/topology cannot exist | Clean skip with reason |
| Fault ran but degradation/recovery assertion fails | Failure |
| No-restart companion recovers | Failure: test does not discriminate |
| Restarted service completes a new observable operation | Green recovery evidence |

## Verified On

| Context | Details |
|---------|---------|
| Odysseus issue #184 and ProjectHermes issue #527 | Plans and source-read findings only; neither full real-server test was executed in CI. |
