---
name: nats-jetstream-jserrcode-stream-exists-misclassification
description: "In cnats (nats.c), ALL JetStream API errors surface as natsStatus == NATS_ERR with the distinguishing code in the jsErrCode out-param of js_AddStream/js_Publish; a branch that treats bare s == NATS_ERR as the benign 'stream already exists' case silently swallows real provisioning failures (subject overlap 10065, account limits, invalid config). Only s == NATS_ERR && jerr == JSStreamNameExistErr (10058) is benign — fail closed on every other (s, jerr) combination, including jerr == 0 (client-side error). The misclassification only becomes an outage when paired with a swallowed void result upstream (void ensure_streams() logged-but-not-returned failures under a provision function that returns true unconditionally), so the provisioner never retries. Use when: (1) writing or reviewing C/C++ NATS JetStream provisioning code that branches on the natsStatus of js_AddStream/js_UpdateStream/js_Publish, (2) fixing error classification inside an ensure_* helper — audit the call chain upward for swallowed void/bool results or the retry path never engages, (3) designing a live regression test for subject-overlap stream conflicts — a publish-probe is the wrong failure signal because the conflicting stream captures the subject; probe stream existence with js_GetStreamInfo instead, (4) a plan cites specific jsErrCode values (10058/10065) or 'already exists with different config' server behavior from memory — rank those as top reviewer-verification items against the pinned cnats/NATS server version, (5) a live test mutates shared broker state (deletes/recreates a production-named stream) — require an RAII cleanup guard and note that restoration depends on the fix under test."
category: architecture
date: 2026-07-03
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [nats, jetstream, jserrcode, cnats, error-classification, provisioner-retry, cpp, planning, pola, swallowed-result, live-broker-test]
---

# NATS JetStream: jsErrCode Stream-Exists Misclassification + Swallowed Provisioner Result

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-03 |
| **Objective** | Plan the fix for ProjectNestor issue #121: a cnats (nats.c v3.12.0) JetStream provisioner that classifies every `NATS_ERR` from `js_AddStream` as the benign "stream already exists" case, silently swallowing real provisioning failures and never retrying |
| **Outcome** | Plan produced identifying a defect PAIR: (1) bare `NATS_ERR` misclassification instead of `jerr == JSStreamNameExistErr` (10058) discrimination, and (2) a `void ensure_streams()` whose failures are logged but not returned under a `provision_jetstream_locked()` that returns true unconditionally — both must be fixed or the retry path never engages. Live regression test designed but not executed |
| **Verification** | unverified — PLANNING session only; no code was executed, no tests run; jsErrCode semantics asserted partly from memory (see reviewer checklist) |

## When to Use

- Writing or reviewing C/C++ code that calls cnats JetStream APIs (`js_AddStream`, `js_UpdateStream`, `js_Publish`, `js_GetStreamInfo`) and branches on the returned `natsStatus`.
- You see a branch like `if (s == NATS_ERR) { /* stream already exists, fine */ }` — that branch is swallowing subject-overlap conflicts (jsErrCode 10065), account limits, and invalid-config rejections.
- Fixing error classification inside an `ensure_*` / provisioning helper: audit the call chain UPWARD for swallowed `void` results before declaring the fix complete.
- Designing a live-broker regression test for a stream-provisioning failure mode, especially one that must mutate shared broker state (delete a production-named stream, create a conflicting one).
- Reviewing a plan that cites specific jsErrCode numeric values or NATS server "already exists with different config" behavior — these are commonly asserted from memory and need verification against the pinned server/client versions.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

(This is a PROPOSED workflow from a planning-only session; the heading "Verified Workflow" is required by the repository validator.)

### Quick Reference

```c
// cnats: ALL JetStream API errors come back as NATS_ERR; the real
// discriminator is the jsErrCode out-param. Three-way branch, fail closed:
jsErrCode jerr = 0;
natsStatus s = js_AddStream(&si, js, &cfg, NULL, &jerr);
if (s == NATS_OK) {
    // created
} else if (s == NATS_ERR && jerr == JSStreamNameExistErr) {  // 10058, cnats src/status.h:196
    // benign: stream already exists
} else {
    // EVERYTHING else — including NATS_ERR with jerr == 0 (client-side error),
    // subject overlap (10065), account limits, invalid config:
    log_error("js_AddStream failed: %s (jsErrCode=%d)", natsStatus_GetText(s), (int)jerr);
    ok = false;  // keep iterating so independent streams still provision
}
```

