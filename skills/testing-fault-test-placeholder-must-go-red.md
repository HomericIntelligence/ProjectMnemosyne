---
name: testing-fault-test-placeholder-must-go-red
description: "Planning discipline for replacing a false-pass placeholder fault/chaos test (a hardcoded `pass`/`assert True` that never exercises the failure path) with a real one. Teaches: a fix is only credible if the new test can go BOTH RED and GREEN against real code, proves recovery by an OBSERVABLE end-to-end effect (not by re-asserting design intent), and uses a clean SKIP — never a pass — where the fault is structurally inapplicable. Most importantly: when a reviewer flags an UNVERIFIED assumption, the fix is to READ THE ACTUAL CLIENT/LIBRARY SOURCE (cite the connect API + its reconnect defaults), not to add hedging prose; scope DOWN off documented-broken substrates instead of supporting them; and never let a verification step depend on a harness helper you never opened. Catalogs the unverified assumptions a planner makes when they write such a plan WITHOUT running code (does the client actually auto-reconnect? is the compose path right? does a hard-kill + same-port relaunch race? is the lifecycle helper idempotent? does the launcher even point at the real entrypoint?) so a reviewer knows exactly what to check. Use when: (1) planning a fix for an issue where a fault/chaos/resilience test is a hardcoded placeholder that always passes; (2) writing a NATS/broker crash-reconnect or kill-restart-recover test; (3) deciding skip-vs-fail semantics for an environment-conditional fault test; (4) responding to a reviewer NOGO that flags an unverified core assumption; (5) reviewing such a plan and needing the high-risk assumptions enumerated; (6) any test that asserts a system property by re-reading source or restating design intent instead of exercising it."
category: testing
date: 2026-06-19
version: "1.1.0"
user-invocable: false
verification: unverified
history: testing-fault-test-placeholder-must-go-red.history
tags:
  - testing
  - chaos
  - fault-injection
  - placeholder-test
  - red-green
  - tdd
  - nats
  - reconnect
  - planning
  - unverified-assumptions
  - observable-recovery
  - skip-vs-fail
  - read-the-source
  - reviewer-nogo
  - scope-down
---

