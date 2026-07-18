---
name: automation-parser-state-refactor-planning-risks
description: "Planning-risk checklist for consolidating repeated ProjectHephaestus automation parser builders and issue-implementer state directory construction. Use when: (1) refactoring many argparse _build_parser() functions behind a shared builder, (2) centralizing build/.issue_implementer paths behind DEFAULT_STATE_DIR and ensure_state_dir(), (3) reviewing parser-parity tests that inspect argparse internals, (4) a plan relies on grep-derived counts for parser builders, magic strings, or state-directory bypasses."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - hephaestus
  - automation
  - argparse
  - parser-parity
  - dry-run
  - state-dir
  - issue-implementer
  - magic-string
  - refactoring
  - review-risks
---

# Automation Parser and State-Dir Refactor Planning Risks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture the unverified planning assumptions for ProjectHephaestus issue #1393: consolidate nine automation `_build_parser()` functions behind `build_automation_parser()`, and centralize repeated `build/.issue_implementer` state directory construction behind `DEFAULT_STATE_DIR` and `ensure_state_dir()`. |
| **Outcome** | Plan written only. The exact target count, bypass count, helper ownership, parser parity test design, and dry-run help preservation still require implementation-time verification. |
| **Verification** | unverified - planning artifact only; no implementation, local tests, or CI run confirmed these steps. |

> **Warning:** This workflow has not been validated end-to-end. Treat every count, path, helper
> placement, and test target as a hypothesis until re-grep, imports, tests, and CI confirm it.

## When to Use

- Planning or reviewing a DRY refactor that replaces many automation `_build_parser()` functions with a shared `build_automation_parser()` helper.
- Centralizing repeated `build/.issue_implementer` or `.issue_implementer` path construction behind `DEFAULT_STATE_DIR` and `ensure_state_dir()`.
- Preserving exact CLI behavior while composing existing argparse helpers such as `add_dry_run_arg`, `add_github_throttle_args`, `add_json_arg`, `add_version_arg`, and `add_agent_argument`.
- Reviewing parser-parity tests that introspect `argparse._actions` to preserve option strings, defaults, action classes, nargs, types, choices, and help text.
- A plan cites grep-derived counts for parser builders, state-directory bypasses, magic strings, or file:line locations that may drift before implementation.

## Proposed Workflow

### Quick Reference

```bash
# Run from the ProjectHephaestus repo root before implementation or review.

# 1. Re-derive the parser-builder target list; do not trust the planning count.
grep -rn "def _build_parser" hephaestus/automation tests/ scripts/
grep -rn "build_automation_parser" hephaestus/automation tests/ scripts/

# 2. Re-derive every issue-implementer state-directory bypass and magic string.
grep -rn "build/.issue_implementer\\|\\.issue_implementer" hephaestus/ tests/ scripts/ docs/
grep -rn "mkdir.*issue_implementer\\|parents=True" hephaestus/automation tests/

# 3. Check import ownership and cycle risk before placing the shared helper.
python - <<'PY'
import importlib
for mod in [
    "hephaestus.automation._review_utils",
    "hephaestus.automation.ensure_state_labels",
    "hephaestus.automation.audit_reviewer",
]:
    importlib.import_module(mod)
    print(f"import OK: {mod}")
PY

# 4. Preserve the highest-risk dry-run help surfaces exactly.
python -m hephaestus.automation.ensure_state_labels --help | grep -n -- "--dry-run"
python -m hephaestus.automation.audit_reviewer --help | grep -n -- "--dry-run"

# 5. Run parser parity snapshots before and after the refactor.
pytest tests/unit/automation -k "parser or dry_run or state_dir" -q
```

### Detailed Steps

1. **Re-grep the target parser builders immediately before editing.** The plan's "nine
   `_build_parser()` functions" count came from a grep snapshot of one checkout. Treat it as a
   TODO, not a fact. Re-run the search on the implementation branch and list every in-scope module
   explicitly in the plan or PR body.

2. **Re-grep the state-directory bypass count and reconcile issue-body drift.** The issue body was
   reported to mention four bypasses, while current grep during planning found six. Before
   centralizing anything, enumerate every hardcoded `build/.issue_implementer` or `.issue_implementer`
   path and classify each hit as code, test fixture, documentation, or intentional temp-dir override.

3. **Prove the shared-helper home by imports, not by intuition.** `_review_utils.py` looked like the
   canonical home because it already has parser helpers. That is only safe if importing it from each
   automation CLI does not create a cycle or pull review-only runtime dependencies into lightweight
   entry points. Run import smoke tests before committing to ownership.

4. **Compose only the existing helper APIs, and preserve every CLI surface field.** When replacing
   local parser code, compare before/after parser metadata for option strings, defaults, action
   classes, nargs, `type`, `choices`, help text, `--json`, `--version`, and dry-run semantics. The
   highest-risk help strings are `ensure_state_labels.py --dry-run` and `audit_reviewer.py` raw
   dry-run help.

