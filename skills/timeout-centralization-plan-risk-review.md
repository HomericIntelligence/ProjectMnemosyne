---
name: timeout-centralization-plan-risk-review
description: "Review planning risks when hardcoded timeout literals are centralized into env-overridable shared constants across automation, runtime, and GitHub direct-agent modules. Use when: (1) a plan moves timeout defaults into a constants module, (2) re-export shims preserve legacy timeout names, (3) timeout literals are replaced across subprocess or agent call sites, (4) reviewers need to separate verified facts from inferred grep findings."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, timeout-centralization, constants-module, env-overrides, import-cycles, automation, github, direct-agent, reviewer-risk, hephaestus]
---

# Timeout Centralization Plan Risk Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture planning risks for centralizing hardcoded timeout defaults into env-overridable constants shared across automation, agent runtime, and GitHub direct-agent modules. |
| **Outcome** | Planning artifact only. The implementation plan for ProjectHephaestus issue #1416 was written, but no code was edited or CI-verified as part of this capture. |
| **Verification** | unverified - schema validation only; the workflow and code changes were not executed end-to-end. |

## When to Use

- Reviewing or authoring an implementation plan that moves hardcoded timeout literals into a canonical `constants.py` or equivalent shared module.
- Re-exporting timeout constants through a legacy helper module, such as keeping names like `_CLAUDE_IMPL_TIMEOUT` available while changing their source of truth.
- Replacing timeout literals across mixed boundaries: automation modules, agent runtime wrappers, and GitHub direct-agent utilities.
- The plan relies on grep-discovered literals and inferred defaults rather than a verified external configuration contract.
- Reviewers need a checklist for import cycles, module import-time env parsing, monkeypatch/reload test hazards, and diagnostic messages that must reflect env overrides.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Re-derive the timeout inventory at implementation time. Do not trust stale plan counts.
rg -n "timeout=|TIMEOUT|7200|600|300|120" hephaestus/ tests/

# Verify import direction before choosing a canonical home.
python - <<'PY'
import hephaestus.constants
import hephaestus.automation.claude_timeouts
print("timeout constants import smoke OK")
PY

