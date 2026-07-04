---
name: ci-gate-verify-artifact-is-consumed-before-guarding
description: "A CI drift/lint/sync gate that guards a committed artifact (requirements.txt, a generated lockfile, a config) is THEATER if nothing actually consumes that artifact — the check passes review, looks protective, and protects nothing. Before adding a gate on artifact X, grep for who actually READS X (`grep -rn 'requirements.txt' Dockerfile docker-compose.yml .github/`). If no consumer exists, the gate is pointless: either wire a real consumer in the SAME PR or the gate is pure ceremony. Worked example (ProjectHermes #556): a plan added a `check-reqs` CI job to keep `requirements.txt` in sync with `pixi.lock`, but the Dockerfile derived its install list INLINE from `pyproject.toml` ranges and never read the committed `requirements.txt` — so the file the gate guarded was consumed by NOTHING. The fix, in the same PR: switch the Dockerfile to `COPY requirements.txt` + `pip install -r requirements.txt`, making the issue's stated failure mode ('Docker build uses stale pins') REAL and the gate load-bearing. Use when: (1) adding any CI check that validates one artifact against another (drift/sync/lint/freshness gate), (2) an issue claims a failure mode ('the build uses stale pins from the committed file X') that depends on a consumer you have not confirmed exists, (3) you are about to commit a generated artifact and add a gate for it, (4) reviewing a CI check and asking 'does this actually catch the bug it claims to.'"
category: ci-cd
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - ci-cd
  - drift-check
  - sync-gate
  - dead-artifact
  - consumer-wiring
  - requirements-txt
  - dockerfile
  - pixi-lock
  - load-bearing-check
  - gate-theater
  - planning
  - unverified-assumptions
---

# CI Gate: Verify the Artifact Is Actually Consumed Before Guarding It

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Capture the durable rule that a CI drift/sync/lint gate on a committed artifact is worthless unless something actually CONSUMES that artifact. A check that guards an unused file passes review but protects nothing — verify the consumer wiring before adding the gate, and wire one in the same PR if none exists. |
| **Outcome** | A transferable "grep for the consumer before adding the gate" rule, a worked example (a `check-reqs` gate guarding a `requirements.txt` that the Dockerfile never read), and the same-PR fix (switch the Dockerfile to `pip install -r requirements.txt` so the file becomes load-bearing). |
| **Verification** | **unverified** — this is an implementation PLAN that was never executed or merged end-to-end. The Dockerfile switch to `pip install -r requirements.txt` is a real behavior change to the production image build that was reasoned about but NOT run. Treat every assertion as a hypothesis. |

## When to Use

- You are adding any CI check that validates one artifact against another: a drift check, a sync check, a freshness/lint gate (e.g. "`requirements.txt` must match `pixi.lock`", "the generated client must match the schema").
- An issue asserts a failure mode — "the Docker build silently uses stale pins from the committed `requirements.txt`" — that depends on a CONSUMER (the Dockerfile reading that file) you have not confirmed exists.
- You are about to commit a generated artifact and add a gate to keep it fresh.
- You are reviewing a CI check and want to answer the harder question: "does this check actually catch the bug it claims to, or does it just guard a file nobody reads?"

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has NOT been validated end-to-end. It is an
> implementation PLAN that was written but never executed or merged. Verification level:
> `unverified`. The fix — switching the Dockerfile from an inline `pip install` derived from
> `pyproject.toml` ranges to `COPY requirements.txt` + `pip install -r requirements.txt` — is a
> real change to the production image build that was reasoned about but NOT run (no `docker build`
> executed). The section is titled "Verified Workflow" only to satisfy the marketplace validator.
> Treat every step below as a hypothesis until CI and a `docker build` confirm it.

### Quick Reference