```cpp
// Defect pair, part 2: propagate the result — do not swallow it.
// void ensure_streams() + unconditional `return true;` above it means
// the provisioner marks the generation provisioned and NEVER retries.
bool provision_jetstream_locked() {
    ...
    const bool streams_ok = ensure_streams();  // now returns bool (accumulated ok)
    resubscribe();      // independent of stream provisioning — run unconditionally
    return streams_ok;  // false => generation not marked provisioned => retry engages
}
```

```cpp
// Live-test trap: under a subject-overlap conflict, js_Publish SUCCEEDS
// (the CONFLICTING stream captures the subject) — publish is NOT a failure
// signal. Probe stream existence instead:
natsStatus s = js_GetStreamInfo(&si, js, "homeric-research", NULL, &jerr);
// expected NATS_NOT_FOUND while the conflict blocks creation (assumed, unverified)
```

### Detailed Steps

1. **Discriminate on jsErrCode, not natsStatus.** In cnats, every JetStream API error — server-side or client-side — surfaces as `natsStatus == NATS_ERR`. The distinguishing code is the `jsErrCode*` out-param (`js_AddStream`, `js_Publish`, etc.). The ONLY benign already-exists case is `s == NATS_ERR && jerr == JSStreamNameExistErr` (10058, defined in cnats `src/status.h:196`).
2. **Fail closed on everything else.** Route every other `(s, jerr)` combination to the failure/retry path — including `NATS_ERR` with `jerr == 0`, which indicates a client-side error (no server code was assigned). Log both `natsStatus_GetText(s)` and the numeric `jerr`.
3. **Accumulate, don't abort.** In a loop that ensures multiple streams, set `ok = false` on failure but keep iterating so independent streams still provision; return the accumulated `ok`.
4. **Audit upward for swallowed results.** The misclassification only becomes an outage because of a second defect: `void ensure_streams()` logged per-stream failures but returned nothing, and the bool-returning `provision_jetstream_locked()` above it returned true unconditionally — so the provisioner marked the generation provisioned and never retried. Change `ensure_*` to return bool, propagate it, and make the null-context guard return false (returning true on a null guard would let a bug mark work as done). Fix BOTH defects or the retry path still never engages.
5. **Keep independent recovery running on failure.** The core NATS subscription (resubscribe) is independent of JetStream stream provisioning — run it unconditionally and return the stream result (`const bool streams_ok = ensure_streams(); resubscribe(); return streams_ok;`). Skipping resubscribe on stream failure would silence message intake during retry windows.
6. **Live regression test: assert observable behavior, not the code.** Create a conflicting stream capturing the target subjects, then assert the intended stream stays absent (bounded wait) and appears after the conflict is removed — do NOT assert the specific jsErrCode (10065) that was never observed in a captured log. Probe with `js_GetStreamInfo`, never with a publish (see Failed Attempts).
7. **Guard shared broker state.** The test deletes the production-named stream (`homeric-research`) and relies on the client's own retry loop to restore it. Mandatory: an RAII cleanup guard for the conflicting stream (a mid-test failure between delete and conflict-cleanup would otherwise strand the broker); serial execution relative to other live tests; and awareness that restoring the deleted stream depends on the fix under test actually working.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Classify bare `s == NATS_ERR` as "stream already exists" | Original code treated any `NATS_ERR` from `js_AddStream` as the benign already-exists case | ALL JetStream API errors surface as `NATS_ERR`; subject overlap (10065), account limits, and invalid config were silently swallowed | Benign branch ONLY on `s == NATS_ERR && jerr == JSStreamNameExistErr` (10058); fail closed otherwise, including `jerr == 0` |
| Fix only the classification branch | First plan draft fixed the jsErrCode discrimination but left the call chain alone | `void ensure_streams()` logged failures without returning them and `provision_jetstream_locked()` returned true unconditionally — provisioner marked the generation provisioned and never retried | When fixing error classification in an `ensure_*` helper, ALSO audit upward for swallowed results; fix both or the retry path never engages |
| Publish-probe as the failure signal in the overlap test | Plan initially used `js_Publish` success/failure to detect the missing stream | The CONFLICTING stream itself captures the subject, so `js_Publish` succeeds even though the intended stream is missing | Probe stream existence (`js_GetStreamInfo`), not publish, when the failure mode is a subject-capture conflict |
| Assumed without verification: 10058 covers "exists with different config" | Asserted from memory of NATS server behavior that `JSStreamNameExistErr` also covers a same-name/different-config stream | Never verified against NATS server source or a live broker; if the server returns a different code, the fix breaks documented tolerance for a peer service (Agamemnon) ensuring the same stream with a possibly different config | Existing live test `SecondClientHitsStreamAlreadyExists` covers same-config only; a different-config live check is the gap — top reviewer item |
| Assumed without verification: 10065 is the overlap code | Plan comments name jsErrCode 10065 (subject overlap) as the repro | Never observed in a captured log; the planned test asserts observable behavior instead, but the comments are unverified | Cite codes as hypotheses in comments until observed; assert behavior, not codes |
| Assumed without verification: `js_GetStreamInfo` returns `NATS_NOT_FOUND` | Missing-stream probe return value assumed from cnats API convention | Never exercised in this session | Exercise the probe's negative path in the live test before relying on it |
| Assumed without verification: constant value via conan cache grep | `JSStreamNameExistErr = 10058` confirmed only by grepping `~/.conan2/p/cnats*/s/src/src/status.h` | Machine-specific cache path; other machines/CI could have a different vendored version | Verify against the project's pinned cnats version (v3.12.0), not whatever is in the local cache |
| Negative assertion via bounded wait | `EXPECT_FALSE(wait_for(pred, 5s))` to prove the stream stays absent | Proves absence only weakly — passes vacuously on a slow broker | Pair the negative assertion with a positive one after conflict removal; treat the negative alone as weak evidence |
| Test relies on declaration-order execution and the fix itself for cleanup | Planned test deletes production-named stream `homeric-research`, creates a conflict, and relies on gtest declaration order plus the client's retry loop to restore state | Parallel/reordered execution, a mid-test failure between delete and conflict-cleanup, or a broken fix would strand shared broker state | RAII cleanup guard for the conflict stream is mandatory; restoring the deleted stream depends on the fix working — flag this dependency in the test comments |

