---
name: planning-env-var-to-typed-cli-option-migration
description: "Plan a migration that REMOVES operator-facing env-var knobs (e.g. HEPH_*_TIMEOUT) and replaces them with explicit CLI flags threaded through typed options objects, across a large fan-out of call sites. Method: map each env-reading helper 1:1 to the typed options object that ALREADY reaches its call site via self.options; keep the helper module as the single source of DEFAULT CONSTANTS (don't delete it); use a None-sentinel CLI flag + pydantic field default (POLA); centralize new flags in a shared add_*_arg(parser); make the env-removal a TESTED invariant (helper IGNORES env + inspect.getsource has no os.environ). Use when: (1) planning an env-var -> typed CLI option migration, (2) a config knob is read by a helper called from many sites, (3) some leaf callers are FREE FUNCTIONS that do NOT hold the options object and need a threaded timeout parameter, (4) collapsing multiple per-phase env knobs onto one options field risks removing operator tunability, (5) a different default (e.g. git_message_timeout=300s vs agent_timeout=7200s) must stay a SEPARATE field."
category: architecture
date: 2026-06-24
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, env-var-migration, typed-options, cli-design, argparse, fan-out-refactor, call-site-mapping, pola, hephaestus]
---

# Planning an Env-Var to Typed CLI-Option Migration Across a Fan-Out of Call Sites

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-24 |
| **Objective** | Plan ProjectHephaestus issue #1526: replace operator-facing `HEPH_*` automation timeout env vars with explicit, typed CLI options threaded through the existing options objects, across many call sites in `hephaestus/automation/`. |
| **Outcome** | Implementation PLAN written (not executed): map each env-reading helper to the typed options object already reaching its call site; keep the helper module as the single source of DEFAULT CONSTANTS; add a `None`-sentinel CLI flag deferring to the pydantic field default; centralize flags in a shared `add_*_arg(parser)`; and make the env-removal a TESTED invariant. The plan was NOT implemented; its highest-risk assumptions are flagged below for the reviewer. |
| **Verification** | unverified — planning session only; no code applied, no tests run, CI not confirmed. |

## When to Use

- You are planning a migration that **removes operator-facing env-var knobs** (e.g. `HEPH_*_TIMEOUT`, feature flags, tuning constants) and replaces them with **explicit CLI flags** threaded through typed options objects (pydantic models / dataclasses).
- A config value is read by a **helper function** that is called from **many** sites (a fan-out refactor), and you need to estimate which sites are cheap vs expensive to migrate.
- Some leaf callers are **free functions** (not methods on a class holding `self.options`) and will need a new `timeout`/value parameter genuinely threaded from their caller.
- You are tempted to **collapse several distinct per-phase env knobs** onto one shared options field, and need to reason about the operator-capability surface you'd be removing.
- Two knobs share a name shape but have **different defaults** (e.g. a 300s git-message timeout vs a 7200s agent timeout) and must stay separate fields.
- You want the env-var removal to be an **executable invariant** (a test that fails if the env var is ever re-honored), not just a deletion.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. It is the plan for ProjectHephaestus issue #1526, captured at planning stage and never executed. Treat every step and every line/symbol reference as a hypothesis until CI confirms it.

### Quick Reference

```bash
# 1. Find EVERY call site of each env-reading helper, then map each to the typed
#    options object that already reaches that site (self.options vs free function).
grep -rn "agent_timeout_seconds()" hephaestus/automation/
grep -rn "git_message_timeout_seconds()" hephaestus/automation/
grep -rn "HEPH_.*TIMEOUT" hephaestus/        # confirm which knobs survive (library layer)

# 2. Confirm the helper module stays the single source of DEFAULT CONSTANTS.
grep -rn "DEFAULT_AGENT_TIMEOUT\|DEFAULT_GIT_MESSAGE_TIMEOUT" hephaestus/automation/

# 3. Find the existing arg helpers + shared parser builder to extend (don't invent a new one).
grep -rn "def add_.*_arg(parser" hephaestus/automation/
grep -rn "def build_review_parser" hephaestus/automation/

# 4. Enumerate the timeout-assertion tests that will break (full blast radius).
grep -rn "timeout=7200\|timeout=300\|agent_timeout\|git_message_timeout" tests/
```

