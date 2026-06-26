---
name: implementation-plan-process-helper-risk-capture
description: "Capture uncertain assumptions, unverified anchors, and reviewer focus for mechanical refactor plans that replace low-level process calls with shared helper APIs. Use when: (1) reviewing a plan that swaps direct subprocess/git probes for a shared helper, (2) the plan preserves an interactive Popen path while changing non-interactive probes, (3) helper behavior is inferred from nearby call sites instead of re-reading the helper contract."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, plan-review, refactoring, subprocess, process-helper, git-probes, risk-capture, unverified-assumptions]
---

# Implementation Plan Risk Capture for Process Helper Refactors

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Preserve plan-review risk discipline for mechanical refactors that replace bare low-level process calls with a shared helper while leaving interactive process paths unchanged. |
| **Outcome** | Planning-only learning captured. The underlying implementation plan was not executed end-to-end, so every workflow item below is a review checklist, not proven implementation guidance. |
| **Verification** | unverified |

## When to Use

- Reviewing or authoring an implementation plan that replaces direct `subprocess.run(...)`, shell, git, or process probes with a shared wrapper such as `run_subprocess(...)`.
- The plan must preserve user-visible CLI behavior while changing the process execution helper underneath.
- The target module contains both non-interactive probes and interactive process commands, and only one class should change.
- The plan cites grep counts, file/line anchors, issue acceptance criteria, or GitHub state gathered during planning.
- The plan infers helper semantics from another module's call sites instead of re-reading the helper implementation or contract.
- Tests need to patch a helper imported into the consumer module and assert exact kwargs such as `check`, `capture_output`, `text`, or `timeout`.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```text
Before approving a mechanical process-helper refactor plan, capture:

1. Most uncertain assumptions:
   - Grep/count observations can drift before implementation.
   - Sibling import examples do not prove layering or import-cycle safety.
   - Shared helper semantics may differ from raw subprocess behavior.
   - The interactive exception is safe only if probes and interactive commands are classified correctly.

2. External anchors not directly verified in the final plan:
   - File/line references and test names are plan-time snapshots.
   - Helper API behavior must be re-read from the helper, not inferred from call sites alone.
   - Import-cycle risk delegated to a guard test still needs the guard to run.
   - Issue acceptance criteria and remote issue state should be re-queried if they matter.

3. Reviewer focus:
   - No bare non-interactive subprocess.run remains in the target module.
   - Interactive Popen paths remain untouched.
   - check=False remains explicit for expected-failure probes.
   - Default check=True remains in place where root/probe detection should raise.
   - Tests patch the consumer's imported helper seam and assert exact kwargs.
   - Focused tests, lint, and import-cycle guard run before claiming confidence.
```

### Detailed Steps

1. **Separate plan-time observations from durable facts.**
   Grep counts, exact line numbers, and "N occurrences remain" statements are snapshots.
   Record them as uncertain unless the implementer will re-run the search immediately before editing.
   Use stable anchors such as function names and behavior categories in the plan, not only absolute lines.

2. **Re-read the shared helper contract before relying on it.**
   Existing call sites show that the helper is usable somewhere; they do not prove equivalence with
   raw `subprocess.run(...)` in this module. Re-read the helper definition or documentation for:
   return type, default `check` behavior, stdout/stderr handling, `text` handling, `timeout`
   propagation, logging behavior, environment merging, and exception type propagation.

3. **Treat import examples as weak evidence for layering safety.**
   A different module importing the helper does not prove this target module can import it without a
   cycle. If the plan depends on "this import pattern already exists elsewhere," capture that as an
   assumption and require an import-cycle or import-smoke guard to run.

4. **Classify process calls before replacing anything.**
   Make an explicit inventory of:
   - non-interactive probes that should move to the shared helper;
   - expected-failure probes that must preserve `check=False`;
   - raising probes that should rely on the helper's default `check=True` or an explicit equivalent;
   - interactive commands, TTY handoff, or long-lived sessions that must keep `subprocess.Popen(...)`.

5. **Preserve behavior through kwargs, not intention.**
   Every changed call should carry over the raw subprocess semantics deliberately. If the old call used
   `capture_output=True`, `text=True`, `check=False`, `timeout=...`, or `cwd=...`, the plan should say
   which kwargs remain and which are intentionally delegated to helper defaults. Do not hide behavior
   changes behind "use the shared helper."

6. **Patch the consumer seam in tests.**
   If the target module does `from helpers import run_subprocess`, tests should patch
   `target_module.run_subprocess`, not the helper's definition site. Assert exact call kwargs for each
   behavior class, including `check=False` probes and timeout propagation. Include at least one test
   that proves the interactive `Popen` path is still untouched if the module has one.

7. **Write the reviewer checklist into the plan itself.**
   The reviewer should not have to rediscover the risk model. Include a short "Most uncertain
   assumptions / Unverified anchors / Reviewer focus" section with commands that can be run from a
   clean checkout.

