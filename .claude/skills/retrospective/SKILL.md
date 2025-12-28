---
name: retrospective
description: "Auto-save session learnings as a new skill. Use after experiments or debugging."
category: marketplace
---

# Retrospective

Capture session learnings and auto-create a PR to the skills registry.

## When to Use

- After completing an experiment (successful or failed)
- After debugging a tricky issue
- After implementing a new pattern
- When you want to preserve learnings for the team
- Automatically prompted on `/exit` and `/clear`

## Quick Reference

```bash
# User invokes manually
/retrospective

# Or auto-triggered on session end
# Hook prompts: "Would you like to save your learnings?"
```

## Workflow

1. **Analyze conversation**: Read entire session transcript
2. **Extract learnings**:
   - Objective: What was the user trying to accomplish?
   - Steps taken: What approaches were tried?
   - Successes: What worked?
   - Failures: What didn't work and why?
   - Parameters: What configs/settings were used?
3. **Prompt for metadata**:
   - Category (from 8 approved categories)
   - Skill name (kebab-case)
   - Tags (for searchability)
4. **Generate plugin**:
   - `plugin.json` with metadata
   - `SKILL.md` with 7-section format
   - `references/notes.md` with raw details
5. **Create PR**:
   - Branch: `skill/<category>/<name>`
   - Commit all files
   - Open PR with summary

## Required Sections in Generated SKILL.md

| Section | Purpose |
|---------|---------|
| Overview table | Date, objective, outcome |
| When to Use | Specific trigger conditions |
| Verified Workflow | Step-by-step that worked |
| **Failed Attempts** | What didn't work (REQUIRED) |
| Results & Parameters | Copy-paste ready configs |
| References | Links to issues, docs |

## Generated plugin.json Format

```json
{
  "name": "skill-name",
  "version": "1.0.0",
  "description": "TRIGGER: (1) condition 1, (2) condition 2. Verified on X.",
  "author": { "name": "Author Name" },
  "date": "YYYY-MM-DD",
  "category": "category-name",
  "tags": ["tag1", "tag2"],
  "skills": "./skills",
  "source_project": "ProjectName"
}
```

## Auto-Trigger Behavior

The SessionEnd hook (`retrospective-trigger.py`) automatically prompts for retrospective:

- Triggers on `/exit` and `/clear` commands
- Checks if session has meaningful content (>10 messages)
- Non-blocking - doesn't prevent session termination
- Outputs system message prompting the user

## Categories

| Category | Use For |
|----------|---------|
| `training` | ML training experiments |
| `evaluation` | Model evaluation |
| `optimization` | Performance tuning |
| `debugging` | Bug investigation |
| `architecture` | Design decisions |
| `tooling` | Automation tools |
| `ci-cd` | Pipeline configs |
| `testing` | Test strategies |

## References

- See CLAUDE.md for plugin standards
- See `templates/experiment-skill/` for full template
- See `.claude/settings.json` for hook configuration
