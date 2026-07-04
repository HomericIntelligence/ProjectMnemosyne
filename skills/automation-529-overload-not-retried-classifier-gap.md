---
name: automation-529-overload-not-retried-classifier-gap
description: "Use when: (1) an agent/API call hits 529 Overloaded or 5xx and is treated as fatal despite max_retries being set; (2) a retry loop only fires on quota/429-with-reset-epoch and ignores server-overload; (3) auditing whether retryability covers ALL transient failure families; (4) a subprocess hard-codes a timeout that bypasses a centralized timeout module; (5) a reviewer/agent path records a synthetic ERROR verdict and IMMEDIATELY retries against an exhausted 429 session-limit quota instead of waiting until reset; (6) a transient-failure (429/529/timeout) handler exists in ONE agent-call path but a SIBLING path that calls the same invoker lacks it — audit every sibling path that calls the same invoker; (7) a CLI exits 0 but returns an `is_error:true` JSON envelope carrying api_error_status 429 that a caller silently treats as a real result; (8) a 429 carries a remediation hint (switch models with /model) instead of a reset epoch — needs a model-switch fallback, not wait-until-reset."
category: debugging
date: 2026-07-03
version: "1.2.0"
user-invocable: false
verification: verified-ci
history: automation-529-overload-not-retried-classifier-gap.history
tags: []
---

