# Session Notes: delegates_to File Existence Check

## Date
2026-03-15

## Issue
GitHub issue #3965 — Add CI check to enforce delegates_to references exist as files
Follow-up from #3333 (junior-documentation-engineer stale reference discovered manually)

## Problem Statement

Agent `.md` files in `.claude/agents/` use a `delegates_to` YAML frontmatter field to declare
which sub-agents they delegate to. When an agent is renamed or deleted, these references can
go stale without any automated detection. The issue requested a CI validation step that would
automatically catch broken references on every PR.

## Approach Taken

1. Explored existing `validate_configs.py` to understand the `AgentConfigValidator` class
2. Searched all `delegates_to` fields with `grep -r "delegates_to" .claude/agents/`
3. Found stale reference: `security-specialist.md` had `senior-implementation-engineer`
4. Added `existing_agents` set to `__init__` (one glob call, stores stems)
5. Added inline list parser in `_validate_frontmatter` — hard error for missing refs
6. Fixed the stale reference in security-specialist.md
7. Wrote 16 pytest tests in `test_validate_delegates_to.py`
8. All 54 agent tests passed

## Key Decision: error vs warning

Stale `delegates_to` references are treated as hard **errors** (not warnings) because:
- They represent definite bugs in the delegation chain
- Warnings don't fail CI
- The whole point is to gate PRs on this check

## Key Decision: inline list format

The project's agent files use YAML inline list syntax `[a, b, c]` for `delegates_to`.
The validator parses this by stripping `[` `]` and splitting on `,`. This matches
the actual format in all 29 agent files.

## Stale Reference Found

`security-specialist.md`:
- Before: `delegates_to: [implementation-engineer, senior-implementation-engineer, test-engineer]`
- After: `delegates_to: [implementation-engineer, test-engineer]`

`senior-implementation-engineer.md` does not exist in `.claude/agents/`.

## PR

https://github.com/HomericIntelligence/ProjectOdyssey/pull/4843