```python
# --- DEFAULT CONSTANTS stay; helper drops its env-reading inner function ---
# hephaestus/automation/timeouts.py  (KEEP this module — many files import it)
DEFAULT_AGENT_TIMEOUT = 7200          # seconds
DEFAULT_GIT_MESSAGE_TIMEOUT = 300     # DIFFERENT default — must be a SEPARATE field

def agent_timeout_seconds() -> int:
    return DEFAULT_AGENT_TIMEOUT      # was: int(os.environ.get("HEPH_AGENT_TIMEOUT", ...))

# --- Options field defaults to the exported constant (omit flag == unchanged behavior) ---
class ImplementerOptions(BaseModel):
    agent_timeout: int = DEFAULT_AGENT_TIMEOUT
    git_message_timeout: int = DEFAULT_GIT_MESSAGE_TIMEOUT   # do NOT fold into agent_timeout

# --- POLA: None-sentinel flag; pass through ONLY when provided ---
def add_agent_timeout_arg(parser):           # mirror existing add_*_arg helpers
    parser.add_argument("--agent-timeout", type=int, default=None)

# in main():
kwargs = {}
if args.agent_timeout is not None:           # let the pydantic default supply the real constant
    kwargs["agent_timeout"] = args.agent_timeout
options = ImplementerOptions(**kwargs)
```

### Detailed Steps

1. **Grep every call site and map each helper 1:1 to its reaching options object.** For each env-reading helper, `grep -n "<helper>()" <pkg>/` and, for each hit, identify the typed options object that ALREADY arrives at that site via `self.options`. The migration is *cheap* only where the options object already reaches the leaf; it is *expensive* where a **free function** reads the helper directly and must gain a new `timeout` parameter threaded down from its caller. Classify every site as cheap-or-expensive before estimating effort.

2. **Keep the helper module as the single source of DEFAULT CONSTANTS — do NOT delete it.** Many files import the constants. Refactor each helper to `return DEFAULT_X` and delete only the env-reading inner logic. Options-class fields then default to those exported constants, so "omit the flag == unchanged behavior" is *exact* (one source of truth for the default).

3. **Use a `None`-sentinel CLI flag (POLA).** Declare each flag with `default=None`. At `main()` construction, pass the value into the options object only when `args.<flag> is not None`, letting the pydantic field default supply the real constant. This avoids duplicating the default (`default=<const>`) in two places.

4. **Centralize the new flags in a shared `add_*_arg(parser)` helper**, mirroring the existing arg helpers, and reuse any already-shared parser builder (e.g. a single `build_review_parser` feeding two CLIs) rather than adding flags ad hoc to each parser.

5. **Make the removal a TESTED invariant.** Rewrite the helper's unit test to assert the helper now *IGNORES* the env var (set `HEPH_AGENT_TIMEOUT=1` in the environment and assert the helper still returns `DEFAULT_AGENT_TIMEOUT`) — an executable guard. Add an `inspect.getsource(module)` assertion that `os.environ` / the `HEPH_` env-prefix string no longer appears in the module, so a future regression that re-reads the env fails the test.

6. **Keep different defaults as different fields.** A 300s `git_message_timeout` folded into a 7200s `agent_timeout` would 24x the lightweight git-message budget. Audit every default before consolidating any two knobs.

## Verified Workflow

