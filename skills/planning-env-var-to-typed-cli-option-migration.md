---
name: planning-env-var-to-typed-cli-option-migration
description: "Plan a migration that REMOVES operator-facing env-var knobs (e.g. HEPH_*_TIMEOUT) and replaces them with explicit CLI flags threaded through typed options objects, across a large fan-out of call sites. Method: map each env-reading helper 1:1 to the typed options object that ALREADY reaches its call site via self.options; keep the helper module as the single source of DEFAULT CONSTANTS (don't delete it); use a None-sentinel CLI flag + pydantic field default (POLA); centralize new flags in a shared add_*_arg(parser); make the env-removal a TESTED invariant (helper IGNORES env + inspect.getsource has no os.environ). Use when: (1) planning an env-var -> typed CLI option migration, (2) a config knob is read by a helper called from many sites, (3) some leaf callers are FREE FUNCTIONS that do NOT hold the options object and need a threaded timeout parameter, (4) collapsing multiple per-phase env knobs onto one options field risks removing operator tunability, (5) a different default (e.g. git_message_timeout=300s vs agent_timeout=7200s) must stay a SEPARATE field."
category: architecture
date: 2026-06-24
version: "1.2.0"
user-invocable: false
verification: unverified
history: planning-env-var-to-typed-cli-option-migration.history
tags: [planning, env-var-migration, typed-options, cli-design, argparse, fan-out-refactor, call-site-mapping, pola, per-knob-granularity, free-function-threading, blast-radius-verification, constants-module, provider-type-verification, options-type-inference, hephaestus]
---

