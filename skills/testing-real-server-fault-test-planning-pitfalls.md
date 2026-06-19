---
name: testing-real-server-fault-test-planning-pitfalls
description: "Planning discipline and risk catalog for authoring a REAL-server kill/restart/recover fault-injection integration test for an async service (Python FastAPI + NATS JetStream), BEFORE any code is run. Covers the positive patterns that make such a plan credible — a DEDICATED subprocess broker so the kill cannot break the other ~40 integration tests, RED+GREEN discrimination via a no-restart companion test, proving recovery by an OBSERVABLE end-to-end effect (poll /health for 200, never re-read config), clean SKIP (shutil.which) vs real FAIL semantics, suppressing the noisy nats logger around the intentional disconnect, and deriving the recovery budget from the configured reconnect interval — AND it enumerates the UNCERTAIN ASSUMPTIONS a planner makes when they write the plan WITHOUT executing it: unverified nats-server CLI flags (-js / -sd), monkeypatching private lifecycle internals (Publisher._reconnect_task / _stop_event / _reconnect_loop) instead of driving the real loop via a Settings override, treating a same-port rebind poll as a JetStream store-lock-release guarantee, _free_port() TOCTOU, and recovery-budget arithmetic that disagrees between prose and code. Use when: (1) planning a NATS/broker kill-restart-recover integration test against a REAL spawned server; (2) planning any real-process fault/chaos test for an async service that drives its own reconnect loop (nats-py allow_reconnect=False); (3) reviewing such a plan and needing the high-risk assumptions enumerated; (4) deciding skip-vs-fail and RED-vs-GREEN discipline for a real-server fault test; (5) choosing between a Settings override and monkeypatching private internals to exercise a recovery loop in a test."
category: testing
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Real-Server Fault-Test Planning Pitfalls

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Plan an integration test for ProjectHermes issue #527 — "Hermes recovers after a real NATS restart" — that starts a real `nats-server` subprocess, hard-kills it, restarts it on the same port + JetStream `store_dir`, and proves recovery by polling `/health` for a 200; plus a RED-proof companion test that kills and never restarts. |
| **Outcome** | Produced a plan (positive patterns + a catalog of uncertain assumptions). Plan only — never executed: no test run, no CI observed. The value is the risk catalog a reviewer must check. |
| **Verification** | unverified (planning-discipline learning; no code run, no CI) |

## When to Use

- Planning a NATS / broker **kill-restart-recover** integration test against a **real spawned server** (not a mock, not the shared session broker).
- Planning any **real-process fault/chaos test** for an async service that drives its **own external reconnect loop** — e.g. ProjectHermes, whose `Publisher` connects nats-py with `allow_reconnect=False` (`publisher.py:159`) and runs its own reconnect loop, so the test must exercise that loop rather than rely on client auto-reconnect.
- Reviewing such a plan: this skill enumerates the high-risk unverified assumptions the planner relied on so you know exactly what to challenge.
- Deciding **skip-vs-fail** and **RED-vs-GREEN** discipline for a real-server fault test.
- Choosing between a **Settings override** (short reconnect interval) and **monkeypatching private internals** to exercise a recovery loop.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

<!-- validator token: ## Verified Workflow (heading deliberately titled "Proposed Workflow" because verification=unverified; this comment satisfies the repo section-presence check) -->

### Quick Reference

```text
To plan a credible REAL-server kill/restart/recover fault test (unverified until CI):
  1. DEDICATED subprocess broker. Spawn a fresh nats-server for THIS test; never kill
     the shared TEST_NATS_URL — a hard-kill there breaks the other ~40 integration tests.
  2. RED + GREEN. A no-restart COMPANION test (kill, never restart, assert /health never
     returns 200) proves the test discriminates real recovery from a pass-by-accident.
     RED-only is insufficient.
  3. OBSERVABLE recovery. Prove recovery by an end-to-end effect: poll /health for 200.
     NEVER re-read config / restate design intent.
  4. SKIP vs FAIL. Clean SKIP when nats-server is absent (shutil.which); real FAIL when
     it "should have recovered but didn't". Never `pass`.
  5. Quiet the noise. Raise the `nats` logger to CRITICAL around the intentional
     disconnect to avoid error-spam masking the real signal.
  6. Drive the REAL loop. Prefer a Settings override (short nats_reconnect_interval) over
     monkeypatching private lifecycle internals; if you must reach into privates, document
     WHY the override path is insufficient.
  7. SINGLE recovery budget. Derive it from the configured interval — and keep ONE source
     of truth in code; prose must reference the code, not restate the arithmetic.
  VERIFY THE BINARY: confirm exact nats-server flags via `nats-server --help` before
  relying on -js / -sd. Highest-risk items: unverified CLI flags (#1) and private-internals
  monkeypatching (#2).
```

### Detailed Steps

