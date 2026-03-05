---
name: agent-tier-consolidation
description: "Consolidate over-segmented agent tiers in a hierarchical agent system. Use when: multiple agents share the same scope and only differ by seniority, agent tiers are over-segmented for the project stage, or the hierarchy needs simplification without losing capability."
category: architecture
date: 2026-03-05
user-invocable: false
---

# Agent Tier Consolidation

## Overview

| Field | Value |
|-------|-------|
| **Objective** | Merge redundant agent tiers into a single comprehensive agent |
| **Trigger** | 3+ agents with same scope differentiated only by complexity level |
| **Outcome** | Fewer agents, same coverage, cleaner hierarchy |
| **Time** | ~15 minutes for a 3-to-1 consolidation |
| **Risk** | Low — purely documentation changes, no code execution |

## When to Use

- Three or more "generalist" tiers exist (e.g. senior/regular/junior) for the same phase
- The only distinction between tiers is complexity/seniority, not role or phase
- Project is early-stage and over-segmentation adds overhead without benefit
- `agent-validate-config` reports delegate chains that skip tiers unnecessarily
- Hierarchy diagram shows agents that never get selected because similar agents exist

## Verified Workflow

### Step 1: Inventory agents to consolidate

```bash
ls .claude/agents/*implementation* # or whatever the tier group is
```

Read each file to identify:

- Which capabilities are unique to each tier
- Which skills each tier uses
- What the `delegates_to` / `receives_from` chains look like

### Step 2: Merge into the "middle" agent

Keep the existing middle agent file (e.g. `implementation-engineer.md`) as the target.
Merge unique capabilities from the tiers being deleted:

- From the **senior** tier: performance-critical patterns, SIMD, profiling constraints, advanced examples
- From the **junior** tier: boilerplate/formatting skills, escalation rules, anti-pattern references, simple examples

Update the YAML frontmatter:

```yaml
delegates_to: []        # Remove tier-specific sub-delegation
receives_from: [specialist-agent]
```

Update description to reflect the full complexity spectrum.

### Step 3: Update delegating agents

Any agent that previously listed the deleted tiers in `delegates_to` must be updated:

```yaml
# Before
delegates_to: [senior-implementation-engineer, implementation-engineer, junior-implementation-engineer]

# After
delegates_to: [implementation-engineer]
```

Also update any examples in the delegating agent that referred to tier-specific task routing.

### Step 4: Delete the obsolete tier files

```bash
rm .claude/agents/senior-<name>.md
rm .claude/agents/junior-<name>.md
```

### Step 5: Update hierarchy documentation

In `agents/hierarchy.md`:

- Update the diagram boxes (agent names and counts)
- Update Level Summaries counts
- Update the Agent Count table
- Update historical note if total changed

### Step 6: Validate

```bash
python3 tests/agents/validate_configs.py .claude/agents/
pixi run pre-commit run markdownlint-cli2 --all-files
```

Expect zero errors. Warnings about missing recommended sections are pre-existing and acceptable.

### Step 7: Commit and PR

```bash
git add .claude/agents/ agents/hierarchy.md
git commit -m "refactor(agents): consolidate <name> tiers (N -> M)"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Creating a new merged file | Started writing a new agent file from scratch | Resulted in a thin agent that lost nuance from both tiers | Keep the existing middle-tier file as the base; merge into it rather than rewriting |
| Keeping `delegates_to` unchanged | Left `delegates_to: [senior-..., junior-...]` on the specialist after deleting those agents | `agent-validate-config` would catch dangling references | Always update `delegates_to` on the parent agent immediately after deleting children |
| Bulk-deleting and bulk-updating | Tried to delete all files then fix references | Easy to miss cross-references in examples/prose | Read and update delegating agents before deleting target files |

## Results & Parameters

### Consolidation from ProjectOdyssey issue #3146

**Before**: 4 implementation tiers

```text
implementation-specialist (L3)
  → senior-implementation-engineer (L4)
  → implementation-engineer (L4)
  → junior-implementation-engineer (L5)
  → implementation-specialist (L3, also receives)
```

**After**: 2 tiers

```text
implementation-specialist (L3)
  → implementation-engineer (L4, full spectrum)
```

**Agent count delta**: 44 → 42

**Key merge decisions**:

- Added `mojo-simd-optimize`, `mojo-memory-check` skills from senior tier
- Added `quality-fix-formatting`, `gh-check-ci-status` skills from junior tier
- Added performance-profiling workflow steps from senior tier
- Added anti-pattern reference and escalation rules from junior tier
- Kept two concrete examples: one standard, one performance-critical
- Removed `hooks.PreToolUse` Bash block (junior-only restriction, not needed for consolidated agent)

### Validation output

```text
Total files: 42
Passed: 42
Failed: 0
Total errors: 0
```

### Hierarchy counts to update

| Section | Before | After |
|---------|--------|-------|
| Level 4 count line | "6 agents" | "5 agents" |
| Level 5 count line | "3 types" | "2 types" |
| Agent Count table L4 | 6 | 5 |
| Agent Count table L5 | 3 | 2 |
| Total | 44 | 42 |
| Diagram box L4 | Lists senior + regular | Lists only regular |
| Diagram box L5 | Lists 3 juniors | Lists 2 juniors |
