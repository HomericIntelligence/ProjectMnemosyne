---
name: hephaestus-agent-timeout-refactor-planning-risks
description: "Capture unverified planning-review risks for ProjectHephaestus issue #1416, where pytest tmp_path migration is combined with centralizing agent subprocess timeout defaults and env overrides. Use when: (1) reviewing a compound timeout/tmp_path refactor plan, (2) deciding timeout-scope boundaries across automation and github packages, (3) checking legacy HEPH_* timeout fallback precedence and call-time env behavior."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [hephaestus, planning, timeouts, tmp-path, review-risk]
---

# ProjectHephaestus Agent Timeout Refactor Planning Risks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Preserve reviewer guidance for ProjectHephaestus issue #1416, a compound refactor that combines pytest `tmp_path` conversion with centralizing agent subprocess timeout defaults and env overrides. |
| **Outcome** | Planning-risk capture only. The issue body, cited line numbers, implementation scope, and command availability were not directly verified during capture. |
| **Verification** | unverified |

## When to Use

- Reviewing or revising a ProjectHephaestus plan that centralizes hardcoded agent subprocess timeouts.
- Deciding whether adjacent timeout constants such as `DIFF_COLLECT_TIMEOUT` or `PRE_PR_TEST_TIMEOUT` belong in the same issue as agent timeout defaults.
- Moving timeout defaults into `hephaestus/constants.py` or another cross-package module while preserving the `hephaestus.github` -> `hephaestus.automation` import boundary.
- Preserving legacy `HEPH_*` timeout env names as fallbacks while introducing new centralized names.
- Testing that timeout env readers evaluate at call time, not at import time or through default arguments.
- Pairing timeout refactors with pytest `tmp_path` conversion and needing a reviewer checklist to prevent broad, untested plumbing changes.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat it as a planning-review hypothesis until the issue body, current source tree, tests, and CI confirm it.

### Quick Reference

```bash
# Verify the issue wording before accepting the plan scope.
gh issue view 1416 --repo HomericIntelligence/ProjectHephaestus --json title,body

# Re-discover timeout sites from the current tree; do not trust stale line numbers.
rg -n "timeout=|TIMEOUT|HEPH_.*TIMEOUT|subprocess\\.run|run_agent_text|run_codex|run_claude" hephaestus tests

# Confirm package boundaries before choosing the constants module.
rg -n "import hephaestus\\.automation|from hephaestus\\.automation|must not import|automation" hephaestus/github docs hephaestus

# Find import-time env reads and default-argument reads.
rg -n "os\\.environ|getenv|def .*timeout=.*\\(|= .*_timeout\\(\\)" hephaestus tests

# Run the repo's real validation only after implementing.
pixi run pytest tests/unit -v
pixi run ruff check hephaestus tests
pixi run ruff format --check hephaestus tests
python3 scripts/validate_plugins.py
```

### Detailed Steps

1. **Verify the issue body first.** The plan cited ProjectHephaestus issue #1416 title/body semantics but did not include direct issue-body evidence. Before accepting scope, read the current issue text and separate the explicit requirement from reviewer or planner extrapolation.

2. **Decide timeout scope deliberately.** Treat `DIFF_COLLECT_TIMEOUT` and `PRE_PR_TEST_TIMEOUT` as scope risks, not automatic inclusions. If the issue only asks for hardcoded agent-related subprocess timeouts, these constants may need a separate follow-up unless the issue body or nearby architecture clearly ties them to the same agent timeout policy.

3. **Choose a cross-package home by import boundary, not convenience.** The plan assumes `hephaestus/constants.py` is the right home because `hephaestus/github/tidy.py` documents that GitHub code must not import `hephaestus.automation`. Re-open the current file and any architecture docs before implementation. Do not fix the timeout issue by adding imports from `hephaestus.github` into `hephaestus.automation` or vice versa unless the boundary is explicitly changed.

4. **Specify env precedence as a table.** If introducing new env names while preserving legacy names, write the precedence before coding: new env var present wins; else legacy phase-specific env var; else centralized default. Include invalid-value behavior and logging level. This prevents accidental migration behavior where old names silently override new names or deprecation warnings become noisy.

5. **Confirm export compatibility before preserving internals.** The plan assumes `implementer._CLAUDE_IMPL_TIMEOUT` must remain exported for public compatibility. Verify whether consumers import it from production code, tests, docs, or external contract. If it is internal residue, keeping it may be unnecessary; if tests or documented compatibility depend on it, keep an alias with targeted coverage.

6. **Make call-time env reads executable.** Tests should mutate env and call the reader twice in the same process without module reload. Avoid module-level computed timeout values, default arguments like `timeout=agent_timeout()`, or cached readers unless cache invalidation is part of the contract.