_Not applicable._ This skill was captured from a planning session and is `unverified`: no code was applied, no tests were run, and CI was not confirmed, so there is no verified workflow. The actionable, hypothesis-level methodology lives under **Proposed Workflow** above and must be treated as unvalidated until CI confirms it. (This placeholder section exists only because `scripts/validate_plugins.py` requires the literal `## Verified Workflow` heading; it makes no verification claim.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| "Every leaf caller already holds `self.options`" | Plan hand-waved free-function helpers with "where a helper is a free function, add a `timeout` parameter." | UNVERIFIED for several modules: `learn.py`, `post_merge_processor.py`, `follow_up.py`, `comment_difficulty.py`, `pr_manager.py` may NOT hold the options object, so the new param has to be genuinely threaded from a caller that DOES — which may itself not have it. | Verify, per free-function site, that the options object actually reaches the caller, or that the param is threaded end-to-end. Don't assume `self.options` is everywhere. |
| Collapse many per-phase env knobs onto ONE `agent_timeout` field | Folded `advise`, `learn`, `follow_up`, planner, implementer timeouts into a single per-options field, justified by "defaults are identical (7200s)." | Silently removes the **per-phase tunability** the separate env vars provided; identical defaults don't make a single field equivalent — it changes the operator-capability surface. | Confirm losing independent per-phase override is acceptable, or keep the fields separate. Identical defaults != identical capability. |
| Fold `git_message_timeout` (300s) into `agent_timeout` (7200s) | Treated all timeouts as one knob. | Different defaults: 300s git-message vs 7200s agent. Folding 24x's the lightweight git-message budget. Easy to miss in a fan-out. | A knob with a DIFFERENT default must stay a SEPARATE field. Audit defaults before consolidating. |
| Trust line numbers cited in the plan | Plan referenced `ci_driver.py:741,856`, `pr_reviewer.py:940`, etc., read once during planning. | Line numbers DRIFT between planning and implementation. | Re-grep the symbol/expression at implementation time; never edit by the planned line number. |
| "No `HEPH_*` timeout env vars anymore" after the migration | Scoped OUT `gh_cli_timeout` / `HEPH_GH_CLI_TIMEOUT` because it lives in the library layer (`github/client.py`), not `automation/`. | Defensible, but it means ONE `HEPH_*` timeout env var SURVIVES; the "none anymore" claim is only true WITHIN `automation/`. | Confirm the issue's acceptance criterion tolerates the library-layer exception; state the exception explicitly in the plan. |
| List "update the broken timeout tests" without enumerating them | Plan noted updating `test_ci_driver.py`, `test_stage_phases.py`, `test_planner_loop.py`. | Tests that ASSERT `timeout=<7200>` kwargs break when the value now flows from options; the FULL blast radius of timeout-assertion tests was not enumerated. | Grep all `timeout=`/`agent_timeout`/`git_message_timeout` assertions up front; the blast radius is larger than the named files. |

These rows are framed as **assumptions a plan author makes that are easy to get wrong** rather than executed-and-failed experiments: this skill is a planning-stage (`unverified`) capture, so each "Why It Failed" row records why the assumption is likely WRONG and must be VERIFIED by the implementer/reviewer before it is trusted.

## Results & Parameters

**Most uncertain assumptions a reviewer should focus on (all UNVERIFIED):**

- **Plan never executed.** No code applied, no tests run, CI not confirmed (verification = unverified). Everything here is a hypothesis.
- **Free-function options reach.** The exact construction sites of each Options object in each `main()`, and whether `StageContext` re-exposes `ImplementerOptions` to every phase that needs `agent_timeout`, are assumed not proven. Whether `pr_manager` / `ci_fix_orchestrator` truly expose an options provider at the cited line is unverified.
- **Per-phase consolidation is a capability change, not a no-op.** Collapsing distinct env knobs onto one field removes independent override even when defaults match — confirm acceptability.
- **Different-default fields must stay separate.** `git_message_timeout` (300s) must not fold into `agent_timeout` (7200s).
- **Library-layer exception survives.** `HEPH_GH_CLI_TIMEOUT` in `github/client.py` is intentionally excluded; "no HEPH_* timeout env vars" holds only within `automation/`.
- **Line numbers drift; re-grep.** Every cited location must be re-located by symbol at implementation time.
- **Timeout-assertion test blast radius under-enumerated.** Re-grep all `timeout=` assertions before declaring the test list complete.

**Verified On / Integration point:** Captured from a planning session for **ProjectHephaestus issue #1526** ("Replace HEPH_* automation timeout env vars with explicit CLI options"). Integration points are the existing typed options objects (`ImplementerOptions` et al.), the timeout-constants helper module, and the shared `add_*_arg(parser)` / `build_review_parser` builders. Plan-stage only — **unverified**.

**Generalization (the durable pattern):** When planning to replace operator env-var knobs with typed CLI options across a fan-out: (1) map each env-reading helper 1:1 to the options object already reaching its call site, separating cheap (options present) from expensive (free function, must thread a param) sites; (2) keep the helper module as the single source of DEFAULT CONSTANTS; (3) use a `None`-sentinel flag deferring to the pydantic field default (POLA, no duplicated default); (4) centralize flags in a shared `add_*_arg` helper; (5) make the env-removal an executable invariant via a helper-ignores-env test + `inspect.getsource` no-`os.environ` assertion. Flag to the reviewer: any "every caller has the options object" assumption, any per-phase-knob consolidation (capability loss), any different-default fold, any surviving env var in an out-of-scope layer, drifting line numbers, and the full timeout-assertion test blast radius.

## Related Skills

- `architecture-defer-env-coercion-lazy-resolver` — complementary env-config pattern: deferring eager env coercion out of import into a lazy resolver. This skill owns the "remove the env knob entirely, replace with a typed CLI option threaded through options objects" angle.
- `argparse-tristate-optional-flag` — the argparse mechanics for `default=None`/sentinel flags used in step 3.
- `hephaestus-env-var-fallback-path-resolution` — related env-var centralization (single source of truth for a resolved value) in the same codebase.
