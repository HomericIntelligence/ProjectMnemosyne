---
name: testing-real-server-fault-test-planning-pitfalls
description: "Planning discipline and risk catalog for authoring a REAL-server kill/restart/recover fault-injection integration test for an async service (Python FastAPI + NATS JetStream), BEFORE any code is run. Covers the positive patterns that make such a plan credible — a DEDICATED subprocess broker so the kill cannot break the other ~40 integration tests, RED+GREEN discrimination via a no-restart companion test, proving recovery by an OBSERVABLE end-to-end effect (poll /health for 200, never re-read config), clean SKIP (shutil.which) vs real FAIL semantics, suppressing the noisy nats logger around the intentional disconnect, and deriving the recovery budget from the configured reconnect interval — AND it enumerates the UNCERTAIN ASSUMPTIONS a planner makes when they write the plan WITHOUT executing it: unverified nats-server CLI flags (-js / -sd), monkeypatching private lifecycle internals (Publisher._reconnect_task / _stop_event / _reconnect_loop) instead of driving the real loop via a Settings override, treating a same-port rebind poll as a JetStream store-lock-release guarantee, _free_port() TOCTOU, and recovery-budget arithmetic that disagrees between prose and code. Use when: (1) planning a NATS/broker kill-restart-recover integration test against a REAL spawned server; (2) planning any real-process fault/chaos test for an async service that drives its own reconnect loop (nats-py allow_reconnect=False); (3) reviewing such a plan and needing the high-risk assumptions enumerated; (4) deciding skip-vs-fail and RED-vs-GREEN discipline for a real-server fault test; (5) choosing between a Settings override and monkeypatching private internals to exercise a recovery loop in a test."
category: testing
date: 2026-06-19
version: "1.1.0"
user-invocable: false
verification: unverified
history: testing-real-server-fault-test-planning-pitfalls.history
tags: []
---

# Real-Server Fault-Test Planning Pitfalls

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Plan an integration test for ProjectHermes issue #527 — "Hermes recovers after a real NATS restart" — that starts a real `nats-server` subprocess, hard-kills it, restarts it on the same port + JetStream `store_dir`, and proves recovery by polling `/health` for a 200; plus a RED-proof companion test that kills and never restarts. |
| **Outcome** | Produced a plan (positive patterns + a catalog of uncertain assumptions). Plan only — never executed: no test run, no CI observed. The value is the risk catalog a reviewer must check. |
| **Verification** | stays **unverified** (planning-discipline learning; the test was never executed and no CI run exists — only the env-override mechanism is verified, by source read) |
| **History** | [changelog](./testing-real-server-fault-test-planning-pitfalls.history) |

## When to Use

- Planning a NATS / broker **kill-restart-recover** integration test against a **real spawned server** (not a mock, not the shared session broker).
- Planning any **real-process fault/chaos test** for an async service that drives its **own external reconnect loop** — e.g. ProjectHermes, whose `Publisher` connects nats-py with `allow_reconnect=False` (`publisher.py:159`) and runs its own reconnect loop, so the test must exercise that loop rather than rely on client auto-reconnect.
- Reviewing such a plan: this skill enumerates the high-risk unverified assumptions the planner relied on so you know exactly what to challenge.
- Deciding **skip-vs-fail** and **RED-vs-GREEN** discipline for a real-server fault test.
- Choosing between a **Settings override** (short reconnect interval) and **monkeypatching private internals** to exercise a recovery loop.

## Verified Workflow

