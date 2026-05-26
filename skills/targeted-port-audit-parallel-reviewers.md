---
name: targeted-port-audit-parallel-reviewers
description: "Targeted code-port audit using 3-5 parallel review agents instead of a full repo audit. Use when: (1) a script/module was rewritten from one language to another (bash→Python, Python→Rust, etc.), (2) you need feature parity verification vs. a previous implementation, (3) the change is narrowly scoped and the full /repo-analyze-strict-full skill would drown actionable findings in 14 irrelevant sections, (4) auditing a refactor against a deleted-or-archived prior version, (5) you have line-by-line side-by-side comparison material available."
category: tooling
date: 2026-05-26
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [port-audit, parallel-review, feature-parity, code-port, rewrite-audit, focused-review, bash-to-python, narrow-scope-audit]
---

# Targeted Port Audit With Parallel Reviewers

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-26 |
| **Objective** | Audit a narrowly-scoped rewrite (one module ported between languages or rewritten in place) for feature parity, semantic preservation, concurrency safety, and test coverage — without paying the cost of a full repo-wide audit. |
| **Outcome** | 5 actionable bugs found in `hephaestus/automation/loop_runner.py` port in ~8 minutes wall time vs. ~30-minute full audit. verified-local. |
| **Scope** | Single-module rewrites (bash → Python, Python → Rust, JS → TS, etc.) and tight-scope refactors with a known prior implementation. |

## When to Use

- A rewrite (bash → Python, JS → TS, etc.) needs feature-parity sign-off before the old version is deleted
- The change touches one module / one feature — not the whole repo
- You already know which dimensions matter (parity, semantics, concurrency, tests) and don't need to discover them
- You have a previous implementation available (in git history, archived, or sibling-language source) to diff against
- The full `/repo-analyze-strict-full` 15-section sweep would produce findings about CI / security / packaging unrelated to the change

## Do NOT Use When

- Auditing a feature without a prior implementation to compare against — use `brainstorm` + design-review instead
- Investigating a single bug — use `systematic-debugging`
- Auditing the whole repo's health — use `/repo-analyze-strict-full`
- The rewrite spans many modules with cross-cutting concerns — use `audit-driven-remediation-workflow` to coordinate

## Verified Workflow

### Quick Reference: 4-Agent Parallel Dispatch

```python
# Dispatch all 4 audit agents in parallel in ONE message.
# Each agent gets the full text of BOTH old and new files,
# a single-dimension charter, and a 500-word output cap.

Agent(description="Feature parity audit",
      prompt="Compare <old> and <new>. Produce a table: every flag, "
             "every env var, every behavior. Status column: "
             "✅ MATCH / ⚠ DIVERGENT / 🔴 MISSING. Cite line numbers "
             "on BOTH sides. 500-word cap.")

Agent(description="Behavior semantics audit",
      prompt="In <old> and <new>, audit the domain-specific invariants: "
             "phase-skip rules, idempotency contract, exit-code propagation. "
             "For each invariant: does the new code preserve it? "
             "Line citations + severity tag. 500-word cap.")

Agent(description="Concurrency/error containment audit",
      prompt="In <new>, audit executor + exception propagation + signal "
             "handling. Are futures awaited? Are exceptions re-raised "
             "or swallowed? Is shutdown cooperative? 500-word cap.")

Agent(description="Test coverage cross-reference audit",
      prompt="For every behavioral claim about <new>, identify the test "
             "that proves it. Mark each claim STRONG / WEAK / ❌ UNTESTED. "
             "Cite test file + line. 500-word cap.")
```

### Step-by-Step

#### Step 1 — Preserve the prior implementation

Always do this BEFORE dispatching agents. Concrete line-number citations on both sides make findings unambiguous.

```bash
# If old version still in git history:
git show HEAD:scripts/run_automation_loop.sh > /tmp/old_loop.sh

# If old version was deleted in a prior commit:
git log --diff-filter=D --name-only -- scripts/run_automation_loop.sh
git show <deletion-commit>^:scripts/run_automation_loop.sh > /tmp/old_loop.sh

# If old version is in a sibling repo / archive:
cp <archive>/run_automation_loop.sh /tmp/old_loop.sh
```

#### Step 2 — Pick 3-5 audit dimensions

Standard set for a port:

1. **Feature parity table** — every flag, every env var, every behavior with status: ✅ MATCH / ⚠ DIVERGENT / 🔴 MISSING.
2. **Domain-specific semantics** — phase-skip rules, idempotency invariants, error-code contracts. Whatever is the "soul" of the module.
3. **Concurrency / error containment** — executor + exception nets + signal handling.
4. **Test coverage cross-reference** — each claim about the new code → which test proves it, marked STRONG / WEAK / ❌ UNTESTED.
5. *(optional)* **Security / secrets boundary** — only if the module handles credentials, shells out, or crosses a trust boundary.