# Planning an Env-Var to Typed CLI-Option Migration Across a Fan-Out of Call Sites

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-24 |
| **Objective** | Plan ProjectHephaestus issue #1526: replace operator-facing `HEPH_*` automation timeout env vars with explicit, typed CLI options threaded through the existing options objects, across many call sites in `hephaestus/automation/`. |
| **Outcome** | Implementation PLAN written (not executed): map **each distinct env knob 1:1** to a typed-options field (one flag + one field PER knob — never collapse N knobs onto one field); keep the helper module as the single source of DEFAULT CONSTANTS; thread a `timeout=` param into **free-function** leaves the same way they already thread `model=`/`agent=`; add a `None`-sentinel CLI flag deferring to the pydantic field default; centralize flags in a shared `add_*_arg(parser)`; and make the env-removal a TESTED invariant. R0 (PR #2815) captured several assumptions as RISKS; R1 (PR #2819) got a NOGO on R0's implementation plan, then VERIFIED most of those risks against the actual code — they are now CONFIRMED patterns below. R2 (this pass) fixed the last two R1-review minors: the `post_merge_processor` provider type was PINNED DOWN (it holds `CIDriverOptions`, NOT `ImplementerOptions` — verified at its `__init__` docstring, not inferred from the call's "learn" semantics), and the blast-radius count was re-derived (23, not R1's 18). Two residual items remain genuinely uncertain and are kept as risk rows. |
| **Verification** | unverified — the plan is still a PLAN; no code applied, no tests run, CI not confirmed. (R1 "verification" means assumptions were checked against the source, NOT that the migration executed.) |

## When to Use

- You are planning a migration that **removes operator-facing env-var knobs** (e.g. `HEPH_*_TIMEOUT`, feature flags, tuning constants) and replaces them with **explicit CLI flags** threaded through typed options objects (pydantic models / dataclasses).
- A config value is read by a **helper function** that is called from **many** sites (a fan-out refactor), and you need to estimate which sites are cheap vs expensive to migrate.
- Some leaf callers are **free functions** (not methods on a class holding `self.options`) and will need a new `timeout`/value parameter genuinely threaded from their caller.
- You are tempted to **collapse several distinct per-phase env knobs** onto one shared options field, and need to reason about the operator-capability surface you'd be removing.
- Two knobs share a name shape but have **different defaults** (e.g. a 300s git-message timeout vs a 7200s agent timeout) and must stay separate fields.
- The issue lists **N distinct env knobs** and you must decide field granularity — the faithful mapping is **one flag + one field PER knob**, not one-per-command (collapsing them silently drops per-knob operator tunability).
- A **shared sub-agent knob** (e.g. `advise`) is invoked from *inside* several commands and needs its OWN field on EACH of those commands' options classes.
- You need to **empirically count** the knobs and the import blast radius before scoping a sweep (worktree duplicates and over-counting inflate the perceived churn).
- You want the env-var removal to be an **executable invariant** (a test that fails if the env var is ever re-honored), not just a deletion.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. It is the plan for ProjectHephaestus issue #1526, captured at planning stage and never executed. Treat every step and every line/symbol reference as a hypothesis until CI confirms it.

### Quick Reference

```bash
# 0. COUNT THE KNOBS EMPIRICALLY FIRST — one field PER distinct knob, never per command.
grep -oE "HEPH_[A-Z_]+" hephaestus/automation/timeouts.py | sort -u   # the actual knob list

# 0b. COUNT THE BLAST RADIUS EMPIRICALLY — strip worktree dupes, __pycache__ AND build/.
#     RE-DERIVE every re-planning pass; counts drift (R0=36 → R1=18 → R2=23) and a
#     wrong-but-conservative number still misleads the implementer's sweep. Enumerate the
#     file LIST, don't trust a prior pass's number.
grep -rl "automation.timeouts" hephaestus/ tests/ | grep -v __pycache__ | grep -v build/ | wc -l   # ground-truth importers (R0=36 dupes, R1=18 wrong, R2=23 correct)

# 1. Find EVERY call site of each env-reading helper, then map each to the typed
#    options object that already reaches that site (self.options vs free function).
grep -rn "agent_timeout_seconds()" hephaestus/automation/
grep -rn "git_message_timeout_seconds()" hephaestus/automation/
grep -rn "HEPH_.*TIMEOUT" hephaestus/        # confirm which knobs survive (library layer)

# 1b. For each leaf, is it a METHOD (self.options) or a FREE FUNCTION? If free, find the
#     param it ALREADY threads (model=/agent=) and thread the timeout BESIDE it.
grep -rn "def run_learn\|def run_follow_up_issues\|def classify_comments\|def run_address_fix_session\|model=\|agent=" hephaestus/automation/

# 2. Confirm the helper module stays the single source of DEFAULT CONSTANTS.
grep -rn "DEFAULT_AGENT_TIMEOUT\|DEFAULT_GIT_MESSAGE_TIMEOUT" hephaestus/automation/

# 3. Find the existing arg helpers + shared parser builder to extend (don't invent a new one).
grep -rn "def add_.*_arg(parser" hephaestus/automation/
grep -rn "def build_review_parser" hephaestus/automation/

# 4. Enumerate the timeout-assertion tests that will break (full blast radius) —
#    INCLUDING tests that mock a helper to a NON-default sentinel (e.g. 120).
grep -rn "agent_timeout\|git_message_timeout" tests/
grep -rn "=120\|timeout=7200\|timeout=300\|timeout=600" tests/   # literal sentinel mocks
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

0. **Count the knobs and the blast radius EMPIRICALLY before scoping anything — and RE-DERIVE every pass.** `grep -oE "HEPH_[A-Z_]+" <module> | sort -u` for the true knob list; `grep -rl <module> hephaestus/ tests/ | grep -v __pycache__ | grep -v build/ | wc -l` for the true importer count — exclude BOTH `__pycache__` AND `build/`. The count DRIFTS across re-planning passes (R0=36 counting git-worktree duplicates → R1=18 wrong → R2=23 correct); re-run the exact command and enumerate the file LIST rather than trusting any prior pass's number. A wrong-but-conservative number still misleads the implementer's sweep. Over-counting inflates perceived churn and can wrongly motivate delete-and-rewrite over keeping a constants module.

1. **One flag + one typed-options field PER distinct knob — never collapse N knobs onto one field.** When the issue lists DISTINCT env knobs, the faithful CLI mapping is one flag + one options field per knob, NOT one-per-command. A shared sub-agent knob (e.g. `advise`) invoked from inside 3 commands gets its OWN `advise_timeout` field on EACH of those 3 commands' options classes, distinct from each command's primary timeout. (R0 collapsed 9 distinct agent-timeout env vars onto a single `agent_timeout` per command and got a NOGO for silently dropping per-knob operator tunability.)

2. **Grep every call site and map each helper 1:1 to its reaching options object.** For each env-reading helper, `grep -n "<helper>()" <pkg>/` and, for each hit, identify the typed options object that ALREADY arrives at that site via `self.options`. The migration is *cheap* where the options object already reaches the leaf (a method); it is *expensive* where a **free function** reads the helper directly.

2a. **VERIFY which typed-options object a call site holds at the holder's `__init__` signature/docstring — NEVER infer the type from the call's semantics.** This is the dominant R2 lesson. R1 reasoned "this is the implementer's learn step, so the options object must be `ImplementerOptions`" and was WRONG. Ground truth: `PostMergeProcessor.__init__(self, options_provider: Callable[[], Any])` is documented "Returns the current `CIDriverOptions`" — so the drive-green learn actually holds `CIDriverOptions`, not `ImplementerOptions`. To pin down which typed-options object a call site threads, READ the holder's `__init__` signature/docstring (or trace the actual constructor call); semantic intuition about which subsystem "owns" a call is an unreliable proxy for the concrete type. **Consequence:** when the verified type DIFFERS from the family you expected, add the new field to the type ACTUALLY held — `CIDriverOptions` (not `ImplementerOptions`) gets the `learn_timeout` field, because that is the object `post_merge_processor` actually reads. The same knob name (`learn_timeout`) legitimately appears on TWO different options classes (`ImplementerOptions` for the implementer's own learn, `CIDriverOptions` for the drive-green learn) — that is correct per-call-site granularity, not duplication to be deduped.

3. **For free-function leaves, thread `timeout=` exactly where they already thread `model=`/`agent=`.** The R0 assumption "every leaf holds `self.options`" was VERIFIED FALSE: four call sites are module-level free functions (`learn.run_learn`, `follow_up.run_follow_up_issues`, `comment_difficulty.classify_comments`, `pr_manager._invoke_git_message_agent` via the `commit_changes`/`create_pr` chain). The CONFIRMED fix: these free functions ALREADY accept threaded params like `model=`/`agent=` passed down from an option-holding method caller, so the timeout threads the IDENTICAL way — add a `timeout: int = DEFAULT` keyword param, and the option-holding caller (e.g. `_followup_phase._run_learn`, which holds `self.options`) passes `self.options.<knob>_timeout`. HEURISTIC: per leaf, grep whether it is a METHOD (has `self.options`) or a FREE FUNCTION; if free, find the param it ALREADY threads and thread the timeout beside it — never hand-wave "add a param."

4. **A shared free-function entry invoked from multiple option-holders takes the UNION of params and forwards each.** `run_address_fix_session` is a free function called from 3 different option-holding callers (implementer review phase, ci_driver, address_review). It gains `address_review_timeout` + `advise_timeout` + `git_message_timeout` params and forwards each to its own leaves; each of the 3 callers passes its own `self.options.*`.

5. **Keep the helper module as the single source of DEFAULT CONSTANTS — do NOT delete it.** Refactor each `*_timeout()` helper to `return DEFAULT_X` and delete the `_read_int_env` inner function; the typed-options fields then default to those exported constants, so "omit the flag == unchanged behavior" is *exact*. This avoids editing every importer and gives one source of truth for the default — the right call confirmed once the importer count (18, not 36) was known.

6. **Use a `None`-sentinel CLI flag (POLA).** Declare each flag with `default=None`. At `main()` construction, pass the value into the options object only when `args.<flag> is not None`, letting the pydantic field default supply the real constant. Avoids duplicating the default in two places.

7. **Centralize the new flags in a shared `add_*_arg(parser)` helper**, mirroring the existing arg helpers, and reuse any already-shared parser builder (e.g. a single `build_review_parser` feeding two CLIs) rather than adding flags ad hoc to each parser.

8. **Make the removal a TESTED invariant.** Rewrite the helper's unit test to assert the helper now *IGNORES* the env var (set `HEPH_AGENT_TIMEOUT=1` and assert the helper still returns `DEFAULT_AGENT_TIMEOUT`). Add an `inspect.getsource(module)` assertion that `os.environ` / the `HEPH_` prefix no longer appears in the module.

9. **Pick BOTH an easy and a hard path for the representative threading test.** The acceptance criterion only requires "at least one representative command," but the easy path (a method that already holds options) is exactly the one LEAST likely to be wrong. Add a test for a free-function path too — that's where the migration actually breaks.

10. **Sweep the FULL test blast radius, including mocks to NON-default sentinels.** A non-default mock SENTINEL is the easy-to-miss test in a blast-radius sweep: a test mocking `git_message_agent_timeout()` to return 120 (not even the real 300 default) would be MISSED by grepping for the default literals (`timeout=300`). Order: grep the helper NAME across the whole `tests/` dir FIRST (catches every mock regardless of the value it returns), THEN grep the literal sentinel values too (`grep -rn "=120\|timeout=7200\|timeout=300\|timeout=600"`) to catch any odd literal a test chose as a sentinel.

11. **Keep different defaults as different fields.** A 300s `git_message_timeout` folded into a 7200s `agent_timeout` would 24x the lightweight git-message budget. Audit every default before consolidating any two knobs.

## Verified Workflow

_Not applicable._ This skill was captured from a planning session and is `unverified`: no code was applied, no tests were run, and CI was not confirmed, so there is no verified workflow. The actionable, hypothesis-level methodology lives under **Proposed Workflow** above and must be treated as unvalidated until CI confirms it. (This placeholder section exists only because `scripts/validate_plugins.py` requires the literal `## Verified Workflow` heading; it makes no verification claim.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Collapse 9 distinct agent-timeout env vars onto ONE `agent_timeout` field per command | R0's implementation plan folded `advise`, `learn`, `follow_up`, planner, implementer, etc. timeouts into a single per-command options field, justified by "defaults are identical." | Got a NOGO: silently DROPS the per-knob operator tunability the separate env vars provided; identical defaults don't make a single field equivalent — it changes the operator-capability surface. | CONFIRMED (R1): when the issue lists DISTINCT knobs, map one flag + one field PER knob, never per-command. A shared sub-agent knob (`advise`) invoked from 3 commands gets its OWN `advise_timeout` field on EACH. Count knobs empirically: `grep -oE "HEPH_[A-Z_]+" <module> | sort -u`. |
| "Every leaf caller already holds `self.options`" | R0 hand-waved free-function helpers with "where a helper is a free function, add a `timeout` parameter." | VERIFIED FALSE (R1): four sites are module-level free functions (`learn.run_learn`, `follow_up.run_follow_up_issues`, `comment_difficulty.classify_comments`, `pr_manager._invoke_git_message_agent` via the `commit_changes`/`create_pr` chain) — they do NOT hold the options object. | CONFIRMED FIX (R1): these free functions ALREADY thread `model=`/`agent=` down from an option-holding method; thread the timeout the IDENTICAL way (`timeout: int = DEFAULT` beside the existing param; the option-holder, e.g. `_followup_phase._run_learn`, passes `self.options.<knob>_timeout`). Per leaf, grep METHOD-vs-FREE; if free, thread beside the param it already threads. |
| Treat a shared free-function entry as a single-param add | R0 did not account for a free function called from several different option-holders. | `run_address_fix_session` is called from 3 option-holding callers (implementer review phase, ci_driver, address_review). | CONFIRMED (R1): such an entry takes the UNION of params (`address_review_timeout` + `advise_timeout` + `git_message_timeout`) and forwards each to its own leaves; each of the 3 callers passes its own `self.options.*`. |
| Trust the cited import/blast-radius COUNT | R0 claimed "36 files import the module"; R1 corrected to 18 — and both were used to scope the sweep. | The count DRIFTS across passes: R0=36 counted git-worktree duplicates, R1=18 was wrong, R2=23 is correct. A wrong-but-conservative number still misleads the implementer's sweep. | CONFIRMED (R2): RE-DERIVE the count every pass and exclude BOTH `__pycache__` AND `build/` — `grep -rl <module> hephaestus/ tests/ | grep -v __pycache__ | grep -v build/ | wc -l` — then enumerate the file LIST rather than trusting any prior pass's number. |
| Infer a call site's typed-options TYPE from the call's semantics | R1 reasoned "this is the implementer's learn step, so the options object must be `ImplementerOptions`" and added `learn_timeout` to `ImplementerOptions` for the drive-green learn. | WRONG TYPE (R2): `PostMergeProcessor.__init__(self, options_provider: Callable[[], Any])` is documented "Returns the current `CIDriverOptions`" — the drive-green learn holds `CIDriverOptions`, not `ImplementerOptions`. Semantic intuition about which subsystem "owns" a call is an unreliable proxy for the concrete type threaded into it. | RESOLVED (R2): verify the type at the holder's `__init__` signature/docstring (or trace the constructor call), never infer it from what the operation "is about." Add the new field to the type ACTUALLY held — `CIDriverOptions` gets `learn_timeout`. The same knob name on TWO options classes (`ImplementerOptions` + `CIDriverOptions`) is correct per-call-site granularity, NOT duplication. |
| Fold `git_message_timeout` (300s) into `agent_timeout` (7200s) | Treated all timeouts as one knob. | Different defaults: 300s git-message vs 7200s agent. Folding 24x's the lightweight git-message budget. | A knob with a DIFFERENT default must stay a SEPARATE field. Audit defaults before consolidating. |
| Sweep the test blast radius by helper name only | R0 named `test_ci_driver.py`, `test_stage_phases.py`, `test_planner_loop.py`. | Tests that mock a helper to a NON-default sentinel (e.g. `git_message_agent_timeout()` -> 120, not even the real 300 default) are easy to miss. | CONFIRMED (R1): grep the literal sentinel values too (`grep -rn "=120\|timeout=7200\|timeout=300\|timeout=600"`), not just the helper name. The blast radius is larger than the named files. |
| Test ONLY the easiest representative command | The acceptance criterion only requires "at least one representative command." | The easy path (a method already holding options) is exactly the one LEAST likely to be wrong; it would pass while the risky free-function threading stayed untested. | CONFIRMED (R1): add a test for a free-function path too — that's where the migration actually breaks. Pick BOTH an easy and a hard path. |
| Trust line numbers cited in the plan | R0 referenced `ci_driver.py:741,856`, `pr_reviewer.py:940`, etc., read once during planning. | Line numbers DRIFT between planning and implementation. | **STILL A RISK** — re-grep the symbol/expression at implementation time; never edit by the planned line number. |
| "No `HEPH_*` timeout env vars anymore" after the migration | Scoped OUT `gh_cli_timeout` / `HEPH_GH_CLI_TIMEOUT` because it lives in the library layer (`github/client.py`), not `automation/`. | ONE `HEPH_*` timeout env var SURVIVES; the "none anymore" claim is only true WITHIN `automation/`. | **STILL A RISK (reviewer judgment)** — whether the issue's "no ... anymore" criterion tolerates the library-layer exception is a reviewer call, not author-resolvable. State the exception explicitly. |
| Assume `post_merge_processor.learn_claude_timeout()` has a `learn_timeout` provider | R0/R1 assumed its options provider carries (or can carry) a `learn_timeout` field but never pinned the TYPE. | The exact provider TYPE was NOT pinned down in R0/R1 (the one residual hand-wave). | RESOLVED (R2): `PostMergeProcessor.__init__(self, options_provider: Callable[[], Any])` docstring says "Returns the current `CIDriverOptions`" — the provider yields `CIDriverOptions`, so `learn_timeout` goes on `CIDriverOptions` (NOT `ImplementerOptions`). Verified at the `__init__` docstring, not inferred from the "learn" semantics. |

R1 update: the first six rows were R0 ASSUMPTIONS that R1 VERIFIED against the actual code after a NOGO on R0's implementation plan — each "Lesson Learned" now records the CONFIRMED resolution. R2 update: the `post_merge_processor` provider type is now RESOLVED (it holds `CIDriverOptions`, verified at the `__init__` docstring rather than inferred from the call's "learn" semantics — the dominant R2 lesson, captured as the new "infer type from semantics → wrong type" row), and the blast-radius count is re-derived (23, not 18; exclude `build/` too). Two rows remain genuinely uncertain and must still be verified by the implementer/reviewer: line-number drift, and the surviving library-layer `HEPH_GH_CLI_TIMEOUT`. The skill as a whole stays `unverified`: the plan was never executed and CI never ran it.

