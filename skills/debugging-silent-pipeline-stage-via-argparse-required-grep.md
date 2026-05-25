---
name: debugging-silent-pipeline-stage-via-argparse-required-grep
description: "Diagnose silent stages in fan-out orchestrators (shell driving N Python CLIs, Makefile driving N tools, CI workflow driving N jobs) via a 3-command source-grep that compares argparse `required=True` flags against the flags the orchestrator actually passes. Use when: (1) a multi-stage pipeline reports success but a downstream stage produced no visible output, (2) only the first phase of run_automation_loop.sh / similar orchestrator runs, (3) orchestrator logs show generic `Warning: ... exited non-zero` with no underlying error detail, (4) you are tempted to re-run with `tee` + banner greps to reproduce a silent-stage bug, (5) the orchestrator uses `|| echo`, `|| true`, `set +e`, or `continue-on-error: true` to swallow exit codes."
category: debugging
date: 2026-05-24
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - argparse
  - orchestrator
  - silent-failure
  - source-grep
  - debugging-methodology
  - fan-out
  - exit-code-swallowing
  - shell
  - python
  - cli-contract
---

# Debugging Silent Pipeline Stages via argparse `required=True` Grep

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-24 |
| **Objective** | Localize silent-stage bugs in fan-out orchestrators in under 60 seconds via source review, instead of re-running the orchestrator with `tee` + banner instrumentation |
| **Outcome** | SUCCESS — methodology applied in ProjectHephaestus session identified root cause (orchestrator invoking 4 phase CLIs without `--issues`, all 4 required it) in ~60 seconds; fix shipped as PR #543 |
| **Verification** | verified-local — methodology applied in one real session; fix mergeable with auto-merge enabled at time of writing, full CI confirmation pending |

## When to Use

- A multi-stage orchestrator (shell, Makefile, CI workflow) reports success or only generic warnings, but a stage produced no visible output
- Only the first phase of a multi-phase pipeline appears to run (e.g., "planning ran but PR review didn't")
- Orchestrator stdout shows lines like `Warning: repo job exited non-zero` with no underlying cause
- You are about to set up `tee` + grep banners + a long dry-run to reproduce — STOP and try this first
- Orchestrator contains exit-code suppressors: `|| echo`, `|| true`, `set +e`, `continue-on-error: true`, `ignore_errors: yes`
- The failing CLI is argparse-based (Python), click-based, typer-based, or any framework that exits before any of the CLI's own logging fires

## Verified Workflow

### Quick Reference

```bash
# 1. List the orchestrator's outbound CLI calls and their flags
grep -nE '\$(PYTHON|.*_BIN)\b.*\.(py)?' scripts/run_automation_loop.sh | head -20

# 2. For each invoked CLI, check argparse required flags
for cli in hephaestus/automation/{plan_reviewer,pr_reviewer,address_review,ci_driver}.py; do
  echo "=== $cli ==="
  grep -n -B1 -A3 'required=True' "$cli" | head
done

# 3. Find the orchestrator's swallow points (these mask the real exit code)
grep -nE '\|\| echo|\|\| true|set \+e|continue-on-error' scripts/run_automation_loop.sh
```

Any flag the orchestrator does NOT pass that the CLI marks `required=True` = root cause. The CLI exited at argparse-time (exit 2) before producing any output the orchestrator could log.

### Detailed Steps

1. **Enumerate outbound calls from the orchestrator.** One grep over the orchestrator script for the binary or interpreter variable (`$PYTHON`, `$NODE_BIN`, `$PR_REVIEW_BIN`, etc.) and the file extensions of CLIs it invokes. Read the exact flag list for each call — copy it down.

2. **For each invoked CLI, locate the argparse setup.** Search the CLI's source for:
   - Python argparse: `required=True`
   - Python click: `@click.argument` (positional, implicitly required), `required=True` on `@click.option`
   - Python typer: positional parameters without `= None` default
   - Go cobra: `cmd.MarkFlagRequired(`
   - Node commander: `.requiredOption(`
   - Rust clap: `.required(true)`

3. **Diff the required-by-CLI set against the passed-by-orchestrator set.** Any flag in (required ∩ ¬passed) is a contract violation. The CLI will exit at parse-time before its own logging or banners run. This is decidable from source — do not run anything.

4. **Locate the swallow point in the orchestrator.** The orchestrator MUST be suppressing the failing exit code, or you would have seen the failure directly. Common patterns:

   | Pattern | Effect |
   |---------|--------|
   | `cmd \|\| echo "Warning: ..."` | Replaces exit 2 with a generic warning line, exit 0 |
   | `cmd \|\| true` | Replaces any non-zero with exit 0, silently |
   | `set +e` | Disables errexit for the block — non-zero is ignored |
   | `continue-on-error: true` (GitHub Actions) | Job continues regardless of step exit |
   | `ignore_errors: yes` (Ansible) | Task failure does not abort the play |
   | `2>/dev/null` on stderr | argparse error message is discarded — operator sees nothing |

   Confirm at least one is present at the call site of the failing stage. This explains why the operator only saw a vague warning.

