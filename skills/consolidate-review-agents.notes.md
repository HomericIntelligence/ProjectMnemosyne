# Session Notes: consolidate-review-agents

## Session Context

- **Date**: 2026-03-05
- **Issue**: ProjectOdyssey #3144 — [P1-1] Consolidate review specialist agents (13 → 5)
- **Branch**: 3144-auto-impl
- **PR created**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/3319

## Objective

Reduce 13 code review specialist agents to 5 by merging 10 overlapping specialists into
`general-review-specialist.md`. Keep mojo-language, security, test, and orchestrator as-is.

## What Was Merged

10 agents deleted:
- algorithm-review-specialist.md
- architecture-review-specialist.md
- data-engineering-review-specialist.md
- dependency-review-specialist.md
- documentation-review-specialist.md
- implementation-review-specialist.md
- paper-review-specialist.md
- performance-review-specialist.md
- research-review-specialist.md
- safety-review-specialist.md

## Steps Taken

1. Read all 10 agent files to understand their structure and scope
2. Read code-review-orchestrator.md and agents/hierarchy.md for reference update targets
3. Created general-review-specialist.md combining all 10 domains
4. Deleted 10 merged files via `git rm`
5. Updated code-review-orchestrator.md: delegates_to, decision matrix, routing table, delegates section
6. Updated agents/hierarchy.md: Level 3 count, total count, breakdown
7. Ran `python3 tests/agents/validate_configs.py .claude/agents/` — ALL VALIDATIONS PASSED
8. Ran `pixi run pre-commit run --all-files` — all hooks passed
9. Committed and pushed; PR #3319 created with auto-merge enabled

## Key Observations

All 10 merged agents were structurally identical:
- Same YAML: `tools: Read,Grep,Glob`, `model: sonnet`, `level: 3`, `phase: Cleanup`
- Identical hooks blocks (block Edit, Write, Bash)
- Identical output location and feedback format references
- Each had a 10-item checklist and one example

The only substantive difference between them was their review domain checklist.

## Error Encountered

The `Edit` tool requires the file to have been read using the `Read` tool in the current
conversation. Reading via Bash (`sed`) does not satisfy this requirement. Solution: always
use the `Read` tool explicitly even when you've seen content via other means.

## Validation Results

```
python3 tests/agents/validate_configs.py .claude/agents/
ALL VALIDATIONS PASSED

pixi run pre-commit run --all-files
Check for deprecated List[Type](args) syntax.............................Passed
Ruff Format Python.......................................................Passed
Ruff Check Python........................................................Passed
Markdown Lint............................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check YAML...............................................................Passed
```

## Metrics

- Files deleted: 10
- Files created: 1
- Files updated: 2
- Net line change: -766 lines
- Total agent count: 44 → 35
- Review specialist count: 13 → 5