> **⚠️ UNVERIFIED — this workflow was authored and reviewed but NEVER executed end-to-end; no CI run exists. Treat every step as a hypothesis until validated.**

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
  6. PUBLIC OVERRIDE > PRIVATE MONKEYPATCH (headline). Drive the REAL loop via a public
     env/Settings knob: monkeypatch.setenv("NATS_RECONNECT_INTERVAL","0.2") + plain connect().
     Works because Settings has no env_prefix & case_sensitive=False. GOTCHA: only takes
     effect if get_settings.cache_clear() runs per test (autouse fixture) — get_settings is
     @lru_cache, so without the clear the override is SILENTLY ignored.
  7. SINGLE recovery budget. Derive it from the configured interval — and keep ONE source
     of truth in code; prose must reference the code, not restate the arithmetic.
  VERIFY THE BINARY: confirm exact nats-server flags via `nats-server --help` before
  relying on -js / -sd. Highest-risk items: unverified CLI flags (#1) and private-internals
  monkeypatching (#2).
```

### Detailed Steps

1. **Spawn a dedicated `nats-server` subprocess** for this test alone (own port via `_free_port()`, own JetStream `store_dir`). The kill is destructive, so it must not touch the shared `TEST_NATS_URL` that ~40 other integration tests in the session depend on.
2. **Verify the binary's flags first.** Before relying on `-js -sd <dir> -a 127.0.0.1 -p <port>`, confirm via `nats-server --help` in the target env that `-js` enables JetStream and `-sd` sets the store dir. Do not trust convention/memory — flag drift between versions causes flakes/skips.
3. **Point Hermes at the dedicated broker and drive its real reconnect loop via a PUBLIC env/Settings override — the headline lesson.** Hermes uses `allow_reconnect=False` (`publisher.py:159`) and owns its reconnect loop, so inject fast timing through the public config surface, NOT private internals. **Verified mechanism:** Hermes' `Settings` is pydantic-settings `BaseSettings` with NO `env_prefix` and `case_sensitive=False` (`config.py:27-31`), so field `nats_reconnect_interval` maps directly to env var `NATS_RECONNECT_INTERVAL`. A plain `monkeypatch.setenv("NATS_RECONNECT_INTERVAL", "0.2")` + ordinary `connect()` makes production code (`publisher.py:107,130` reads `settings.nats_reconnect_interval`) launch a fast reconnect loop with ZERO coupling to private `_stop_event` / `_reconnect_task`. **NON-OBVIOUS GOTCHA:** this works ONLY because an autouse fixture calls `get_settings.cache_clear()` per test (`conftest.py:46-55`); `get_settings` is `@lru_cache` (`config.py:248`), so WITHOUT that cache-clear the env override is silently ignored. This is the only genuinely VERIFIED item in this skill (verified by source read, not by executing the test).
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
| P1/KISS — monkeypatched churned private internals when a public knob existed | Reached into `Publisher._stop_event` / `_reconnect_task` to inject fast timing even though `NATS_RECONNECT_INTERVAL` / `nats_reconnect_interval` is a public Settings field the production path already reads | Reviewer escalated to a Major, GO-blocking finding: testing through private internals couples the test to recently-churned implementation detail when a stable public seam exists | Before poking private attrs in a test, grep for an env var / Settings field the production path already reads and drive the behavior through that public seam instead |
| P7/POLA — derived timeout stated two contradictory ways | Prose said the recovery budget was `interval*3 + 10 ≈ 25s` while the code computed `interval*10 + 10 ≈ 12s` | Two different arithmetic statements for one value is a POLA violation and a maintenance trap; a reviewer flagged it Minor | One named module constant is the single source of truth; prose REFERENCES the constant and never restates differing arithmetic |
| Same-store/same-port relaunch race | Used only a TCP port-free poll (`not _port_listening(port)`) to decide it was safe to relaunch on the same port + same JetStream store_dir | A port-free poll is necessary but NOT sufficient: port-free ≠ JetStream store-lock released, so the relaunch can still fail to acquire the store lock | Use a bounded `start(attempts=5)` spawn-retry that kills + re-probes on listen-timeout, instead of trusting a single port-free poll |
| Unverified CLI flags blind-spawned | Assumed `nats-server -js -sd -p -a` would all be accepted and spawned the subprocess directly | Flag drift between nats-server versions silently breaks the spawn and produces confusing failures | Gate the spawn with a `_flags_supported()` probe of `nats-server --help` that `pytest.skip`s if `-js` / `-sd` / `-p` / `-a` are not all present — never blind-spawn |

## Results & Parameters

**Verification level: `unverified`.** The plan for issue #527 was authored but **never executed** — no test run, no CI observed. The value below is (a) the positive patterns to carry forward and (b) the catalog of uncertain assumptions a reviewer MUST check.

**Headline verified fact (the one genuinely verified item):** Drive the real reconnect loop through a PUBLIC env/Settings override, not private internals. Hermes' `Settings` is pydantic-settings `BaseSettings` with no `env_prefix` and `case_sensitive=False` (`config.py:27-31`), so `monkeypatch.setenv("NATS_RECONNECT_INTERVAL", "0.2")` + a plain `connect()` makes the production path (`publisher.py:107,130`) launch a fast reconnect loop with zero coupling to `_stop_event` / `_reconnect_task`. **Cache-clear gotcha:** this works ONLY because an autouse fixture calls `get_settings.cache_clear()` per test (`conftest.py:46-55`); `get_settings` is `@lru_cache` (`config.py:248`), so without that clear the env override is silently ignored. This is the only item verified (by source read, not by executing the test).

**Positive signals the reviewer accepted (keep):**

- **Dedicated subprocess broker** spawned for this test alone (not the shared session `TEST_NATS_URL`), so the destructive kill cannot break the other ~40 integration tests.
- **RED+GREEN discriminating companion test** — a no-restart kill test that asserts `/health` never returns 200 within budget, proving the green test does not pass by accident.
- **Observable `/health` proof** of recovery (poll for 200), not a config re-read or restated design intent.
- **Clean SKIP vs honest FAIL** — `pytest.skip` when the binary is absent (`shutil.which`), a real FAIL when it "should have recovered but didn't"; never `pass`.
- **Single named recovery-budget constant** — one source of truth in code that prose references, never restated arithmetic.

**Honest caveat:** these patterns were validated only by a reviewer NOGO→revision cycle on a PLAN, not by running anything. Only the env-override fact is verified (by source read of `config.py` / `publisher.py` / `conftest.py`); the test itself was never executed and no CI run exists. Verification therefore stays `unverified`.

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