7. **Test the real subprocess plumbing.** A test that only asserts helper return values is too shallow. Include at least one path where `subprocess.run(...)`, `run_agent_text(...)`, or the relevant agent invoker receives the centralized timeout after env mutation. Patch at the consumer binding, not only the definition site.

8. **Keep the tmp_path migration scoped.** The `tmp_path` conversion should remove shared filesystem coupling without changing timeout behavior. Review file-fixture changes independently from timeout-default changes so a broad diff does not hide behavior regressions.

9. **Treat audits as locators, not evidence.** File paths and line numbers from the plan may drift. Re-run `rg` or AST checks against the implementation branch and edit by symbol/call site, not by stale `file.py:NNN`.

10. **State residual verification gaps in the PR.** An AST audit can catch literal timeout values but cannot prove every timeout's semantic category is correct. The PR should say which timeout classes were intentionally centralized, which were deferred, and which tests prove env precedence and call-time behavior.

## Verified Workflow

Not applicable. This skill is `unverified`; no implementation, tests, or CI run was executed for the captured plan. The actionable guidance is the warning-marked **Proposed Workflow** above.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat every nearby numeric timeout as in scope | The plan grouped `DIFF_COLLECT_TIMEOUT`, `PRE_PR_TEST_TIMEOUT`, and agent subprocess timeouts together. | The user-facing issue may only require hardcoded agent-related timeouts; broader centralization increases blast radius. | Verify issue #1416 wording and split adjacent timeout classes unless the issue explicitly owns them. |
| Pick `hephaestus.automation` as the timeout home for convenience | Centralizing defaults in an automation module is tempting because most agent code lives there. | GitHub package code documents an import boundary that must not depend on automation modules. | Use a cross-package constants module only after confirming the boundary in current source/docs. |
| Preserve legacy env names without precedence rules | The plan kept old `HEPH_*` names as fallbacks but did not prove precedence or deprecation behavior. | Ambiguous precedence can make old names override new names or produce noisy fallback logs. | Write and test the precedence matrix before implementation. |
| Preserve `_CLAUDE_IMPL_TIMEOUT` by assumption | The plan assumed the symbol is a supported public seam. | It may be a legacy internal alias, or it may be compatibility-critical; the plan did not prove either. | Search imports/docs/tests before deciding to retain, deprecate, or remove the symbol. |
| Assert call-time behavior from helper tests only | Tests can validate a reader function while subprocess call sites still use import-time values or default arguments. | Real behavior depends on where the timeout value is read and passed. | Mutate env in one process and assert the actual agent/subprocess invoker receives the changed value without module reload. |
| Trust planning audit line numbers | The plan cited file paths and line numbers from an audit. | Line numbers drift before implementation and may point at the wrong call site. | Re-run `rg` or AST checks on the implementation branch and edit by symbol. |

## Results & Parameters

Reviewer focus areas:

- **Scope:** confirm whether issue #1416 includes only hardcoded agent subprocess timeouts or also diff collection and pre-PR test budgets.
- **Architecture:** verify `hephaestus/constants.py` or another non-automation module is the correct home for defaults needed by both automation and GitHub packages.
- **Env compatibility:** define new-vs-legacy env precedence, invalid-value fallback behavior, and deprecation/noise expectations.
- **Public surface:** decide whether `hephaestus.automation.implementer._CLAUDE_IMPL_TIMEOUT` is compatibility API, test-only residue, or internal implementation detail.
- **Call-time behavior:** reject module-level env reads, cached readers, and default-argument reads unless intentionally covered.
- **Subprocess proof:** include tests that inspect the timeout passed into the real consumer call, not just the helper output.
- **tmp_path separation:** review tmp_path fixture conversion separately from timeout behavior so filesystem cleanup does not mask agent-timeout regressions.
- **Verification limits:** AST or `rg` audits can find timeout literals, but they cannot classify each timeout's semantic ownership; reviewer judgment is still required.

External inputs that must be re-verified before relying on them:

- GitHub issue #1416 title/body and acceptance criteria.
- Current source paths and line numbers from any previous audit.
- Comments in `hephaestus/github/tidy.py` and any architecture docs that define package import boundaries.
- Availability and behavior of `pytest`, `pixi`, `ruff`, and repository validators in the implementation environment.

Related skills:

- `planning-env-var-to-typed-cli-option-migration` for broader timeout env knob migration and per-knob granularity.
- `automation-529-overload-not-retried-classifier-gap` for routing hardcoded agent subprocess timeouts through centralized helpers.
- `planning-verify-issue-premise-before-implementing` for treating issue bodies and cited artifacts as hypotheses until verified.
- `planning-test-coverage-verify-premise-and-mock-targets` for patching consumer-bound subprocess helpers in tests.
