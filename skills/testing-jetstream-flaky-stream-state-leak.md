---
name: testing-jetstream-flaky-stream-state-leak
description: "Planning-reasoning checklist for diagnosing flaky NATS/JetStream integration tests that assert an exact message count and intermittently OVER-count (e.g. `assert 2 == 1`) only under full-suite or repeated runs. Key correction: classify the subscriber type FIRST — a core NATS push subscriber (`nc.subscribe(...)`) receives live fan-out only and NEVER reads a JetStream stream, so purging streams is inert for it; only a JetStream consumer (`js.pull_subscribe`/`js.subscribe`) reads stream history. Use when: (1) a test asserts `len(received) == N` on a `nc.subscribe(...)` callback and flakes; (2) you are tempted to purge a JetStream stream to fix it — STOP and classify first; (3) tests use broad wildcard subjects (`hi.agents.>`, `hi.>`) and/or a fixed `asyncio.sleep` before the count assert."
category: testing
date: 2026-06-19
version: "2.0.0"
verification: unverified
user-invocable: false
history: testing-jetstream-flaky-stream-state-leak.history
tags:
  - flaky
  - integration-test
  - jetstream
  - nats
  - test-isolation
  - push-subscriber
  - subject-overlap
  - wildcard-subscription
  - poll-until-count
  - fan-out
  - deliver-policy
  - durable-consumer
  - purge-stream
  - planning
  - pytest
---

# Diagnosing Flaky NATS Push-Subscriber Over-Count (Planning)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Diagnose and fix flaky NATS integration tests that assert exact message counts and intermittently OVER-count (`assert 2 == 1`). Core correction: distinguish core-NATS push delivery (live-only) from JetStream consumers (stream-backed) BEFORE choosing a fix. |
| **Outcome** | Planning hypothesis (corrected) — the v1.0.0 "purge the JetStream stream" plan was NOGO'd because core push subscribers never read streams; the over-count is live cross-test fan-out on a broad wildcard subscription. The revised plan was reasoned through but NOT executed. |
| **Verification** | unverified — corrected planning hypothesis; no test was run, CI was not run, and the failure was not reproduced this round. |
| **History** | [changelog](./testing-jetstream-flaky-stream-state-leak.history) |

## When to Use

- An integration test asserts `len(received) == N` on a `nc.subscribe(...)` callback and flakes only under full-suite / repeated runs (passes in isolation), surfacing as an over-count like `assert 2 == 1`.
- You are tempted to "purge the JetStream stream" to fix it — **STOP** and first classify the subscriber type. Purging a stream is INERT for a core NATS push subscriber.
- Tests use broad wildcard subjects (`hi.agents.>`, `hi.>`) and/or a fixed `asyncio.sleep(0.x)` before the count assert.
- A plan (or an issue) claims "streams persist and deliver stale messages" — treat that as a hypothesis and verify the subscriber type against the code before acting on it.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. The corrected plan was reasoned
> through but NOT executed — no test, no CI run, no reproduction. Treat as a hypothesis until CI
> confirms.

### Quick Reference

```python
# Poll-until-count helper — replaces `asyncio.sleep(0.x)`-then-assert.
# Returns as soon as enough messages have arrived, so a generous timeout
# can't be starved by CI load, yet an exact-count assert still catches over-delivery.
import asyncio

async def wait_for_messages(received, expected, timeout=5.0, poll_interval=0.01):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if len(received) >= expected:
            return
        await asyncio.sleep(poll_interval)
    # fall through on timeout; the caller's exact-count assert reports the shortfall

# Subject narrowing (the source fix): wildcard -> the test-unique fully-qualified subject.
#   BEFORE:  await nc.subscribe("hi.agents.>", cb=on_msg)          # matches OTHER tests' publishes
#   AFTER:   await nc.subscribe("hi.agents.prod-host.my-agent.created", cb=on_msg)  # test-unique

# DeliverPolicy.NEW belongs ONLY to an actual JetStream consumer (cross-RUN replay), not push tests.
from nats.js.api import ConsumerConfig, DeliverPolicy
cfg = ConsumerConfig(deliver_policy=DeliverPolicy.NEW)
sub = await js.pull_subscribe("subject", durable="d", config=cfg)
```

```bash
# Load-bearing verification — run UNDER full-suite pressure, repeatedly.
# A single green run and per-test isolation are NOT sufficient.
for i in $(seq 1 30); do pytest <module> -m integration -q || break; done
```

### Detailed Steps

1. **CLASSIFY the failing subscriber FIRST.** Grep the test for `subscribe(` and whether a
   `js` / `jetstream()` object is involved. Is it core NATS `nc.subscribe()` (live fan-out, no
   stream read) or a JetStream consumer `js.pull_subscribe` / `js.subscribe` (reads stream
   history, retains a cursor across runs)? The root cause and correct fix differ by type;
   conflating them mis-locates the bug. **A core push subscriber NEVER reads a JetStream stream.**
