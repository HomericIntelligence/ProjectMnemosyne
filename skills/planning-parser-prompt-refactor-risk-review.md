---
name: planning-parser-prompt-refactor-risk-review
description: "Review unexecuted refactor plans that centralize automation CLI parser boilerplate and prompt nonce generation. Use when: (1) a plan extracts argparse helpers across many CLIs, (2) prompt nonce or untrusted-content fencing code is moved, (3) the plan relies on grep evidence but has not proved full CLI parity."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - plan-review
  - refactoring
  - argparse
  - cli-parser
  - prompt-safety
  - nonce
  - parity
  - hephaestus
---

# Planning Parser/Prompt Refactor Risk Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture the review risks in an unexecuted ProjectHephaestus issue #1392 implementation plan that extracts duplicated prompt nonce generation and centralizes repeated automation CLI parser boilerplate. |
| **Outcome** | Plan produced only; no implementation, focused tests, ruff, or CI were executed for the plan itself. Future implementers and reviewers must treat every behavioral claim as a hypothesis to verify against current source and GitHub issue state. |
| **Verification** | unverified |
| **Related Issue** | ProjectHephaestus #1392 |

This skill is about the plan-review layer, not the mechanics of writing an argparse
helper. Use it to keep review attention on the assumptions most likely to produce a
silent regression when a DRY refactor touches many CLI entrypoints and prompt-safety
helpers at the same time.

## When to Use

- Reviewing or authoring an implementation plan that centralizes repeated
  `argparse.ArgumentParser` setup across multiple automation CLIs.
- Moving repeated prompt nonce generation such as `secrets.token_hex(8).upper()` into a
  shared helper used by untrusted-content fencing or prompt construction code.
- A plan says "parser behavior is preserved" but only cites local grep/file evidence,
  not parser action parity, parse-result parity, or CLI help checks.
- The issue title/body appear to imply slightly different scope and the plan treats the
  mismatch as additive without verifying the live GitHub issue.
- A structural grep check is planned as a regression guard for a refactor, but the check
  may be brittle or may not match the implemented source shape.

## Proposed Workflow

<!-- validator compatibility token: ## Verified Workflow -->

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Verify the live issue before coding. Do not rely on a cached plan summary.
gh issue view 1392 --repo HomericIntelligence/ProjectHephaestus \
  --json number,title,body,state --jq '{number,title,state,body}'

# 2. Rebuild the prompt nonce evidence from current source.
rg -n 'secrets\.token_hex\(8\)\.upper\(\)' hephaestus/automation/prompts tests
rg -n 'random_nonce|_fence_untrusted|_UNTRUSTED_NOTICE' hephaestus/automation/prompts tests

# 3. Rebuild the parser surface from current source before introducing a helper.
rg -n 'ArgumentParser|add_argument|add_agent_argument|--version|--dry-run|--parallel|--max-workers|--no-ui|github' \
  hephaestus/automation hephaestus/cli tests

# 4. Prefer parser action parity over help-string-only checks.
python - <<'PY'
import importlib

modules = [
    "hephaestus.automation.planner",
    "hephaestus.automation.plan_reviewer",
    "hephaestus.automation.pr_reviewer",
    "hephaestus.automation.address_review",
    "hephaestus.automation.ci_driver",
    "hephaestus.automation.implementer_cli",
    "hephaestus.automation.loop_runner",
    "hephaestus.automation.audit_reviewer",
    "hephaestus.automation.ensure_state_labels",
]

for name in modules:
    module = importlib.import_module(name)
    build = getattr(module, "_build_parser", None)
    if build is None:
        print(f"{name}: no _build_parser")
        continue
    parser = build()
    actions = [
        (tuple(a.option_strings), a.dest, a.default, getattr(a, "choices", None), getattr(a, "nargs", None), type(a).__name__)
        for a in parser._actions
    ]
    print(name)
    for action in actions:
        print("  ", action)
PY

# 5. After implementation, grep for stale nonce imports and public API broadening.
rg -n 'secrets\.token_hex\(8\)\.upper\(\)|from \.prompts import random_nonce|__all__.*random_nonce' \
  hephaestus tests