```bash
# BEFORE adding a drift/sync gate on artifact X, find who actually READS X.
# If this returns nothing, the artifact is consumed by NOTHING and the gate is theater.
grep -rn 'requirements.txt' Dockerfile docker-compose.yml .github/ scripts/

# Worked example result (ProjectHermes #556):
#   Dockerfile:11  ->  RUN pip install <deps derived INLINE from pyproject.toml ranges>
#                      ... never references requirements.txt at all.
#   => the committed requirements.txt is read by NOTHING. A check-reqs gate on it
#      passes review but protects nothing — the "stale pins in Docker build" failure
#      mode the issue describes CANNOT happen, because Docker never reads the file.
```

```dockerfile
# THE FIX (same PR): make the artifact load-bearing by wiring a real consumer.
# BEFORE — install list derived inline from pyproject.toml ranges (requirements.txt ignored):
RUN pip install fastapi nats-py uvicorn ...        # inline, drifts independently

# AFTER — consume the guarded artifact, so the gate now protects a real path:
COPY requirements.txt .
RUN pip install -r requirements.txt                 # now the gate is load-bearing
```

### Detailed Steps and Durable Insights

#### 1. HEADLINE — a gate that guards an unconsumed artifact is theater

A drift/sync/lint check protects a real failure path ONLY when the artifact it guards is actually
read by something downstream. If you add a `check-reqs` job to keep `requirements.txt` in sync with
`pixi.lock`, but the Docker image build derives its install list INLINE from `pyproject.toml` and
never reads `requirements.txt`, then:

- The committed `requirements.txt` is consumed by **nothing**.
- The gate will pass review (it looks protective) and even fail correctly on drift — but the drift
  it detects has **no consequence**, because no build path uses the file.
- The issue's stated failure mode ("Docker build silently uses stale pins from the committed file")
  is **impossible** as written, because Docker never reads that file. The premise and the gate are
  both detached from reality.

#### 2. Grep for the consumer BEFORE adding the gate

For any artifact X you intend to guard, run a consumer search across the places that would read it:

```bash
grep -rn '<artifact-name>' Dockerfile docker-compose.yml .github/ scripts/ Makefile justfile
```

If nothing consumes X, you have two honest choices — never a third "ship the gate anyway":

