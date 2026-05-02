# Session Notes: update-stale-agent-references

## Date
2026-03-07

## Issue
GitHub issue #3323 — "Verify no remaining cross-references to deleted review agents"
Follow-up from #3144 (consolidate 13 review specialist agents → 5)

## Objective
After deleting 10 review specialist agent files in #3144, verify and fix any remaining
cross-references in other files that still point to the deleted agent names.

## Deleted agents (from issue #3144)
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

## Surviving agents (kept as-is)
- general-review-specialist.md (consolidated replacement)
- mojo-language-review-specialist.md
- security-review-specialist.md
- test-review-specialist.md
- code-review-orchestrator.md

## Steps taken

1. Read .claude-prompt-3323.md for task description
2. Read issue #3144 via `gh issue view 3144` to understand which agents were deleted
3. Ran grep across all *.md files for all 10 deleted agent names
4. Found ONE file with stale references:
   - `docs/dev/agent-claude4-update-status.md` (lines 69-82)
   - This is a tracking doc that listed agents needing Claude 4 best-practice updates
5. Read the file to understand context (a "Review Specialists (10):" list)
6. Edited the section: replaced 10-item deleted list with 4-item current list
7. Re-ran grep to confirm zero stale references
8. Committed and pushed; created PR #3942

## Key finding
The `.claude/agents/` directory and `agents/hierarchy.md` had already been cleaned up
by the original consolidation PR. Only the status tracking doc in `docs/dev/` had
been missed.

## Commit
670d4e9c — "fix(docs): update agent-claude4-update-status to reflect consolidated review specialists"

## PR
https://github.com/HomericIntelligence/ProjectOdyssey/pull/3942
