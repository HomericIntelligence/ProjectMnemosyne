---
name: planning-pixi-security-transitive-caps
description: "Plan pixi.toml security-pinned transitive dependency cap changes without overstating advisory evidence, lockfile behavior, or regression-test coverage. Use when: (1) adding next-major upper caps to security floor pins in pixi.toml, (2) planning from inherited CVE/PYSEC context, (3) reviewing whether a cap-only dependency change is security-complete."
category: ci-cd
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - pixi
  - dependency-pinning
  - security
  - transitive-dependency
  - pip-audit
  - planning
  - projecthephaestus
---

# Planning Pixi Security Transitive Caps

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-02 |
| **Objective** | Capture planning risks from ProjectHephaestus issue #1478, which proposed adding next-major upper caps to security-pinned transitive dependencies in `pixi.toml`. |
| **Outcome** | Unverified planning guidance only. The planning turn did not freshly verify advisory data, run the proposed pixi/test commands, or prove the regression failed before the dependency caps were added. |
| **Verification** | unverified |

## When to Use

- A ProjectHephaestus plan proposes changing security floor pins like `pygments>=2.20.0`, `urllib3>=2.7.0`, or `pyjwt>=2.13.0` to include next-major caps such as `<3`.
- The security floor came from issue, audit, or reviewer context rather than a fresh advisory lookup during the planning turn.
- The plan assumes `pixi install --locked` will accept stricter caps because the lock already satisfies them.
- The proposed regression test relies on existing dependency consistency helpers such as `_floor()` and `_upper_cap()`.
- Reviewers need a checklist for distinguishing a cap-only hardening change from complete security remediation.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Re-check authoritative advisory data before treating the change as security-complete.
# Replace these placeholders with the repository's current advisory lookup path.
pixi run --environment lint pip-audit

# 2. Apply cap-only changes in pixi.toml only when these are pixi environment pins.
# Example shape, not freshly verified here:
# pygments = ">=2.20.0,<3"
# urllib3 = ">=2.7.0,<3"
# pyjwt = ">=2.13.0,<3"

# 3. Prove the existing lock remains valid or refresh it intentionally.
pixi install --locked

# 4. Add or update the focused regression in the existing dependency consistency test.
pixi run pytest tests/unit/scripts/test_dependency_floor_consistency.py -v

# 5. Run lint/security checks named by the implementation plan.
pixi run ruff check tests/unit/scripts/test_dependency_floor_consistency.py
pixi run --environment lint pip-audit
```

### Detailed Steps

1. **Separate inherited security evidence from verified security evidence.** If the plan inherited CVE, PYSEC, or fixed-version facts from an issue body, audit context, or reviewer comments, say that explicitly. Do not claim advisory databases or issue bodies were freshly checked unless they were.

2. **Re-verify fix floors before calling the change security-complete.** For packages such as `pygments`, `urllib3`, and `pyjwt`, confirm that the proposed floors still match authoritative advisory data and the repository's active pip-audit findings. A next-major cap can constrain future resolution, but it does not prove the current floor remediates the advisory.

3. **Confirm the cap convention is real, not just nearby style.** If the plan infers that 2.x security floors should use `<3` from adjacent `pixi.toml` entries, label that as an inferred convention unless there is a formal policy, helper, or test enforcing it.

4. **Treat `pixi install --locked` as required evidence.** A stricter cap should be accepted without lockfile changes only if the locked versions already satisfy the new ranges. Run `pixi install --locked`; if it fails, the plan needs a lock refresh or a different constraint.

5. **Keep `pyproject.toml` out of scope only when that distinction is deliberate.** If these dependencies are direct pixi environment pins and not package install requirements, document why `pyproject.toml` remains unchanged. Re-check before assuming the package metadata should not change.

6. **Put the regression in the existing consistency test.** Prefer `tests/unit/scripts/test_dependency_floor_consistency.py` when it already owns dependency floor/cap checks. Reuse `_floor()` and `_upper_cap()` rather than adding ad hoc string checks.

7. **Prove the regression protects against reintroduction.** Before depending on the test as a guard, confirm it fails on floor-only specs or otherwise genuinely detects missing upper caps. A test added after the fix without a red check is weaker evidence.

## Verified Workflow

No verified workflow exists for this skill. Verification is `unverified`; use the
`## Proposed Workflow` section above until advisory checks, locked install, test
execution, and CI results confirm the approach.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat inherited advisory context as freshly verified | The plan used existing issue/audit context for `pygments>=2.20.0`, `urllib3>=2.7.0`, and `pyjwt>=2.13.0` | No authoritative advisory database or issue body check was executed during planning | State inherited evidence honestly and require advisory re-check before claiming security completeness |
| Assume locked installs will remain valid | The plan expected stricter `<3` caps to be accepted because locked versions should already satisfy them | `pixi install --locked` was not run during planning | Make locked-install validation a required implementation step, and refresh the lock if the assumption is false |
| Assume existing helpers are sufficient without a red test | `_floor()` and `_upper_cap()` looked appropriate from local file inspection | The proposed regression was not executed, and its failure mode before the caps was not proven | Reuse helpers, but still prove the test fails against floor-only specs or otherwise guards the intended regression |
| Infer a repository policy from nearby examples | The `<3` next-major cap convention was inferred from adjacent 2.x dependency specs in `pixi.toml` | Nearby style is weaker than a documented policy or enforced invariant | Label the convention as inferred unless the repository has a formal rule |

## Results & Parameters

Planning context from ProjectHephaestus issue #1478:

| Item | Planning Assumption | Required Follow-up |
|------|---------------------|--------------------|
| `pygments` | Security floor `>=2.20.0` should receive `<3` cap | Verify floor against authoritative CVE/PYSEC advisory data |
| `urllib3` | Security floor `>=2.7.0` should receive `<3` cap | Verify floor against authoritative CVE/PYSEC advisory data |
| `pyjwt` | Security floor `>=2.13.0` should receive `<3` cap | Verify floor against authoritative CVE/PYSEC advisory data |
| `pixi.lock` | Existing locked versions should satisfy stricter caps | Run `pixi install --locked`; refresh lock only if needed |
| `pyproject.toml` | Should remain unchanged because these are pixi environment pins | Confirm they are not package install requirements |
| Regression test | Existing `_floor()` and `_upper_cap()` helpers should cover the added cap checks | Run the test and prove it catches floor-only reintroduction |

Proposed verification commands from the planning turn, not executed during capture:

```bash
pixi run pytest tests/unit/scripts/test_dependency_floor_consistency.py -v
pixi install --locked
pixi run ruff check pixi.toml tests/unit/scripts/test_dependency_floor_consistency.py
pixi run --environment lint pip-audit
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1478 planning capture | Unverified planning notes only; commands and advisory checks were proposed but not executed during the planning turn |
