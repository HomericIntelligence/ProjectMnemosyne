---
name: fix-tier-label-mismatches
description: "Fix incorrect tier labels in ProjectScylla documentation (T3\u2192T2,\
  \ T4\u2192T3, T5\u2192T4 pattern). Use when quality audits flag tier name/number\
  \ mismatches in .claude/shared/metrics-definitions.md or CLAUDE.md tier table references."
category: documentation
date: 2026-03-03
version: 1.0.0
user-invocable: true
---
# Fix Tier Label Mismatches in Documentation

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-03 |
| **Objective** | Fix tier label mismatches in `.claude/shared/metrics-definitions.md` flagged by the March 2026 quality audit (issue #1348) |
| **Outcome** | 19 label corrections across 4 sections; PR #1362 merged |
| **Related Issues** | ProjectScylla #1348 (4th recurrence), #1345 (prior partial fix) |

## Authoritative Tier Table (CLAUDE.md)

| Tier | Name |
|------|------|
| T0 | Prompts |
| T1 | Skills |
| T2 | Tooling |
| T3 | Delegation |
| T4 | Hierarchy |
| T5 | Hybrid |
| T6 | Super |

## When to Use This Skill

Use this skill when:

- A quality audit flags "tier label mismatch" or "incorrect tier numbers" in documentation
- `grep -n "T[0-9]" .claude/shared/metrics-definitions.md` reveals labels like "T3 (Tooling)", "T4 (Delegation)", "T5 (Hierarchy)" — those are off-by-one from the correct table above
- The issue title mentions "fix tier label mismatch" or "T3/T4/T5 → T2/T3/T4"
- A prior PR partially fixed some occurrences but others remained

**Triggers:**

- Issue references `.claude/shared/metrics-definitions.md` with specific wrong lines
- Quality audit marks it as "recurring" — this has appeared in multiple audits
- The word "mismatch" appears with tier names and numbers

## Verified Workflow

### Phase 1: Check What the Issue Says vs What Actually Exists

**Critical**: Prior partial fixes may mean the issue description's line numbers are already correct. Always read the file first.

```bash
# Scan ALL tier label occurrences in the file
grep -n "T[0-9]" .claude/shared/metrics-definitions.md
```

The issue description said lines 239, 253, 267 were wrong — those were already fixed by PR #1345. The real remaining mismatches were elsewhere.

### Phase 2: Identify All Remaining Mismatches

Cross-reference each `T[0-9]` occurrence against the authoritative tier table:

| Pattern That Is Wrong | Correct Replacement |
|----------------------|---------------------|
| `T2 (Skills)` | `T1 (Skills)` |
| `T3 (Tooling)` | `T2 (Tooling)` |
| `T4 (Delegation)` | `T3 (Delegation)` |
| `T5 (Hierarchy)` | `T4 (Hierarchy)` |
| `T2 skill instructions` | `T1 skill instructions` |
| `T3 JSON tool definitions` | `T2 JSON tool definitions` |
| `T4/T5 coordination` | `T3/T4 coordination` |

### Phase 3: Fix All Occurrences with Targeted Edits

Use the `Edit` tool with exact string replacement. Never rewrite whole sections.

**Sections that contained mismatches in this audit:**

1. **`## Future Instrumentation` section** (subsection headers):
   - `### 1. Tool Call Success Rate (T3 - Tooling)` → `(T2 - Tooling)`
   - `### 2. Tool Utilization (T3 - Tooling)` → `(T2 - Tooling)`
   - `### 3. Task Distribution Efficiency (T4 - Delegation)` → `(T3 - Delegation)`
   - `### 4. Correction Frequency (T5 - Hierarchy)` → `(T4 - Hierarchy)`
   - `### 5. Iterations to Success (T5 - Hierarchy)` → `(T4 - Hierarchy)`

2. **`## Token Tracking` section** (header, body, and interpretation):
   - Section header: `T2 vs T3 Analysis` → `T1 vs T2 Analysis`
   - Body text: `T2 (Skills) and T3 (Tooling)` → `T1 (Skills) and T2 (Tooling)`
   - `Total tokens consumed by tool schemas (T3+)` → `(T2+)`
   - `T3 architectures load JSON schemas` → `T2 architectures`
   - `no schema overhead (pure T2)` → `(pure T1)`

3. **Component Cost table** (9 rows):
   ```
   T2 skill instructions    → T1 skill instructions
   T2 domain knowledge      → T1 domain knowledge
   T3 JSON tool definitions → T2 JSON tool definitions
   T3 tool invocations      → T2 tool invocations
   T3 tool results          → T2 tool results
   T4/T5 coordination       → T3/T4 coordination
   T4/T5 delegated agents   → T3/T4 delegated agents
   T5 error detection       → T4 error detection
   T5 self-reflection       → T4 self-reflection
   ```

### Phase 4: Final Verification

```bash
# Verify all remaining tier references are correct
grep -n "T[0-9]" .claude/shared/metrics-definitions.md

# Check specific lines that should be fixed
grep -n "T[0-9]\s*(" .claude/shared/metrics-definitions.md
```

Cross-check each remaining hit against the authoritative table. Bare tier numbers in formulas (e.g., `T0`, `T1` in example data) are fine — only named references with `(Name)` parentheticals or `-` dashes need checking.

### Phase 5: Commit and PR

```bash
git add .claude/shared/metrics-definitions.md
git commit -m "fix(docs): Fix all tier label mismatches in metrics-definitions.md

Fix recurring tier label mismatches across multiple sections:
- Future Instrumentation section: T3→T2, T4→T3, T5→T4 in headers
- Token Tracking section: T2→T1, T3→T2 throughout
- Component Cost table: T2→T1, T3→T2, T4/T5→T3/T4, T5→T4

Closes #<issue>"

git push -u origin <branch>
gh pr create --title "fix(docs): Fix all tier label mismatches in metrics-definitions.md" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Key Observations

1. **Prior partial fixes are common** — this issue recurred 4 times across March 2026 audits. Each prior fix corrected some but not all occurrences. Always do a full file scan with `grep -n "T[0-9]"`.

2. **Token Tracking section is a hotspot** — the "Token Efficiency Chasm" analysis between Skills (T1) and Tooling (T2) is often written with the old numbering (T2 vs T3) because it was created before the tier renumbering.

3. **Component Cost table is another hotspot** — the 9-row table mapping component types to tier numbers uses the old numbering throughout. Fix all 9 rows together in a single `Edit` call.

4. **Named tier references only need fixing** — bare tier numbers in formula examples (e.g., `T0: composite_median = 0.70`) are data, not tier labels, and are correct as-is.

5. **Pre-commit passes instantly** — only markdown files change, so mypy/ruff/pip-audit all skip. The commit is fast.

## Results

| File | Changes Applied |
|------|----------------|
| `.claude/shared/metrics-definitions.md` | 19 label fixes across 4 sections: Future Instrumentation headers (5), Token Tracking section (5), Component Cost table (9) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1348, PR #1362 | March 2026 4th quality audit; 19 corrections applied |