8. **Run narrow verification before upgrading confidence.**
   Until focused tests, lint, and import-cycle checks run, keep the plan at `unverified`. Passing
   validation of the plan text or reading source is not enough to call the implementation verified.

## Verified Workflow

No implementation workflow has been verified for this skill. This heading is retained for the current
ProjectMnemosyne validator, which still requires `## Verified Workflow`; use `## Proposed Workflow`
above as the operative guidance.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat grep counts as stable | Plan cited exact occurrence counts and file/line anchors gathered during planning | The target file can change before implementation, and sequential edits can make line anchors stale | Record counts as plan-time observations and require the implementer to re-run the search before editing |
| Infer helper behavior from sibling call sites | Plan relied on another module's usage of the shared helper instead of re-reading the helper contract | Call sites do not prove return type, default `check`, stdout/text handling, timeout propagation, or exception behavior for the target use | Re-read the helper implementation or API contract before asserting behavior parity |
| Use sibling imports as proof of no cycle | Plan pointed at an existing import from elsewhere as evidence that importing the helper is safe | A safe import in one layer does not prove this target module has no cycle or dependency inversion problem | Mark import safety as an assumption and run the import-cycle guard or smoke import |
| Replace all process calls mechanically | Plan treated every `subprocess` use as a candidate for the helper swap | Interactive `Popen` or TTY handoff paths can have different semantics and must often remain raw | Classify non-interactive probes separately from interactive commands before replacing calls |
| Patch the helper definition site in tests | Tests mock `helpers.run_subprocess` after the target module imported the helper by name | The consumer module already has its own binding, so the real helper may still run and tests can pass or fail for the wrong reason | Patch `target_module.run_subprocess` and assert exact kwargs on the imported seam |
| Declare the plan verified from source reading | Plan described tests and guards but did not execute them | Reading source can identify risks, but it does not prove behavior, import safety, or timeout propagation | Keep the learning and plan marked `unverified` until focused tests and guards actually run |

## Results & Parameters

### Plan-Risk Capture Template

```markdown
## Plan Risk Capture

### Most uncertain assumptions
- Grep/count observations are current only as of planning time; implementer must re-run them.
- Existing imports from sibling modules do not prove this module's import-cycle or layering safety.
- Shared helper semantics may differ from raw subprocess behavior around stdout, text, check, timeout, logging, and exceptions.
- Keeping an interactive process exception is safe only if non-interactive probes and interactive commands are classified correctly.

### External anchors not directly verified
- Referenced file/line anchors and tests are plan-time observations, not guaranteed current state.
- Helper behavior was inferred from existing call sites; re-read the helper contract before implementation.
- Import-cycle risk is delegated to the import-cycle guard; run it before claiming safety.
- Issue acceptance criteria and remote issue state were not re-queried in the final plan text.

### Reviewer focus
- Verify no bare non-interactive `subprocess.run(` remains in the target module.
- Verify `subprocess.Popen(...)` or other interactive process paths remain untouched when intentionally excluded.
- Confirm `check=False` behavior is preserved for expected-failure probes.
- Confirm raising probes still use default `check=True` or an explicit equivalent.
- Confirm tests patch the actual imported seam, for example `target_module.run_subprocess`.
- Confirm tests assert exact kwargs and still cover timeout propagation.
- Run focused tests, lint, and import-cycle guard before upgrading confidence.
```

### Focused Verification Command Shape

```bash
# Re-run searches from a clean checkout before implementation or review.
rg -n "subprocess\\.run\\(" path/to/target_module.py
rg -n "subprocess\\.Popen\\(" path/to/target_module.py

# Confirm tests patch the consumer seam rather than the helper definition site.
rg -n "patch\\(\".*run_subprocess|monkeypatch\\.setattr\\(.*run_subprocess" tests/

# Run the narrow behavioral tests, lint target, and import-cycle guard used by the repo.
pytest tests/path/to/test_target_module.py
ruff check path/to/target_module.py tests/path/to/test_target_module.py
pytest tests/unit/utils/test_no_import_cycles.py
```

### Mechanical Refactor Review Checklist

```text
- [ ] Every process call in the target file is classified as helper-swap, expected-failure probe,
      raising probe, or interactive/raw exception.
- [ ] Expected-failure probes preserve `check=False`.
- [ ] Raising probes preserve `check=True` behavior, either explicitly or through the helper default.
- [ ] stdout/stderr/text/cwd/env/timeout kwargs are intentionally preserved or intentionally changed.
- [ ] Tests patch the target module's imported helper binding.
- [ ] Tests assert exact kwargs for representative calls.
- [ ] Timeout propagation remains covered.
- [ ] Interactive `Popen` behavior remains covered or explicitly left unchanged.
- [ ] Import-cycle or import-smoke guard ran after adding the helper import.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning-only review of a mechanical refactor replacing bare non-interactive git probes with a shared process helper while leaving an interactive process path untouched | unverified - plan risk capture only; no implementation or CI run was performed |