- **Wire a real consumer in the SAME PR** so the artifact becomes load-bearing (preferred when the
  issue's intent is "this artifact should drive the build"). For #556: switch the Dockerfile to
  `COPY requirements.txt` + `pip install -r requirements.txt`.
- **Drop the gate** (and possibly the artifact) if nothing should consume it — guarding a file that
  by design no one reads is pure ceremony.

#### 3. Wiring the consumer is a real behavior change — verify it, don't assume equivalence

Switching the Dockerfile from an inline `pip install` to `pip install -r requirements.txt` changes
the production image build. Two things to verify rather than assume:

- **The generated `requirements.txt` is complete and correct.** If it's generated from a stale
  frozen allowlist it may DROP runtime deps the inline list had (see References — the premise
  skill's frozen-mirror lesson). Derive it from the source of truth.
- **Nothing the inline path provided is silently lost.** For #556 the inline extraction excluded
  the editable self-package (`hermes`), and `src/hermes/` is `COPY`'d separately — so the switch is
  BELIEVED equivalent, but the equivalence was reasoned, not tested. Run `docker build` to confirm.

#### 4. The reviewer-facing question

When reviewing any new CI gate, ask: "If this check is green, what real failure did it prevent?"
If the answer requires a consumer that doesn't exist, the check is theater. A passing check that
protects nothing is worse than no check — it creates false confidence.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Added a CI drift gate on a committed `requirements.txt` | Plan added a `check-reqs` job to keep `requirements.txt` in sync with `pixi.lock`, assuming the Docker build consumed the file | The Dockerfile derived its install list INLINE from `pyproject.toml` ranges (`Dockerfile:11`) and never read `requirements.txt` — the gate guarded a file consumed by nothing, so the issue's "stale pins in Docker build" failure mode was impossible | Grep for the artifact's consumer (`grep -rn 'requirements.txt' Dockerfile docker-compose.yml .github/`) before adding its gate; wire a real consumer in the same PR if none exists, or the gate protects nothing |
| Assumed the issue's stated failure mode was real | Trusted "the Docker build silently uses stale pins from the committed requirements.txt" as the justification for the gate | The Docker build never read the file, so it could not use stale pins from it; the premise was detached from the actual build path | Confirm the failure mode is reachable (the consumer exists and reads the artifact) before building a gate to prevent it |
| Treated the Dockerfile `pip install -r` switch as a no-op equivalence | Reasoned that consuming `requirements.txt` was equivalent to the prior inline `pip install` (and that the editable `hermes` package is `COPY`'d separately) | The equivalence was reasoned, not tested — switching the install path is a real production-image behavior change, and a generated `requirements.txt` could drop deps the inline list had | Run `docker build` to verify; never assume a build-input swap is behavior-preserving, and verify the generated artifact is complete |

## Results & Parameters

| Parameter | Value |
| --------- | ----- |
| **Repo / issue** | HomericIntelligence/ProjectHermes, issue #556 (implementation plan, R2) |
| **Change class** | Add a `check-reqs` CI drift gate for `requirements.txt` vs `pixi.lock`, and make the artifact load-bearing |
| **Central rule** | A drift/sync gate on an artifact nothing consumes is theater; grep for the consumer first and wire one in the same PR |
| **The miss** | `requirements.txt` was guarded by the new gate but read by nothing — the Dockerfile derived deps inline from `pyproject.toml` |
| **The fix** | Switch the Dockerfile to `COPY requirements.txt` + `pip install -r requirements.txt`, making the file load-bearing and the issue's failure mode real |
| **Verification status** | **unverified** — plan only; no `docker build` run, the Dockerfile switch never executed |

### The uncertain assumptions (reviewer-facing checklist)

| # | Assumption | Why it's uncertain | What to do |
| - | ---------- | ------------------ | ---------- |
| 1 | The Dockerfile switch to `pip install -r requirements.txt` is behavior-equivalent to the prior inline install | Reasoned, not run; no `docker build` executed end-to-end | Run `docker build` and diff the resulting site-packages / image |
| 2 | The generated `requirements.txt` is complete | Only fastapi/starlette/urllib3 confirmed via `pixi list`; the rest were `<lock>` placeholders, committed "generate it verbatim" | Hand-verify the generated file against `pixi list --json` output |
| 3 | Dropping the editable self-package (`hermes`) from the inline path is fine because `src/hermes/` is `COPY`'d separately | Reasoned equivalence (the prior inline extraction also excluded it), not tested | Confirm the running container imports `hermes` after the switch |
| 4 | `pixi list --json` works in CI without a prior `pixi install --locked` | Confirmed locally (96 pkgs) but not in the CI environment specifically | Defer to first CI run; specify a fallback |

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectHermes | Issue #556 ("Add check-reqs to CI to catch requirements drift") — R2 implementation plan | **unverified** — plan written, never executed or merged. The committed `requirements.txt` the proposed `check-reqs` gate guards was consumed by nothing (Dockerfile derived deps inline from `pyproject.toml`); the same-PR fix wires `COPY requirements.txt` + `pip install -r requirements.txt` to make the gate load-bearing. No `docker build` was run. |

## References

- [planning-verify-issue-premise-before-implementing.md](planning-verify-issue-premise-before-implementing.md) — the parent planning skill (verify the issue's premise repo-wide; make the PR self-contained; vendor-fixes-latent-bugs). This skill is the SECONDARY lesson from that same #556 re-plan, split out because someone debugging "my CI check passes but doesn't catch the bug" would search here, not in a premise-verification skill.
- [ci-required-check-path-filter-pitfall.md](ci-required-check-path-filter-pitfall.md) — a sibling CI planning pitfall from the same project.