5. **Verify the fix is in the orchestrator, not the CLI.** The CLI is behaving correctly (rejecting invalid input). The orchestrator must either:
   - Pass the missing required flag, OR
   - Stop suppressing the exit code so the operator sees the real error.

   Both are typically warranted: pass the flag AND remove `|| echo` so future contract drift is loud.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Re-run with tee + banner grep | Plan to capture a full dry-run log via `tee`, then grep for banner lines from each phase | Slow (5+ min orchestrator run × N repos), and the bug is upstream of stdout — banners would only confirm the symptom, not the cause. argparse exits before the CLI's own logging runs | Do not reproduce when the bug is decidable from source. Run repros only after source review fails to localize the failure |
| Hypothesize `--phases` env was set to a subset | Theory: orchestrator's `PHASES` env variable filtered out the missing stages | Possible but only explains one of two observable symptoms (the missing banner). Does not explain the `Warning: repo job exited non-zero` line the user pasted — that line proves the stage WAS invoked and exited non-zero | Multi-symptom triage: a hypothesis must explain ALL observed symptoms, not just the loudest one. A single observation can mislead; the warning line was the load-bearing clue |
| Read orchestrator logs for warnings/errors | Scrub orchestrator stdout for ERROR/WARN lines | The orchestrator was actively suppressing the very signal needed: `\|\| echo "Warning: ..."` collapses exit code 2 from argparse into a generic warning identical to per-issue runtime failures. Logs cannot show what the logger refuses to record | When the system actively suppresses error detail, source review is the only reliable path. Logs lie when the logger is the perp. Always grep for `\|\| echo`, `\|\| true`, and `set +e` before trusting orchestrator logs |
| Assume the CLI's own logging would show the failure | Expected the failing CLI to log "missing required argument" somewhere | argparse exits via `parser.error()` → writes to stderr → `sys.exit(2)`. This happens BEFORE any user-defined logging setup runs. If the orchestrator discards stderr or wraps the call in `\|\| echo`, the operator never sees the message | argparse failures are upstream of application logging. The only place the message lands is the orchestrator's captured stderr — if that is suppressed, source review is mandatory |

## Results & Parameters

### Decision Rule

```text
IF orchestrator stage produces no output AND orchestrator reports success/generic warning:
  required_flags := grep required=True in CLI source
  passed_flags   := grep CLI invocation in orchestrator
  IF required_flags - passed_flags ≠ ∅:
    ROOT CAUSE = contract violation at <flag>
    FIX = pass the flag, AND remove the swallow at the call site
  ELSE:
    fall back to dry-run with tee + banners (now justified)
```

### Time Budget Comparison

| Approach | Wall-clock | Sensitivity | When to Use |
|----------|------------|-------------|-------------|
| Source-grep (this skill) | ~60 seconds | Catches all argparse-time failures, missed flags, removed flags | Always try first |
| Dry-run with tee + banners | 5+ minutes per repo × N repos | Catches runtime failures inside the CLI body | Only after source-grep clears |
| Read orchestrator logs | Seconds, but unreliable | Useless when orchestrator suppresses exit codes | Never trust alone if `\|\| echo` is present |

### Concrete Example (ProjectHephaestus PR #543)

**Symptom**: `scripts/run_automation_loop.sh` appeared to only run the planning phase. User reported "why is run_automation_loop.sh only running the planning phase?"

**Diagnostic** (~60 seconds):
- 4 phase CLIs in `hephaestus/automation/`: `plan_reviewer.py`, `pr_reviewer.py`, `address_review.py`, `ci_driver.py`
- All 4 had `--issues` declared with `required=True`
- Orchestrator invoked all 4 WITHOUT `--issues`
- Orchestrator wrapped each call in `|| echo "Warning: repo job exited non-zero"`

**Root cause**: Missing `--issues` flag → argparse exit 2 → swallowed by `|| echo` → operator saw only generic warning + missing banner.

**Fix shape**: Pass `--issues "$issues"` to each phase invocation; replace `|| echo` with a structured failure that preserves the exit code.

### Generalization Across Stacks

| Stack | "Required flag" pattern | "Swallow" pattern |
|-------|------------------------|-------------------|
| Python argparse | `add_argument(..., required=True)` | shell `\|\| echo`, `\|\| true` |
| Python click | `@click.option(..., required=True)`, `@click.argument` | shell `\|\| echo`, `\|\| true` |
| Python typer | Positional param without default | shell `\|\| echo`, `\|\| true` |
| Go cobra | `cmd.MarkFlagRequired("name")` | shell `\|\| echo`, `errcheck` ignored |
| Node commander | `.requiredOption("--name <value>")` | shell `\|\| echo`, `.catch(() => {})` |
| Make targets | `$(error ...)` on missing var | `-` prefix on recipe line |
| GitHub Actions | `inputs.<name>.required: true` | `continue-on-error: true` |
| Ansible | `required: true` in arg_spec | `ignore_errors: yes` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #543 — `scripts/run_automation_loop.sh` invoking 4 automation CLIs without `--issues` | Methodology localized root cause in ~60s; fix mergeable with auto-merge enabled, full CI confirmation pending |