2. **If it is a CORE push subscriber** the over-count is live cross-test fan-out, NOT stream
   replay. Do **not** purge streams — it is inert. Instead, two-part fix on the push layer:
   (a) **narrow the subscription** from the wildcard (`hi.agents.>`) to the exact fully-qualified
   subject the test itself publishes (e.g. `hi.agents.prod-host.my-agent.created`), so no sibling
   test's live publish can match; (b) **replace `asyncio.sleep(0.x)`-then-assert** with a
   poll-until-count helper that returns as soon as `len(received) >= expected` on a generous
   timeout (~5s), so load can't starve a real delivery while an exact-count assert still catches
   over-delivery.
3. **If it is a JetStream consumer** cross-RUN replay / cursor retention IS possible. Use
   `config=ConsumerConfig(deliver_policy=DeliverPolicy.NEW)` so it ignores pre-existing stream
   content; optionally purge the stream for a guaranteed-clean start. `DeliverPolicy.NEW` is a
   JetStream-consumer concept and has NO effect on a core push subscriber — never apply it to push
   tests to "fix" them.
4. **Understand WHY the push over-count happens** so the fix is at the source: a broad-wildcard
   subscription's subject space OVERLAPS what sibling/adjacent tests publish; the fixed
   `asyncio.sleep(0.1)` window lets a second live message from another test land before the
   assert; and `sub.unsubscribe()` is async fan-out, so a broad subscriber can outlive its own
   test and still receive a foreign message. Narrowing the subject eliminates the overlap at the
   source; a longer wait alone does not.
5. **VERIFY under full-suite pressure, repeatedly.** Run a repeat loop
   (`for i in $(seq 1 30); do pytest <module> -m integration -q || break; done`) — a single green
   run and per-test isolation passing are NOT sufficient. Pass-when-run-together-repeatedly is the
   criterion.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Diagnosing `assert 2 == 1` as JetStream stream replay | Wrote an autouse `jsm.purge_stream` fixture as the primary fix (v1.0.0) | Core NATS push subscribers never read streams; the purge is inert — the plan was NOGO'd for a fix whose mechanism cannot affect the symptom | Classify subscriber type (core push vs JetStream consumer) BEFORE choosing a stream-level vs subscription-level fix |
| Trusting the issue's stated cause ("streams persist and deliver stale messages") without classifying the subscriber | Built the whole plan on the issue's framing | The issue conflated two subscriber types; the seven failing tests were core push subscribers, not stream readers | Treat the issue's root-cause claim as a hypothesis; verify the subscriber type against the code |
| Widening the wait or only swapping the sleep, leaving the broad wildcard subscription | (considered) just polling longer on `hi.agents.>` | A longer wait still receives a sibling test's live message on the wildcard; the over-count persists | Eliminate the non-determinism at the source — narrow the subject so foreign messages can't match |
| Applying `DeliverPolicy.NEW` to "fix" the push-subscriber tests | (considered) blanket DeliverNew across the failing tests | DeliverNew is a JetStream-consumer concept; it has no effect on a core push subscriber | Scope DeliverNew to actual JetStream consumers only (cross-run replay), not push tests |

## Results & Parameters

- **Decision table (subscriber type → correct fix).**
  - **Core push subscriber** (`nc.subscribe(...)`, live fan-out, no stream read): narrow the
    subject from the wildcard to the test-unique fully-qualified subject **+** poll-until-count.
    Purging streams and `DeliverPolicy.NEW` are inert here.
  - **JetStream consumer** (`js.pull_subscribe` / `js.subscribe`, reads stream history): use
    `DeliverPolicy.NEW` (+ optional `jsm.purge_stream` for a guaranteed-clean stream) to ignore
    pre-existing content across runs.
- **Poll helper params.** `wait_for_messages(received, expected, timeout=5.0, poll_interval=0.01)`
  — `timeout=5.0s` is generous so CI load can't starve a real delivery; `poll_interval=0.01s`;
  it returns at `>= expected` so an exact-count assert still catches over-delivery.
- **Verification.** The repeat loop
  `for i in $(seq 1 30); do pytest <module> -m integration -q || break; done` is load-bearing; a
  single green run and per-test isolation are NOT sufficient.
- **nats-py API note (verified by reviewer this round).** `jsm.purge_stream`, `ConsumerConfig`,
  `DeliverPolicy.NEW`, and `pull_subscribe(config=...)` are all real API surface in nats-py — but
  they apply to JetStream consumers only, not to core push subscribers.
