---
name: pydantic-basemodel-to-dataclass-behavioral-parity
description: "Swapping a pydantic BaseModel for a stdlib @dataclass is NOT a behavioral drop-in: pydantic v2 silently IGNORES unknown kwargs and COERCES str/int -> float, while a dataclass raises TypeError on both. Use when: (1) removing pydantic from a package's base dependencies to satisfy an import/automation boundary, (2) replacing a BaseModel config/event model with @dataclass, (3) a loader does Model(**yaml_dict) with possibly-extra keys or string-typed numeric fields, (4) planning an audit-remediation that claims a validation-library swap has no behavior change."
category: architecture
date: 2026-07-01
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [pydantic, dataclass, basemodel, behavioral-parity, dependency-strip, coercion, audit-remediation, config-loading, tdd]
---

# Pydantic BaseModel -> Stdlib @dataclass Is Not a Behavioral Drop-In

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-01 |
| **Objective** | Strip `pydantic` from `hephaestus.nats` (two `BaseModel` classes: `NATSConfig`, `NATSEvent`) so pydantic can leave base deps and the automation/library boundary holds — replacing them with stdlib `@dataclass`. |
| **Outcome** | Plan REVISED after a reviewer NOGO. The first plan asserted the swap was a behavior-preserving drop-in; it is not. Two silent behavior changes must be handled at the loader boundary. |
| **Verification** | unverified — plan-only. No code was executed, no tests run, no CI. |
| **History** | n/a (initial version) |

## When to Use

- You are removing `pydantic` from a package's **base** dependency set (e.g. to keep an `import <pkg>` surface free of `pydantic` per an automation/library boundary) and must replace `BaseModel` classes with stdlib `@dataclass`.
- A loader constructs the model from external input: `Model(**yaml_dict)` / `Model(**json_obj)` where the dict may contain extra/unknown keys, or where numeric fields arrive as strings (YAML `"0.5"`, env vars).
- A model defines validation constraints (`Field(gt=...)`, `Field(ge=...)`, `@model_validator`) that you intend to move into `__post_init__`.
- You are writing (or reviewing) an audit-remediation plan that claims a validation-library swap has "no behavioral change." Treat that claim as a red flag until the two parity gaps below are addressed.

## Verified Workflow

> **Warning:** This workflow has NOT been validated end-to-end. It is a revised proposal only — no code was executed, no tests were run, and CI never ran it. The pydantic-v2 default behaviors below were asserted from knowledge of pydantic v2 defaults and independently confirmed by the reviewer, but should be RE-VERIFIED against the pinned pydantic version before relying on them. Treat as a hypothesis until CI confirms.

### Quick Reference

```python
import dataclasses

@dataclasses.dataclass
class NATSConfig:
    reconnect_wait: float = 2.0
    # ... other fields ...

    def __post_init__(self) -> None:
        # pydantic Field(gt=0) / Field(ge=0) -> explicit raise.
        # ValidationError WAS a subclass of ValueError, so keep raising ValueError
        # to preserve existing `pytest.raises(ValueError)` tests.
        if self.reconnect_wait <= 0:
            raise ValueError("reconnect_wait must be > 0")


# The LOADER (external-input boundary) is the tolerant + coercing layer.
# Direct dataclass construction stays STRICT by design.
def load_config(raw: dict) -> NATSConfig:
    known = {f.name for f in dataclasses.fields(NATSConfig)}
    # (1) unknown-key tolerance: pydantic ignores extras; dataclass raises TypeError.
    filtered = {k: v for k, v in raw.items() if k in known}
    # (2) coercion: pydantic coerces str/int -> float; dataclass does NOT.
    if "reconnect_wait" in filtered:
        filtered["reconnect_wait"] = float(filtered["reconnect_wait"])
    return NATSConfig(**filtered)
```

```bash
# Confirm the TRUE blast radius before dropping pydantic from base deps:
# every LIBRARY-layer (non-product) usage must be removed first.
grep -rn "pydantic\|BaseModel" hephaestus/ | grep -v "hephaestus/automation/"
# (For issue #1500 this returned exactly 2 files under hephaestus/nats/.)
```

### Detailed Steps

1. **Map the blast radius.** To drop a package from base deps, ALL library-layer (non-product)
   usages must go first. `grep -rn "pydantic\|BaseModel" <pkg>/ | grep -v <product-layer>`
   to confirm exactly which files change. Do not start editing until this number is known.
