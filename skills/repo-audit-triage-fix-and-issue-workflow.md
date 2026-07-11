---
name: repo-audit-triage-fix-and-issue-workflow
description: "Full workflow for strict repo audit triage: run audit, verify each finding is true before acting on it, classify findings by complexity, batch-fix simple items in one PR, file GitHub issues for complex work. Use when: (1) running a comprehensive repository quality audit and acting on all findings, (2) needing to triage audit results into immediate fixes vs tracked issues, (3) remediating dead code, stale docs, broken CI, or missing requirements files, (4) acting on a multi-agent swarm audit (`/repo-analyze-strict-full`) whose section reports may contain false positives that must be verified before triage."
category: tooling
date: 2026-05-19
version: "1.2.0"
user-invocable: false
verification: verified-local
history: repo-audit-triage-fix-and-issue-workflow.history
tags: [audit, triage, remediation, github-issues, dead-code, ci, requirements, parallel-execution, swarm-audit, false-positive, trust-but-verify]
---

# Repo Audit: Triage, Fix, and Issue Workflow

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-19 |
| **Objective** | Run a strict repo audit, triage findings by complexity, batch-fix scoped items, and reconcile complex work against the existing GitHub issue backlog before creating focused gaps. |
| **Outcome** | Successful across Mnemosyne and Radiance: one audit cleanup PR pattern, existing issues updated/commented/labeled first, and only missing focused gaps filed as new issues. The skill now includes a finding-verification gate (Phase 1.5) that confirms each CRITICAL/MAJOR finding is true before triage — catching swarm-audit false positives. |
| **Verification** | verified-local |
| **History** | [changelog](./repo-audit-triage-fix-and-issue-workflow.history) |

## When to Use

- You have just run `/repo-analyze-strict` and have a list of graded findings
- The audit was produced by a multi-agent swarm and individual section findings may be factually wrong — you need to verify each finding before acting on it
- You want to separate work that fits in one PR from work that needs its own branch/epic
- You need to map audit findings onto an existing GitHub backlog without creating duplicates
- You want to update/comment/label existing issues before filing only the missing gaps
- You need to clear dead migration scripts, duplicate files, or stale changelog entries
- CI tests are partially broken and you need to scope the test runner to the working subset
- You suspect some test failures are pre-existing (not caused by your changes) and need to verify

## Verified Workflow

### Quick Reference

```bash
# Step 1: Run strict audit
/repo-analyze-strict

# Step 2: Triage findings (see decision criteria below)
# fix-now: <1 hour, no design decisions, self-contained
# file-as-issue: requires design, cross-repo impact, or multi-session work

# Step 3: Batch all independent fixes in parallel tool calls

# Step 4: Verify pre-existing test failures before attributing to your changes
git stash
python3 -m pytest tests/ -v 2>&1 | grep -E "PASSED|FAILED|ERROR"
git stash pop

# Step 5: Search/update existing issues before filing gaps
gh issue list --state open --limit 200 --json number,title,labels,url,updatedAt
gh issue list --state all --limit 200 \
  --search "runtime OR healthcheck OR auth OR security OR upload OR dependencies" \
  --json number,title,state,labels,url,updatedAt
gh issue comment 167 --body "Audit update (...): ..."
gh issue edit 167 --add-label bug --add-label priority:P0 --add-label phase:release

# Step 6: Scope CI to working test files only (if needed)
# In workflow YAML, change:
#   run: pytest tests/
# to:
#   run: pytest tests/test_generate_marketplace.py -v

# Step 7: Validate skill files
python3 scripts/validate_plugins.py

# Step 8: Commit, push, open PR with auto-merge
```

### Detailed Steps

#### Phase 1: Run the Audit

Run `/repo-analyze-strict`. This produces a graded report across 15 dimensions. Record:
- Overall score (letter grade + %)
- Per-section grades
- All findings classified as Critical / Major / Minor / Nitpick

#### Phase 1.5: Verify Findings Before Triage

**A swarm-audit finding is a claim, not an observation.** Multi-agent audits dispatch
one Sonnet agent per section (`/repo-analyze-strict-full` runs one agent per audit
section). Individual section agents make confident-sounding factual errors — they can
even miss context they were explicitly given in the dispatch prompt. Acting on a
false-positive finding wastes work, produces misleading commits, or — worst case — runs
a destructive command against a wrong premise.

For **every CRITICAL and MAJOR finding**, before triaging it, run the cheapest read-only
command that confirms or refutes its specific factual assertion:

| Finding shape | Verification command |
| --------------- | ---------------------- |
| "X is committed to git" | `git ls-files <path>` — empty output = not tracked = false positive |
| "no CI / `.github/` is empty" | `ls` the path the finding names **AND the repo root** — in a monorepo the workflow may live at root, path-scoped to the subproject |
| "file/artifact is missing" | `ls` / `test -f` the path |
| Finding cites a line number | open the file at that line |