# Find modules that import timeout names directly; these may need reload-aware tests.
rg -n "from hephaestus\\.(constants|automation\\.claude_timeouts) import .*TIMEOUT|claude_timeout|timeout_seconds" hephaestus/ tests/
```

### Detailed Steps

1. **Treat the issue title as a hypothesis when it conflicts with the body.** In the issue #1416 plan, the title mentioned `tests/unit/automation/test_loop_runner_early_exit.py` and `TemporaryDirectory()`, but the body and proposed files pointed at timeout centralization. Before implementation, verify the live issue body, comments, and target files still agree. If the title is stale or mismatched, state that explicitly in the plan and do not let it drive edits.

2. **Choose the canonical constants home only after proving import direction.** `hephaestus/constants.py` was assumed to be the best source of truth because it appeared stdlib-only and would avoid GitHub modules importing `automation`. That is plausible, but reviewers must confirm the import graph after edits. GitHub direct-agent modules should import a low-level constants module, not reach upward into `hephaestus.automation`.

3. **Separate legacy compatibility from source-of-truth ownership.** Re-exporting constants through `automation/claude_timeouts.py` can preserve existing names such as `_CLAUDE_IMPL_TIMEOUT`, but the canonical value should still live in the shared constants module. The review should confirm old exports remain available and that new call sites do not accidentally create two competing defaults.

4. **Do not centralize phase helper behavior just because the value matches.** The plan assumed existing 7200-second phase helper functions should remain unchanged because current tests assert them. Verify the issue intent before changing those helpers. Same numeric value does not prove same semantic knob.

5. **Treat env var names and defaults as inferred until verified.** Proposed constant names and defaults were inferred from hardcoded values and issue wording, not from an external operator contract. Before implementation, check docs, existing tests, CLI help, and any deployment config that may treat a timeout as public API.

6. **Design reload-sensitive tests deliberately.** Import-time env parsing can make `monkeypatch.setenv` tests order-sensitive. If modules import constants by value, reloading only the constants module may not update consumers that already bound the old names. Tests should either reload all direct importers or assert the public helper path rather than relying on incidental module state.

7. **Re-sweep literals by call semantics, not only exact text.** A grep for `timeout=7200` can miss positional timeout arguments, pre-assigned variables, differently spaced call sites, and constants that flow into subprocess wrappers. Reviewers should inspect timeout-bearing APIs, not just literal replacements.

8. **Keep diagnostics tied to the new constants.** Warning and log messages that mention a timeout budget should interpolate the new constant or resolved value. Otherwise env overrides change behavior while diagnostics still claim the old hardcoded default.

## Verified Workflow

_Not applicable._ This skill is `unverified`: it captures a planning risk checklist, not an executed implementation. The actionable workflow is the hypothesis-level **Proposed Workflow** above. This heading exists so the ProjectMnemosyne schema validator can process the skill without implying end-to-end verification.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Follow the issue title literally | The issue title referenced an early-exit test and `TemporaryDirectory()` while the plan scoped timeout centralization from the body and proposed files | Title and body appeared mismatched; implementing the title would target the wrong surface | Verify title, body, comments, and proposed files against live code before committing to scope; record mismatch as a reviewer risk |
| Assume `constants.py` is safe because it looks low-level | Picked `hephaestus/constants.py` as canonical because it seemed stdlib-only and avoids GitHub modules importing automation | Import-cycle safety was reasoned, not proven after edits | Run import smoke tests and inspect import direction; GitHub modules should depend on shared constants, not automation |
| Treat equal numeric defaults as identical semantics | Existing 7200-second phase helpers were left unchanged because tests asserted them and they looked intentionally separate | Same value may represent different operator contracts; centralizing them blindly can change behavior or test meaning | Preserve phase helpers unless issue intent explicitly requires unifying them; reviewers should verify semantic ownership, not just value equality |
| Infer env override names from hardcoded literals | Proposed env-var names/defaults were derived from issue wording and observed hardcoded values | No external config contract was verified, so a public knob could be renamed or omitted accidentally | Check docs, deployment config, CLI help, and tests before treating an inferred name/default as contract |
| Sweep only obvious literal forms | Grep discovery looked for timeout literals in known Python files | Positional args, differently spaced literals, variables assigned before call sites, and indirect subprocess wrappers may be missed | Audit timeout-bearing APIs and assignments in addition to exact literal grep patterns |
| Test env overrides by reloading only one module | Planned tests set env vars and reload the constants provider | Consumers that imported names directly may retain stale values, making tests order-sensitive or falsely green | Reload direct importers or test through public helper functions that resolve the current constants path |

## Results & Parameters

### Planning Source Captured

- **Project**: ProjectHephaestus
- **Issue**: #1416
- **Plan objective**: centralize hardcoded timeout defaults into env-overridable constants in `hephaestus/constants.py`, re-export through `automation/claude_timeouts.py`, and replace remaining literals across automation, `agents/runtime.py`, and GitHub direct-agent modules.
- **Compatibility constraint**: preserve phase helper behavior and legacy names such as `_CLAUDE_IMPL_TIMEOUT`.
- **Verification level**: `unverified`; only this skill's schema should be validated unless the implementation is later run through tests or CI.

### Files and APIs the Plan Relied On Without Direct Verification

- Grep results over `hephaestus` Python files for timeout literals.
- Local code paths: `hephaestus/constants.py`, `hephaestus/automation/claude_timeouts.py`, `hephaestus/automation/implementer.py`, `hephaestus/automation/advise_runner.py`, `hephaestus/agents/runtime.py`, `hephaestus/automation/planner.py`, `hephaestus/automation/planner_claude.py`, `hephaestus/automation/planner_review_loop.py`, `hephaestus/automation/learn.py`, `hephaestus/automation/_review_phase.py`, `hephaestus/automation/_pr_create_phase.py`, `hephaestus/github/tidy.py`, and `hephaestus/github/fleet_sync.py`.
- Tests cited for future edits: `tests/unit/automation/test_claude_timeouts.py`, `tests/unit/automation/test_stage_phases.py`, `tests/unit/automation/test_advise_runner.py`, `tests/unit/agents/test_runtime.py`, `tests/unit/github/test_tidy.py`, and `tests/unit/github/test_fleet_sync.py`.

### Reviewer Focus Checklist

```text
- Import cycles: GitHub modules must not import automation just to get timeout defaults.
- Env parsing: module import-time constants need reload-aware tests; direct imports can leak stale values.
- Public defaults: replacing subprocess timeout literals must not silently change public behavior.
- Legacy exports: old names like _CLAUDE_IMPL_TIMEOUT must remain present if callers or tests rely on them.
- Grep completeness: search for positional timeout args, assigned variables, and wrapper defaults, not just timeout=<literal>.
- Diagnostics: warnings and logs should interpolate the resolved constants so env overrides are visible.
```