2. **Handle unknown-key tolerance (parity gap #1).** pydantic v2 `BaseModel` silently
   IGNORES extra/unknown kwargs by default. A stdlib `@dataclass` raises `TypeError` on any
   unexpected keyword. If any loader does `Model(**arbitrary_dict)`, filter the dict to known
   fields first: `{k: v for k, v in raw.items() if k in {f.name for f in dataclasses.fields(Model)}}`.
3. **Handle type coercion (parity gap #2).** pydantic coerces `str -> float` and `int -> float`
   (a YAML string `"0.5"` becomes `0.5`). A stdlib `@dataclass` does NO coercion — the string
   flows unconverted into `__post_init__` numeric comparisons and raises `TypeError` at
   compare-time (`'<' not supported between str and int`) instead of a clean validation error.
   Explicitly coerce the numeric fields at the loader boundary.
4. **Port constraints to `__post_init__`.** pydantic `Field(gt=0)` / `Field(ge=0)` /
   `@model_validator` map to explicit `if ...: raise ValueError(...)` checks. Because
   `pydantic.ValidationError` IS a subclass of `ValueError`, existing tests that assert bare
   `pytest.raises(ValueError)` keep passing. Only tests that import `ValidationError` explicitly
   go RED and must migrate.
5. **Design the tolerance boundary deliberately.** Make the LOADER function (the YAML/external-input
   entry point) the extra-tolerant + coercing boundary; leave DIRECT dataclass construction STRICT.
   Document this asymmetry in a comment/docstring so it is not misread as an inconsistency.
6. **RED-step realism (TDD).** Before claiming which tests go RED, RE-READ the actual test
   bodies. The first plan misread `test_config.py` as asserting `pydantic.ValidationError` when it
   already used bare `pytest.raises(ValueError)`. Re-reading the live test files revealed the RED
   surface was much narrower than claimed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| First plan (NOGO'd) | Replace `NATSConfig`/`NATSEvent` `BaseModel` with `@dataclass` and claim it is a behavior-preserving drop-in with no loader changes | pydantic v2 silently ignores extra kwargs; a dataclass raises `TypeError`. Any `Model(**yaml_dict)` with an extra YAML key would break. | Field-filter the dict to `{f.name for f in dataclasses.fields(Model)}` at the loader boundary before construction. |
| First plan (NOGO'd) | Assume numeric config values arrive already typed as `float` | pydantic coerces `str -> float` / `int -> float`; a dataclass does not. A YAML string `"0.5"` stays a `str` and raises `TypeError` inside `__post_init__` numeric comparison. | Explicitly coerce numeric fields (`float(...)`) at the loader boundary; the dataclass itself performs no coercion. |
| First plan (NOGO'd) | Assert `test_config.py` asserts `pydantic.ValidationError` and would go RED wholesale | The live test already used bare `pytest.raises(ValueError)`, which still passes since `ValidationError` subclasses `ValueError`. The claimed RED surface was far too wide. | Re-read the actual test bodies before predicting the RED set; `ValidationError` is a `ValueError` subclass so only explicit-import tests migrate. |
| First plan (NOGO'd) | Treat "swap validation library for stdlib" as behaviorally equivalent in general | Validation libraries add implicit behavior (extra-key tolerance, coercion, rich error types) that stdlib constructs do not replicate. | A library->stdlib swap is a behavior change by default; enumerate every implicit behavior and re-implement or intentionally drop each one. |

## Results & Parameters

**The two pydantic-v2 default behaviors that break parity (RE-VERIFY against the pinned version):**

| Behavior | pydantic v2 `BaseModel` (default) | stdlib `@dataclass` | Fix at loader boundary |
|----------|-----------------------------------|---------------------|------------------------|
| Unknown/extra kwargs | Silently ignored | `TypeError: unexpected keyword argument` | Filter dict to `{f.name for f in dataclasses.fields(Model)}` |
| Numeric coercion | `str`/`int` -> `float` coerced | No coercion; wrong type flows in | `float(value)` on the numeric fields before construction |
| Constraint violation error | raises `pydantic.ValidationError` (a `ValueError` subclass) | raise your own `ValueError` in `__post_init__` | Keep raising `ValueError`; only explicit-`ValidationError` tests migrate |

**Boundary-design rule:** the LOADER (external-input entry point) is tolerant + coercing;
DIRECT dataclass construction stays strict. Document the asymmetry.

**Dependency-strip precondition:** every library-layer usage removed first — confirmed via
`grep -rn "pydantic\|BaseModel" <pkg>/ | grep -v <product-layer>` (issue #1500: exactly 2 files
under `hephaestus/nats/`).

**Verification / risk notes (unverified plan-only):**

- No code executed, no tests run, no CI. This is a revised proposal only.
- The pydantic-v2 defaults (ignore-extra, `str->float` coercion) were asserted from knowledge of
  pydantic v2 defaults, NOT re-confirmed by running pydantic this session. The reviewer independently
  confirmed them, but they must be re-verified against the pinned pydantic version before relying on them.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1500 audit remediation — strip pydantic from base deps via `hephaestus.nats` `BaseModel` -> `@dataclass`; plan re-planned after reviewer NOGO | Plan-only, never executed (verification=unverified) |
