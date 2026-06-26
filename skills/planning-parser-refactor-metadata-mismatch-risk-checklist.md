---
name: planning-parser-refactor-metadata-mismatch-risk-checklist
description: "Plan parser-consolidation refactors when issue metadata conflicts with body/review evidence. Use when: (1) an issue title points at one subsystem but the body, proposed solution, prior review, and affected-file list point elsewhere; (2) consolidating argparse _build_parser() boilerplate behind a shared helper; (3) preserving exact CLI contract parity across non-universal flags, action classes, defaults, help text, and argument order; (4) reviewer focus should be a risk checklist rather than a broad refactor endorsement."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, parser-refactor, argparse, parser-parity, cli-contract, metadata-mismatch, stale-issue-title, nonce-title-mismatch, hephaestus, review-risk-checklist]
---

# Planning Parser Refactors Amid Issue Metadata Mismatch

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture a planning-stage checklist for ProjectHephaestus issue #1392, where the issue title referenced nonce extraction but the body, proposed solution, prior review, and affected-file list were about automation CLI parser consolidation. |
| **Outcome** | Implementation plan proposed a shared `build_automation_parser()` helper in `hephaestus/automation/_review_utils.py`, migration of nine `_build_parser()` functions, and characterization tests that freeze each parser's exact argparse contract before refactoring. No implementation, parser baseline generation, or CI run happened in that planning turn. |
| **Verification** | unverified - planning-stage learning only. The plan named searches, files, tests, and line numbers that must be re-run against current `main` before implementation. |

## When to Use

- An issue title points at one area, but the body, proposed solution, affected-file list, and review history point at a different area.
- A parser refactor centralizes repeated argparse boilerplate and risks subtle CLI contract drift even when option names stay the same.
- A shared parser helper might accidentally expose flags on commands that never had them, such as default throttle flags, `--version`, `--no-ui`, or parallelism flags.
- Help text parity matters, including cases where two commands share a flag name but historically had different help strings.
- The plan cites `rg` output, line numbers, proposed test files, or tool availability that was not directly reverified in the planning turn.
- Reviewers need a focused risk checklist for a broad parser-consolidation plan.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Resolve the issue-scope mismatch from primary evidence, not title alone.
gh issue view 1392 --repo HomericIntelligence/ProjectHephaestus --json title,body

# 2. Re-run the source searches immediately before implementation.
rg -n "nonce|_fence_untrusted|random|secrets" hephaestus/automation tests/unit/automation
rg -n "def _build_parser|build_review_parser|ArgumentParser|--gh-global-rate|--gh-global-burst|--version|--no-ui|--parallel|--max-workers|--codex|--dry-run" hephaestus/automation tests/unit/automation

# 3. Freeze every affected parser's current argparse contract before migration.
# Suggested characterization fields:
# option_strings, dest, action class, default, const, required, nargs, choices,
# metavar, type, help text, and action order.