# Fault-Test Placeholder Must Be Able To Go Red

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Plan a fix for a false-pass fault test: a NATS crash-reconnect e2e test that was a hardcoded `pass` placeholder (Odysseus e2e, GitHub issue #184), then RE-PLAN it after a reviewer NOGO |
| **Outcome** | Produced an implementation plan (kill -> degrade -> restart -> prove reconnect via a real task lifecycle), and on re-plan strengthened it by reading the actual NATS client source and scoping down to the one working topology. Plan only — never executed. |
| **Verification** | unverified (planning-discipline learning, no code run, no CI observed) |
| **History** | [changelog](./testing-fault-test-placeholder-must-go-red.history) |

## When to Use

- Planning a fix for an issue where a fault, chaos, or resilience test is a hardcoded placeholder (`pass`, `assert True`, `return 0`) that always passes without exercising the failure path.
- Writing a broker/NATS crash-reconnect or kill-restart-recover test for the first time.
- Deciding skip-vs-fail semantics for a fault test that only applies under some topologies/environments.
- **Responding to a reviewer NOGO that flags an "unverified core assumption"** — this skill's #1 lesson is that the fix is to read the actual client/library source, not to hedge.
- Reviewing such a plan: this skill enumerates the high-risk unverified assumptions the planner relied on.
- Any test that "verifies" a property by re-reading source or restating design intent instead of exercising it.

## Verified Workflow

> **Warning:** This is a planning-discipline learning, not an executed workflow. Treat as a hypothesis until applied and confirmed.
> _(Proposed — derived from a plan that was never run; the assumptions below are unverified against code or CI.)_

### Quick Reference

```text
To fix a false-pass fault/chaos test, the plan MUST include:
  1. A way to exercise the REAL fault path (e.g. kill/restart lifecycle helpers).
  2. An explicit RED step AND a GREEN step: the test must be shown able to FAIL
     (stub the recovery) and to PASS against real code. "Can fail" alone is
     necessary-but-insufficient — a reviewer treats RED-only as unproven recovery.
  3. A GREEN assertion that is an OBSERVABLE end-to-end effect (a brand-new task
     lifecycle completing AFTER restart) — never "asserts the system is designed for X".
  4. Clean SKIP (not pass) where the fault is structurally inapplicable — and SKIP
     the substrate entirely (with the bug cited inline) when it is documented-broken.
  5. Source-cited assumptions: a reconnect/recovery plan MUST cite the client's
     connect API and its reconnect defaults, and confirm the consumer loop CONTINUES
     (not exits) on transient errors. Reading source > hedging prose.
  6. Conventions MIRRORED from the repo, and every helper your verification depends on
     OPENED and confirmed to work on a clean run — discovered by grep + read, not assumed.
```

### Detailed Steps

1. **Confirm the placeholder's sin.** The original test asserted design intent ("designed for graceful degradation") instead of exercising it. Re-asserting source or design is the same bug class you are fixing.
2. **Add a real fault path.** Introduce lifecycle helpers (`nats_kill`, `nats_restart`) that actually SIGKILL the broker and relaunch it, mirroring existing repo kill helpers found by grep rather than inventing a new style.
3. **Drive an observable effect.** After restart, run a brand-new end-to-end task lifecycle and assert it completes. Recovery is proven by the new work succeeding, not by re-reading config.
4. **Show the test can go BOTH RED and GREEN.** Temporarily stub/disable the recovery and confirm it FAILS; then revert and confirm it PASSES against real code. Proving only RED is what got the v1.0.0 plan a NOGO — reviewers correctly treat "can fail" as necessary-but-insufficient. You must also show the happy path actually reconnects.
5. **Answer "unverified assumption" findings by reading the source, not hedging.** When a reviewer flags an unverified core assumption, READ THE ACTUAL CLIENT/LIBRARY SOURCE. Here, confirming both NATS clients call `natsConnection_ConnectTo` — which uses libnats DEFAULT options = auto-reconnect ON (`AllowReconnect=true`, `MaxReconnect=60`, `ReconnectWait=2s`) — converted the #1 risk from "assumed" to "verified can-go-GREEN". A reconnect/recovery plan MUST cite the connect API and its reconnect defaults, and confirm the consumer loop continues (does not exit) on transient errors. More prose hedging is still a NOGO.
6. **Scope DOWN off broken substrates.** Supporting fewer topologies that actually work beats supporting all of them. Dropping the documented-broken topology (T4) deleted a whole class of defects at once: the internally-contradictory compose path, the documented port-override bug substrate, and an over-generalized persistence rationale. When a substrate is documented-broken, `skip_topology`/skip it explicitly with the bug cited inline — never build on it.
7. **Open every helper your verification depends on.** Reading code to fix one finding surfaced a PRE-EXISTING BLOCKER the issue never mentioned: the T1 launcher (`start_myrmidon_bg`) pointed at a non-existent `main.py` while the component is C++ (`main.cpp`), so the test's own baseline precondition could never pass. "The harness already does X" is an assumption, not a fact. A plan whose verification steps depend on a broken harness is not actually verifiable — it is aspirational.
8. **Resolve DRY/divergence by referencing exact exported variables.** Use `${VAR:?}` (fail-loud if unset) instead of duplicating defaults like `${PORT:-18222}`. This guarantees the helper can never silently drift from its source of truth.
9. **Make code blocks self-correct; never rely on a trailing Note.** A code block whose body contradicts a prose "Note" correction will be followed literally by an implementer (they ship the broken path, not the note). The code block itself must be correct.
10. **Get skip-vs-fail semantics right.** "Structurally inapplicable" (the fault cannot occur in this topology) -> clean `skip_topology`/skip. "Should have worked but didn't" -> real fail. A pass where the fault cannot run is the same defect as the bug you are fixing.
11. **Mark the plan's remaining assumptions.** Even after reading source, list every reliance NOT proven by running code (see Failed Attempts + Results) so a reviewer can check them.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Hardcoded pass placeholder | Test body was `pass` / `assert True`, never exercising the fault | Always green; cannot detect a broken recovery path | A fault test that can never go red is a slower placeholder — add an explicit RED step |
| Assert design intent | Asserted "system is designed for graceful degradation" by re-reading source/config | Verifies the comment, not the behavior; passes even if recovery is broken | Prove recovery by an OBSERVABLE end-to-end effect (new task lifecycle completing post-restart) |
| Pass where inapplicable | Returned pass when the topology cannot exercise the fault | Same bug class as the placeholder — silently green without exercising anything | Use a clean skip for structurally-inapplicable cases; reserve fail for real breakage |
| Assume the client auto-reconnects | Plan relied on the NATS client reconnecting within timeout after restart, unverified | If the client does one-shot connect (KB warns nats-py `allow_reconnect` can hang / connect is one-shot) the post-restart lifecycle hangs and the "fix" is itself flaky/false | Verify reconnect behavior against the actual client code BEFORE trusting the plan (#1 risk) |
| Wrong relative compose path | Helper wrote `$(_e2e_root)/docker-compose.e2e.yml` | Compose file lives at repo ROOT, asserted from a single `find` hit; `_e2e_root()` returns `e2e/`, so the file is one level up | Correct path is `$(_e2e_root)/../docker-compose.e2e.yml`; a path from one `find` hit is brittle and was never executed |
| Hedge instead of read source | Answered the reviewer's "unverified assumption" finding with more cautionary prose | Still NOGO — prose does not turn an assumption into a fact | Cite the connect API + reconnect defaults from the actual client file (`natsConnection_ConnectTo`; libnats `AllowReconnect=true`, `MaxReconnect=60`, `ReconnectWait=2s`) |
| Claim multi-topology support on a broken substrate | Asserted T1+T4 support where T4 rests on a documented port-override bug | Reviewer flags T4 as untested / likely-nonfunctional; the broken substrate also dragged in a self-contradictory compose path and an over-broad persistence rationale | Scope to the working topology (T1); `skip_topology` the broken one with the bug cited inline |
| Code block contradicted by a trailing Note | Shipped a compose-path code block whose body was wrong, "fixed" only by a prose `_e2e_root` Note below it | An implementer follows the code, not the note, and ships the broken path | The code block itself must be correct; never rely on a caveat to fix code |
| Verification depends on an unopened helper | Relied on `start_myrmidon_bg` to bring up the baseline, never opening it | The launcher pointed at a non-existent `main.py` (component is C++ `main.cpp`); the baseline precondition could never pass — "aspirational verification" | Open and validate EVERY helper your verification depends on; "the harness does X" is an assumption |
| Prove only RED, never GREEN | Argued the new test can fail, but never showed it reconnects against real code | Necessary-but-insufficient; reviewer treats the recovery path as unproven and flaky-in-the-other-direction | A recovery test must be shown able to go BOTH RED and GREEN against real code |

## Results & Parameters

**Verification level: `unverified`.** This re-plan (for issue #184) was never executed; no code ran and no CI was observed. The value below is the catalog of assumptions a planner relied on, refined after reading client source — a reviewer MUST still check the remaining ones.

What reading the source resolved (the v1.1.0 delta):

- **Client auto-reconnect is now source-cited, not assumed.** Both the Agamemnon C++ `NatsClient` and the Python myrmidon connect via `natsConnection_ConnectTo`, which uses libnats DEFAULT options: `AllowReconnect=true`, `MaxReconnect=60`, `ReconnectWait=2s`. That single source read converts the #1 risk from "assumed" to "verified can-go-GREEN" — provided the consumer loop continues (does not exit) on transient errors, which must also be confirmed in the loop body.
- **Scope reduced to T1 only.** T4 was dropped because it rests on a documented port-override bug; skipping it removed the self-contradictory compose path, the bug substrate, and an over-generalized persistence rationale in one move.
- **Pre-existing blocker surfaced.** The T1 launcher `start_myrmidon_bg` references a non-existent `main.py` (component is C++ `main.cpp`); the test's baseline precondition cannot pass until the launcher is fixed. This is a precondition the issue never mentioned.

Remaining uncertain assumptions / unverified reliances a reviewer should still focus on (ordered):

1. **libnats reconnect defaults are version-dependent.** Even after reading the client source, pin/verify the linked libnats version actually enables `AllowReconnect` by default in THIS build.
2. **Hard-kill + immediate same-port/same-`store_dir` relaunch on T1.** SIGKILL then relaunch races: the JetStream store lock / port-rebind race is still untested; the 30s health-wait may mask intermittent failures.
3. **Double `run_task_lifecycle` idempotency.** Calling it twice in one run (baseline + post-restart) — collision of repeated agent/team/task creation — is not verified.
4. **The 90s post-restart timeout is a derived budget, not a measured one** (2s reconnect + 5s fetch poll + rebind). Could be too tight under load or too slow to fail fast.
5. **Runner invocation.** `pixi run bash e2e/run-ipc-tests.sh` is still assumed; the runner documents bare `bash e2e/run-ipc-tests.sh`. Whether pixi wraps it is unconfirmed.
6. **Skip-vs-fail correctness for every topology** — confirm no path silently passes without exercising the fault, especially the now-skipped T4.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus (e2e) | Re-plan of issue #184 after a reviewer NOGO — NATS crash-reconnect placeholder test | unverified; plan only, never executed |