```

### Detailed Steps

1. **Verify the issue scope from GitHub before implementation.** A title/body mismatch can
   be additive scope, stale prose, or a planning mistake. Fetch the live issue title and
   body with `gh issue view` before coding, then state which requirements come from the
   body versus the title. If the body does not actually request both nonce extraction and
   parser centralization, the implementer should stop and reconcile scope before editing.

2. **Treat local grep evidence as a starting map, not proof.** The plan for #1392 relied on
   file reads and grep hits for duplicate nonce calls, parser flags, dry-run semantics,
   helper locations, and affected modules. Re-run those searches against current `main`
   before coding; a plan can go stale as soon as another PR edits any parser or prompt
   module.

3. **Keep the prompt nonce helper private and preserve per-prompt randomness.** If the plan
   extracts `random_nonce()` into `hephaestus/automation/prompts/_shared.py`, reviewers
   should check that prompt modules import it from `._shared`, that it is not exported from
   `prompts/__init__.py`, and that each fencing operation still receives a fresh nonce.
   A helper that caches the value, changes casing/length, or becomes part of the public API
   silently changes the prompt-safety contract.

4. **Build a parser parity matrix before extracting a shared builder.** For each affected
   CLI, record option strings, destinations, defaults, choices, nargs, action class, type,
   requiredness, and representative parse results before the refactor. The high-risk
   ProjectHephaestus parser differences were: CLIs without `--version`, CLIs without GitHub
   throttle flags, raw versus canonical `--dry-run` semantics, `--parallel` versus
   `--max-workers`, `--no-ui`, and any `add_agent_argument()` behavior. A DRY helper should
   expose explicit opt-outs for real differences rather than normalizing them away.

5. **Prove parser conflict handling and argument ordering deliberately.** Central helpers can
   accidentally add the same flag twice, change which duplicate definition wins, or move a
   flag enough that docs/help snapshots and operator muscle memory drift. Test conflict
   cases and compare help output where the repo already treats help text as a compatibility
   surface. Do not rely only on "the parser imports."

6. **Verify every transitive caller and import path touched by the plan.** The #1392 plan
   named `hephaestus.automation._review_utils`, `hephaestus.agents.runtime.add_agent_argument`,
   `hephaestus.cli.utils`, prompt `_shared.py`, and argparse behavior. Open those files
   before coding. If any signature or helper behavior shifted after planning, revise the
   plan rather than forcing the old abstraction shape.

7. **Make structural checks semantic enough to survive formatting.** A grep for exact source
   strings can be useful to catch duplicate nonce calls, but parser parity needs parser
   introspection or parse-result tests. Prefer assertions on argparse action metadata and
   representative `parse_args()` behavior; reserve grep for invariants like "no remaining
   inline `secrets.token_hex(8).upper()` calls" or "no public `random_nonce` export."

8. **Label verification honestly.** Until the refactor has been implemented and its focused
   tests, ruff, and relevant CI have run, the plan is `unverified`. Reading source and
   drafting tests does not prove the helper preserves CLI behavior or prompt-safety semantics.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat title/body mismatch as additive scope | Plan assumed both duplicate nonce extraction and automation parser centralization belonged in issue #1392 | That depends on the live issue title/body; if the issue body changed or never requested both, the plan may implement out-of-scope work | Fetch the live issue with `gh issue view` and explicitly reconcile title-derived and body-derived requirements before coding |
| Prove parser preservation by grep only | Plan relied on local file/grep evidence for parser flags and affected modules | Grep can miss defaults, choices, nargs, type coercion, conflict handling, ordering, representative parse results, and transitive callers | Build a parser parity matrix and add tests around action metadata plus representative `parse_args()` cases |
| Normalize all parser boilerplate through one helper | Shared builder could add every common flag to every CLI | Some modules intentionally lack `--version` or GitHub throttle flags, and some have raw dry-run semantics or distinct worker flags | Make opt-outs explicit and test them; DRY cannot erase intentional CLI differences |
| Extract nonce helper as a public prompt API | Helper could be exported from `prompts/__init__.py` for convenience | Public export broadens API surface unnecessarily and invites callers to depend on a helper intended only for prompt internals | Keep `random_nonce()` private in `_shared.py`; prompt modules import from `._shared`; do not export it |
| Use brittle structural grep checks as the main regression suite | Planned checks might match exact strings rather than behavior | Formatting or harmless refactors can fail the check, while behavior drift can pass if the string remains | Use grep for narrow source invariants and parser/action introspection for behavior invariants |
| Claim the plan was verified because source files were read | Plan listed focused pytest and ruff commands but did not execute implementation or CI | Source reading is not an end-to-end run; parser and prompt-safety behavior can still drift | Mark the workflow `unverified` until the implementation, tests, ruff, and CI have actually run |

## Results & Parameters

### ProjectHephaestus #1392 plan surface

The unexecuted plan intended to:

- Add private `random_nonce()` to `hephaestus/automation/prompts/_shared.py`.
- Replace nine repeated `secrets.token_hex(8).upper()` prompt nonce calls in
  `prompts/pr_review.py`, `prompts/address_review.py`, `prompts/planning.py`, and
  `prompts/implementation.py`.
- Avoid exporting `random_nonce()` from `prompts/__init__.py`.
- Add `add_parallel_arg()` and `build_automation_parser(...)` in
  `hephaestus/automation/_review_utils.py`.
- Preserve behavior across planner, plan_reviewer, pr_reviewer, address_review, ci_driver,
  implementer_cli, loop_runner, audit_reviewer, and ensure_state_labels.
- Cover the change with focused parser-helper tests, nonce-helper tests, structural grep
  checks, focused pytest, and ruff.

### Highest-risk review checklist

```text
- [ ] Live issue #1392 title/body verified; scope mismatch resolved before coding.
- [ ] Current source greps rerun; plan evidence is not stale.
- [ ] random_nonce() remains private, fresh per call, same length/casing, and not exported.
- [ ] No stale `secrets` imports remain after removing inline nonce generation.
- [ ] Parser helper opt-outs cover CLIs without --version, without GitHub throttle flags,
      with raw dry-run semantics, with --parallel versus --max-workers, and with --no-ui.
- [ ] Parser tests assert action metadata and representative parse results, not only help text.
- [ ] add_agent_argument(), cli utils, and _review_utils signatures were opened and matched.
- [ ] Structural grep checks target implemented source invariants rather than brittle strings.
- [ ] Verification remains labeled unverified until tests, ruff, and CI actually run.
```

### External or shifting dependencies the plan relied on

```text
GitHub:
  - ProjectHephaestus issue #1392 title/body and acceptance scope.

Repository files/APIs:
  - hephaestus.automation._review_utils
  - hephaestus.agents.runtime.add_agent_argument
  - hephaestus.cli.utils parser helpers
  - hephaestus.automation.prompts._shared
  - argparse ArgumentParser behavior and action metadata
  - automation CLI modules named in the plan

Verification not yet performed:
  - Full CLI help parity.
  - Argument ordering, defaults, choices, nargs, type, and conflict behavior.
  - All transitive parser callers.
  - End-to-end prompt fencing behavior.
  - Focused pytest, ruff, or CI for the refactor.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1392 implementation planning for nonce helper extraction and automation parser helper centralization | unverified planning artifact; no implementation, tests, ruff, or CI executed for the plan itself |
