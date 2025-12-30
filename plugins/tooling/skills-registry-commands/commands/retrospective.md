---
description: Save session learnings as a new skill plugin
---

# /retrospective

Capture session learnings and create a new skill plugin.

## Instructions

When the user invokes this command:

1. **Analyze the conversation** to extract:
   - Objective: What was the user trying to accomplish?
   - Steps taken: What approaches were tried?
   - Successes: What worked?
   - Failures: What didn't work and why?
   - Parameters: What configs/settings were used?

2. **Prompt for metadata**:
   - Category (training, evaluation, optimization, debugging, architecture, tooling, ci-cd, testing)
   - Skill name (kebab-case)

3. **Generate plugin files**:
   - `.claude-plugin/plugin.json` with metadata
   - `skills/<name>/SKILL.md` with findings
   - `references/notes.md` with raw details

4. **Create PR**:
   - Branch: `skill/<category>/<name>`
   - Commit all files
   - Open PR with summary

## Required SKILL.md Sections

| Section | Purpose |
|---------|---------|
| Overview table | Date, objective, outcome |
| When to Use | Trigger conditions |
| Verified Workflow | Steps that worked |
| **Failed Attempts** | What didn't work (REQUIRED) |
| Results & Parameters | Copy-paste configs |

## Example

```
/skills-registry-commands:retrospective
```

Claude will analyze the session and guide you through creating a new skill.