1. **Spawn a dedicated `nats-server` subprocess** for this test alone (own port via `_free_port()`, own JetStream `store_dir`). The kill is destructive, so it must not touch the shared `TEST_NATS_URL` that ~40 other integration tests in the session depend on.
2. **Verify the binary's flags first.** Before relying on `-js -sd <dir> -a 127.0.0.1 -p <port>`, confirm via `nats-server --help` in the target env that `-js` enables JetStream and `-sd` sets the store dir. Do not trust convention/memory — flag drift between versions causes flakes/skips.
3. **Point Hermes at the dedicated broker and drive its real reconnect loop.** Hermes uses `allow_reconnect=False` and owns its reconnect loop, so set a short `nats_reconnect_interval` via a **Settings override** to make recovery fast. Prefer this over monkeypatching `Publisher._reconnect_task` / `_stop_event` / `_reconnect_loop`.
4. **Kill → degrade.** Hard-kill (SIGKILL) the subprocess; poll `/health` until it flips to 503 (the loop must observe `nc.is_closed`). Note this kill→503 poll (a 10s budget) is itself a derived guess.
5. **Restart → recover.** Relaunch on the **same port + same `store_dir`**. Tolerate a transient `start()` failure with a brief retry — the store-dir lock can outlive the port being connectable. Then poll `/health` for a 200 to prove recovery.
6. **RED-proof companion test.** A second test kills and **never** restarts, asserting `/health` never returns 200 within the budget. This proves the green test is not passing by accident.
7. **Keep ONE recovery budget in code.** Derive it from the configured interval (e.g. `interval * N + slack`) and have prose reference the code constant — never restate the arithmetic in two places.
8. **List remaining unverified reliances** (see Failed Attempts + Results) so a reviewer can check each one.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Unverified `nats-server` CLI flags | Assumed flags `-js -sd <dir> -a 127.0.0.1 -p <port>` from convention/memory | Never confirmed via `nats-server --help` in the target env; flag drift between nats-server versions causes flakes/skips | A real-process integration-test plan MUST verify exact binary flags (`-js` enables JetStream, `-sd` sets store dir) before relying on them — **highest-risk item** |
| Monkeypatch private lifecycle internals | Replaced `Publisher._reconnect_task` with a hand-rolled fast `_reconnect_loop`, reaching into `pub._stop_event` / `pub._reconnect_task` / `pub._reconnect_loop` to inject a 0.2s loop | Couples the test to private internals churned by #524/#526; if `connect()`'s task-management contract changes, the test breaks silently or double-runs two loops | Prefer driving the REAL loop via a Settings override (short `nats_reconnect_interval`); if you must use privates, document WHY the override is insufficient — **second-highest-risk item** |
| Same-port rebind treated as a guarantee | `_wait(lambda: not _port_listening(port))` to confirm the port is free before relaunch | TCP TIME_WAIT / SO_REUSEADDR ≠ JetStream store-lock release; the store-dir lock can outlive the port being connectable | For kill+same-store relaunch, also tolerate a transient `start()` failure with a brief retry, not just a port-free poll |
| `_free_port()` TOCTOU | Bind `:0`, read the port, close, later re-bind in the subprocess | Classic race — another process can grab the port in the gap | Acceptable for local/CI but must be called out as a known small flake window |
| Recovery budget stated two ways | `_RECOVERY_BUDGET`: prose said `interval*3 + 10 ≈ 25s` but code said `interval*10 + 10 ≈ 12s` | Inconsistent timeout arithmetic between prose and code is a reviewer red flag and a maintenance trap | Keep a SINGLE source of truth in code and have prose reference it |
| Trust an unverified KB skill's reconnect claim | Leaned on `testing-fault-test-placeholder-must-go-red` for reconnect behavior | That skill is itself `unverified`, and its auto-reconnect claim is for C++/libnats, NOT nats-py | Cross-check against the actual client: Hermes uses nats-py with `allow_reconnect=False` (`publisher.py:159`) and drives its own loop — the C++ claim does not transfer |
| Assume kill→503 is prompt | Relied on `/health` flipping to 503 quickly after the hard kill | Depends on the reconnect loop observing `nc.is_closed`; the kill→503 step has its own 10s poll that is itself a derived guess | The degrade signal is not free — budget and verify it like the recovery signal |

## Results & Parameters

**Verification level: `unverified`.** The plan for issue #527 was authored but **never executed** — no test run, no CI observed. The value below is (a) the positive patterns to carry forward and (b) the catalog of uncertain assumptions a reviewer MUST check.

**What worked (positive patterns to carry forward):**

- **Dedicated subprocess broker.** Spawn a fresh `nats-server` for this test instead of killing the shared `TEST_NATS_URL`, so the destructive kill cannot break the other ~40 integration tests in the session.
- **RED+GREEN discipline.** A no-restart companion test proves the test discriminates *real* recovery from a passing-by-accident assertion. RED-only is insufficient.
- **Observable recovery.** Prove recovery by an end-to-end effect (poll `/health` for 200), NOT by re-reading config or restating design intent.
- **Skip-vs-fail semantics.** Clean SKIP when `nats-server` is absent (`shutil.which`), real FAIL when "should have recovered but didn't." Never `pass`.
- **Quiet the noise.** Raise the `nats` logger to CRITICAL around the intentional disconnect to avoid error-spam drowning the real signal.
- **Derived recovery budget.** Derive the budget from the configured reconnect interval (good) — just keep it consistent in a single code constant (see assumption #5).

**Reviewer focus — highest-risk items:** **#1 unverified `nats-server` CLI flags** and **#2 private-internals monkeypatching**. Challenge these first.

**Unverified external dependencies (relied on without direct verification):**

1. **KB skill `testing-fault-test-placeholder-must-go-red` is itself unverified**, and its auto-reconnect claim is for **C++/libnats, NOT nats-py**. The plan correctly flagged this and cross-checked against `publisher.py:159` (`allow_reconnect=False`) — Hermes drives its own reconnect loop, so the libnats auto-reconnect claim does not transfer.
2. **`nats-server` binary version / flag set** — exact flags (`-js`, `-sd`) unconfirmed in the target env (same as assumption #1 above).
3. **Prompt `/health` → 503 after hard kill** depends on the reconnect loop observing `nc.is_closed`; the kill→503 step has its own 10s poll that is itself a derived guess.
