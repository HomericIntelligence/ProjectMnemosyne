---
name: tooling-claude-plugin-third-party-skill-porting
description: "Port skills from third-party Claude Code plugins into an existing plugin without license violations. Use when: (1) integrating an open-source skill repo like obra/superpowers, (2) deciding which skills to port vs skip vs avoid, (3) adapting external skills to your project's conventions."
category: tooling
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags: [claude-code, plugin, skills, porting, third-party, mit-license, superpowers, hephaestus]
---

# Tooling: Claude Code Plugin Third-Party Skill Porting

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-28 |
| **Objective** | Integrate obra/superpowers methodology skills into ProjectHephaestus without license violations, avoiding duplication of existing capabilities |
| **Outcome** | Successful — 8 additive skills ported, 4 redundant skills skipped, MIT attribution applied, PR #206 opened |
| **Verification** | verified-precommit — PR open, file structure verified, CI not yet confirmed |
| **Source** | HomericIntelligence/ProjectHephaestus#206, https://github.com/obra/superpowers |

## When to Use

- Evaluating whether to adopt skills from an open-source Claude Code plugin (e.g., obra/superpowers)
- Deciding between: install as separate plugin, fork/vendor, or port select skills
- Porting skills that reference hardcoded paths or unknown tooling into your project's conventions
- Applying MIT license attribution when adapting third-party Claude Code skills
- Designing a meta-skill (skill-advisor) as an alternative to SessionStart hooks

## Verified Workflow

> **Warning:** Verified at precommit level only — file structure and YAML validation confirmed, but CI has not yet run. Treat workflow steps as well-reasoned but unconfirmed end-to-end.

### Quick Reference

```bash
# Step 1: Audit source repo
gh repo clone <org>/<repo> /tmp/source-repo
ls /tmp/source-repo/  # look for: SKILL.md files, hooks/, agents/, .claude-plugin/

# Step 2: Overlap analysis — list source skills and compare to yours
ls /tmp/source-repo/  | grep -i "skill\|SKILL"
ls <your-plugin>/skills/

# Step 3: For each skill to port, adapt and create in your skills/ dir
# Step 4: Run validation
python3 scripts/validate_plugins.py

# Step 5: Version bump plugin (minor if <10 skills, major if restructuring)
# Step 6: Update CLAUDE.md with new skill catalog entry
# Step 7: Commit and PR
```

### Detailed Steps

#### 1. Audit the Source Repository

Examine the source plugin's structure before committing to any integration approach:

```bash
gh repo clone <org>/<repo> /tmp/source-repo
ls /tmp/source-repo/
# Look for: SKILL.md files, hooks/hooks.json (SessionStart), agents/, .claude-plugin/
```

