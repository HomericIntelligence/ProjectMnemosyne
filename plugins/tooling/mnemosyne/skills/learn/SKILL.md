---
name: learn
description: Save session learnings as a new skill plugin. Use after experiments, debugging sessions, or when you want to preserve team knowledge.
user-invocable: false
---

# /learn

Capture session learnings and create a new skill plugin with PR.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-29 |
| Objective | Automate knowledge capture from sessions into searchable skill plugins |
| Outcome | ✅ Operational |

## When to Use

- After completing an experiment (successful or failed)
- After debugging a tricky issue
- After implementing a new pattern
- When you want to preserve learnings for the team
- Automatically prompted on session-ending keywords (if hooks configured)

## Common Mistakes and Fixes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Forgot `.claude-plugin/plugin.json` | "Missing .claude-plugin/plugin.json" | Create with name, version, description, category, date |
| Description < 20 chars | "Description too short" | Add "Use when:" trigger conditions |
| Failed Attempts as prose | "should contain a table" | Use pipe-delimited table format |
| Missing frontmatter | "missing YAML frontmatter" | Add `---` delimiters at top of SKILL.md |
| Wrong category | "Invalid category" | Use one of 9 approved categories |
| `## Workflow` instead of `## Verified Workflow` | "Missing Verified Workflow section" | Use exact header name |
| SessionEnd hook | Hook doesn't display messages to user | Use UserPromptSubmit hook instead |
| Committed without validating | PR fails CI | Run `python3 scripts/validate_plugins.py skills/` before commit |

## Failed Attempts

| Attempt | Why Failed | Lesson Learned |
|---------|-----------|----------------|
| Auto-trigger on every session | User fatigue from constant prompts | Use >10 messages threshold |
| Generic skill names | Hard to find later via /advise | Enforce kebab-case with category prefix |
| Optional Failed Attempts section | Most valuable content missing | Make failures REQUIRED in template |
| Single references/notes.md | Information overload in one file | Split into experiment-log + troubleshooting |
| No environment capture | "Works on my machine" problems | Add environment table to Overview section |
| Committing without validation | Bad plugins entered registry | Run validate_plugins.py before commit |

## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- See `commands/learn.md` for the full command implementation
- See `validation-workflow` for CI validation details
- See `documentation-patterns` for writing quality skills