# 4. Run the actual repository test/format tools after the helper migration.
pixi run pytest tests/unit/automation/test_automation_parsers.py
pixi run ruff check hephaestus/automation tests/unit/automation/test_automation_parsers.py
pixi run ruff format --check hephaestus/automation tests/unit/automation/test_automation_parsers.py
```

### Detailed Steps

1. **Separate title from body/review evidence.** Treat the title as a search clue, not the final scope. If the title says "nonce extraction" but the body, proposed solution, prior review, and affected-file list all describe parser consolidation, document that conflict explicitly and make the plan test the parser work. Also state the negative scope: do not touch `hephaestus/automation/prompts/` or nonce/random code unless the freshly re-read issue body actually requires it.

2. **Reverify the issue body and affected-file list at implementation time.** The load-bearing scoping claim is that parser consolidation supersedes the nonce title. A reviewer should confirm the current issue body still says that before accepting a parser-only plan.

3. **Generate a frozen parser baseline from current code before editing.** Parser parity is not just flag-name parity. Capture each current `argparse.Action` field: option strings, `dest`, action class, `default`, `const`, `required`, `nargs`, `choices`, `metavar`, `type`, help text, and ordering. Then migrate one parser at a time and compare against the frozen baseline.

4. **Make helper defaults conservative.** `build_automation_parser()` should default `add_github_throttle=False`; each caller must opt into throttle flags explicitly. A prior review flagged accidental throttle flag exposure as a regression, so "central helper default adds everything" is the wrong baseline.

5. **Model non-universal flags as absence tests.** `--version` is not universal, `--no-ui` is not universal, and parallelism flags differ (`--parallel` versus `--max-workers`). The deprecated `--codex` flag on `audit_reviewer.py` must remain if it existed historically. Tests need to assert both presence and absence per command.

6. **Preserve same-name flag help text exactly.** `audit_reviewer.py` and `ensure_state_labels.py` both used raw `--dry-run` help rather than the shared prefix pattern. A helper needs a `dry_run_help` override distinct from `dry_run_prefix`; otherwise a DRY refactor silently changes user-facing help while keeping the same flag.

7. **Treat planned file and line references as unstable.** The planning pass cited `_review_utils.py`, `planner.py`, `plan_reviewer.py`, `pr_reviewer.py`, `address_review.py`, `ci_driver.py`, `implementer_cli.py`, `loop_runner.py`, `audit_reviewer.py`, and `ensure_state_labels.py`. Those references must be found again by symbol or `rg`, not edited by stale line number.

8. **Name verification assumptions honestly.** If the plan says `tests/unit/automation/test_automation_parsers.py` should be created, confirm that path and module naming match current test conventions. If the plan assumes `pixi`, `ruff`, or entry-point behavior, run the commands before claiming parity.

9. **Review prompt/nonce files as a negative-scope guard.** Since the title mentions nonce extraction, reviewers should explicitly check the diff for unintended prompt/nonce changes. A parser-consolidation PR touching nonce/random code should be treated as scope drift unless the reverified issue body requires it.

## Verified Workflow

Not applicable. This skill records a planning-stage workflow and is marked `unverified`. The section exists because `scripts/validate_plugins.py` requires a literal `## Verified Workflow` heading; the actionable workflow is the **Proposed Workflow** above and must be validated by a downstream implementation PR and CI.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Let the issue title decide scope | The title referenced nonce extraction, so a planner could start in `prompts/` or nonce/random code. | The body, proposed solution, prior review, and affected-file list pointed at parser boilerplate, not nonce extraction. Title-only scope would send the implementer to the wrong subsystem. | Resolve conflicts across title, body, proposed solution, review history, and affected-file list. If body/review evidence wins, document the mismatch and add a negative-scope guard. |
| Treat flag names as sufficient parser parity | A refactor can preserve option strings while changing defaults, action class, `nargs`, `choices`, help, requiredness, or order. | `argparse` behavior and help output can drift without flag-name changes. Reviewers then find regressions only after the helper lands. | Freeze full `argparse.Action` specs before editing and compare exact fields after migration. |
| Put throttle flags in the shared helper by default | A convenient helper default would expose GitHub throttle flags everywhere. | Prior review specifically flagged accidental throttle flag exposure as a regression. Commands that never had the flag must not gain it silently. | Default `add_github_throttle=False` and require each caller to opt in explicitly. |
| Standardize same-name flags without a help override | `--dry-run` could use one shared prefix-based help builder everywhere. | Some commands historically used raw dry-run help. A shared prefix would change help text even if behavior stayed the same. | Add a separate `dry_run_help` override distinct from `dry_run_prefix` and test exact help text. |
| Trust planning-time `rg` output and line numbers | The plan cited files, line numbers, and proposed tests from searches that were not fully re-run during the planning turn. | Line numbers and affected files drift; proposed test module names may not exist; tool availability may differ from assumptions. | Re-run all source searches and validation commands on current `main` before implementation and classify any unverified citation as a risk. |

## Results & Parameters

**Planned helper shape:**

```python
def build_automation_parser(
    description: str,
    *,
    add_agent: bool = True,
    add_max_workers: bool = True,
    add_dry_run: bool = True,
    dry_run_prefix: str | None = None,
    dry_run_help: str | None = None,
    add_github_throttle: bool = False,
) -> argparse.ArgumentParser:
    ...
```

**Parser parity fields to freeze:**

```text
option_strings
dest
action class
default
const
required
nargs
choices
metavar
type
help
relative order
```

**Affected modules named by the plan:**

- `hephaestus/automation/_review_utils.py`
- `hephaestus/automation/planner.py`
- `hephaestus/automation/plan_reviewer.py`
- `hephaestus/automation/pr_reviewer.py`
- `hephaestus/automation/address_review.py`
- `hephaestus/automation/ci_driver.py`
- `hephaestus/automation/implementer_cli.py`
- `hephaestus/automation/loop_runner.py`
- `hephaestus/automation/audit_reviewer.py`
- `hephaestus/automation/ensure_state_labels.py`

**Reviewer focus for the ProjectHephaestus #1392 parser plan:**

- Confirm the current issue body and affected-file list really supersede the nonce-related title.
- Confirm the parser baseline was generated from current code before the migration.
- Confirm non-universal flags are absent where historically absent.
- Confirm `--github-throttle` is opt-in, not helper-default.
- Confirm `--dry-run` help text is byte-for-byte preserved where raw help existed.
- Confirm deprecated `--codex` on `audit_reviewer.py` remains.
- Confirm `--parallel` and `--max-workers` are not normalized into one behavior.
- Confirm no prompt, nonce, random, or `_fence_untrusted()` code changed.
- Confirm planned verification commands actually run in the implementation branch.
