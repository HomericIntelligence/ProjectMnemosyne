---
name: recurring-tier-label-fix
description: "Fix recurring tier label mismatches in metrics-definitions.md. Use when a quality audit flags tier label inconsistencies."
category: documentation
date: 2026-03-03
user-invocable: false
---

# Recurring Tier Label Fix in metrics-definitions.md

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-03 |
| Issue | #1348 (4th quality audit recurrence) |
| Objective | Fix tier label mismatches in `.claude/shared/metrics-definitions.md` |
| Outcome | SUCCESS — commit `ab31ab8b`, PR #1362 |
| Prior occurrences | PR #1345 (March 2026 3rd audit), multiple earlier audits |

## When to Use

- A quality audit flags tier label mismatches in `.claude/shared/metrics-definitions.md`
- Labels like `T3 (Tooling)`, `T4 (Delegation)`, `T5 (Hierarchy)` appear anywhere in the file
- The authoritative tier table in CLAUDE.md is: T0=Prompts, T1=Skills, T2=Tooling, T3=Delegation, T4=Hierarchy, T5=Hybrid, T6=Super
- This issue recurs because fixes are partial — section headers get fixed but inline references further down the file do not

## Authoritative Tier Table

| Tier | Name |
|------|------|
| T0 | Prompts |
| T1 | Skills |
| T2 | Tooling |
| T3 | Delegation |
| T4 | Hierarchy |
| T5 | Hybrid |
| T6 | Super |

## Verified Workflow

### 1. Confirm current state

```bash
grep -n "T[0-9]" .claude/shared/metrics-definitions.md | grep -E "T3.*(Tool|Skill)|T4.*(Deleg|Tool)|T5.*(Hier|Deleg)"
```

### 2. Identify ALL mismatches (not just section headers)

The file has TWO distinct zones with tier labels:
- **Section headers** (~lines 239, 253, 267): `### T2 (Tooling)` etc.
- **Inline references** (~lines 330–825): `T3 - Tooling`, `T4 - Delegation`, `T5 - Hierarchy`, `T2 vs T3 Analysis`

Both zones must be fixed. Prior partial fixes only addressed section headers, causing the issue to recur.

### 3. Fix all inline references

Typical mismatched strings and their corrections:

| Wrong | Correct |
|-------|---------|
| `T3 - Tooling` | `T2 - Tooling` |
| `T4 - Delegation` | `T3 - Delegation` |
| `T5 - Hierarchy` | `T4 - Hierarchy` |
| `T2 vs T3 Analysis` (when comparing Skills vs Tooling) | `T1 vs T2 Analysis` |
| `between T2 (Skills) and T3 (Tooling)` | `between T1 (Skills) and T2 (Tooling)` |
| `tool schemas (T3+)` | `tool schemas (T2+)` |
| `T2 skill instructions` | `T1 skill instructions` |
| `T3 JSON tool definitions` | `T2 JSON tool definitions` |
| `T4/T5 coordination` | `T3/T4 coordination` |

### 4. Verify completeness

```bash
# Should show only legitimate T2/T3/T4 references after fix
grep -n "### T[0-9]" .claude/shared/metrics-definitions.md
# Should return no results for wrong patterns
grep -n "T3.*Tool\|T4.*Deleg\|T5.*Hier\|T2.*Skill" .claude/shared/metrics-definitions.md
```

### 5. Commit and PR

```bash
git add .claude/shared/metrics-definitions.md
git commit -m "fix(docs): Fix all tier label mismatches in metrics-definitions.md"
gh pr create --title "fix(docs): Fix tier label mismatches in metrics-definitions.md" \
  --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts / Root Cause of Recurrence

**Why this issue keeps recurring:**
- PR #1345 fixed only the section headers (3 changes) but not the inline references further down (~14 additional mismatches).
- Each quality audit rediscovers the remaining inline references.
- Fix: Always grep the entire file for ALL tier label patterns, not just section headers.

**Partial-fix trap:**
- Reading only lines 235–275 (the section headers) misses the bulk of the mismatches.
- Always search the full file: `grep -n "T[0-9]" .claude/shared/metrics-definitions.md`

## Results

After full fix (issue #1348, PR #1362):
- 17 total tier label corrections applied across the file
- Both section headers and all inline references corrected
- Verified with grep showing no remaining mismatches

## References

- Issue #1348: 4th recurrence of this fix
- PR #1362: Full fix (section headers + inline references)
- PR #1345: Partial fix (section headers only, caused recurrence)
- Authoritative source: `CLAUDE.md` tier table
