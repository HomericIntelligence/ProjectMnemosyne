---
name: retrospective
description: "Auto-save session learnings as a new skill"
category: tooling
invokedBy: user
---

# /retrospective

Capture session learnings and create a new skill plugin with PR.

## When to Use

- After completing an experiment (successful or failed)
- After debugging a tricky issue
- After implementing a new pattern
- When you want to preserve learnings for the team
- Automatically prompted on `/exit` and `/clear` (if hooks configured)

## Invocation

```
/retrospective
```

Or configure auto-trigger on session end (see Hooks section).

## Workflow

1. **Analyze conversation**: Read entire session transcript
2. **Extract learnings**:
   - Objective: What was the user trying to accomplish?
   - Steps taken: What approaches were tried?
   - Successes: What worked?
   - Failures: What didn't work and why?
   - Parameters: What configs/settings were used?
3. **Prompt for metadata**:
   - Category (from approved categories)
   - Skill name (kebab-case)
   - Tags (for searchability)
4. **Generate plugin**:
   - `.claude-plugin/plugin.json` with metadata
   - `skills/<name>/SKILL.md` with required sections
   - `references/notes.md` with raw details
5. **Create PR**:
   - Branch: `skill/<category>/<name>`
   - Commit all files
   - Open PR with summary

## Generated Plugin Structure

```
plugins/<category>/<skill-name>/
├── .claude-plugin/
│   └── plugin.json
├── skills/<skill-name>/
│   └── SKILL.md
└── references/
    └── notes.md
```

## Required SKILL.md Sections

| Section | Purpose |
|---------|---------|
| Overview table | Date, objective, outcome |
| When to Use | Specific trigger conditions |
| Verified Workflow | Step-by-step that worked |
| **Failed Attempts** | What didn't work (REQUIRED!) |
| Results & Parameters | Copy-paste ready configs |
| References | Links to issues, docs |

## Generated plugin.json Format

```json
{
  "name": "skill-name",
  "version": "1.0.0",
  "description": "What this does. Use when: (1) trigger 1, (2) trigger 2. Verified on X.",
  "author": { "name": "Author Name" },
  "skills": "./skills"
}
```

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

## Implementation for Importing Agents

Add this to your project's `CLAUDE.md`:

```markdown
## Commands

### /retrospective

Save learnings after a session (auto-creates PR).

1. Read entire conversation history
2. Extract: objective, steps taken, successes, failures, parameters
3. Prompt user for category and skill name
4. Generate plugin:
   - plugin.json with metadata
   - SKILL.md with required sections
   - references/notes.md with raw details
5. Create branch: `skill/<category>/<name>`
6. Commit and push
7. Create PR with summary
```

## Hooks Configuration (Optional)

Auto-prompt retrospective on session end:

```json
{
  "hooks": {
    "SessionEnd": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "echo 'Would you like to save your learnings? Run /retrospective'"
      }]
    }]
  }
}
```

## Quality Checklist

Before creating the skill, verify:
- [ ] Description has specific trigger conditions (`Use when:`)
- [ ] Failed Attempts section is populated
- [ ] Parameters are copy-paste ready
- [ ] Environment/versions are documented

## References

- Source: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
- See `skill-documentation-patterns` for writing quality skills
- See `plugin-validation-workflow` for CI validation
