# Session Notes: Repository Audit Count Reconciliation

**Date**: 2026-03-07
**Project**: HomericIntelligence/ProjectOdyssey
**Session type**: Comprehensive repository audit + priority fix implementation

## Objective

Apply top 5 priority fixes from a comprehensive repository audit of ProjectOdyssey
(~197,500 lines Mojo, 489 files, grade B overall). Priority 1 was reconciling count
mismatches across documentation — agents (3 different numbers), skills (3 different numbers).

## Audit Findings

| Entity | CLAUDE.md | hierarchy.md | agents/README.md | Actual (disk) |
| -------- | ----------- | -------------- | ------------------ | --------------- |
| Agents | 42 | 37 | 42 | 31 |
| Skills | 82 | — | — | 58 |

Three different numbers for agents across three files. Skills claimed "82 total" but 58
actual skill definitions exist.

## Investigation Steps

1. `ls .claude/agents/ | wc -l` → 32 (but includes `templates/` dir)
2. `ls .claude/agents/*.md | xargs -I{} basename {} .md | sort` → 31 agent files listed
3. `ls .claude/skills/ | wc -l` → 61 (includes SKILL_FORMAT_TEMPLATE.md + tier-1/ + tier-2/)
4. 61 - 1 (template) - 2 (tier dirs) = 58 actual skills
5. Cross-checked README.md agent list against disk → found 12 MISSING entries

## Missing Agents (existed in docs, not on disk)

These were likely removed in a consolidation effort but the README was not updated:

- implementation-review-specialist
- documentation-review-specialist
- safety-review-specialist
- performance-review-specialist
- algorithm-review-specialist
- architecture-review-specialist
- data-engineering-review-specialist
- paper-review-specialist
- research-review-specialist
- dependency-review-specialist
- senior-implementation-engineer
- junior-implementation-engineer

## Files Updated

1. `CLAUDE.md` — 3 changes: "42 agents"→"31", "All 42"→"All 31", "82 total"→"58 total", "82+"→"58"
2. `agents/README.md` — total "42"→"31", level 3 "(22 agents)"→"(13 agents)", removed 12 non-existent stubs,
   level 4 "(6 agents)"→"(5 agents)" (removed senior-implementation-engineer),
   level 5 "(3 agents)"→"(2 agents)" (removed junior-implementation-engineer)
3. `agents/hierarchy.md` — table row L3: 17→13, L4: 6→5, L5: 3→2, total: 37→31, breakdown updated
4. `docs/dev/skills-architecture.md` — "35+"→"58"

## Key Lesson

Never trust any single doc for entity counts. Always count on disk first:

```bash
ls .claude/agents/*.md | wc -l    # agents
ls .claude/skills/ | grep -v "\.md\|^tier-" | wc -l  # skills
```

Then search ALL docs for claims and update each one.

## Other Fixes in Same PR

The PR also included:
1. Dockerfile layer caching (dep manifests before `pixi install`, source after)
2. Security CI: removed `continue-on-error` from Semgrep SAST and dependency review

PR: https://github.com/HomericIntelligence/ProjectOdyssey/pull/3659