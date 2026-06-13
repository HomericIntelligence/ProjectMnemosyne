---
name: audit-finding-read-adr-before-planning
description: "When an audit finding cites an ADR, read the ADR before planning. Use when: (1) an audit finding references an architectural decision record, (2) a finding describes a structural smell and a remedy, (3) a plan would involve large structural refactors to a well-established codebase."
category: architecture
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [adr, audit, planning, architecture-decision-record, remediation]
---

# Audit Finding: Read the ADR Before Planning

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Plan a correct remedy for an audit finding that cited an existing ADR |
| **Outcome** | Round 1 proposed wrong remedy (physical decomposition); Round 2 correctly identified documentation-only fix |
| **Verification** | unverified |

## When to Use

- An audit finding cites an architectural decision record (ADR) by name or path
- A finding says "X is a smell" but also describes a remedy or points to a design doc
- The plan would involve a large structural refactor (moving modules, creating sub-packages)
- An issue body contains explicit remedy language like "install-boundary (not decomposition) remedy"

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Step 1: Read the cited ADR in full
cat docs/adr/<cited-adr>.md

# Step 2: Check if the ADR's remedy is already implemented
grep -A5 'optional-dependencies' pyproject.toml | grep <package-name>
pixi run pytest tests/unit/validation/test_automation_boundary.py -v

# Step 3: Measure actual on-disk LoC (don't trust stale audit figures)
find hephaestus -name '*.py' | xargs wc -l | tail -1
find hephaestus/automation -name '*.py' | xargs wc -l | tail -1

# Step 4: Re-read the issue body for explicit remedy language
# Look for phrases like "(not decomposition)", "install-boundary remedy", "already implemented"
```

### Detailed Steps

1. **Read the cited ADR first** — before writing a single line of plan, read the ADR referenced in the finding. Pay attention to: (a) what problem it solved, (b) what remedy it prescribed, (c) what alternative remedies it explicitly rejected.

2. **Check whether the ADR remedy is already implemented** — look for the extra in `pyproject.toml`, boundary tests passing in CI, gating imports in `__init__.py`. If the remedy is already implemented, the correct plan is documentation-only.

3. **Re-read the issue body carefully for explicit remedy language** — audit findings often contain the answer. Phrases like "install-boundary (not decomposition) remedy" or "with the X approach (not Y)" are authoritative.

4. **Measure actual on-disk figures** before updating any documentation — stale audit figures can be months out of date. Use `find ... | xargs wc -l` to get current numbers.

5. **Decide: code change or docs update?**
   - If remedy is already implemented → plan is documentation update only (update stale figures, close the finding)
   - If remedy is NOT implemented → plan implements the ADR's decision, not an alternative the ADR rejected

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Round 1: Physical decomposition | Proposed moving 50 modules into 8 sub-packages with `import *` shims | ADR-0001 explicitly rejected decomposition as remedy; shims broken without `__all__`; relative imports break on move | Read the cited ADR before planning; the issue body often contains the answer |
| Round 1: `import *` shims | `from subpkg.module import *` as backward-compat shims | 40/50 modules have no `__all__`; private symbols silently dropped | Audit `__all__` coverage before any wildcard-import strategy |
| Round 1: `git mv` without import rewrite | Claimed "no logic changes" after moving modules | Every moved module uses relative imports that break after directory change | `git mv` is never sufficient for Python module moves; always audit relative imports first |
| Round 1: Stale file count | Used audit figure of 52 files | Actual on-disk count was 50; audit was dated | Always measure on disk before referencing file counts |

## Results & Parameters

```bash
# ProjectHephaestus issue #1177 — actual measurements (2026-06-13)
# Total Python LoC in hephaestus/
find hephaestus -name '*.py' | xargs wc -l | tail -1
# → 48,522 lines

# automation/ LoC
find hephaestus/automation -name '*.py' | xargs wc -l | tail -1
# → 26,125 lines (53.9% of total)

# ADR stale figures (at time of writing): 19,726 / 41,034 = 48%
# Actual ratio: 26,125 / 48,522 = 53.9%

# Confirm ADR remedy is already in place
grep -A5 '\[project.optional-dependencies\]' pyproject.toml | grep automation
# → automation = [...]  ← remedy implemented

# ADR location
cat docs/adr/0001-automation-library-boundary.md
# Lines 51-59 explicitly reject physical decomposition as remedy
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1177 planning round 1 vs round 2 | Two-round plan iteration; Round 1 NOGO, Round 2 approved |
