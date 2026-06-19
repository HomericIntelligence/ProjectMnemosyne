---
name: planning-bounded-queue-eviction-durability-ordering
description: "Planning-discipline meta-pattern: before deciding how to remediate a bounded in-memory collection (deque(maxlen=N), ring buffer, LRU cache) that 'drops'/'evicts' items, READ THE SOURCE to determine whether a DURABLE write precedes the in-memory append. If durable-write-precedes-eviction, the eviction is NOT data loss — it is loss of an inspection/view cache only — so the correct fix is a distinct WARNING + metric (log-and-continue), NOT rejecting the caller with an error (fail-fast / HTTP 503), which would falsely signal failure for an operation that already succeeded durably and may violate the service's documented contract. Ordering of durable-write vs in-memory mutation decides whether 'queue full' is a failure or a benign rollover. Detection subtlety: a deque(maxlen=N) never exceeds N, so a POST-append len() cannot detect eviction — you must capture fullness (len()==maxlen) BEFORE the append. Use when: (1) planning a fix for a 'queue/buffer full', 'backpressure', 'eviction', or 'dropped events' issue against a bounded in-memory structure, (2) choosing between fail-fast (reject/503) and log-and-continue remediation, (3) an issue offers option-a (reject request) vs option-b (warn + metric) and you must pick, (4) adding an eviction counter/metric to a maxlen deque, (5) the plan asserts an HTTP/contract behavior (e.g. '200 OK for accepted events') that the remediation might contradict, (6) the plan relies on unverified test seams (monkeypatching get_settings + cache_clear, prometheus_client private _value.get(), an assumed publish() signature) or drift-prone file:line citations."
category: architecture
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning-methodology
  - bounded-collection
  - deque-maxlen
  - eviction
  - backpressure
  - durable-vs-volatile-ordering
  - fail-fast-vs-log-and-continue
  - http-contract
  - metrics-counter
  - prometheus-test-assertion
  - monkeypatch-seam
  - line-number-drift
  - unverified
---

# Planning: Bounded-Queue Eviction — Verify Durable-vs-Volatile Ordering Before Choosing Remediation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Stop planners from reflexively treating a "bounded in-memory queue is full / dropping items" issue as data loss and reaching for fail-fast (reject / HTTP 503). The remediation is decided by ONE source-level fact: is a durable write performed BEFORE the in-memory append? |
| **Outcome** | Plan produced for ProjectHermes #533 (dead-letter deque eviction). Recommendation: distinct WARNING + eviction metric (log-and-continue), NOT reject-with-503. Plan was authored but NEVER executed — `unverified`. |
| **Verification** | `unverified` — durable-before-volatile ordering was read from source, not confirmed by running tests; the load-bearing claim is the cited line ordering. |

## When to Use

- Planning a fix for an issue described as "queue full", "buffer full", "backpressure", "eviction", or "dropped/lost events" where the structure is a **bounded in-memory collection** (`collections.deque(maxlen=N)`, ring buffer, fixed-size LRU cache).
- An issue presents two options — **(a) reject the request / fail fast (HTTP 503)** vs **(b) log a warning + emit a metric and continue** — and you must choose.
- You are about to add an eviction counter/metric to a `deque(maxlen=N)`.
- The plan asserts (or the service documents, e.g. in an ADR) an HTTP/API contract such as "200 OK for accepted/dead-lettered events" that a fail-fast remediation might silently break.
- The plan leans on test seams or APIs you have NOT executed: monkeypatching a cached `get_settings()` (+ `cache_clear()`), reading a `prometheus_client` Counter via the private `._value.get()`, or an assumed function signature.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

<!-- The heading below is required verbatim by scripts/validate_plugins.py; the human-facing
     title for this `unverified` skill is "Proposed Workflow" above. -->
## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

The load-bearing decision is a single source-level fact. Find it before writing any remediation.

