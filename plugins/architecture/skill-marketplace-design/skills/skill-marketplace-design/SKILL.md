---
name: skill-marketplace-design
description: "Design patterns for Claude Code skill marketplaces"
category: architecture
source: ProjectMnemosyne
date: 2025-12-28
---

# Skill Marketplace Design

Architecture and design patterns for building Claude Code skill marketplaces.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-28 |
| Objective | Create searchable, validated skill registry |
| Outcome | Success (this skill) |

## When to Use

- Setting up team knowledge capture system
- Implementing `/advise` and `/retrospective` commands
- Designing plugin structure and validation
- Adding automatic retrospective via hooks

## Verified Workflow

1. **Define plugin structure**:

   ```text
   plugins/<category>/<name>/
   ├── .claude-plugin/plugin.json
   ├── skills/<name>/SKILL.md
   └── references/notes.md
   ```

2. **Implement core skills**:
   - `/advise` - Search marketplace.json, return findings
   - `/retrospective` - Extract learnings, create PR

3. **Add SessionEnd hook** for auto-trigger:

   ```json
   {
     "hooks": {
       "SessionEnd": [{
         "hooks": [{
           "type": "command",
           "command": "python3 retrospective-trigger.py"
         }]
       }]
     }
   }
   ```

4. **Validate with CI**:
   - Check plugin.json required fields
   - Verify SKILL.md has Failed Attempts section
   - Auto-generate marketplace.json on merge

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Flat directory structure | Hard to categorize, search | Use category subdirectories |
| Optional failures section | Most valuable info missing | Make it required in validation |
| Manual marketplace.json | Gets out of sync | Auto-generate in CI |
| Vague descriptions | Claude can't match skills | Require specific trigger conditions |

## Results & Parameters

```yaml
# Key design decisions
plugin_structure: ".claude-plugin/plugin.json"
skill_format: "SKILL.md with YAML frontmatter"
categories: 8 (training, evaluation, optimization, debugging, architecture, tooling, ci-cd, testing)

# Validation rules
min_description_length: 20
required_sections: ["Failed Attempts"]
required_plugin_fields: ["name", "version", "description", "category", "date", "tags"]

# Hooks
session_end_trigger: ["exit", "clear"]
min_transcript_lines: 10
```

## References

- HuggingFace skills blog: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
- Claude Code hooks: https://code.claude.com/docs/en/hooks
- Meta: This skill documents its own design
