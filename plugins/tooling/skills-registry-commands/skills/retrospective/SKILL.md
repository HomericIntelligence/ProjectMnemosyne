---
name: retrospective
description: Save session learnings as a new skill plugin. Use after experiments, debugging sessions, or when you want to preserve team knowledge.
user-invocable: false
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

## Verified Workflow

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
4. **Generate plugin** (⚠️ **MUST follow CI requirements**):
   - `.claude-plugin/plugin.json` with metadata
   - `skills/<name>/SKILL.md` with:
     - ✅ **YAML frontmatter** (starts with `---`)
     - ✅ **Overview section** with table (must have `## Overview` header)
     - ✅ **Failed Attempts table** with pipe (`|`) characters (subsections with `###` or prose alone will FAIL CI)
     - ✅ **Verified Workflow section** (not just "## Workflow")
     - ✅ All other required sections
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

## CRITICAL: CI Validation Requirements

**These requirements are enforced by CI and will cause PR failures if not met:**

### 1. YAML Frontmatter (REQUIRED)

**Every SKILL.md MUST start with YAML frontmatter:**

```yaml
---
name: skill-name
description: "Brief description. Use when: specific trigger conditions."
mcp_fallback: none
category: architecture  # or training, evaluation, etc.
tier: 2
date: YYYY-MM-DD
---
```

**Common failure**: Forgetting the frontmatter entirely or missing the opening `---`

### 2. Overview Table (REQUIRED)

**Must have an "## Overview" section header with a table:**

```markdown
## Overview

| Aspect | Details |
|--------|---------|
| **Date** | 2026-01-04 |
| **Objective** | What you were trying to accomplish |
| **Outcome** | ✅ Success or ❌ Failure |
| **Root Cause** | Why the problem occurred |
| **Solution** | How it was fixed |
```

**Common failure**: Having the table without the "## Overview" header

### 3. Failed Attempts Table (REQUIRED)

**Failed Attempts MUST be in table format with pipe (`|`) characters. This is enforced by CI validation.**

**✅ CORRECT FORMAT (use this):**

```markdown
## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| **Approach 1** | Description of what was tried | Why it didn't work | What you learned |
| **Approach 2** | Another attempt | Reason for failure | Key insight |
| **Approach 3** | Third attempt if applicable | Failure reason | Insight gained |
```

**❌ INCORRECT FORMATS (will fail CI):**

```markdown
## Failed Attempts

### ❌ Attempt 1: First approach
We tried X but it failed because Y...

### ❌ Attempt 2: Second approach
Another approach that didn't work...
```

```markdown
## Failed Attempts

We tried several approaches but they all failed for various reasons...
```

**Key requirement**: The section MUST contain at least one pipe character (`|`) to form a table. Subsections with `###` or plain prose paragraphs will **fail CI validation**.

**Best practice**: If you have detailed subsections, add a summary table at the top, then include detailed subsections below:

```markdown
## Failed Attempts

| Attempt | Issue | Details |
|---------|-------|---------|
| Approach 1 | Error X occurred | See subsection below |
| Approach 2 | Performance issue | See subsection below |

### ❌ Attempt 1: Detailed Analysis
[Detailed explanation here...]
```

### 4. Results & Parameters Section (RECOMMENDED)

While not strictly required for CI, this section is highly valuable:

```markdown
## Results & Parameters

**Command used**:
```bash
pixi run pytest tests/unit/ -x
```

**Configuration**:
- Python 3.14
- pytest 9.0.2
- All 70 tests passing
```

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

**Before creating the skill, verify CI requirements are met:**

### CI-Enforced (Will Fail Build)
- [ ] **YAML frontmatter** at the top with `---` delimiters
- [ ] **Overview section** with `## Overview` header and table
- [ ] **Failed Attempts table** with pipe (`|`) characters (prose paragraphs or `###` subsections alone will FAIL)
- [ ] **Proper markdown formatting** (no malformed tables)

### Quality Requirements (Best Practices)
- [ ] Description has specific trigger conditions (`Use when:`)
- [ ] Parameters are copy-paste ready
- [ ] Environment/versions are documented
- [ ] References to issues/PRs included

## Failed Attempts

| Attempt | Why Failed | Lesson Learned |
|---------|-----------|----------------|
| Auto-trigger on every session | User fatigue from constant prompts | Use >10 messages threshold |
| Generic skill names | Hard to find later via /advise | Enforce kebab-case with category prefix |
| Optional Failed Attempts section | Most valuable content missing | Make failures REQUIRED in template |
| Single references/notes.md | Information overload in one file | Split into experiment-log + troubleshooting |
| No environment capture | "Works on my machine" problems | Add environment table to Overview section |
| Committing without validation | Bad plugins entered registry | Run validate_plugins.py before commit |

## References

- Source: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
- See `skill-documentation-patterns` for writing quality skills
- See `plugin-validation-workflow` for CI validation