Outcomes:

- **Findings that survive verification** proceed to Phase 2 triage.
- **Findings refuted by verification** are downgraded or dropped — and the section grade
  is corrected (a refuted CRITICAL/MAJOR finding usually means the section was graded too
  low).

Note the cost asymmetry: verification is **seconds**; acting on a false positive is
wasted work, a misleading commit, or a destructive command run on a wrong premise. Verify
first, always.

This is the same **trust-but-verify** discipline that the Mnemosyne skill
`tooling-sub-agent-pr-trust-but-verify` applies to sub-agent PR reports — here applied to
sub-agent *audit findings*.

#### Phase 2: Triage Findings

Use these criteria to decide between **fix-now** and **file-as-issue**:

| Criteria | Fix Now | File as Issue |
| ---------- | --------- | --------------- |
| Time estimate | < 1 hour | > 1 hour |
| Design decisions required | None | Yes |
| Cross-repo or multi-file refactor | No | Yes |
| Requires running tests suite changes | Minor scope | Major restructure |
| Impact if deferred | Low (hygiene) | Low–Medium (can track) |
| Concrete fix known | Yes | Needs investigation |

**Fix-now categories (typical)**:
- Dead scripts / migration artifacts with no callers
- Duplicate files left from refactors
- Missing `requirements.txt` / `requirements-dev.txt`
- Stale `[Unreleased]` changelog sections
- Incorrect CLI usage in docs
- Missing test fixture fields
- `.gitignore` gaps for local config files
- Wrong metadata in `.claude-plugin/plugin.json`

**File-as-issue categories (typical)**:
- Broken test files importing non-existent modules (requires module creation or deletion + test rewrite)
- Missing type annotations throughout a codebase
- Security hardening (e.g., input validation, sandboxing)
- Major CI matrix expansion
- Architectural restructuring (e.g., monorepo layout changes)

#### Phase 3: Batch-Execute Simple Fixes

Group all independent fix-now items and execute them in parallel tool calls within a single message. This dramatically reduces round-trips:

```
Parallel batch example:
- Edit .gitignore              (independent)
- Delete dead_script_1.py      (independent)
- Delete dead_script_2.py      (independent)
- Edit CONTRIBUTING.md         (independent)
- Edit CHANGELOG.md            (independent)
- Write requirements.txt       (independent)
- Write requirements-dev.txt   (independent)
- Edit tests/conftest.py       (independent)
- Edit .github/workflows/*.yml (independent — but verify test scope first)
```

Only serialize operations that have data dependencies (e.g., read a file before editing it).

#### Phase 4: Verify Pre-Existing Test Failures

Before attributing test failures to your changes, always verify they existed before your edits:

```bash
# Stash your changes
git stash

# Run the full test suite on the unmodified codebase
python3 -m pytest tests/ -v 2>&1 | grep -E "PASSED|FAILED|ERROR|ImportError"

# Restore your changes
git stash pop
```

If failures exist on the stashed (original) codebase, they are pre-existing. Document this in the PR description and scope CI to skip the broken test files.

**Pattern for broken test files that import non-existent modules**:

```bash
# Identify the broken imports
python3 -c "import tests.test_broken_file" 2>&1

# Scope CI to only the working tests
pytest tests/test_working_file.py -v
# Do NOT run: pytest tests/  (picks up broken files)
```

File a GitHub issue for the broken test files rather than deleting them (they may contain valuable test logic once the missing module is created).

#### Phase 5: File GitHub Issues for Complex Items

Before creating issues, search the backlog. Strict audits often rediscover known work.
Use both title lists and broader full-text searches:

```bash
gh issue list --state open --limit 200 \
  --json number,title,labels,url,updatedAt \
  --jq '.[] | "#\(.number)\t\(.title)\t[\([.labels[].name] | join(","))]"'

gh issue list --state all --limit 200 \
  --search "runtime OR healthcheck OR auth OR security OR upload OR dependencies" \
  --json number,title,state,labels,url,updatedAt \
  --jq '.[] | "#\(.number)\t\(.state)\t\(.title)"'
```

Classify each audit finding:

| Audit finding state | Action |
| --------------------- | -------- |
| Existing open issue covers it | Add an audit comment with concrete evidence and any new acceptance detail |
| Existing closed issue regressed | Comment on the closed issue with regression evidence, then open a narrow follow-up |
| Existing issue covers adjacent but not exact scope | Comment to clarify boundary, then open a focused gap issue |
| No issue found | Create a new issue with orchestrator kickoff, evidence, and acceptance criteria |