5. **Use parser-parity tests as regression guards, but acknowledge brittleness.** Snapshotting
   `argparse._actions` is useful because it catches subtle CLI drift, but `_actions` is private.
   Keep snapshots focused on user-visible behavior and parser contract fields, and verify they catch
   ordering, help, default, and action-class changes without turning harmless refactors into churn.

6. **Centralize state-dir creation without breaking tests that intentionally inject temp dirs.**
   `ensure_state_dir()` must create the same path as the old code and should not make tests leak into
   the real repository state directory. Preserve explicit temp-dir parameters and fixtures.

7. **Do not over-clean magic strings.** A repo-wide cleanup should remove duplicated code constants,
   not erase useful user-facing docs. Documentation may stay if it remains accurate, or it may refer
   to `DEFAULT_STATE_DIR` when documenting the canonical path.

## Verified Workflow

Not applicable. This skill is `unverified`: it records a planning checklist and reviewer-risk map,
not an executed implementation. The actionable procedure is under **Proposed Workflow** above and
must be treated as unvalidated until the refactor is implemented and CI confirms the parser and
state-directory behavior.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the planning grep count for parser builders | The plan scoped exactly nine automation `_build_parser()` functions from the current checkout | The codebase can drift before implementation; a stale count silently misses new builders or includes removed ones | Re-run the `_build_parser` search on the implementation branch and list the final target set in the PR |
| Trust the issue body's state-dir bypass count | The issue reportedly mentioned four hardcoded state-directory paths | Current planning grep found six, proving the issue body and checkout already disagreed | Treat issue-body counts as claims; re-grep `build/.issue_implementer` and `.issue_implementer` before accepting scope |
| Pick `_review_utils.py` as helper home by proximity | The module already contained parser helpers, so the plan assumed it was canonical | Existing helper ownership does not prove import-safety; automation CLIs may create cycles or pull review-only dependencies | Prove placement with import smoke tests from every target CLI before committing to shared ownership |
| Rely on `argparse._actions` snapshots without review | Parser parity tests used private argparse internals to catch regressions | Private internals are useful but brittle; tests can fail on harmless ordering or formatter changes if scoped too broadly | Snapshot user-visible parser contract fields and confirm the test fails for real help/default/action drift |
| Treat dry-run help as uniform | `dry_run_prefix` and `dry_run_help` parameters were chosen from current help text needs | `ensure_state_labels.py --dry-run` and `audit_reviewer.py` raw dry-run help have high preservation risk | Compare before/after help output for those commands explicitly, not just parser construction metadata |

## Results & Parameters

### Verification Level

- `verification: unverified`
- Captured from planning only.
- No ProjectHephaestus implementation was executed.
- No local test run or CI result confirmed the refactor.

### Reviewer Focus Checklist

```text
Before approving an implementation of this plan:

- [ ] Re-grep `_build_parser` and verify the target module list is complete.
- [ ] Re-grep `build/.issue_implementer` and `.issue_implementer`; reconcile code, tests, and docs.
- [ ] Prove the chosen shared-helper module imports cleanly from every target CLI.
- [ ] Preserve exact parser metadata: option strings, defaults, action, nargs, type, choices, help.
- [ ] Verify `--json` and `--version` presence where previously exposed.
- [ ] Verify dry-run semantics and help text, especially `ensure_state_labels.py` and `audit_reviewer.py`.
- [ ] Keep tests that intentionally use temp state dirs isolated from `DEFAULT_STATE_DIR`.
- [ ] Avoid deleting accurate user-facing docs during magic-string cleanup.
```

### Unverified Dependencies and Sources

- File paths and line numbers came from grep of ProjectHephaestus files during planning and were not revalidated after the plan was written.
- Existing verification commands and tests named in the plan were assumed to exist and exercise the relevant CLI behavior.
- Existing helper APIs `add_dry_run_arg`, `add_github_throttle_args`, `add_json_arg`, `add_version_arg`, and `add_agent_argument` were assumed safe to compose in one builder.
- GitHub issue #1393 details and prior review concerns were reflected in the prompt and plan, not fetched live during planning.

### Search Keywords

`parser parity`, `argparse`, `automation parser`, `dry-run help`, `state dir centralization`,
`magic string`, `issue implementation state`, `build_automation_parser`, `DEFAULT_STATE_DIR`,
`ensure_state_dir`, `build/.issue_implementer`, `ProjectHephaestus issue #1393`.

## Related Skills

- `python-cli-dry-run-and-entrypoint-patterns` - verified patterns for DRY dry-run help text and testable parser builders.
- `dry-refactoring-plan-assumption-audit` - generic DRY consolidation assumption checks.
- `refactor-extraction-plan-unverified-assumptions` - planning-risk checks for unexecuted refactor plans.
- `planning-env-var-to-typed-cli-option-migration` - similar plan-stage automation refactor capture with verification honesty.