1. **Locate the append site.** Find where items enter the bounded collection (e.g. `self._dead_letters.append(entry)`). Open the surrounding function.
2. **Read the ordering relative to the durable write.** Look at the lines immediately *before* the append. Is there a durable/external write (e.g. `await js.publish(...)`, DB insert, file/WAL append) that completes first?
   - **Durable write PRECEDES append** → the in-memory collection is an *inspection/view cache*. Eviction is a **benign rollover**, not data loss. The durable store (JetStream stream, DB, dead-letter stream) is the source of truth and already has the record. → choose **log-and-continue (option b)**: distinct WARNING + eviction metric.
   - **Append PRECEDES the durable write**, or there is **no** durable write → eviction *is* real data loss. → fail-fast (reject / 503 / apply real backpressure) may be correct.
3. **Cross-check the documented contract.** Grep the ADRs / API docs for the endpoint's promised status (e.g. ADR-002 "200 OK for dead-lettered events"). If the durable write already succeeded, returning 503 would *contradict the contract* and falsely report failure. The contract is a second, independent reason fail-fast is wrong in the durable-precedes case.
4. **Fix the detection bug.** A `deque(maxlen=N)` **never exceeds N**, so a POST-append `len(dq) > N` (or `== N+1`) can never fire. Capture fullness BEFORE the append:
   ```python
   was_full = len(self._dq) == self._dq.maxlen   # capture BEFORE append
   self._dq.append(entry)                         # this evicts the oldest if was_full
   if was_full:
       logger.warning("dead-letter inspection cache full; oldest entry evicted (durable copy retained)")
       DEAD_LETTER_EVICTIONS.inc()
   ```
5. **Avoid alert redundancy.** If a threshold alert (e.g. fires at 80% of maxlen) ALREADY logs on every call once the queue is full, adding a second "100% full" warning per call is redundant and noisy. Decide whether the new signal is the eviction *event* (preferred: fires only on an actual eviction) vs another fullness *level* (redundant). Prefer signalling the eviction event.
6. **Verify every test seam before trusting it** (see Failed Attempts). Do not assume the injection point, the metric-read API, or the function signature — open the `def` and run the test.
7. **State the load-bearing assumption explicitly.** Because the recommendation flips entirely on step 2's ordering, write in the plan: "Recommendation assumes durable write at <file:line> precedes the in-memory append at <file:line>; if reversed, fail-fast becomes correct." Make the reviewer verify exactly that.

### Quick Reference

