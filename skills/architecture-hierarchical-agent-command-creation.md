---
name: architecture-hierarchical-agent-command-creation
description: "Create a Claude Code custom command that orchestrates hierarchical multi-agent
  workflows with model tier assignments. Use when: (1) building a reusable /command
  that spawns sub-agents at different model tiers (Opus/Sonnet/Haiku), (2) integrating
  ProjectOdyssey's 6-level agent hierarchy into a portable command, (3) implementing
  wave-based parallel agent execution with approval gates."
category: architecture
date: 2026-03-25
version: 1.0.0
user-invocable: false
verification: verified-local
tags:
  - claude-code
  - agent-hierarchy
  - model-tiers
  - custom-command
  - orchestration
---

# Hierarchical Agent Command Creation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Create a reusable Claude Code custom command (`/myrmidon-swarm`) that decomposes complex tasks into hierarchical agent trees with automatic model tier assignment (Opus for orchestrators, Sonnet for specialists, Haiku for executors) |
| **Outcome** | Success - 387-line command file installed at `~/.claude/commands/myrmidon-swarm.md`, immediately discoverable in Claude Code autocomplete |
| **Verification** | verified-local |

## When to Use

- Building a Claude Code custom command that spawns sub-agents at different model tiers
- Porting ProjectOdyssey's 6-level agent hierarchy (L0-L5) into a portable, repo-agnostic command
- Implementing wave-based parallel agent execution with mandatory user approval gates
- Integrating ProjectMnemosyne `/advise` auto-invocation into a workflow command
- Creating commands that follow the XML-structured prompt pattern from `repo-analyze.md`

## Verified Workflow

### Quick Reference

```bash
# Command file location
~/.claude/commands/<command-name>.md

# YAML frontmatter (only description field needed)
---
description: Brief description of what the command does
---

# Invocation
/<command-name> <arguments>
```

### Detailed Steps

1. **Study the existing command pattern** — Read `~/.claude/commands/repo-analyze.md` for the established structure: YAML frontmatter with `description` field, then markdown body with XML-structured sections (`<system>`, `<task>`, etc.)

2. **Study the agent hierarchy pattern** — Read ProjectOdyssey's agent configs at `.claude/agents/`:
   - `chief-architect.md` (L0, Opus) — strategic decisions, delegation
   - `foundation-orchestrator.md` (L1, Sonnet) — section coordination
   - `implementation-specialist.md` (L3, Sonnet) — component expertise
   - `implementation-engineer.md` (L4, Haiku) — execution

3. **Define model tier assignments** — Map agent levels to Claude models:

   | Tier | Levels | Model | Role |
   |------|--------|-------|------|
   | Orchestrator | L0, L1 | `model: "opus"` | Strategic decisions, coordination |
   | Specialist | L2, L3 | `model: "sonnet"` | Design, analysis, code review |
   | Executor | L4, L5 | `model: "haiku"` | Implementation, boilerplate |

4. **Structure the command file** with XML sections (~300-400 lines):
   - `<system>` — Orchestrator identity and behavior
   - `<agent_tiers>` — Tier definitions with decision flowchart
   - `<workflow>` — 5-phase workflow (Plan, Test, Implementation, Package, Cleanup)
   - `<delegation_rules>` — Agent spawning, wave execution, escalation
   - `<integrations>` — Mnemosyne, AI Maestro, Scylla
   - `<constraints>` — Safety rules, scope control
   - `<agent_prompt_template>` — Template for sub-agent prompts
   - `<output_format>` — Status reporting format

5. **Implement the approval gate** — Phase 1 (Plan) must present a decomposition table and WAIT for user approval before spawning any agents. Use explicit stop instruction: "STOP HERE. Ask the user."

6. **Implement auto-invocation of /advise** — Use the Skill tool:
   ```
   Skill(skill: "skills-registry-commands:advise", args: "<task description>")
   ```

7. **Use Agent tool with model parameter** for spawning tiered sub-agents:
   ```
   Agent(
     model: "sonnet",
     isolation: "worktree",
     description: "5-word summary",
     prompt: "... full self-contained instructions ..."
   )
   ```

8. **Write the file** to `~/.claude/commands/<name>.md` and verify it appears in autocomplete

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Initial model mapping from ProjectOdyssey | Used Odyssey's exact mapping (only L0=Opus, L1-L3=Sonnet, L4-L5=Haiku) | User wanted Orchestrators (L0+L1) on Opus, not just L0 | Always confirm model tier assignments with the user — the command owner's preferences may differ from the source project |
| Generic command name | Proposed `/agentic-workflow` as the command name | User wanted `/myrmidon-swarm` to fit the Homeric theme | Ask about naming preferences — ecosystem naming conventions matter |
| Skip approval gate | Considered autonomous execution for speed | User explicitly wanted mandatory approval before spawning agents | Default to requiring approval for commands that spawn multiple agents — the cost of misunderstood tasks is high |

## Results & Parameters

### Command File Structure

```yaml
# ~/.claude/commands/myrmidon-swarm.md
---
description: Summon the Myrmidon swarm — hierarchical agent delegation with Opus/Sonnet/Haiku model tiers
---

# Sections (XML-structured):
# <system>            — L0 orchestrator identity (~30 lines)
# <agent_tiers>       — 3 tiers with decision flowchart (~35 lines)
# <workflow>          — 5-phase workflow with approval gate (~75 lines)
# <delegation_rules>  — wave execution, escalation (~55 lines)
# <integrations>      — Mnemosyne, AI Maestro, Scylla (~40 lines)
# <constraints>       — safety rules, tooling preferences (~30 lines)
# <agent_prompt_template> — reusable template for sub-agents (~40 lines)
# <output_format>     — status reporting (~30 lines)
# Total: ~387 lines, ~14KB
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| File location | `~/.claude/commands/` (user-level) | Works across all repos without per-repo setup |
| Prompt structure | XML sections in markdown | Matches `repo-analyze.md` convention, gives Claude clear semantic boundaries |
| Approval gate | Mandatory in Phase 1 | Prevents wasted compute on misunderstood tasks |
| `/advise` invocation | Auto-invoke via Skill tool | Ensures prior learnings are always consulted |
| Wave sizing | Max 5 agents per wave | Prevents resource exhaustion |
| File conflict prevention | No two agents in same wave touch same file | Prevents merge conflicts |

### Wave-Based Execution Pattern

```
Wave 1: [Independent sub-tasks with no dependencies]
  ↓ wait for all to complete
Wave 2: [Sub-tasks that depend on Wave 1 results]
  ↓ wait for all to complete
Wave N: [Final sub-tasks]
```

Key rules from `wave-based-bulk-issue-triage` skill:
- Use `isolation: "worktree"` for file-modifying agents
- Never `git add -A` — stage specific files
- Never `--no-verify` — fix hook failures
- Max 5 agents per wave

### Integration Points

| Integration | Required? | How |
|-------------|-----------|-----|
| ProjectMnemosyne `/advise` | Yes (auto) | Skill tool invocation in Phase 1 |
| ProjectMnemosyne `/retrospective` | No (suggest) | User decides in Phase 5 |
| AI Maestro | No (detect) | Check for `~/.aimaestro/` directory |
| ProjectScylla T0-T6 | No (when relevant) | Only for agent evaluation tasks |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence ecosystem | Session creating /myrmidon-swarm command | Installed at ~/.claude/commands/myrmidon-swarm.md, 387 lines, appears in autocomplete |
