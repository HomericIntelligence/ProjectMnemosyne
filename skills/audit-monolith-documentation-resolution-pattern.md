---
name: audit-monolith-documentation-resolution-pattern
description: "Resolve audit nitpicks for monolithic code by documenting verified design rationale. Use when: (1) auditor questions code organization as violation of SRP, (2) splitting vs. documenting trade-off exists, (3) design decision lacks permanent record."
category: documentation
date: 2026-06-05
version: "1.0.0"
verification: verified-local
tags: [audit, documentation, architecture-decision, monolith, nitpick]
---

# Audit Monolith Documentation Resolution Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-05 |
| **Objective** | Resolve audit nitpicks that question code organization (monolithic scripts) by documenting verified design rationale instead of splitting. |
| **Outcome** | Successful — issue #792 resolved via documented architecture decision; PR #984 merged with all policy gates passing. |
| **Verification** | verified-local (end-to-end execution + PR merge; CI gates passed) |

## When to Use

- Audit finding questions SRP violation in monolithic code organization
- Nitpick-level severity (not critical)
- Splitting has tangible cost (replicating shared state, building dispatcher)
- Design decision is sound and defensible (can be fact-verified)
- Design lacks permanent record in repo (codebase doc gap)

## Verified Workflow

### Quick Reference

**8-step implementation pattern:**

1. Verify claims at planning time (grep-based: check actual usage, not capability)
2. Identify the three pillars justifying the monolith (shared state, unified filter, aggregated results)
3. Add brief Architecture comment block to source (14 lines, points to detailed doc)
4. Create standalone architecture decision record (docs/ARCHITECTURE_FOCUS.md, ~50 lines)
5. Include accuracy caveats (e.g., "no callers currently source this"; defensive only)
6. Run pre-commit validation (shellcheck, linters)
7. Smoke test the code (bash -n, --help, etc.)
8. Verify zero external callers after commit (negative grep that fails if callers appear)

### Detailed Steps

**Step 1: Fact-Verify the Design at Planning Time**

Don't defer verification to implementation. Use grep to check actual usage patterns:

```bash
# Example: verify no callers source the script (not just capability)
grep -rn "source.*install\.sh\|\. .*install\.sh" scripts/ docs/ .github/ README.md CONTRIBUTING.md justfile 2>/dev/null | grep -v "install_helpers" | grep -v "^scripts/shell/install.sh:"
```

If the result is empty, the sourceable-contract claim is **defensive, not load-bearing**. Add a caveat in the doc: "Although the guard permits sourcing, **no callers currently source it**."

**Step 2: Identify Three Pillars Justifying the Monolith**

For scripts with shared state, list the three things that make splitting expensive:

1. **Shared state** — counters, flags, globals that all sections read/increment (e.g., `_PASS`, `_FAIL`, `_WARN`, `_SKIP`)
2. **Unified filter** — single argument or config applied uniformly (e.g., `--role worker|control|all`)
3. **Aggregated results** — single trailing summary that combines outputs from all sections

If splitting would require replicating these in N children or building a dispatcher, document that cost.

**Step 3: Add Architecture Comment Block to Source**

Insert 14-line comment block at the top-level (after usage/exit-codes, before main logic):

```bash
# Architecture (see docs/INSTALLER_ARCHITECTURE.md):
#   12 numbered sections intentionally live in this one file.
#   The SRP boundary that matters is already in scripts/shell/lib/install_helpers.sh.
#   The sections themselves share three pieces of state:
#     1. _PASS/_FAIL/_WARN/_SKIP counters (defined in lib/install_helpers.sh)
#     2. The --role filter via should_check_worker / should_check_control
#     3. The single trailing summary that aggregates results across sections
#   A per-tool split would require replicating these in every child or
#   threading them through a dispatcher.
```

**Step 4: Create Standalone Architecture Decision Record**

File: `docs/INSTALLER_ARCHITECTURE.md` (or similar, ~50 lines)

Sections:
- **Purpose** — what the script does and where it's invoked
- **The SRP Boundary That Exists** — what was already extracted (e.g., lib/install_helpers.sh)
- **Why the Sections Stay Together** — the three pillars with explanations
- **What the Script Is *Not*** — the accuracy caveat (e.g., "no callers source it; defensive guard only")
- **Triggers That Would Justify Revisiting** — concrete conditions to split later (size, independent entry points, role-gating change, actual sourcing caller)

**Step 5: Include Accuracy Caveats**

If a design claim turned out to be unverified (e.g., "we keep this monolithic because callers source it for helpers"), **demote it to a caveat** in the "What the Script Is *Not*" section:

