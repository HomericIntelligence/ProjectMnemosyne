---
name: automation-log-path-helper-planning-risks
description: "Planning-risk checklist for extracting standard automation log path naming into a shared helper. Use when: (1) a plan consolidates repeated per-issue log filename construction into hephaestus.automation._review_utils.log_file_path(...), (2) issue text hints at one scope but examples/affected files imply another, (3) standard .log filenames and diagnostic parse-error filenames must stay distinct, (4) reviewers need to re-grep drift-prone call-site inventories before implementation."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - automation
  - logging
  - log-paths
  - helper-extraction
  - planning
  - reviewer-risks
  - issue-scope
  - grep-inventory
  - filename-contract
  - projecthephaestus
---

# Automation Log Path Helper - Planning Risks

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Capture the uncertain assumptions in a plan for ProjectHephaestus issue #1397: extract standard automation log path naming into `hephaestus/automation/_review_utils.py::log_file_path(...)`. |
| **Outcome** | Planning learning captured only; implementation, GitHub issue body, current branch state, and CI were not verified during this capture. |
| **Verification** | unverified - plan-review artifact only |

This skill is about reviewing a plan before implementation. It records what the
planner inferred, what was not verified directly, and where a reviewer should push
hardest before approving the implementation plan.

## When to Use

- Reviewing a plan that consolidates repeated automation log filename construction into a shared helper.
- The issue title appears to mention one scope, but the issue body, examples, or affected files seem to imply a narrower or different scope.
- A plan distinguishes standard per-issue `.log` files from parse-error or diagnostic logs with intentionally different filenames.
- A call-site inventory was produced by grep during planning, but implementation may happen after line numbers or call sites drift.
- A helper is placed in a shared utility module such as `_review_utils.py`, and reviewers need to check import direction and dependency cycles.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a
> hypothesis until the GitHub issue body, current checkout, implementation, tests,
> and CI are verified.

### Quick Reference

```bash
# Re-ground the issue scope before implementing.
gh issue view 1397 --repo HomericIntelligence/ProjectHephaestus --json title,body

# Rebuild the call-site inventory from current code, not from planning line numbers.
rg -n 'review.*\\.log|feedback.*\\.log|address.*\\.log|parse.*\\.log|Path\\(|open\\(' \
  hephaestus/automation tests

# Verify the proposed helper boundary does not introduce import cycles.
python -c "import hephaestus.automation._review_utils"

# After implementation, prove no standard per-issue log construction remains outside
# log_file_path except intentionally different diagnostic filenames.
rg -n 'f\".*\\{.*issue.*\\}.*\\.log|\\.with_suffix\\(\"\\.log\"\\)|Path\\([^)]*\\.log' \
  hephaestus/automation tests
```

### Detailed Steps

1. **Re-read the live issue before locking scope.** If the title appears to mention
   `gh_json` but the body/examples/affected files point at log path construction,
   make that a reviewer-confirmed scope decision. Do not silently broaden the plan
   into JSON parsing changes such as `json.loads(result.stdout...)` unless the live
   issue body actually asks for that.

2. **Re-grep the current checkout during implementation.** Treat planning-time line
   numbers and call-site lists as stale hints. Re-run `rg` over `hephaestus/automation`
   and `tests` to find standard per-issue `.log` construction before editing.

3. **Separate standard log contracts from diagnostic filenames.** A helper named
   `log_file_path(prefix, issue_number, iteration)` that always appends `.log` and
   standardizes `{prefix}-{issue_number}-r{iteration}.log` should not automatically
   absorb parse-error diagnostics if those filenames intentionally carry different
   detail. Reviewers must confirm diagnostic names are contractually different, not
   missed standard logs.

4. **Prove naming parity with tests and consumers.** Expected standard names should
   be `{prefix}-{issue_number}-r{iteration}.log`, including feedback, address, and
   review logs. Pay special attention to off-by-one behavior around
   `prev_iteration + 1` and any consumers that read old filenames.

