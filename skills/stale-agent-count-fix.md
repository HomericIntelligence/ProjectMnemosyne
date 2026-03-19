---
name: stale-agent-count-fix
description: 'Fix stale agent count references in documentation after agents are deleted
  or converted to skills. Use when: agent files are removed/converted and doc counts
  are out of sync.'
category: documentation
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | stale-agent-count-fix |
| **Category** | documentation |
| **Context** | ML Odyssey / ProjectOdyssey agent system |
| **Trigger** | Agents deleted or converted to skills, leaving stale count references |
| **Outcome** | All agent count references updated and tracking docs annotated |

## When to Use

- After deleting agent `.md` files from `.claude/agents/`
- After converting agents to skills (agent files removed, skill files added)
- When `CLAUDE.md` references an agent count that doesn't match `ls .claude/agents/*.md | wc -l`
- When tracking docs (e.g. `docs/dev/agent-claude4-update-status.md`) still list files that no longer exist

## Verified Workflow

1. **Verify actual agent count**:

   ```bash
   ls .claude/agents/*.md | wc -l
   # Note the actual count
   ```

2. **Find all stale count references**:

   ```bash
   grep -rn "<old-count> agents" CLAUDE.md agents/hierarchy.md agents/README.md
   ```

3. **Update CLAUDE.md** — typically two locations:
   - Quick Links section: `- [Agent Configurations](/.claude/agents/) - N agents`
   - Agent Hierarchy section: `- All N agents with roles and responsibilities`

   Use the `Edit` tool with exact string replacement (not sed/awk).

4. **Update tracking docs** — annotate deleted entries rather than removing them outright:

   ```markdown
   - ~~`.claude/agents/deleted-agent.md`~~ — converted to skill
   ```

   This preserves history while making the status clear.

5. **Verify no stale refs remain**:

   ```bash
   grep -n "<old-count> agents" CLAUDE.md
   # Expected: no output
   ```

6. **Run pre-commit on changed files** (skip mojo-format if GLIBC incompatible):

   ```bash
   pre-commit run --all-files
   # mojo-format may fail due to GLIBC version mismatch — this is pre-existing, not caused by doc changes
   # All other hooks (markdownlint, trailing-whitespace, end-of-file-fixer, check-yaml) must pass
   ```

7. **Run agent validation**:

   ```bash
   python3 tests/agents/validate_configs.py .claude/agents/
   # Expected: ALL VALIDATIONS PASSED
   ```

8. **Commit**:

   ```bash
   git add CLAUDE.md docs/dev/agent-claude4-update-status.md
   git commit -m "fix: update stale agent count references (N → M agents)"
   ```

## Key Parameters

| Parameter | Value |
|-----------|-------|
| Files to check | `CLAUDE.md`, `agents/hierarchy.md`, `agents/README.md`, `docs/dev/*.md` |
| Count verification | `ls .claude/agents/*.md \| wc -l` |
| Validation command | `python3 tests/agents/validate_configs.py .claude/agents/` |
| Edit tool | Use `Edit` (exact string), not `sed` |
| Tracking doc style | Strikethrough + annotation, not deletion |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Files to check | `CLAUDE.md`, `agents/hierarchy.md`, `agents/README.md`, `docs/dev/*.md` |
| Count verification | `ls .claude/agents/*.md \| wc -l` |
| Validation command | `python3 tests/agents/validate_configs.py .claude/agents/` |
| Edit tool | Use `Edit` (exact string), not `sed` |
| Tracking doc style | Strikethrough + annotation, not deletion |
| Pre-commit runner | `pre-commit run --all-files` (not `just pre-commit-all`) |
| Expected validation result | `ALL VALIDATIONS PASSED` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `just pre-commit-all` | Used `just` command runner for pre-commit | `just` not in PATH in this environment | Use `pre-commit run --all-files` directly |
| Expecting mojo-format to pass | Ran full pre-commit suite | `mojo` binary requires GLIBC 2.32-2.34, host only has older version | This is a pre-existing env limitation; only non-Mojo hooks matter for doc-only changes |
| Deleting tracking doc entries outright | Removing lines 95-96 from status doc | Would lose historical context of what was converted | Use strikethrough annotation instead: `~~file~~` — converted to skill |