Key things to document:
- License (MIT/Apache/GPL — determines attribution requirements)
- Total number of skills
- Presence of SessionStart hooks (conflict risk with your plugin's hooks)
- Hardcoded paths (need adaptation)
- Agent personas (`.md` files in `agents/`)

**obra/superpowers structure** (reference):
- 14 SKILL.md files at repo root
- `hooks/hooks.json` — SessionStart injection (conflict risk)
- `agents/code-reviewer.md` — persona file
- `.claude-plugin/` — plugin registration

#### 2. Integration Approach Decision Tree

Choose one of three approaches:

| Approach | When to Use | Risk |
|---|---|---|
| **Install as separate plugin** | Source skills don't overlap AND hooks don't conflict | SessionStart hook conflicts, routing confusion, double maintenance |
| **Fork/vendor** | Need all skills AND can maintain a fork | High — rapidly evolving repos require ongoing sync |
| **Port select skills** | Only need a subset AND source has hardcoded conventions | Low — only adapt what you need |

**Why "port select skills" won for superpowers:**
- Two plugins competing for the same action space causes skill routing confusion
- superpowers SessionStart hook would conflict with ai-maestro hooks already present
- Only 7 of 14 skills provided additive value (others already covered by myrmidon-swarm, planning, etc.)
- Forking a 120K-star rapidly-evolving repo is unnecessary when only 7 skills are needed

#### 3. Overlap Analysis

For each source skill, classify as: **redundant** (skip) or **additive** (port).

**Redundancy signals:**
- Your plugin already has a skill covering the same workflow
- Your equivalent is superior (more context-aware, integrated with your tooling)

**obra/superpowers overlap analysis result:**

| Superpowers Skill | Decision | Reason |
|---|---|---|
| subagent-driven-development | SKIP | myrmidon-swarm is superior: tiered models, waves, Mnemosyne integration |
| dispatching-parallel-agents | SKIP | Covered by myrmidon-swarm Phase 3 wave execution |
| writing-skills | SKIP | Covered by learn + ProjectMnemosyne advise/learn loop |
| writing-plans / executing-plans | SKIP | Covered by Hephaestus planning skill |
| test-driven-development | PORT | Additive — detailed TDD workflow not in Hephaestus |
| systematic-debugging | PORT | Additive — structured debugging methodology |
| verification-before-completion | PORT | Additive — explicit verification checklist |
| using-git-worktrees | PORT | Additive — worktree patterns not documented |
| finishing-a-development-branch | PORT | Additive — branch cleanup and PR workflow |
| brainstorming | PORT | Additive — structured brainstorm methodology |
| requesting-code-review + receiving-code-review + agents/code-reviewer.md | PORT (merged) | Additive — combined into single code-review skill |
| using-superpowers (meta) | ADAPT | Becomes skill-advisor meta-skill |

#### 4. Adaptation Checklist

When porting each skill, apply all of the following adaptations:

```
[ ] Add Mnemosyne integration: auto-invoke /advise at task start, suggest /learn at end
[ ] Add cross-references to myrmidon-swarm phases where relevant to the skill
[ ] Align git commands: conventional commits, gh pr create, protected-main branch conventions
[ ] Add project tooling refs: pixi run pytest, pixi run mypy, pixi run ruff (replace generic commands)
[ ] Change hardcoded spec paths: docs/superpowers/specs/ → docs/specs/
[ ] Change worktree defaults: <source convention> → /tmp/<project>-<branch>
[ ] Add MIT attribution footer (see Section 5)
[ ] Convert from source format (SKILL.md or raw markdown) to Hephaestus YAML frontmatter format
[ ] Validate with scripts/validate_plugins.py
```

#### 5. MIT License Attribution

Add this footer to every ported skill file:

```markdown
---
*Adapted from [obra/superpowers](https://github.com/obra/superpowers) under MIT License.
Copyright (c) 2025 Jesse Vincent.*
```

Create `skills/THIRD_PARTY_LICENSES.md` with:
- Full MIT license text
- Source repo link and author
- Table mapping each ported skill to its source file
- Date of derivation

#### 6. Meta-Skill vs SessionStart Hook

**Problem:** superpowers injects a skill-advisor prompt via `hooks/hooks.json` SessionStart. This would conflict with ai-maestro hooks.

**Solution:** Convert to a manually-invoked `skill-advisor` skill that the user or model calls before substantive work.

In `CLAUDE.md`, add an "Automatic Skill Selection" section:
```markdown
## Automatic Skill Selection

Before beginning any substantive task, invoke /skill-advisor with a brief task description.
skill-advisor will recommend the most relevant Hephaestus skills to apply.
```

This achieves the same guidance effect without hook conflicts.

#### 7. Version Bump the Plugin

| Change size | Version bump |
|---|---|
| 1-3 new skills | Minor (2.0.0 → 2.1.0) |
| 4+ new skills or significant restructuring | Major (2.0.0 → 3.0.0) |
| Bug fixes or attribution only | Patch (2.0.0 → 2.0.1) |

Adding 8 new skills from superpowers: bump v2.0.0 → v3.0.0 (major).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Install superpowers as separate plugin | Would add all 14 skills without modification | SessionStart hook in hooks/hooks.json conflicts with ai-maestro hooks; two plugins routing the same action space causes confusion | Check for hook conflicts before choosing separate plugin installation |
| Fork/vendor superpowers | Would maintain full upstream compatibility | Forking a 120K-star rapidly-evolving repo creates ongoing sync burden for only 7 needed skills | Prefer selective porting over forking when you only need a subset |
| Direct copy without adaptation | Would save time on each skill port | superpowers hardcodes docs/superpowers/specs/ and docs/superpowers/plans/ paths; doesn't reference Mnemosyne, myrmidon-swarm, or pixi tooling | Always audit for hardcoded paths and project-specific tooling before copying |
| Merging code-review into two separate skills (one for requesting, one for receiving) | Matched superpowers' split of requesting-code-review + receiving-code-review | Redundant — reviewer persona and both sides of review naturally belong together in one skill | Consolidate closely-related source skills into a single ported skill when they form a cohesive workflow |

## Results & Parameters

### Skills Successfully Ported (8 total)

| Ported Skill File | Source Skill(s) | Key Adaptation |
|---|---|---|
| `skills/test-driven-development.md` | superpowers test-driven-development | Added pixi run pytest, /advise before, /learn after |
| `skills/systematic-debugging.md` | superpowers systematic-debugging | Added Mnemosyne loop, conventional commits |
| `skills/verification.md` | superpowers verification-before-completion | Added Hephaestus checklist items |
| `skills/git-worktrees.md` | superpowers using-git-worktrees | Changed path convention to /tmp/<project>-<branch> |
| `skills/finish-branch.md` | superpowers finishing-a-development-branch | Added protected-main convention, gh pr create |
| `skills/brainstorm.md` | superpowers brainstorming | Added /advise call before brainstorm |
| `skills/code-review.md` | requesting-code-review + receiving-code-review + agents/code-reviewer.md | Merged all three into single skill |
| `skills/skill-advisor.md` | superpowers using-superpowers (meta) | Converted SessionStart hook → manually-invoked meta-skill |

### Plugin Version History

| Version | Change |
|---|---|
| v2.0.0 | Pre-integration baseline |
| v3.0.0 | +8 skills from superpowers; CLAUDE.md Automatic Skill Selection section; THIRD_PARTY_LICENSES.md |

### Validation Command

```bash
# In ProjectHephaestus root
python3 scripts/validate_plugins.py
# Expected: 17 skills validated (9 existing + 8 new), 0 errors
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | obra/superpowers integration, PR #206 | 8 skills ported from MIT-licensed repo, YAML frontmatter valid, CI pending |