# Automation 529 Overload Not Retried — Classifier Gap

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-03 |
| **Objective** | Identify and fix why transient-failure handling (429 session-limit / 529 Overloaded / model-specific usage cap) is wired into one agent-call code path but absent from a sibling path — or absent from the classifier taxonomy entirely — so the gap recurs per-path or per-family |
| **Outcome** | Root cause found and fixed in three instances: (1) 529 single-classifier gap in the planner (PR #1375); (2) 429 session-limit gap in the in-loop PR-review path (PRs #1531/#1537) — the detect-quota-then-`wait_until` pattern present in the implement phase was missing from the review phase, so an exhausted quota fired ~39 doomed reviewer sessions in one hour. Fix: shared `_handle_reviewer_quota_or_overload` helper + opt-in `raise_for_error_envelope` for the exit-0 is_error envelope; (3) model-specific 429 usage cap with NO reset epoch (PR #1794) — remediation is a MODEL SWITCH, not a wait: `detect_model_usage_cap` classifier + sticky `_capped_models` fallback registry at the single `invoke_claude_with_session` chokepoint |
| **Verification** | verified-ci AND verified end-to-end against a live automation-loop run |

## When to Use

- An agent or API call receives `API Error: 529 Overloaded` (or any 5xx) and execution fails with `phase plan FAILED rc=1` despite `max_retries` being non-zero
- A retry loop is gated on `scan_quota_reset()` / `resolve_quota_reset_epoch()` or any similar function that only matches 429-with-reset-epoch phrasings — meaning it structurally cannot trigger on server-overload responses
- Auditing a retry implementation to confirm retryability covers ALL transient failure families (quota/rate-limit, server-overload, timeout)
- A subprocess invokes a hard-coded literal timeout (e.g. `timeout=600`) that bypasses a centralized timeout helper, silently capping the budget below the configured value
- **A reviewer/agent path records a synthetic ERROR verdict (e.g. `Verdict=ERROR Grade=F`) and IMMEDIATELY re-reviews against an exhausted 429 session-limit quota** instead of detecting the reset epoch and waiting (`wait_until`) — this burns dozens of doomed sessions per hour against a quota that does not reset until a fixed time (e.g. "resets 5pm")
- **A sibling code path that calls the same Claude invoker lacks the quota/overload handling its peer has** — when you find a transient-failure handler in ONE path, audit EVERY sibling catch site that calls the same invoker; the gap recurs per-path
- **A CLI exits 0 but returns an `is_error:true` JSON envelope** (carrying `api_error_status` 429) that a caller parses as a real result — this is a distinct, easily-missed detection gap from the non-zero-exit / `CalledProcessError` path
- **A 429 message offers a remediation hint INSTEAD of a reset time** — e.g. "You've reached your Fable 5 limit. Run /usage-credits to continue or switch models with /model." carries NO "resets <time>" clause, so `resolve_quota_reset_epoch` returns None and every wait-until-reset handler treats it as fatal. A 429 that says "switch models" is a DIFFERENT failure family ("switch-resource") from a quota-wait ("wait-until-reset") — audit whether the classifier taxonomy distinguishes the two remediations; the fix is a model-switch fallback, not a wait

## Verified Workflow

### Quick Reference

```python
# 1. Separate classifier for server overload (does NOT require a reset epoch)
import re

_OVERLOAD_PATTERNS = re.compile(
    r"(API Error.*?529|status[:\s]+529|Overloaded|overloaded_error"
    r"|API Error.*?5[0-9]{2}|status[:\s]+5(?!00\b)[0-9]{2})",
    re.IGNORECASE,
)
_OVERLOAD_REJECT = re.compile(r"\b4[0-9]{2}\b")  # never match 4xx

def detect_server_overload(*texts: str) -> bool:
    """Return True if any text signals a transient server-overload (529 / 5xx)."""
    combined = " ".join(t for t in texts if t)
    if _OVERLOAD_REJECT.search(combined):
        return False
    return bool(_OVERLOAD_PATTERNS.search(combined))

# 2. Union-of-classifiers retry branch in call_claude()
for attempt in range(max_retries + 1):
    result = _run_claude(...)
    reset_epoch = scan_quota_reset(result.stderr, result.stdout)  # 429 path
    if reset_epoch is not None:
        _wait_until(reset_epoch)
        continue
    if detect_server_overload(result.stderr, result.stdout):     # 529/5xx path
        delay = min(5 * (2 ** attempt), 20)                     # 5s → 10s → 20s
        time.sleep(delay)
        continue
    # ... timeout path, fatal path

# 3. Route subprocess timeout through centralized helper (not a literal)
timeout = planner_claude_timeout()   # reads HEPH_PLANNER_AGENT_TIMEOUT, default 7200
subprocess.run([...], timeout=timeout)

# 4. SHARED reviewer quota/overload helper — wire into EVERY sibling catch site so
#    the review path is symmetric with the implement path. Call this BEFORE returning
#    the INFRA_ERROR sentinel so an exhausted quota does NOT trigger an immediate re-review.
def _handle_reviewer_quota_or_overload(error, *, issue_number, iteration):
    """Wait on quota reset / back off on overload before surfacing INFRA_ERROR.

    Honors a typed ClaudeUsageCapError.reset_epoch (its message carries no reset
    phrasing for text scanning), else falls back to scanning the error text.
    """
    msg = str(error)
    reset_epoch = getattr(error, "reset_epoch", None)  # typed error wins
    if reset_epoch is None:
        reset_epoch = resolve_quota_reset_epoch(msg)
    if reset_epoch is not None:
        wait_until(reset_epoch)            # do NOT re-review until the quota resets
        return
    if detect_server_overload(msg):
        for attempt in range(3):
            time.sleep(min(5 * (2 ** attempt), 20))  # 5s → 10s → 20s, capped
            return
    # otherwise fall through to INFRA_ERROR sentinel

# 5. OPT-IN guard for the exit-0 `is_error:true` JSON envelope (api_error_status 429).
#    MUST stay opt-in: a central raise inside invoke_claude_with_session would break
#    retry-aware callers (planner_claude, _implement_phase) that inspect
#    CalledProcessError.stdout themselves.
class ClaudeUsageCapError(RuntimeError):
    def __init__(self, message, *, reset_epoch=None):
        super().__init__(message)
        self.reset_epoch = reset_epoch

def raise_for_error_envelope(stdout: str) -> None:
    """Raise on a Claude CLI exit-0 `is_error:true` envelope; no-op otherwise."""
    envelope = _try_parse_json(stdout)
    if not (isinstance(envelope, dict) and envelope.get("is_error")):
        return
    if _envelope_status(envelope) == 429:
        raise ClaudeUsageCapError("usage cap hit", reset_epoch=_envelope_reset_epoch(envelope))
    raise RuntimeError("Claude CLI returned an is_error envelope")

# 6. MODEL-SPECIFIC usage cap (429 with NO reset epoch) — remediation is a MODEL
#    SWITCH, not a wait. Three independent signals so a partial rewording still
#    matches; negative lookahead keeps "session limit"/"usage limit" owned by the
#    wait-path detectors.
_MODEL_CAP_LIMIT = re.compile(
    r"reached\s+your\s+(?!session\b|usage\b)[\w .-]{1,40}?\s+limit",
    re.IGNORECASE,
)

def detect_model_usage_cap(*texts: str) -> bool:
    """Return True if any text signals a model-specific usage cap."""
    combined = " ".join(t for t in texts if t)
    return bool(
        _MODEL_CAP_LIMIT.search(combined)
        or "/usage-credits" in combined
        or "switch models with /model" in combined.lower()
    )

_capped_models: set[str] = set()   # sticky per-process registry

# In invoke_claude_with_session (the ONE chokepoint, NOT per-path):
#   - UP FRONT: if the requested model is in _capped_models, substitute
#     agent_config.fallback_model() (HEPH_FALLBACK_MODEL env override, default
#     claude-opus-4-8) — avoids repeated doomed ~0.5s calls (prior art in this
#     skill: 39 doomed reviewer sessions/hour)
#   - ON FIRST CAP DETECTION: register the model, retry the SAME request once on
#     the fallback; NO retry when the effective model already IS the fallback
#     (no loop; the error propagates to existing handling)
#   - Scan the exit-0 envelope ONLY when output_format == "json"; NEVER scan
#     plain-text exit-0 output — agent prose can legitimately contain the
#     trigger phrases (false-positive guard)
```

### Detailed Steps

1. **Identify the single-classifier gate**: locate the retry loop and find the ONLY condition that enables retry. If that condition requires a reset epoch (or any field 529s never carry), the loop is structurally broken for 529s.

2. **Add `detect_server_overload(*texts)`**: implement a separate regex classifier matching `529`, `Overloaded`, `overloaded_error`, and `5xx` patterns anchored to `API Error` / `status` context. Explicitly reject bare 4xx matches with a negative pattern so fatal client errors are never retried.

3. **Wire a separate overload-retry branch**: after the quota-reset check, add `elif detect_server_overload(...)` with bounded exponential backoff (e.g. 5 / 10 / 20 seconds). Do not mix it with the quota path — they have different wait strategies.

4. **Enumerate all transient families and confirm each has a detector**:
   - Quota / 429 with reset epoch → `scan_quota_reset` / `resolve_quota_reset_epoch`
   - Server overload / 529 / 5xx → `detect_server_overload` (new)
   - Timeout / SIGKILL → separate timeout detector or exception catch

5. **Route subprocess timeouts through the centralized helper**: replace any literal `timeout=600` (or similar hard-coded value) with `timeout=planner_claude_timeout()` which reads `HEPH_PLANNER_AGENT_TIMEOUT` (default 7200).

6. **AUDIT EVERY SIBLING PATH that calls the same invoker**: once you find a transient-failure handler in one agent-call path, grep for all other catch sites that invoke the same Claude runner (e.g. `_run_impl_review_step`, `_run_impl_review`, `pr_reviewer.py`, `review_validator.py`). The detect-quota-then-`wait_until` pattern present in `_implement_phase.py` was ABSENT from `_review_phase.py` — so an exhausted quota recorded a synthetic `Verdict=ERROR Grade=F` and immediately re-reviewed, firing ~39 doomed reviewer sessions in one hour. Add a SHARED module-level helper (`_handle_reviewer_quota_or_overload`) and wire it into BOTH catch sites so the review path is symmetric with the implement path.

7. **Wait BEFORE surfacing the INFRA_ERROR sentinel**: the shared helper must check `resolve_quota_reset_epoch` (or a typed error's `reset_epoch`) and `wait_until` it BEFORE returning the sentinel — otherwise the caller re-reviews instantly against the still-exhausted quota.

8. **Guard the exit-0 `is_error` envelope as a DISTINCT gap**: the Claude CLI can EXIT 0 while returning an `is_error:true` JSON envelope carrying `api_error_status` 429. Callers (`pr_reviewer` / `review_validator`) parsed that envelope as review text → silent bogus verdict. Add an OPT-IN `raise_for_error_envelope(stdout)` that raises `ClaudeUsageCapError(reset_epoch=...)` on a 429 envelope (a `RuntimeError` subclass) or a plain `RuntimeError` otherwise. Keep it OPT-IN: a central raise inside `invoke_claude_with_session` would break retry-aware callers (`planner_claude`, `_implement_phase`) that inspect `CalledProcessError.stdout` themselves. Teach the review-phase helper to honor `ClaudeUsageCapError.reset_epoch` because the typed error's message has no reset phrasing for text scanning.

9. **Classify by REMEDIATION, not just by status code**: a 429 whose message offers a remediation hint ("switch models with /model") instead of a "resets <time>" clause is a DIFFERENT failure family from a quota-wait — `resolve_quota_reset_epoch` returns None and every wait-until-reset handler hard-fails it. In the 2026-07-03 run, ~48 doomed calls failed across planner/reviewer/implementer/advise/learn until the loop degraded to no-ops, in BOTH failure shapes (non-zero exit AND exit-0 `is_error:true` envelope with `api_error_status` 429). Fix at the ONE chokepoint (`invoke_claude_with_session`), not per-path: add `detect_model_usage_cap(*texts)`, a sticky per-process `_capped_models` registry that substitutes `agent_config.fallback_model()` up front once a model caps, and a once-only retry of the SAME request on the fallback (never when the effective model already IS the fallback). Take the fallback model from config (`HEPH_FALLBACK_MODEL` env override), never a hardcoded literal at the call site. Scan the exit-0 envelope only for `output_format="json"` — plain-text output can legitimately contain the phrases.

10. **Validate**: run `pixi run pytest tests/unit -v` — confirm new unit tests pass and existing retry tests are unaffected. Then re-run the live automation loop end-to-end and confirm zero 429/ERROR/Traceback lines.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single quota-reset-epoch retry trigger | Retry loop conditioned solely on `scan_quota_reset()` returning non-None; `max_retries=3` was set | `resolve_quota_reset_epoch` only matches 429 phrasings that carry a reset timestamp; 529 Overloaded has no reset epoch so `scan_quota_reset` returned None and the retry branch was skipped entirely | A retry loop gated on ONE classifier is structurally blind to any transient error family that classifier does not recognize — even if `max_retries` is non-zero |
| Hard-coded 600s subprocess timeout | `plan-issues` subprocess used `timeout=600` literal instead of the centralized `planner_claude_timeout()` | The configured budget is 7200s (`HEPH_PLANNER_AGENT_TIMEOUT`); the literal 600s cap silently killed long-running plan runs 12x earlier than intended | Every subprocess timeout must be routed through the centralized timeout helper — never a literal value — to honor the operator-configured budget |
| Record synthetic ERROR verdict + immediate re-review on quota exhaustion | The in-loop reviewer caught a 429 session-limit, recorded `Verdict=ERROR Grade=F`, and immediately looped back to re-review — with NO `wait_until(reset_epoch)` (the implement phase HAD this; the review phase did not) | The quota does not reset until a fixed time (e.g. "resets 5pm"), so every re-review hit the same exhausted quota — ~39 doomed reviewer sessions fired in one hour | When a sibling path lacks the wait-on-quota handling its peer has, the gap recurs per-path; the handler must `wait_until` the reset BEFORE returning the INFRA_ERROR sentinel, never re-invoke immediately |
| Centralize the raise inside `invoke_claude_with_session` | Considered raising `ClaudeUsageCapError` centrally inside the shared invoker so every caller would see the typed error | Retry-aware callers (`planner_claude`, `_implement_phase`) inspect `CalledProcessError.stdout` themselves and a central raise would break their existing flows (they never see the `CalledProcessError`) | The error-envelope guard MUST be OPT-IN (`raise_for_error_envelope(stdout)`), called only by callers that want it, so it does not change the invoker's contract for retry-aware callers |
| Treat every 429 as wait-until-reset | Model-specific cap ("You've reached your Fable 5 limit. Run /usage-credits to continue or switch models with /model.") was routed through the quota-wait handlers | The message carries NO reset epoch, so `resolve_quota_reset_epoch` returned None and every wait-until-reset handler treated the call as a fatal error — ~48 doomed calls failed across planner/reviewer/implementer/advise/learn in one run until it degraded to no-ops | Classify by REMEDIATION — a 429 offering "switch models" needs a model-switch fallback (sticky registry + once-only same-request retry on the fallback), not a wait; audit whether the taxonomy distinguishes "wait-until-reset" from "switch-resource" |

## Results & Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Overload backoff schedule | 5s / 10s / 20s (capped) | `min(5 * 2**attempt, 20)` |
| Overload retry max attempts | Shares `max_retries` (default 3) | Same counter as quota retries |
| Centralized timeout env var | `HEPH_PLANNER_AGENT_TIMEOUT` | Default 7200s; read by `planner_claude_timeout()` |
| Classifier match set (529) | `API Error.*529`, `status.*529`, `Overloaded`, `overloaded_error` | Case-insensitive |
| Classifier match set (5xx) | `API Error.*5[0-9]{2}`, `status.*5[0-9]{2}` (excluding 500) | Anchored to avoid bare digit matches |
| Classifier reject set | `\b4[0-9]{2}\b` | Prevents matching fatal 4xx client errors |
| Shared reviewer helper | `_handle_reviewer_quota_or_overload(error, *, issue_number, iteration)` | Module-level in `_review_phase.py`; wired into BOTH `_run_impl_review_step` and `_run_impl_review`; called BEFORE returning the INFRA_ERROR sentinel |
| Exit-0 envelope guard | `raise_for_error_envelope(stdout)` in `claude_invoke.py` | OPT-IN; raises `ClaudeUsageCapError(reset_epoch=...)` (RuntimeError subclass) on a 429 envelope, else plain `RuntimeError`; does NOT change `invoke_claude_with_session`'s contract |
| Typed error reset epoch | `ClaudeUsageCapError.reset_epoch` | Review-phase helper honors this attribute (the typed error's message carries no reset phrasing for text scanning) |
| Fix 1 (429 reviewer sibling gap) | PR #1531 / issue #1528 | Shared `_handle_reviewer_quota_or_overload`; review path made symmetric with implement path |
| Fix 2 (exit-0 is_error envelope) | PR #1537 / issue #1536 | Opt-in `raise_for_error_envelope` + `ClaudeUsageCapError` |
| Model-cap classifier | `detect_model_usage_cap(*texts)` in `claude_invoke.py` | Regex `reached\s+your\s+(?!session\b|usage\b)[\w .-]{1,40}?\s+limit` OR `/usage-credits` OR `switch models with /model` — three independent signals; lookahead keeps session/usage limits owned by the wait-path detectors |
| Sticky cap registry | `_capped_models` per-process set | Once model M caps, the `invoke_claude_with_session` chokepoint substitutes the fallback UP FRONT — no repeated doomed ~0.5s calls |
| Fallback model source | `agent_config.fallback_model()` | `HEPH_FALLBACK_MODEL` env override, default `claude-opus-4-8`; from config, never a hardcoded literal at the call site |
| Fallback retry policy | Retry SAME request once on the fallback | NO retry when the effective model already IS the fallback — no loop; error propagates to existing handling |
| Envelope scan scope | ONLY `output_format="json"` | Plain-text exit-0 output never scanned — agent prose can legitimately contain the trigger phrases |
| Fix 3 (model-cap 429, no reset epoch) | PR #1794 / issue #1793 | Merged, CI green; fix at the ONE chokepoint, not per-path |
| Prereq + supporting PRs | #1530 (prereq), #1533, #1535 | All merged green to ProjectHephaestus main |
| End-to-end re-validation | Issue #1517 → PR #1538 | Re-ran the automation loop: plan phase `Verdict=GO`; implement phase created PR #1538; in-loop review `Verdict=GO`; ZERO 429/ERROR/Traceback lines |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1375 / issue #1374 — automation-loop planner hit 529 on issue #1357 | CI green; `detect_server_overload` unit tests pass; subprocess timeout routed through `planner_claude_timeout()` |
| ProjectHephaestus | PRs #1531 (issue #1528) + #1537 (issue #1536) — 429 session-limit in the in-loop PR-review sibling path | Shared `_handle_reviewer_quota_or_overload` helper + opt-in `raise_for_error_envelope`; PRs #1530/#1531/#1533/#1535/#1537 merged green; end-to-end re-validated on issue #1517 → PR #1538, Verdict=GO, zero error lines |
| ProjectHephaestus | PR #1794 / issue #1793 — 2026-07-03 automation-loop run: ~48 doomed calls on a model-specific 429 cap with NO reset epoch (both non-zero exit AND exit-0 `is_error:true` envelope with `api_error_status` 429) | `detect_model_usage_cap` + sticky `_capped_models` fallback (once-only same-request retry) at the `invoke_claude_with_session` chokepoint; merged, CI green |