For each new file-as-issue item, create a GitHub issue with:
- Clear title stating the problem
- Background: what the audit found
- Acceptance criteria: what "done" looks like
- Relevant file paths and error messages
- Label: `technical-debt`, `testing`, `ci-cd`, etc.

```bash
gh issue create \
  --title "Fix broken test files importing non-existent module" \
  --body "$(cat <<'EOF'
## Background
Two test files import `fix_remaining_warnings` which does not exist...

## Acceptance Criteria
- [ ] Module created or test files deleted and rewritten
- [ ] `pytest tests/` runs clean with no ImportError

## Files Affected
- tests/test_fix_remaining_warnings.py
- tests/test_quick_reference_transform.py
EOF
)" \
  --label "technical-debt,testing"
```

After creating or updating issues, normalize labels so the backlog is filterable:

```bash
gh issue edit 181 \
  --add-label bug \
  --add-label type:validation \
  --add-label area:runtime \
  --add-label priority:P0 \
  --add-label phase:core
```

Read back the final issue list and comment counts:

```bash
gh issue list --state open --limit 50 --json number,title,labels,url \
  --jq '.[] | "#\(.number)\t\(.title)\t[\([.labels[].name] | join(","))]\t\(.url)"'
```

#### Phase 6: Validate and Commit

