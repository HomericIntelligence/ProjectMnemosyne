---
name: automation-claude-model-per-phase
description: "Route each phase of a Claude-CLI automation pipeline to its own model tier (Opus for planning, Haiku for implementation, Sonnet for review) via a centralized module with HEPH_<PHASE>_MODEL env-var overrides, while leaving --resume sites unflagged so they inherit the originating session's model. Use when: (1) a multi-phase Claude-CLI pipeline (planner -> reviewer -> implementer -> CI driver) is dying with HTTP 429 on one tier while another tier's quota is untouched, (2) every `claude` invocation in the pipeline runs without `--model` and silently picks up the user's default, (3) you need an operator escape hatch to flip a phase to a cheaper model without code changes when one tier exhausts, (4) you are wiring `--model` into a pipeline that also has `--resume` sites and need to know which sites must NOT pass the flag."
category: architecture
date: 2026-05-05
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - claude-cli
  - model-selection
  - opus
  - haiku
  - sonnet
  - automation
  - planner
  - implementer
  - resume
  - cost-optimization
  - hephaestus
---

# Per-Phase Claude Model Selection in CLI Automation Pipelines

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-05 |
| **Project** | ProjectHephaestus (`HomericIntelligence/ProjectHephaestus`) |
| **Branch** | `feat/hephaestus-tidy` |
| **Objective** | Stop a multi-phase `claude` CLI pipeline from dying on HTTP 429 when one tier's quota exhausts, by routing each phase to a model that matches its cognitive demands. |
| **Outcome** | Success — 9 invocation sites across 7 modules now pass `--model`; resume sites correctly omit it; all 1990 unit tests pass locally with 83.04% coverage. |
| **Verification** | verified-local (CI run pending — work is on a feature branch not yet pushed) |
| **Category** | architecture |
| **Related** | [automation-6phase-issue-pr-pipeline](./automation-6phase-issue-pr-pipeline.md) — the pipeline whose phases are being routed |

## When to Use

- A multi-phase Claude-CLI pipeline (planner -> reviewer -> implementer -> CI driver) dies on HTTP 429 within seconds of launch even though only ONE tier's quota is exhausted.
- Every `claude` invocation in the pipeline runs without `--model` and silently inherits the user's terminal default (typically Opus).
- You want each phase to spend the right tier of compute: high-reasoning small-token work on Opus, mechanical long tool-use loops on Haiku, middle-ground review on Sonnet.
- You need an operator escape hatch: flip one phase to a cheaper model without a code change when its tier exhausts.
- You are wiring `--model` into a pipeline that ALSO uses `claude --resume <session_id>` and need a clear rule for which sites must NOT pass `--model`.
- Your codebase already uses Pydantic options classes for runtime knobs and you want to know whether to thread model selection through them or use a different mechanism.

## Verified Workflow

### Quick Reference

```python
# hephaestus/automation/claude_models.py — single source of truth
import os

OPUS = "claude-opus-4-7"
SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5"


def planner_model() -> str:
    return os.environ.get("HEPH_PLANNER_MODEL", OPUS)


def implementer_model() -> str:
    return os.environ.get("HEPH_IMPLEMENTER_MODEL", HAIKU)


def reviewer_model() -> str:
    return os.environ.get("HEPH_REVIEWER_MODEL", SONNET)


def advise_model() -> str:
    return os.environ.get("HEPH_ADVISE_MODEL", SONNET)


def learn_model() -> str:
    return os.environ.get("HEPH_LEARN_MODEL", SONNET)
```

```python
# At every claude-CLI invocation site that CREATES a new session:
from hephaestus.automation.claude_models import implementer_model

argv = ["claude", "--model", implementer_model(), "--print", prompt]

# At every claude-CLI invocation site that RESUMES a session:
# DO NOT pass --model. The model is locked by the original session.
argv = ["claude", "--resume", session_id, "--print", prompt]
```

```bash
# Operator escape hatch when one tier exhausts mid-run:
HEPH_PLANNER_MODEL=claude-haiku-4-5 \
HEPH_IMPLEMENTER_MODEL=claude-haiku-4-5 \
  pixi run python -m hephaestus.automation.implementer
```

### Detailed Steps

