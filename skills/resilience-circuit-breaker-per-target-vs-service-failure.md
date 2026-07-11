---
name: resilience-circuit-breaker-per-target-vs-service-failure
description: "A circuit breaker must not count 'the service answered correctly about one target' errors (404, could-not-resolve, no-checks) as failures — split per-target errors from per-credential errors, add a generic ignore predicate, and ANCHOR the classifying regexes or you fail OPEN. Use when: (1) adding or reviewing a circuit breaker that shells out to a CLI/HTTP service, (2) a handful of deterministic 404-style errors is opening a breaker and failing unrelated calls, (3) porting a retry (non-transient) classifier into a breaker (service-down) classifier."
category: architecture
date: 2026-07-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - circuit-breaker
  - resilience
  - fail-open
  - error-classification
  - regex-anchoring
---

# Resilience: Per-Target vs Service Failure in a Circuit Breaker

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-10 |
| **Objective** | Stop a circuit breaker from counting "the service answered correctly about one specific target" errors (HTTP 404, could-not-resolve, no-checks-reported) toward its failure threshold, so a handful of deterministic per-target errors can no longer open the breaker and fail every unrelated call behind it (the #1795 cascade). |
| **Outcome** | Successful. Added a generic keyword-only `ignore` predicate to `CircuitBreaker`; GitHub-specific anchored patterns live in the client. Fixed a CRITICAL fail-open hole found by strict review (bare `not found` matched real outages). PR #2049 merged to ProjectHephaestus main, all CI green. |
| **Verification** | verified-ci |

## When to Use

- You are adding, or reviewing, a circuit breaker that fronts a service reached via a CLI or HTTP call whose errors mix "service is down" with "service is up and told me about a specific target."
- A small number of deterministic errors (a missing issue, a 404) is opening a breaker and then failing unrelated calls that share it.
- You are tempted to copy a retry classifier's "is this non-transient?" regexes into a breaker's "is the service down?" classifier — they tolerate error in OPPOSITE directions and this port is a fail-open.
- You are tempted to "just record a success on 404" to keep the breaker closed — this masks a real outage building underneath.
- You are writing or reviewing a HALF_OPEN test and need to know why a `state is HALF_OPEN` assertion cannot fail.

## Verified Workflow

### Quick Reference

```python
# GENERIC layer (resilience/circuit_breaker.py): optional, keyword-only.
class CircuitBreaker:
    def __init__(self, *, ignore: Callable[[BaseException], bool] | None = None, ...):
        self._ignore = ignore

    def call(self, fn, *a, **k):
        self._enter()  # may consume a HALF_OPEN probe slot
        try:
            result = fn(*a, **k)
        except BaseException as exc:
            if self._ignore is not None and self._ignore(exc):
                self._release_half_open_slot()  # MUST release, or slots leak
                raise                            # re-raise: NOT failure, NOT success
            self._record_failure()
            raise
        else:
            self._record_success()
            return result
```

```python
# DOMAIN layer (github/client.py): anchored, service-specific patterns.
# Per-TARGET (service answered correctly about one target) -> DO NOT open breaker:
_PER_TARGET = re.compile(
    r"HTTP 404"
    r"|could not resolve to (an )?(issue|pull ?request)"  # note: pull ?request
    r"|Expected VALUE, actual: UNKNOWN_CHAR"              # anchored, not bare "Parse error"
    r"|Body is not editable"
    r"|no checks reported on the",
    re.IGNORECASE,
)
# Per-CREDENTIAL (401/403/token-scope/400/422) is DELIBERATELY EXCLUDED here:
# it recurs on every call, so it SHOULD open the breaker (fail fast).
gh_breaker = get_circuit_breaker("gh", ignore=lambda e: bool(_PER_TARGET.search(str(e))))
```

### Detailed Steps

1. **Name the two questions and keep them separate.** "Non-transient?" is a RETRY
   question (should we retry?). "Service down?" is a BREAKER question (is the target
   unavailable?). They are not the same predicate and must not share one regex set.
2. **Add a generic `ignore` predicate to the breaker** (resilience layer), keyword-only,
   defaulting to `None`. A matched exception is re-raised but recorded as NEITHER
   failure NOR success. Other breaker consumers pass nothing and are unaffected.
3. **Put the service-specific anchored patterns in the domain client**, not in the
   generic breaker. Keep the resilience layer ignorant of GitHub.
4. **Anchor every per-target pattern** to the service's ACTUAL per-target rendering
   (`HTTP 404`, `could not resolve to ...`, `no checks reported on the`). Never use a
   bare substring like `not found` or `Parse error` (see Failed Attempts).
5. **Classify per-credential errors as service failures** (401/403/token-scope/400/422):
   they recur on every call, so failing fast via the breaker is correct. Do NOT add
   them to the ignore set.
6. **Release the HALF_OPEN probe slot** on an ignored exception, or a burst of ignored
   errors leaks slots and wedges the breaker in HALF_OPEN.
7. **Run the adversarial-string check and the mutation test** (Results & Parameters)
   before claiming the classifier is safe.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Copy retry regexes into the breaker | Reused the retry classifier's non-transient patterns verbatim as the breaker's ignore set | CRITICAL fail-open. Bare `not found` matched `gh: command not found` (CLI missing), `ssh: Could not resolve hostname github.com: ... not found` (DNS failure), and `GitHub is temporarily unavailable. Page not found.` (outage page). Bare `Parse error` matched a truncated 502 HTML body fed to a JSON parser. All of these mean the service IS down, yet they were excluded from the breaker. | Over-matching is SAFE in a retry classifier (you just skip a retry) but UNSAFE in a breaker classifier (you blind it to a real outage). Anchor per-target patterns to the service's exact renderings. |
| Record a success on 404 | "Naive fix": on an ignored per-target error, call `record_success()` to keep the breaker closed | A success ZEROES the accumulating failure count, masking a genuine outage building underneath. | An ignored error is NEITHER failure NOR success. Do not record either. |
| Forget the HALF_OPEN slot | Ignored exceptions re-raised but the consumed HALF_OPEN probe slot was never released | A burst of ignored errors leaks slots; the next probe hits HALF_OPEN_EXHAUSTED and the breaker wedges in HALF_OPEN. | Releasing the probe slot on an ignored exception is part of "ignore," not an optimization. |
| Assert only `state is HALF_OPEN` | HALF_OPEN test asserted the breaker state was unchanged after an ignored exception | The state doesn't change whether or not the slot was released, so the test CANNOT FAIL. Mutation test: neuter `_release_half_open_slot` to `pass` — the test stays green while the slot leaks. | Assert the slot is RETURNED: with `half_open_max_calls=1`, admit a LATER probe through the single slot and assert `_half_open_calls == 0`. Test the behaviour, not the unobservable state. |
| Assert subset on regex source strings | Verified the invariant by set-comparing `.pattern` strings of the per-target vs non-transient regexes | Breaks the moment you correctly NARROW a pattern, and never proved the semantic implication anyway. | Assert the invariant on BEHAVIOUR against real stderr samples: "anything classified per-target must also be non-transient." Not a `.pattern` set comparison. |
| Re-register breaker with a new predicate | Called `get_circuit_breaker("gh", ignore=...)` a second time for an already-registered name | `get_circuit_breaker` is a singleton-per-NAME registry; the second call SILENTLY DISCARDS the `ignore` predicate and returns the existing instance. | Document the footgun and pin it with a test. Wire the predicate at first construction. |
| `pull request` with a space | A prior fix (#1806) matched the GraphQL type as `pull request` | gh emits the type name as `PullRequest` (no space) for a missing PR, so the pattern missed and the call was retried 6x. | Use `pull ?request` in both the retry and breaker patterns to tolerate both renderings. |

## Results & Parameters

**Adversarial-string check** — every string below means the SERVICE IS DOWN and MUST
be classified as a failure (i.e. the ignore predicate must return `False`). Run this
against your final anchored predicate; the naive bare-`not found` version fails it:

```python
import re

PER_TARGET = re.compile(
    r"HTTP 404"
    r"|could not resolve to (an )?(issue|pull ?request)"
    r"|Expected VALUE, actual: UNKNOWN_CHAR"
    r"|Body is not editable"
    r"|no checks reported on the",
    re.IGNORECASE,
)
is_per_target = lambda s: bool(PER_TARGET.search(s))

SERVICE_DOWN = [
    "gh: command not found",                                             # CLI missing
    "ssh: Could not resolve hostname github.com: Name or service not found",  # DNS
    "GitHub is temporarily unavailable. Page not found.",                # outage page
    "<html><title>502 Bad Gateway</title> Parse error: unexpected <",    # truncated 502
    "HTTP 401: Bad credentials",                                         # per-credential
    "HTTP 403: token scope insufficient",                               # per-credential
    "HTTP 422: Validation Failed",                                       # per-credential
]
leaked = [s for s in SERVICE_DOWN if is_per_target(s)]
assert not leaked, f"FAIL-OPEN: breaker would ignore real outages: {leaked}"

PER_TARGET_OK = [
    "GraphQL: Could not resolve to an Issue with the number 999 (repository.issue)",
    "GraphQL: Could not resolve to a PullRequest with the number 42",
    "gh: HTTP 404: Not Found (https://api.github.com/repos/x/y/issues/1)",
    "no checks reported on the 'abc123' ref",
    "Body is not editable",
]
missed = [s for s in PER_TARGET_OK if not is_per_target(s)]
assert not missed, f"per-target errors misclassified as service-down: {missed}"
print("adversarial-string check PASSED")
```

**Mutation test for the HALF_OPEN slot release** — proves the test can actually fail.
A `state is HALF_OPEN` assertion survives this mutation; the slot-return assertion does not:

```python
def test_ignored_exception_releases_half_open_slot():
    # Single probe slot so a leak is observable.
    cb = CircuitBreaker(name="t", failure_threshold=1, half_open_max_calls=1,
                        ignore=lambda e: isinstance(e, PerTargetError))
    cb._force_open_then_half_open()  # drive to HALF_OPEN in your test harness

    # First probe raises an IGNORED exception -> must RELEASE the slot.
    with pytest.raises(PerTargetError):
        cb.call(lambda: (_ for _ in ()).throw(PerTargetError("HTTP 404")))

    # If the slot was released, a LATER probe is admitted through the single slot.
    assert cb._half_open_calls == 0            # slot returned
    assert cb.call(lambda: "ok") == "ok"       # later probe admitted
    # Mutation: replace _release_half_open_slot body with `pass`.
    #   -> _half_open_calls stays 1, the later probe is rejected -> THIS TEST FAILS.
    #   A test asserting only `cb.state is HALF_OPEN` stays GREEN under that mutation.
```

**Layering contract:**

- Generic `ignore` predicate lives in `resilience/circuit_breaker.py` — no GitHub knowledge.
- Anchored per-target patterns live in `github/client.py`.
- Per-credential errors (401/403/token-scope/400/422) are EXCLUDED from ignore — they
  correctly open the breaker.
- Import-time `ignore=<name>` requires the predicate be DEFINED ABOVE the breaker
  construction (see companion import-order skill).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #2049 (merged, all CI green); `hephaestus/github/client.py` + `hephaestus/resilience/circuit_breaker.py`. Fail-open hole and fix both reproduced with runnable scripts and mutation-tested. Companion to the #1795 cascade skill. | verified-ci |