## Results & Parameters

### Corrected branch shape (three-way, fail closed)

| Condition | Classification | Action |
|-----------|----------------|--------|
| `s == NATS_OK` | Stream created | proceed |
| `s == NATS_ERR && jerr == JSStreamNameExistErr` (10058) | Already exists — benign | proceed |
| Anything else (incl. `NATS_ERR` + `jerr == 0`) | Real failure | log `natsStatus_GetText(s)` + `jerr`, set `ok = false`, keep iterating |

### Propagation pattern

```cpp
const bool streams_ok = ensure_streams();  // bool, accumulated across streams
resubscribe();                             // independent — run unconditionally
return streams_ok;                         // false => provisioner retries
```

- Null-context guard in `ensure_streams()` returns **false** (true would mark work done on a bug).

### Ranked reviewer checklist (unverified assumptions to check first)

1. **(Top)** Does jsErrCode 10058 also cover "stream name already in use with a DIFFERENT configuration"? Asserted from memory, never verified against NATS server source or a live broker. If the server returns a different code, the fix breaks tolerance for peer service Agamemnon ensuring the same stream with a possibly different config. Existing live test `SecondClientHitsStreamAlreadyExists` covers same-config only — the different-config live check is the gap.
2. jsErrCode 10065 (subject overlap) cited as the repro code but never observed in a captured log; the test asserts observable behavior (stream absent, then appears after conflict removal), which is acceptable, but the code comments naming 10065 are unverified.
3. `js_GetStreamInfo` returning `NATS_NOT_FOUND` for a missing stream — assumed from cnats API convention, not exercised.
4. `JSStreamNameExistErr = 10058` verified only via a machine-specific conan cache grep (`~/.conan2/p/cnats*/s/src/src/status.h:196`); verify against the pinned cnats v3.12.0, not the local cache.
5. The live test mutates shared broker state (deletes `homeric-research`, creates a conflicting stream) and relies on (a) gtest declaration-order serial execution and (b) the client's own retry loop for restoration. RAII cleanup guard for the conflict stream is mandatory; check for interference with other live tests.
6. `EXPECT_FALSE(wait_for(pred, 5s))` is a weak negative — can pass vacuously on a slow broker.
7. Publish-probe cannot be the failure signal in the overlap scenario (conflicting stream captures the subject, so `js_Publish` succeeds) — the test must probe stream existence.

## Verified On

| Project | Context | Notes |
|---------|---------|-------|
| ProjectNestor | Issue #121 planning session (2026-07-03) | Plan only; no code executed; cnats (nats.c) v3.12.0; live test design informed by `test/src/test_nats_client_live.cpp` from PR #120 |