1. **Map phases to model tiers by token shape, not by intuition:**

   | Phase | Token shape | Tier | Why |
   |-------|-------------|------|-----|
   | Planner | Small input, high reasoning, low total tokens | Opus | This is the right place to spend Opus quota |
   | Implementer | Long mechanical tool-use loop, many turns, high token volume | Haiku | This is the right place to save cost |
   | Reviewer / plan-reviewer / PR-reviewer | Middle ground (read code, produce structured feedback) | Sonnet | Default to Sonnet for everything that isn't clearly planner or implementer |
   | Advise / learn (knowledge-base ops) | Middle ground | Sonnet | Same as reviewer |

2. **Create a single module `claude_models.py` exporting per-phase functions, not constants:**
   - Functions (not constants) so env-var lookup happens at call time, not import time.
   - Each function reads `HEPH_<PHASE>_MODEL` and falls back to a tier constant.
   - Keep `OPUS = "claude-opus-4-7"`, `SONNET = "claude-sonnet-4-6"`, `HAIKU = "claude-haiku-4-5"` as module-level constants so callers can import them directly when they need a specific tier (e.g. tests).

3. **Wire `--model <id>` into every site that CREATES a Claude session:**
   - In ProjectHephaestus this was 9 sites across `planner.py`, `implementer.py`, `reviewer.py`, `plan_reviewer.py`, `pr_reviewer.py`, `address_review.py`, `ci_driver.py`.
   - Pattern: `argv = ["claude", "--model", implementer_model(), "--print", prompt]`.
   - Verify with `grep -n '"claude"' hephaestus/automation/*.py | grep -v test` — every line that opens a fresh session should be near a `--model` flag.

4. **Do NOT pass `--model` at sites that RESUME a session:**
   - When invoking `claude --resume <session_id>`, the model is locked to whatever the original session used. Passing `--model` alongside `--resume` is at best ignored and at worst rejected by the CLI.
   - In ProjectHephaestus, the deliberately-unflagged sites are: `learn.py`, `follow_up.py`, and the `--resume` branches of `address_review.py` and `ci_driver.py`.
   - **Invariant to enforce:** the phase that creates a session dictates the model for every resume of that session. So picking the implementer's model is doubly important — it locks in the model for the entire downstream chain (address-review, /learn, follow-up, CI fix iterations).

5. **Add unit tests for the model module:**
   - Default values: assert `planner_model() == OPUS`, `implementer_model() == HAIKU`, etc., when env is clean.
   - Env override: `monkeypatch.setenv("HEPH_PLANNER_MODEL", "x"); assert planner_model() == "x"`.
   - Reimport stability: monkeypatching the env then reimporting the module must NOT mutate the constants.

6. **Add argv assertions in pipeline tests:**
   - In `test_planner.py` and similar, assert that `--model` appears in the argv list passed to `subprocess.run` (or whatever the test harness uses), and assert it does NOT appear in resume-branch tests.

7. **Run local verification:**

   ```bash
   pixi run ruff check hephaestus/ tests/
   pixi run mypy
   pixi run pytest tests/unit
   ```

   Expected: ruff clean, mypy clean, all tests passing. If a test was previously asserting `subprocess.run(["claude", "--print", ...])` exactly, update it to expect `--model <id>` between `claude` and `--print`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run pipeline with no per-phase model flag | Every `claude` invocation just inherited the user's terminal default (Opus). | When Opus quota exhausted, every issue died with HTTP 429 in ~3 seconds even though Haiku quota was completely untouched. Single-tier failure became total-pipeline failure. | A multi-tier subscription is wasted on a pipeline that pins everything to one tier by accident. Always pass `--model` explicitly at session-creating sites. |