5. **Validate the abstraction boundary by import execution.** `_review_utils.py` is a
   plausible home because it already owns shared reviewer/logging helpers, but that
   is still an assumption. Confirm the new helper does not make callers import a
   module that imports them back, and smoke-test the relevant imports.

6. **Match verification depth to filename-consumer risk.** Targeted helper tests are
   not enough if downstream automation reads artifacts by exact name. Require a grep
   audit plus affected workflow tests. Run full pytest and ruff when feasible.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust inferred issue scope from title keywords | The planner noticed the issue title apparently mentioned `gh_json`, but chose not to touch `json.loads(result.stdout...)` because the body/examples/affected files appeared to point at log path construction | The actual GitHub issue body was not directly verified during this capture, so the scope split is an inference | Before implementation, read the live issue body and make the scope decision explicit for review |
| Freeze planning-time grep output | The call-site inventory came from grep during planning and included proposed local line numbers | Line numbers and duplicated log construction are drift-prone; implementation may happen against a different checkout | Re-run grep during implementation and review; do not rely on stale planning line numbers |
| Treat all `.log` filenames as standard logs | Parse-error diagnostics were intentionally excluded because the proposed helper always appends `.log` and standardizes prefix/issue/iteration only | This is correct only if diagnostic names are contractually different; otherwise the plan missed standard logs | Reviewers should confirm each excluded diagnostic filename is intentionally non-standard |
| Assume iteration naming parity | Plan expected `{prefix}-{issue_number}-r{iteration}.log` for feedback/address/review logs | Off-by-one iteration behavior, especially `prev_iteration + 1`, can silently change artifact names | Add tests around iteration boundaries and check any consumers of old names |
| Assume `_review_utils.py` is always the right boundary | The plan placed the helper in `_review_utils.py` because that module already owns shared reviewer/logging helpers | A shared helper can still create undesirable import dependencies or cycles | Smoke-test imports and inspect caller direction before approving |
| Rely on targeted tests only | The verification plan emphasized focused tests but did not prove downstream artifact consumers were covered | Filename changes can break automation that reads old paths without touching the helper test | Require grep plus affected workflow tests, and full pytest/ruff if feasible |

## Results & Parameters

### Most Uncertain Assumptions

- The scope split is inferred: issue title apparently mentions `gh_json`, while the selected plan targets log path construction and leaves `json.loads(result.stdout...)` unchanged.
- Planning-time file paths and line numbers came from the local ProjectHephaestus checkout, but the live GitHub issue #1397 body, current branch state, and CI behavior were not directly verified during this capture.
- `_review_utils.py` is assumed to be the correct abstraction boundary because it already contains shared reviewer/logging helpers.
- Parse-error diagnostic filenames are assumed to be intentionally outside the standard helper contract.

### External Sources Not Directly Verified

- Live GitHub issue #1397 body and acceptance criteria.
- Current branch state at implementation time.
- Full call-site inventory after any intervening code changes.
- Downstream automation or consumers that may read exact artifact filenames.
- CI behavior after introducing the shared helper.

### Reviewer Focus Checklist

```text
- [ ] Confirm issue #1397 really targets standard log path construction, not gh_json/json.loads handling.
- [ ] Re-grep current code and tests for standard per-issue .log construction before and after the change.
- [ ] Confirm parse-error diagnostics are intentionally non-standard filenames.
- [ ] Check exact naming parity: {prefix}-{issue_number}-r{iteration}.log for feedback/address/review logs.
- [ ] Test off-by-one iteration behavior, especially prev_iteration + 1.
- [ ] Smoke-test imports to rule out _review_utils.py dependency cycles.
- [ ] Run affected workflow tests, plus full pytest/ruff if feasible.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning session for issue #1397, standard automation log path naming helper | Plan produced, not implemented. This skill records unverified assumptions and reviewer risks for the eventual implementation/review pass. |