> Although the source guard at install.sh:46–48 permits sourcing, **no callers currently source it**. This guard is defensive infrastructure with no actual consumer.

This prevents future auditors from being misled by inherited claims.

**Step 6: Run Pre-Commit Validation**

```bash
pre-commit run --files scripts/shell/install.sh docs/INSTALLER_ARCHITECTURE.md
```

Shellcheck, markdownlint, and other hooks must pass. Re-run once if auto-fixers touched files.

**Step 7: Smoke Test the Code**

```bash
bash -n scripts/shell/install.sh                # Parse check
bash scripts/shell/install.sh --help            # CLI still works
```

**Step 8: Verify Zero External Callers**

After committing, run a negative grep that fails if external callers appear:

```bash
! grep -rn "source.*install\.sh" scripts/ docs/ .github/ README.md CONTRIBUTING.md justfile \
  | grep -v "docs/INSTALLER_ARCHITECTURE.md" \
  | grep -v "^scripts/shell/install.sh:" \
  | grep -v "install_helpers"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Sourceable-contract as justification | Cited the source guard (`if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; return 0`) as a reason to keep the monolith | Unverified claim — grep showed zero actual callers across the repo. The guard is defensive infrastructure, not a load-bearing design pillar. Baking an unverified claim into permanent docs would mislead future auditors. | Always verify claims before documenting them. Mechanism (capability to source) ≠ Usage (actual callers). Use grep to check real usage patterns. Include caveats: "Although X is possible, no callers currently do X." |
| Conditional CONTRIBUTING.md edit | Plan proposed editing docs/CONTRIBUTING.md only if a "Scripts" section already exists | Resolved at planning time: a read of CONTRIBUTING.md showed no such section exists. YAGNI applies; adding a new section for a nitpick violates it. | Resolve definitional questions at planning time, not deferring to implementation. Use git to check current state before creating conditional logic. |
| Mechanism-based verification | Attempted to verify sourceable-contract by running `bash -c 'source scripts/shell/install.sh && type has_cmd'` | Proof of mechanism (script can be sourced, functions are defined) is not proof of usage (actual callers doing so). This test proved the script *can* be sourced but said nothing about whether it *is* sourced anywhere in the repo. | Verify usage patterns with grep (searches the codebase for actual callers), not capability tests. Don't confuse "this feature is technically possible" with "this feature is actively used." |

## Results & Parameters

### Architecture Comment Block Template

```bash
# Architecture (see docs/INSTALLER_ARCHITECTURE.md):
#   12 numbered sections (Section 0 … Section 11 + Summary)
#   intentionally live in this one file. The SRP boundary that matters is
#   already in scripts/shell/lib/install_helpers.sh, which extracts reusable
#   primitives. The sections themselves share three pieces of state that
#   make splitting expensive:
#     1. _PASS/_FAIL/_WARN/_SKIP counters (defined in lib/install_helpers.sh)
#     2. The --role filter via should_check_worker / should_check_control
#     3. The single trailing summary that aggregates results across sections
#   A per-tool split would require replicating these in every child or
#   threading them through a dispatcher.
```

### Standalone Doc Sections

**Purpose** — Brief statement of what the script does and where invoked
**The SRP Boundary That Exists** — List extraction that already happened (e.g., lib/install_helpers.sh with colors, counters, has_cmd, apt_install)
**Why Sections Stay Together** — Three paragraphs explaining each pillar (shared counters, unified filter, aggregated results)
**What the Script Is *Not*** — Accuracy caveat with verification command (grep result showing zero callers)
**Triggers for Revisiting** — Bullet list: size (>150 lines per section), independent entry points, per-section role-gating, verified external caller

### Verification Commands (Copy-Paste Ready)

```bash
# Check 1: Architecture block present
grep -A2 "^# Architecture" scripts/shell/install.sh

# Check 2: Doc lists the three pillars
grep -E "_PASS/_FAIL|--role filter|trailing summary" docs/INSTALLER_ARCHITECTURE.md

# Check 3: Accuracy caveat present
grep -E "no callers currently source|defensive" docs/INSTALLER_ARCHITECTURE.md

# Check 4: Script syntax valid
bash -n scripts/shell/install.sh

# Check 5: No external source-callers
! grep -rn "source.*install\.sh" scripts/ docs/ .github/ README.md CONTRIBUTING.md justfile \
  | grep -v "docs/INSTALLER_ARCHITECTURE.md" \
  | grep -v "^scripts/shell/install.sh:" \
  | grep -v "install_helpers"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #792 (audit nitpick S13) | Monolithic installer (751 lines, 12 sections). Resolved via documented architecture decision. PR #984 merged with all policy gates passing (signed commit, label, auto-merge, body format). |
