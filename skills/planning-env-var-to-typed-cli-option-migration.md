---
name: planning-env-var-to-typed-cli-option-migration
description: "Plan timeout/config migrations across large agent call-site fan-outs. Covers two related Hephaestus patterns: (a) removing operator env-var knobs and replacing them with typed CLI options, and (b) centralizing hardcoded issue-body timeout literals behind named constants plus runtime env-aware accessors. Use when: (1) a timeout/config knob is read by helpers called from many sites, (2) some leaves are free functions that need explicit parameters, (3) different defaults must stay separate fields/constants, (4) import direction forces constants into a lower-level module, (5) a plan relies on unverified issue-body files, line references, APIs, or reviewer assumptions."
category: architecture
date: 2026-06-26
version: "1.3.0"
user-invocable: false
verification: unverified
history: planning-env-var-to-typed-cli-option-migration.history
tags: [planning, env-var-migration, typed-options, cli-design, argparse, fan-out-refactor, call-site-mapping, pola, per-knob-granularity, free-function-threading, blast-radius-verification, constants-module, provider-type-verification, options-type-inference, hardcoded-timeout-centralization, env-aware-accessors, import-direction, reviewer-risks, hephaestus]
---

# Planning an Env-Var to Typed CLI-Option Migration Across a Fan-Out of Call Sites

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Plan Hephaestus timeout/config refactors across many agent call sites: first issue #1526's env-var to typed CLI option migration, then the issue-body timeout-centralization plan that preserves env-aware runtime accessors while replacing hardcoded timeout integers with named constants. |
| **Outcome** | Implementation PLANS written, not executed. Durable pattern: count the real knobs/literals and call sites empirically; keep different defaults separate; put defaults in a dependency-safe lower-level constants module when runtime/import direction requires it; use runtime accessors at execution points and constants only for import-time default parameters; explicitly surface title/body mismatches, unverified file/API assumptions, and reviewer risk checks in the plan. |
| **Verification** | unverified — these are planning captures only. No code was applied, no tests run, no CI confirmed. Source-reading checks in prior passes reduce some uncertainty, but the workflows here were not executed end to end. |

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
- You are planning to replace **hardcoded timeout integers copied from an issue body** with named constants/accessors, while preserving exact default durations and existing compatibility aliases.
- A lower-level agent runtime module cannot safely import an automation timeout helper without reversing dependency direction, so defaults may need to move to a lower-level constants module and be re-exported upward.
- The issue title and issue body point at different work (for example, title says patch fixtures but body/review findings say timeout centralization) and the plan must choose the body while explicitly flagging that choice.
- A plan relies on file names, line references, helper names, GitHub APIs, or review findings that were not verified in the current repo state; use this skill to make those reviewer risks visible before implementation.

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

# 5. For hardcoded issue-body timeout centralization, enumerate the ACTUAL literals
#    and the intended target files before editing. Verify 2400 separately because
#    it may mean a rebase budget, not an agent/session budget.
rg -n "\b(1800|600|300|30|120|10|60|2400)\b" hephaestus/ tests/
rg -n "_CLAUDE_IMPL_TIMEOUT|AGENT_AUTH_STATUS_TIMEOUT|timeout=" hephaestus/automation hephaestus/agents hephaestus/github tests/

# 6. Check import direction before choosing the constants home. If a low-level
#    module already sits under hephaestus.agents, do not make it import automation.
rg -n "from hephaestus\.automation|from hephaestus\.agents|import hephaestus\.automation" hephaestus/agents hephaestus/automation
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