```bash
# 1. Find the bounded-collection append site
rg -n "\.append\(|deque\(maxlen" src/

# 2. Read ~10 lines BEFORE the append — is there a durable write first?
#    (js.publish / db.execute / file.write / WAL append)
rg -n -B10 "_dead_letters\.append" src/hermes/publisher.py

# 3. Confirm the documented HTTP/API contract the fix must not break
rg -ni "200 OK|dead-letter|status" docs/adr/ADR-002*.md

# Decision:
#   durable-write BEFORE append  -> log + metric (option b); 503 would be WRONG
#   append BEFORE durable-write  -> fail-fast / 503 may be correct

# Detect eviction CORRECTLY (maxlen deque never exceeds N):
#   was_full = len(dq) == dq.maxlen   # BEFORE append, not after
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Reflex remediation (option a) | Treat "deque full / dropping items" as data loss → reject the webhook with HTTP 503 | The durable write (`js.publish`) precedes the in-memory `append`; the record is already persisted to the dead-letter stream. 503 falsely reports failure AND contradicts ADR-002's documented "200 OK for dead-lettered events" | Read durable-vs-volatile ordering in source FIRST; for a durable-backed view cache, eviction is benign rollover, so warn+metric (option b) is correct, not fail-fast |
| Detect eviction after append | Plan an eviction check using `len(deque)` AFTER `append()` | `deque(maxlen=N)` silently drops the oldest and `len()` caps at N — a post-append length can never reveal that an eviction happened | Capture `was_full = len(dq) == dq.maxlen` BEFORE the append; the append itself performs the eviction |
| Trust the test injection seam unread | Assume `Settings(dead_letter_max_size=..., dead_letter_alert_threshold=...)` is constructor-settable and that monkeypatching `hermes.config.get_settings` + calling `get_settings.cache_clear()` is the right seam | Inferred only from reading that `Publisher.__init__` calls `get_settings()`; never confirmed by running the test. Cached-settings seams routinely surprise (frozen models, lru_cache scope, import-time capture) | Open the `Settings` model + the exact call site and RUN one test before building the plan on the seam |
| Read a Counter via private API | Assert metric value with `DEAD_LETTER_EVICTIONS._value.get()` | `._value` is a private `prometheus_client` internal that can change across versions; brittle | Prefer the public registry read `REGISTRY.get_sample_value("dead_letter_evictions_total")` for version-robust assertions |
| Assume the publish() signature | Write tests calling `publisher.publish(payload)` positionally | The real signature has more optional params (`publish_timeout`, `publish_retries`, `request_id`); the assumed call may not match | Re-read the actual `def publish(...)` before writing call sites in tests/plan |
| Trust cited line numbers | Cite `publisher.py:388-402`, `metrics.py:54-57`, `config.py:46-48`, `ADR-002 ~line 71` as stable anchors | Line numbers drift between filing and implementation; the file may have already changed | Re-grep by symbol/string against the CURRENT tree, not by line number; cite the symbol, not the offset |
| Add a redundant 100%-full warning | Add a "queue 100% full" warning on top of the existing 80%-threshold alert | The 80% threshold alert already fires on every call once the queue passes 80%, so a second per-call warning at 100% is redundant noise | Signal the eviction EVENT (fires only when an item is actually evicted), not another fullness LEVEL |

> These rows are the uncertain assumptions baked into the #533 plan. None were executed — each is a "verify-before-trusting" item for the next planner/reviewer.

## Results & Parameters

**Verification level: `unverified`.** The plan was authored from source reading only — no tests run, no lint, no CI. The durable-before-append ordering (read as `js.publish` then `deque.append` at the cited publisher lines) is the single load-bearing claim; if reversed, the recommendation flips to fail-fast.

**Decision rule (project-agnostic):**

| Source-level fact | "Queue full" means | Correct remediation |
|-------------------|--------------------|--------------------|
| Durable write completes BEFORE in-memory append | Loss of an inspection/view cache entry only; source of truth retains the record | Log distinct WARNING + emit eviction metric; keep returning success. Do NOT 503. |
| In-memory append BEFORE durable write, or no durable write at all | Real data loss | Fail fast / apply real backpressure / 503 may be correct |

**Worked example — ProjectHermes #533 (dead-letter deque):**

- Structure: `self._dead_letters: deque(maxlen=DEAD_LETTER_MAX_SIZE)` (default 1000) in `publisher.py`.
- Ordering (read, not run): `await js.publish(...)` to the `homeric-deadletter` JetStream stream **precedes** `self._dead_letters.append(entry)`. The deque is therefore an inspection cache for `GET /dead-letters`, not the durable record.
- Recommendation: **option (b)** — add a `dead_letter_evictions_total` Counter and a distinct WARNING that fires only on actual eviction (`was_full` captured before append). Reject **option (a)** (HTTP 503): it would falsely signal failure and break ADR-002's "200 OK for dead-lettered events" contract.

**Reviewer focus (highest-risk items to verify before merge):**

1. Is the durable-before-volatile ordering ACTUALLY true at the cited publisher lines? (load-bearing — flips the whole recommendation if false)
2. The prometheus private-API test assertion (`._value.get()`) — swap to `REGISTRY.get_sample_value`.
3. Test injection seam correctness (`get_settings` monkeypatch + `cache_clear()`).
4. Is a distinct 100%-full warning redundant with the existing 80%-threshold alert that already fires every call once full?

**Reusable eviction-detection snippet (any `maxlen` deque):**

```python
was_full = len(self._dq) == self._dq.maxlen   # MUST be before append
self._dq.append(entry)
if was_full:
    logger.warning("inspection cache full; oldest entry evicted (durable copy retained)")
    EVICTIONS_COUNTER.inc()  # assert via REGISTRY.get_sample_value(...), not ._value.get()
```