```bash
# Validate skill/plugin files if any were modified
python3 scripts/validate_plugins.py

# Run scoped tests
python3 -m pytest tests/test_generate_marketplace.py -v

# Check git diff for accidental deletions
git diff --stat

# Commit
git add <specific-files>
git commit -m "fix: apply audit remediation (dead code, CI, docs, requirements)"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Run `pytest tests/` in CI | Pointed the CI workflow test step at the full `tests/` directory | Two test files import a non-existent module (`fix_remaining_warnings`), causing `ImportError` collection failure | Always verify full test suite runs clean before setting CI to `tests/`; scope to working subset and file issues for broken files |
| Attribute test failures to own changes | Assumed `ImportError` failures in `test_fix_remaining_warnings.py` were caused by the deletion of migration scripts | Git stash + re-run proved the failures pre-existed | Always stash and re-run before concluding test failures are your fault |
| Fix broken test files in same PR | Tried to fix the broken test imports as part of the cleanup PR | The missing module `fix_remaining_warnings` doesn't exist and creating it is a design decision requiring its own scope | Keep the cleanup PR focused; file a dedicated issue for the broken tests |
| Create a new issue for every audit finding | Treating each strict audit finding as new work without checking the backlog first | Existing issues may already cover the work, and duplicate issues fragment implementation context | Search open and closed issues first; update existing issues and create only focused gap issues |
| Reopen broad closed work for a narrow regression | A closed implementation issue may be related to a new failing behavior | Reopening the broad issue can obscure the exact regression and old acceptance criteria | Comment on the closed issue for traceability, then open a narrow regression follow-up |
| Acted on a swarm-audit MAJOR finding without verifying it | A `/repo-analyze-strict-full` section agent reported `tests/__pycache__/` was committed to git; the plan was to `git rm -r --cached` it | `git ls-files` showed `__pycache__` was never tracked — it existed on disk but was correctly `.gitignore`-excluded. The finding was a false positive | Verify every CRITICAL/MAJOR swarm-audit finding with a single read-only command before triaging it. `git ls-files <path>` settles any "committed to git" claim in one second |
| Trusted a swarm-audit CRITICAL "no CI exists" finding | A section agent reported `.github/workflows/` was empty and there was no CI; the plan was to author a CI workflow | The agent checked only the project-subdirectory `.github/`. The real CI workflow lived at the monorepo-root `.github/workflows/`, path-scoped to the project. CI existed and ran | In a monorepo, a "no CI" finding must be checked against the repo root, not just the subproject. More broadly: a swarm agent can miss context it was even given — verify |

## Results & Parameters

### Swarm-audit false-positive rate (2026-05-19 session)

A 15-section `/repo-analyze-strict-full` run on a predictive-coding research project
produced **2 demonstrable false positives** — roughly **13% of sections** carried at
least one finding that did not survive verification:

- Section 1 (Project Structure): "MAJOR — `tests/__pycache__/` committed to git" —
  refuted by `git ls-files` (untracked, `.gitignore`-excluded). Downgraded to a one-line
  housekeeping note.
- Section 13 (Developer Experience): "CRITICAL — `.github/workflows/` empty, no CI" —
  refuted by `ls` of the monorepo root, where the path-scoped CI workflow actually lived.
  Finding removed; section grade corrected **D+ → C-**.

Both false positives were caught by a **single read-only command** in the Phase 1.5
verification gate, before any triage. The lesson: at least 1-in-8 swarm-audit sections
can carry a finding that would have caused wasted or misleading work if acted on naively.

### Audit Score Baseline (Mnemosyne, 2026-03-28)

| Section | Grade | Key Findings |
| --------- | ------- | -------------- |
| Documentation | B+ | Good README/CHANGELOG, missing ADRs |
| AI Agent Tooling | B+ | Skills marketplace functional |
| Planning/Compliance | B | Issues filed but no roadmap doc |
| Testing | C | 2 broken test files, no coverage enforcement |
| Dependencies | D | No requirements.txt (fixed in this session) |
| Safety | D | No input validation, no sandboxing |

### Changes Applied (10 fix-now items)

| Change | Type | Net Lines |
| -------- | ------ | ----------- |
| Fix `.claude-plugin/plugin.json` metadata | Edit | +10 / -10 |
| Create `requirements.txt` | New file | +2 |
| Create `requirements-dev.txt` | New file | +3 |
| Update CI to use `requirements-dev.txt` + scoped pytest | Edit | +5 / -3 |
| Delete 5 dead migration scripts | Delete | -1,100 |
| Delete 2 duplicate plugin scripts | Delete | -180 |
| Delete duplicate `learn-trigger.py` | Delete | -35 |
| Fix `CONTRIBUTING.md` CLI usage | Edit | +1 / -1 |
| Fix `tests/conftest.py` missing fixture field | Edit | +1 |
| Add `.claude/settings.local.json` to `.gitignore` | Edit | +1 |
| Clear stale `[Unreleased]` CHANGELOG section | Edit | +2 / -8 |

**Total**: 14 files changed, ~1,280 net lines deleted

### GitHub Issues Filed (Complex Work)

| Issue | Title | Label |
| ------- | ------- | ------- |
| #1105 | Fix broken test files (`fix_remaining_warnings`) | testing, technical-debt |
| #1106 | Add type annotations throughout codebase | code-quality |
| #1107 | Security hardening: input validation + sandboxing | security |
| #1108 | Expand CI matrix (Python versions, OS) | ci-cd |
| #1109 | Add ADR directory and document key decisions | documentation |
| #1110 | Enforce test coverage threshold in CI | testing, ci-cd |

### Existing Backlog Mapping Example (Radiance, 2026-04-28)

After a strict Radiance audit, most findings already had issue coverage:

| Audit finding | Existing or New Issue | Action |
| --------------- | ----------------------- | -------- |
| Mutating API endpoints exposed before non-local deployment | #167 | Commented with updated evidence and labels |
| Archive extraction hardening | #168 | Commented to keep archive scope separate from upload boundary |
| Oversized run orchestration module | #171 | Commented that runtime execution wiring should be sequenced with the refactor |
| Dependency lock/constraints strategy | #172 | Commented with container build dependency-resolution evidence |
| Browser/container smoke usability | #173 | Commented with stale container/port diagnostic evidence |
| Coverage gaps | #175 | Commented with new high-value regression targets |
| Healthcheck regression in previously closed hardening issue | #114 and #182 | Commented on closed #114, opened focused #182 |
| Runtime execution not wired into runtime mode | #181 | Opened new focused P0 blocker |
| Upload size enforcement independent of `Content-Length` | #183 | Opened new focused issue |
| User-provided model code execution policy | #184 | Opened new focused issue |

This produced four new focused issues instead of duplicating the entire audit as new tickets.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Mnemosyne | Strict audit + triage + 10-item cleanup PR (March 2026) | 9/9 tests passing, 6 issues filed (#1105–#1110) |
| Radiance | Strict audit issue-backlog reconciliation (April 2026) | Existing open issues were updated/commented/labeled first; only four missing focused issues were created (#181–#184) |
| A predictive-coding research project | `/repo-analyze-strict-full` 15-section swarm audit, 2026-05-19 — 2 section false positives caught by finding-verification gate before triage | A phantom committed `__pycache__` (refuted by `git ls-files`) and a phantom "no CI" (refuted by `ls` of the monorepo root) were both caught before triage; one section grade corrected D+ → C- |

## References

- Related skill: [audit-driven-remediation](./audit-driven-remediation.md) — implementing audit findings systematically (focuses on CI/source/test changes, not triage)
- Related skill: [issue-triage-wave-parallel-execution](./issue-triage-wave-parallel-execution.md) — parallel batching of independent fixes
- Related skill: [pre-existing-ci-failure-triage](./pre-existing-ci-failure-triage.md) — diagnosing failures that existed before your changes
- Related skill: [preexisting-ci-failure-triage](./preexisting-ci-failure-triage.md) — alternate entry for same pattern