#### Step 3 — Dispatch each dimension in parallel

Each agent gets:
- The full text of both old and new files (via absolute paths)
- A **single-dimension charter** (one dimension only)
- The expected **report format** (table with line-number citations, severity-tagged findings)
- A **500-word output cap** so the agent doesn't drift into unrelated dimensions

Dispatch ALL agents in one message so they run in parallel.

#### Step 4 — Consolidate findings

After all agents return, consolidate into a fix list ordered by severity:

```
🔴 MISSING   > 🐛 DIVERGENT > 🟡 weak-test > deferred (with explicit rationale)
```

Explicitly name trade-offs that are consciously deferred — a focused review distinguishes "we're not fixing this because X" from "we forgot about this".

#### Step 5 — Implement fixes + regression tests

For each bug, add a regression test whose name encodes the bug. Examples from the worked case:
- `test_implement_argv_has_single_max_workers`
- `test_review_plans_argv_has_no_no_ui`
- `test_loop_index_env_only_on_drive_green`

Run `pixi run pytest tests/unit/<module>/ -v` to confirm green before opening the PR.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Run `/repo-analyze-strict-full` on a narrowly-scoped port | Default 15-section sweep over the whole repo for a question that's really "does loop_runner.py match the deleted bash script" | ~30 minutes wall time, output is 14 sections of CI/security/packaging/compliance findings irrelevant to the port, actual port-fidelity findings buried | Scope the audit to the actual question. 3-5 parallel agents on the dimensions that matter beats 15 agents on dimensions that don't. |
| Single broad code-review agent | One `feature-dev:code-reviewer` agent asked to "review the port" | Agent picks 1-2 obvious findings and stops — produces a shallow review without the structured per-dimension coverage | Structure forces depth. Split the question into 3-5 narrow charters, each with an enumerated checklist of subclaims. Agents go deeper when the scope is narrower. |
| Skip the prior-version preservation | Audit only the new code; assume reviewer can reconstruct the old behavior from context | Reviewer can't cite line numbers from the old version, so 🔴 MISSING findings get phrased vaguely as "this might have been in the old version" — fixes get delayed by re-verification | Always `git show HEAD:path > /tmp/old.ext` before dispatching parity agents. Concrete line-number citations on both sides make findings unambiguous. |

## Results & Parameters

### Worked Example — ProjectHephaestus 2026-05-26

**Subject:** `hephaestus/automation/loop_runner.py` (Python port) vs. deleted `scripts/run_automation_loop.sh` (bash original).

**Dispatch:** 4 parallel agents (feature parity / semantics / concurrency / test coverage). Wall time: ~8 minutes.

**Findings — 5 actionable bugs:**

| Severity | Finding |
| -------- | ------- |
| 🔴 MISSING | `--no-follow-up` flag on loop 3+ entirely absent from the Python port |
| 🐛 DIVERGENT | `--max-workers` duplicated in the implement-phase argv (passed twice) |
| 🐛 DIVERGENT | `--no-ui` spuriously added to `review-plans` phase argv (was not in the bash original) |
| 🐛 DIVERGENT | `HEPH_LOOP_INDEX` / `TOTAL_LOOPS` env vars leaked to all phases (bash only set them for drive-green) |
| 🐛 DIVERGENT | Lazy clone race condition when `--parallel-repos > 1` |

**Findings — 2 explicit deferrals (named, not buried):**
- Cooperative-shutdown timing diverges by ~50ms — acceptable
- `threading.Event` vs. plain `bool` flag in shutdown handler — equivalent for the access pattern in use

**Compared to alternatives:**
- `/repo-analyze-strict-full`: would have found these but mixed with ~100 unrelated findings across 14 other sections (~30 min wall time, hours to triage)
- Single broad code-review agent: found 1 of the 5 bugs (`--no-follow-up`), missed the four argv/env divergences

### Parameter Tuning

| Parameter | Value Used | Rationale |
| --------- | ---------- | --------- |
| Number of agents | 4 | 3 too narrow (missed test coverage), 5+ produced overlapping findings |
| Per-agent word cap | 500 | Forces concrete citations over prose; agents drift past 800 |
| Parallel dispatch | All in one message | Wall-time savings only realized if dispatched together |
| Output format | Table + severity tag + line citations | Required for clean consolidation in Step 4 |