## Results & Parameters

**CONFIRMED in R1 (assumptions verified against the source after a NOGO on R0's impl plan):**

- **Per-knob granularity is the faithful mapping.** One flag + one field PER distinct knob; never collapse N knobs onto one field. A shared sub-agent knob (`advise`) gets its OWN field on EACH command that invokes it.
- **Free-function leaves thread `timeout=` beside their existing `model=`/`agent=` param.** Four sites (`learn.run_learn`, `follow_up.run_follow_up_issues`, `comment_difficulty.classify_comments`, `pr_manager._invoke_git_message_agent`) are free functions; the option-holder caller passes `self.options.<knob>_timeout`.
- **A shared free-function entry takes the UNION of params.** `run_address_fix_session` gains `address_review_timeout` + `advise_timeout` + `git_message_timeout`, forwarding each; its 3 option-holding callers each pass their own `self.options.*`.
- **Provider type pinned to `CIDriverOptions` (R2).** `PostMergeProcessor.__init__`'s `options_provider` is documented "Returns the current `CIDriverOptions`" — so the drive-green `learn_timeout` field goes on `CIDriverOptions`, NOT `ImplementerOptions`. VERIFY the type at the holder's `__init__` signature/docstring; never infer it from the call's semantics. The same knob name on TWO options classes is correct per-call-site granularity, not duplication.
- **Blast radius is 23 importers (R2), not 18 (R1) or 36 (R0)** — the count DRIFTS, so re-derive it every pass with `grep -rl <module> hephaestus/ tests/ | grep -v __pycache__ | grep -v build/ | wc -l` (exclude BOTH `__pycache__` and `build/`) and enumerate the file LIST. This justified KEEPING the constants module over delete-and-rewrite.
- **Test sweep must include mocks to NON-default sentinels** (e.g. `git_message_agent_timeout()` -> 120); grep literal sentinel values, not just the helper name.
- **Test BOTH an easy (method) and a hard (free-function) representative path** — the free-function path is where the migration breaks.
- **Different-default fields must stay separate.** `git_message_timeout` (300s) must not fold into `agent_timeout` (7200s).

**STILL UNVERIFIED — residual risks a reviewer should focus on:**

- **Plan never executed.** R1 verified the assumptions against the code and R2 pinned the provider type, but NO code was applied, no tests run, CI not confirmed (verification = unverified). The migration itself is still a hypothesis, and every line number read once during planning will have drifted.
- **Library-layer exception survives.** `HEPH_GH_CLI_TIMEOUT` in `github/client.py` is intentionally excluded; "no HEPH_* timeout env vars" holds only within `automation/`. Whether the issue's "no ... anymore" criterion tolerates that is a reviewer judgment call — not author-resolvable.
- **Line numbers drift; re-grep.** Every cited `file.py:NNN` location was read once during planning and must be re-located by symbol at implementation time.

**Verified On / Integration point:** Captured from a planning session for **ProjectHephaestus issue #1526** ("Replace HEPH_* automation timeout env vars with explicit CLI options"). Integration points are the existing typed options objects (`ImplementerOptions` et al.), the timeout-constants helper module, and the shared `add_*_arg(parser)` / `build_review_parser` builders. Plan-stage only — **unverified**.

**Generalization (the durable pattern):** When planning to replace operator env-var knobs with typed CLI options across a fan-out: (0) count the knobs and the import blast radius EMPIRICALLY first (`grep -oE "HEPH_[A-Z_]+" | sort -u`; `grep -rl | grep -v __pycache__ | wc -l`) — worktree dupes over-count; (1) map ONE flag + ONE field PER distinct knob, never collapse N knobs onto one field, and give a shared sub-agent knob its own field on each command that invokes it; (2) for each leaf, grep METHOD-vs-FREE — methods read `self.options`, free functions thread `timeout=` beside the `model=`/`agent=` param they ALREADY thread (a shared free-function entry takes the UNION of params and forwards each) — and when a call site holds a typed-options object, VERIFY which class it is at the holder's `__init__` signature/docstring (or trace the constructor), NEVER infer the type from the call's semantics (the same knob name legitimately living on two different options classes is correct per-call-site granularity, not duplication); (3) keep the helper module as the single source of DEFAULT CONSTANTS (refactor `*_timeout()` to `return DEFAULT_X`, drop the `_read_int_env` inner fn); (4) use a `None`-sentinel flag deferring to the pydantic field default (POLA); (5) centralize flags in a shared `add_*_arg` helper; (6) make the env-removal an executable invariant (helper-ignores-env test + `inspect.getsource` no-`os.environ`); (7) test BOTH an easy method path and a hard free-function path, and sweep the test blast radius by literal sentinel value too, not just helper name. Residual reviewer judgment calls: a not-yet-pinned options-provider type for a stray helper, a surviving library-layer env var, and drifting line numbers.

## Related Skills

- `architecture-defer-env-coercion-lazy-resolver` — complementary env-config pattern: deferring eager env coercion out of import into a lazy resolver. This skill owns the "remove the env knob entirely, replace with a typed CLI option threaded through options objects" angle.
- `argparse-tristate-optional-flag` — the argparse mechanics for `default=None`/sentinel flags used in step 3.
- `hephaestus-env-var-fallback-path-resolution` — related env-var centralization (single source of truth for a resolved value) in the same codebase.