| Thread model selection through every `PlannerOptions` / `ImplementerOptions` Pydantic class as a CLI flag | Considered as a "more typed" approach since the codebase already had options classes. | Adds noise to every options class and every CLI parser; doesn't compose well across the 9 invocation sites; doesn't give an operator escape hatch (CLI flags don't propagate to subprocess invocations launched by orchestration code). | A module + env vars matches the codebase's existing pattern for runtime knobs (cf. the `CLAUDECODE` env var already read in `planner.py`). Use the pattern that's already there. |
| Place a small helper function between import groups | Tried putting the tier constants and `_get_model()` helper in the middle of the imports for visual grouping. | `ruff` raised E402 (module-level import not at top of file). | Helpers go BELOW all imports, never between. This is non-negotiable in projects that enforce E402. |
| Pass `--model` at `claude --resume` sites for symmetry with the create sites | Initially considered passing `--model` everywhere uniformly so no site is special. | The Claude CLI locks the model to the originating session when `--resume` is used. Passing `--model` alongside `--resume` is at best ignored and at worst rejected, and creates a misleading audit trail (test argv shows a model that isn't actually being used). | Resume sites must deliberately NOT pass `--model`. Document this as an invariant in the calling code. |

## Results & Parameters

### Verified parameters (exact constants used)

```python
# hephaestus/automation/claude_models.py
OPUS = "claude-opus-4-7"
SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5"

# Env-var overrides (one per phase):
# HEPH_PLANNER_MODEL
# HEPH_IMPLEMENTER_MODEL
# HEPH_REVIEWER_MODEL
# HEPH_ADVISE_MODEL
# HEPH_LEARN_MODEL
```

### Phase -> default model mapping

| Phase | Default | Env-var override |
|-------|---------|------------------|
| Planner | `claude-opus-4-7` (OPUS) | `HEPH_PLANNER_MODEL` |
| Implementer | `claude-haiku-4-5` (HAIKU) | `HEPH_IMPLEMENTER_MODEL` |
| Reviewer (plan / PR / address) | `claude-sonnet-4-6` (SONNET) | `HEPH_REVIEWER_MODEL` |
| Advise (knowledge search) | `claude-sonnet-4-6` (SONNET) | `HEPH_ADVISE_MODEL` |
| Learn (skill capture) | `claude-sonnet-4-6` (SONNET) | `HEPH_LEARN_MODEL` |

### Operator escape hatch

```bash
# Flip both planner and implementer to Haiku when Opus is exhausted:
HEPH_PLANNER_MODEL=claude-haiku-4-5 \
HEPH_IMPLEMENTER_MODEL=claude-haiku-4-5 \
  pixi run python -m hephaestus.automation.implementer

# Flip review tier to Haiku to save cost during a no-stakes batch:
HEPH_REVIEWER_MODEL=claude-haiku-4-5 \
  pixi run python -m hephaestus.automation.pr_reviewer
```

### Key invariants

1. **Session-creating site:** MUST pass `--model <id>` where `<id>` comes from the appropriate `*_model()` function.
2. **Session-resuming site (`--resume`):** MUST NOT pass `--model`. The originating session's model is inherited.
3. **The implementer's model determines the entire downstream chain** because address-review, /learn, follow-up, and CI fix iterations all `--resume` the implementer's session.
4. **Env-var override at call time, not import time** — use functions, not module-level constants, so a process started before the env var is set still picks it up if the env var is set later (e.g. by a test fixture).

### Files modified

| File | Change |
|------|--------|
| `hephaestus/automation/claude_models.py` | NEW — module with `planner_model()`, `implementer_model()`, `reviewer_model()`, `advise_model()`, `learn_model()` and tier constants |
| `hephaestus/automation/planner.py` | Added `--model` to `claude` argv |
| `hephaestus/automation/implementer.py` | Added `--model` to `claude` argv |
| `hephaestus/automation/reviewer.py` | Added `--model` to `claude` argv |
| `hephaestus/automation/plan_reviewer.py` | Added `--model` to `claude` argv |
| `hephaestus/automation/pr_reviewer.py` | Added `--model` to `claude` argv |
| `hephaestus/automation/address_review.py` | Added `--model` to create-session branch; `--resume` branch deliberately unchanged |
| `hephaestus/automation/ci_driver.py` | Added `--model` to create-session branch; `--resume` branch deliberately unchanged |
| `hephaestus/automation/learn.py` | Deliberately unchanged — uses `--resume` |
| `hephaestus/automation/follow_up.py` | Deliberately unchanged — uses `--resume` |
| `tests/unit/automation/test_claude_models.py` | NEW — env override + reimport stability tests |
| `tests/unit/automation/test_planner.py` | Added argv assertions verifying `--model` is present |

### Test results

| Metric | Value |
|--------|-------|
| Tests passing | 1990 |
| Tests skipped (pre-existing) | 7 |
| Coverage | 83.04% |
| `ruff check` | clean |
| `mypy` | clean |
| CI status | pending (feature branch not yet pushed at time of skill capture) |

### Cross-reference

The widening of rate-limit detection (which initially had a bug where `or`-chaining detectors masked legitimate `0` epoch returns) is captured in a parallel skill — see the rate-limit detection skill (created in the same session as this one). That work is independent of model selection but was triggered by the same incident.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Multi-phase issue/PR automation pipeline (`hephaestus.automation`) on branch `feat/hephaestus-tidy`. Verified locally: 1990 tests pass, ruff and mypy clean. CI run pending — work is on a feature branch not yet pushed. |
