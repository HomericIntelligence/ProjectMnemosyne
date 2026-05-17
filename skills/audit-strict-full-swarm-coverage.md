---
name: audit-strict-full-swarm-coverage
description: "Methodology for running a strict, full-coverage repository audit by dispatching one swarm agent per audit section in waves of 5. Use when: (1) running /hephaestus:repo-analyze-strict-full or equivalent full-coverage audit on a repo with >500 files, (2) bug-finding completeness matters and sampling is unsafe, (3) you need pre-release readiness review with strict grading (default F, evidence required), (4) single-agent audits are overflowing context or producing shallow results."
category: tooling
date: 2026-05-17
version: "1.1.0"
user-invocable: false
verification: verified-local
history: audit-strict-full-swarm-coverage.history
tags: [audit, repo-analyze, swarm, myrmidon, strict-grading, full-coverage, wave-dispatch, bucketing, go-no-go]
---

# Audit: Strict Full-Coverage Swarm Methodology

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-17 |
| **Objective** | Run a strict, evidence-based full-coverage repository audit by bucketing files per audit section and dispatching one swarm agent per section (in waves of 5 if concurrency is capped, or all 15 in parallel if not). |
| **Outcome** | Verified on two projects. ProjectScylla 2026-05-07: B- (82%), CONDITIONAL GO, 3 critical / 19 major / 3 grouped minor (issues #1934-#1959). ProjectAgamemnon 2026-05-17: B- (78%), CONDITIONAL GO, 1 critical (triple-copy Python orchestration) / 19 major / ~15 minor, all with file:line citations. Wall-clock ~10-15 min when 15 agents run in parallel. |
| **Verification** | verified-local |
| **History** | [changelog](./audit-strict-full-swarm-coverage.history) |

## When to Use

- A repo audit where bug-finding completeness matters (sampling-based audits would miss bugs)
- Repos > 500 files where a single agent would overflow context
- Pre-release / pre-merge readiness reviews where every file must be inspected
- Strict grading is required: default F, A reserved for 0 critical + 0 major + ≤2 minor
- You are running `/hephaestus:repo-analyze-strict-full`, `/hephaestus:repo-analyze-full`, or equivalent

## When NOT to Use

- Quick health checks (use `/hephaestus:repo-analyze-quick` instead — defaults to B, sampling OK)
- Single-section spot audits (use a single agent directly)
- Repos < ~200 files where a single agent can read everything in one pass

## Verified Workflow

### Step 1 — Inventory every file

```bash
find . -type f \
  -not -path '*/\.*' \
  -not -path '*/node_modules/*' \
  -not -path '*/.venv/*' \
  -not -path '*/build/*' \
  -not -path '*/.pixi/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/htmlcov/*' \
  | sort > /tmp/repo-files.txt
wc -l /tmp/repo-files.txt
```

The file list is the source of truth — every entry must end up in exactly one section bucket.

### Step 2 — Bucket files by audit section

Partition `/tmp/repo-files.txt` into 15 section buckets:

1. Project structure & layout
2. Documentation (README, docs/, CHANGELOG)
3. Architecture & design
4. Source code quality
5. Testing
6. CI/CD & build
7. Dependencies & lockfiles
8. Security
9. Safety / runtime guarantees
10. Planning & issue tracking
11. AI tooling & agent configs (.claude/, agents/, skills/)
12. Packaging & distribution
13. Developer experience (justfile, tooling scripts)
14. API design (CLI, public Python API)
15. Compliance & licensing

Bucketing rules:
- Every file appears in exactly one bucket. Some files (e.g., `pyproject.toml`) span concerns — assign to the dominant one (packaging) and let other sections cross-reference.
- Save bucket lists as `/tmp/audit-section-NN.txt` so each agent gets a precise, finite worklist.

### Step 3 — Dispatch the agents

Two valid topologies, depending on the harness's concurrency cap:

- **Single parallel batch (preferred when concurrency allows):** issue all 15 Agent tool calls in a **single assistant message**. Verified on ProjectAgamemnon 2026-05-17 — completed in ~10-15 min wall-clock.
- **3 waves of 5 (fallback when the swarm runtime caps at 5 concurrent agents):**
  - Wave 1: sections 1–5
  - Wave 2: sections 6–10
  - Wave 3: sections 11–15
  - Launch each wave by issuing 5 Agent tool calls in a single assistant message with `run_in_background=true`. Wait for all 5 to complete before launching the next wave.

Either way, every section MUST get its own dedicated agent — never collapse multiple sections into one prompt or the agent will run out of context (see Failed Attempts).

### Step 4 — Per-agent prompt template

Every dispatched agent receives all of:

0. **Subagent type: `general-purpose`.** Do NOT use `feature-dev:code-reviewer` despite the natural fit — review subagents are read-only and lack the Bash tool. Audit agents need `Bash` to run `find`, `gh issue list`, `git log`, `grep`, etc. for evidence gathering. `general-purpose` has the full tool palette and is the only working choice.
1. **Section criteria verbatim** — copy the rubric for that section from the parent skill (`/hephaestus:repo-analyze-strict-full`). Every agent gets the SAME grading rubric + anti-inflation rules so the output format is identical and synthesis is mechanical.
2. **Strict grading rubric:**
   - Default grade is **F**.
   - **A** requires 0 critical + 0 major + ≤2 minor findings.
   - **B** requires 0 critical + ≤1 major.
   - "Exists" is not enough — the artifact must be correct, complete, and maintained.
   - Missing required items are **MAJOR** or **CRITICAL**, never nitpicks.
   - Anti-inflation: do not round up. A B+ stays B+, never becomes A-.
3. **Development principles list:** KISS, YAGNI, SOLID, DRY, POLA, TDD, MODULARITY — agent must flag violations.
4. **Bucketed file list:** path to `/tmp/audit-section-NN.txt`. Agent MUST read every file (no sampling).
5. **Report format:**
   - Grade + percentage
   - Evidence (file:line citations for every claim)
   - Strengths (verified, not aspirational)
   - Findings, each tagged severity (critical / major / minor) with `file:line`
   - Missing items (with severity)
   - Principle violations (with file:line)

### Step 5 — Final assembly (the L0 orchestrator's job)

Compute weighted overall grade:

| Section | Weight |
| ------- | ------ |
| Architecture | 15% |
| Source Quality | 15% |
| Testing | 12% |
| Security | 12% |
| Safety | 10% |
| CI/CD | 8% |
| Documentation | 7% |
| AI Tooling | 5% |
| Other 7 sections | 16% total (≈2.3% each) |

Sum to 100%.

### Step 6 — GO / NO-GO decision

| Verdict | Criteria |
| ------- | -------- |
| **GO** | 0 critical findings AND ≤2 major AND overall ≥80% |
| **CONDITIONAL GO** | ≤2 critical (each with a clear, scoped fix path) AND overall ≥65% |
| **NO-GO** | otherwise |

Always file critical and major findings as GitHub issues before merging the audit report.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Single-agent full audit | One agent reads every file in the repo | Context overflow on >500-file repos; quality drops sharply | Per-section swarm with bucketing keeps each agent's context tight |
| Sampling-based strict audit | Default `repo-analyze-strict` (10 random + 5 largest + 5 smallest per section) | Misses bugs in unsampled files; cannot honestly claim full coverage | Use the FULL variant when bug-finding completeness matters |
| Launching all 15 agents at once | Single message with 15 Agent tool calls | On harnesses that cap at 5 concurrent agents, extras queue or fail. On uncapped harnesses (verified ProjectAgamemnon 2026-05-17), this is the FASTEST topology (~10-15 min wall-clock). | Check harness limits first: use single-batch when allowed, fall back to 3 waves of 5 otherwise. |
| Letting agents pick their own files | No bucketed list; agents discover files via `find` | Overlap (same file audited twice) and gaps (files audited zero times) | Pre-bucket every file into exactly one section list |
| Sequential single-agent strict-full audit | One agent walks all 15 sections in a single prompt | Ran out of context partway through Section 8 (Security) on ProjectAgamemnon 2026-05-17. Output was truncated and several sections never produced findings. | Strict-full MUST be split per-section — there is no working single-agent variant. |
| `subagent_type: feature-dev:code-reviewer` | Natural first guess: it's literally a code reviewer | Code-reviewer subagents are read-only and lack the Bash tool. They cannot run `find` to enumerate files, `gh issue list` to check planning state, `git log` for history evidence, or `grep` for cross-cutting concerns. Outputs ended up shallow and citation-free. | Use `subagent_type: general-purpose` for audit agents — the full tool palette is non-negotiable for evidence-based grading. |

## Results & Parameters

Audit run on ProjectScylla 2026-05-07:

| Parameter | Value |
| --------- | ----- |
| Total files inventoried | 1821 |
| `src/scylla/` Python files | 168 |
| Audit sections | 15 |
| Concurrent agents per wave | 5 |
| Total waves | 3 |
| Critical findings | 3 |
| Major findings | 19 |
| Minor findings (grouped) | 3 |
| Overall weighted grade | B- (82%) |
| Verdict | CONDITIONAL GO |
| Issues filed | #1934-#1959 |

Audit run on ProjectAgamemnon 2026-05-17:

| Parameter | Value |
| --------- | ----- |
| Audit sections | 15 |
| Topology | Single parallel batch (15 Agent calls in one message) |
| Subagent type | `general-purpose` (Sonnet) |
| Wall-clock duration | ~10-15 min |
| Critical findings | 1 (triple-copy Python orchestration code) |
| Major findings | 19 |
| Minor findings | ~15 |
| Overall weighted grade | B- (78%) |
| Verdict | CONDITIONAL GO |
| All findings cited | file:line citations throughout |

Tunable parameters when applying this skill to other repos:

- **Wave size**: 5 (limited by swarm runtime; do not increase)
- **Section count**: 15 default; add or merge to fit the repo's risk profile
- **Weights**: rebalance per project (e.g., research-only repos can drop CI/CD to 3% and raise Documentation to 15%)
- **GO threshold**: 80% default; raise to 90% for production gates

### Quick Reference

```bash
# 1. Inventory
find . -type f \
  -not -path '*/\.*' -not -path '*/node_modules/*' -not -path '*/.venv/*' \
  -not -path '*/build/*' -not -path '*/.pixi/*' -not -path '*/__pycache__/*' \
  -not -path '*/htmlcov/*' \
  | sort > /tmp/repo-files.txt
wc -l /tmp/repo-files.txt

# 2. Bucket into /tmp/audit-section-01.txt ... /tmp/audit-section-15.txt
#    (every file in exactly one bucket)

# 3. Dispatch wave 1: 5 Agent tool calls in ONE message, run_in_background=true
#    Each agent gets: section rubric + strict grading + principles + bucket file + report format

# 4. Wait for wave 1 → dispatch wave 2 (sections 6-10) → wait → wave 3 (sections 11-15)

# 5. Assemble: weighted overall grade, GO/NO-GO, consolidated findings list

# 6. File critical/major findings as GitHub issues before publishing the audit
```

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectScylla | 2026-05-07 audit | 1821 files, 168 src .py; overall B- (82%); CONDITIONAL GO; 3 critical / 19 major / 3 grouped minor findings filed as issues #1934-#1959 |
| ProjectAgamemnon | 2026-05-17 audit | Single-batch (15 parallel `general-purpose` Sonnet agents); ~10-15 min wall-clock; overall B- (78%); CONDITIONAL GO; 1 critical (triple-copy Python orchestration) / 19 major / ~15 minor; all findings with file:line citations |

## Cross-References

- Companion: `/hephaestus:repo-analyze-strict-full` — the slash command this skill operationalizes
- Companion: `repo-audit-triage-fix-and-issue-workflow` — what to do with findings AFTER the audit completes
- Companion: `myrmidon-swarm-end-to-end-orchestration-full-workflow` — broader L0 orchestration patterns
- Contrast: `research-corpus-audit-parallel-agent-pattern` — similar swarm pattern but for research docs, 10 dimensions instead of 15 sections