```python
# --- Hardcoded timeout centralization pattern (planning-only) ---
# hephaestus/constants.py lives low enough for hephaestus.agents.runtime to import.
AGENT_IMPL_TIMEOUT = 1800
AGENT_REVIEW_TIMEOUT = 600
AGENT_PLAN_TIMEOUT = 300
AGENT_LEARN_TIMEOUT = 300
AGENT_GIT_TIMEOUT = 30
AGENT_CLONE_TIMEOUT = 120
AGENT_AUTH_STATUS_TIMEOUT = 10
AGENT_DIFF_TIMEOUT = 60
AGENT_REBASE_TIMEOUT = 2400

# hephaestus/automation/claude_timeouts.py re-exports constants and provides
# runtime env-aware accessors. Constants are safe for default parameters; accessors
# are used at execution points where env overrides must still take effect.
def agent_impl_timeout() -> int:
    return _read_timeout_env("HEPH_IMPL_TIMEOUT", AGENT_IMPL_TIMEOUT)

_CLAUDE_IMPL_TIMEOUT = AGENT_IMPL_TIMEOUT  # compatibility alias, if existing code imports it
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

12. **For hardcoded timeout centralization, preserve exact issue-body durations before naming anything.** Write the default matrix into the plan and tests before editing: impl `1800`, review `600`, plan `300`, learn `300`, git `30`, clone `120`, auth status `10`, diff `60`, rebase `2400`. Identical numeric values are not automatically the same semantic knob: `plan=300` and `learn=300` stay separate names because reviewers and future operators reason about those budgets independently.

13. **Choose the constants module by import direction, not by conceptual ownership.** If `hephaestus.agents.runtime` needs the timeout names, it cannot import `hephaestus.automation.claude_timeouts` without making the low-level agent runtime depend on the automation package. Put shared defaults in `hephaestus/constants.py` (or the repo's equivalent lower-level constants home), then re-export them from the higher-level timeout helper. Treat this as an assumption to verify by reading the current imports, not by architecture intuition.

14. **Use constants for import-time defaults and runtime accessors for env-aware behavior.** Python default parameters are evaluated at import time, so `def run(..., timeout=agent_impl_timeout())` freezes the env at import and is almost always wrong. Use `timeout: int = AGENT_IMPL_TIMEOUT` for compatibility defaults, but call `agent_impl_timeout()` at the runtime call site where an env override must still apply. Reviewer checklist item: every env-sensitive execution path should call an accessor at execution time, not rely on a default parameter.

15. **Preserve compatibility aliases deliberately.** Existing names such as `_CLAUDE_IMPL_TIMEOUT` and `AGENT_AUTH_STATUS_TIMEOUT` may be imported by tests or downstream code. Re-export/alias them to the new constants unless the plan explicitly proves no caller remains. Removing aliases in the same sweep turns a constants refactor into a breaking API change.

16. **Do not let a title/body mismatch become a clarification blocker when the body and prior review findings agree.** If the issue title says one thing (for example, patch fixtures) but the body and review findings consistently describe timeout centralization, follow the body and state the mismatch in the plan. The durable reviewer risk is not "ask by default"; it is "document why the scoped implementation follows the strongest evidence."

17. **List every unverified external/file/API assumption as a reviewer task.** For this class of plan, the high-risk assumptions are: exact line references from the issue body, whether the named target files still contain the literals, whether GitHub/prior-review findings reflect current `main`, whether `planner_review_loop.py` is verification-only, whether tests patch `_pr_create_phase` vs implementer paths, and whether `2400` means a rebase timeout in both `github/tidy.py` and `github/fleet_sync.py`. Put those in reviewer focus instead of burying them in prose.

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
| Treat timeout centralization as "replace every integer with one timeout" | The new plan replaced issue-body hardcoded timeout literals with named constants/accessors across agent, planner, review, learn, Mnemosyne, tidy, and fleet-sync paths. | A shared integer does not prove shared semantics; defaults must remain exact and separately named (`plan=300` vs `learn=300`; `rebase=2400` vs any long agent budget). | Preserve the full default matrix in tests and code names. Add `AGENT_REBASE_TIMEOUT` only where the `2400` literal is semantically a rebase budget, and ask reviewers to confirm both `tidy.py` and `fleet_sync.py` align. |
| Put env-aware accessors directly in default parameters | The plan needs env-aware timeout accessors and constants for function defaults. | Python evaluates default parameters at import time; calling an accessor there silently freezes env values and makes runtime overrides unreliable. | Constants are acceptable in defaults; accessors belong at execution points. Add tests that mutate env near the call site if runtime override behavior matters. |
| Import automation timeout helpers from low-level agent runtime | Conceptual ownership suggested `hephaestus.automation.claude_timeouts` as the shared home. | `hephaestus.agents.runtime` importing automation reverses dependency direction and can introduce import cycles or layering drift. | Put shared defaults in a lower-level constants module, then re-export through the automation helper for existing callers. Verify by reading imports before finalizing the plan. |
| Trust issue-body target files and prior review findings without current verification | The plan named target files and reviewer risks from the issue body, including planner/review paths, `_pr_create_phase`, and two `2400` locations. | Files, line numbers, helper names, and current call paths drift. A correct-looking plan can patch the wrong call site or leave a stale literal if it does not re-grep current `main`. | Reviewer focus must include re-grepping hardcoded literals and verifying actual patch targets against current code before implementation starts. |

R1 update: the first six rows were R0 ASSUMPTIONS that R1 VERIFIED against the actual code after a NOGO on R0's implementation plan — each "Lesson Learned" now records the CONFIRMED resolution. R2 update: the `post_merge_processor` provider type is now RESOLVED (it holds `CIDriverOptions`, verified at the `__init__` docstring rather than inferred from the call's "learn" semantics — the dominant R2 lesson, captured as the new "infer type from semantics → wrong type" row), and the blast-radius count is re-derived (23, not 18; exclude `build/` too). R3 update: issue-body timeout centralization adds the import-direction, runtime-accessor, compatibility-alias, and reviewer-risk checklist above. The skill as a whole stays `unverified`: these plans were not executed end to end and CI never ran them.

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

- **Plan never executed.** R1 verified some assumptions against the code and R2 pinned one provider type, but the current timeout-centralization learning was NOT executed end to end: no code applied, no tests run, CI not confirmed (verification = unverified). The migration itself is still a hypothesis, and every line number read once during planning will have drifted.
- **Library-layer exception survives.** `HEPH_GH_CLI_TIMEOUT` in `github/client.py` is intentionally excluded; "no HEPH_* timeout env vars" holds only within `automation/`. Whether the issue's "no ... anymore" criterion tolerates that is a reviewer judgment call — not author-resolvable.
- **Line numbers drift; re-grep.** Every cited `file.py:NNN` location was read once during planning and must be re-located by symbol at implementation time.
- **Timeout centralization target list must be re-verified.** The plan named `constants.py`, `automation/claude_timeouts.py`, implementer/planner/review/learn paths, `agents/runtime.py`, `github/tidy.py`, `github/fleet_sync.py`, and tests. Those names came from the plan body; an implementer must re-grep current `main` before editing.
- **Default-parameter env behavior is a real reviewer trap.** Constants in signatures preserve compatibility; env-aware accessors must be used at runtime. Tests should prove both paths where env overrides matter.
- **`AGENT_REBASE_TIMEOUT` needs semantic confirmation.** Replacing `2400` in both tidy and fleet-sync is only correct if both literals represent the same rebase operation budget.

**Default matrix for the timeout-centralization plan (preserve exactly):**

| Name | Seconds | Reviewer note |
|------|---------|---------------|
| impl | 1800 | Keep compatibility alias such as `_CLAUDE_IMPL_TIMEOUT` if it already exists. |
| review | 600 | Separate from plan/learn even if all are agent-ish operations. |
| plan | 300 | Same integer as learn, different semantic budget. |
| learn | 300 | Same integer as plan, different semantic budget. |
| git | 30 | Lightweight command budget; never fold into agent budgets. |
| clone | 120 | External process/network operation; keep distinct. |
| auth status | 10 | Preserve alias such as `AGENT_AUTH_STATUS_TIMEOUT`. |
| diff | 60 | Short local command budget; keep distinct. |
| rebase | 2400 | Verify both tidy and fleet-sync use this as rebase budget before replacing. |

**Verified On / Integration point:** Captured from planning sessions for **ProjectHephaestus issue #1526** ("Replace HEPH_* automation timeout env vars with explicit CLI options") and a later ProjectHephaestus issue-body plan to centralize hardcoded timeout integers behind constants/accessors. Integration points are existing typed options objects, timeout helper modules, `hephaestus/constants.py`, `hephaestus/automation/claude_timeouts.py`, `hephaestus.agents.runtime`, automation call sites, and github tidy/fleet-sync paths. Plan-stage only — **unverified**.

**Generalization (the durable pattern):** When planning timeout/config migrations across a fan-out: (0) count knobs/literals and import/call-site blast radius empirically; (1) preserve one semantic name per knob/default, even when integers match; (2) locate the constants home by dependency direction, then re-export for compatibility; (3) distinguish import-time constants from runtime env-aware accessors; (4) for each leaf, grep METHOD-vs-FREE and thread values beside existing `model=`/`agent=` params where needed; (5) make env behavior and literal replacement executable invariants in tests; (6) sweep by helper names and numeric sentinels; (7) make unverified issue-body files, line references, external APIs, and prior-review findings explicit reviewer tasks rather than plan assumptions.

## Related Skills

- `architecture-defer-env-coercion-lazy-resolver` — complementary env-config pattern: deferring eager env coercion out of import into a lazy resolver. This skill owns the "remove the env knob entirely, replace with a typed CLI option threaded through options objects" angle.
- `argparse-tristate-optional-flag` — the argparse mechanics for `default=None`/sentinel flags used in step 3.
- `hephaestus-env-var-fallback-path-resolution` — related env-var centralization (single source of truth for a resolved value) in the same codebase.
