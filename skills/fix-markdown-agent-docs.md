---
name: fix-markdown-agent-docs
description: 'Fix common markdown issues in agent hierarchy docs: malformed closing
  code fences, stale agent counts, and line length violations. Use when: (1) markdownlint
  fails on agents/hierarchy.md, (2) agent counts in docs diverge from actual .claude/agents/
  files, (3) closing code fences have language specifiers.'
category: documentation
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | fix-markdown-agent-docs |
| **Category** | documentation |
| **Applies To** | agents/hierarchy.md and similar agent hierarchy docs |
| **Key Tools** | Read, Edit, Grep, Glob, Bash (pre-commit) |

## When to Use

- Markdownlint reports errors on `agents/hierarchy.md` after agent restructuring
- PR review feedback flags stale agent counts (e.g., "13 specialists" when it's now 5)
- Code fence closing tags have language specifiers (` ```text ` instead of ` ``` `)
- Agent count tables/breakdowns don't match actual files in `.claude/agents/`
- Lines exceed 120 characters (MD013) in hierarchy docs

## Verified Workflow

### Step 1: Read the file to understand current state

```bash
Read agents/hierarchy.md
```

### Step 2: Count actual agents by level using Grep

```bash
# Get level assignments from all agent YAML frontmatter
Grep pattern="^level:" path=".claude/agents" glob="*.md" output_mode="content"
```

Count agents per level from the grep output. Exclude template files.

### Step 3: Fix malformed closing code fences

Closing code fences must be bare ` ``` ` with no language tag. The pattern ` ```text `
on a closing fence is invalid — only opening fences take a language specifier.

Search for this pattern and fix each occurrence:

```
old: ```text    ← closing fence (no opening context above)
new: ```
```

**How to identify closing vs opening fences**: A closing fence immediately follows content
lines (not a heading/blank line). An opening fence immediately follows a blank line or heading.

### Step 4: Reconcile agent counts

After counting actual Level 3 agents:

1. Split into review specialists (name contains `-review-`) vs implementation specialists
2. Update the diagram box counts (e.g., "4 Code Review Specialists", "6 Additional Specialists")
3. Update the Level Summaries section text (e.g., "15 total (11 + 4)")
4. Update the Agent Count table total
5. Update the Level 3 Breakdown list

Note: The `code-review-orchestrator` is Level 2, NOT a Level 3 review specialist.
Do not count it in the Level 3 review specialist total.

### Step 5: Fix line length violations (MD013)

Lines over 120 chars must be wrapped. For bullet list items, wrap by continuing the
text on the next line with 2-space indent (continuation indent):

```markdown
- **Field**: Short intro text that is within 120 chars;
  continuation text here on next line indented 2 spaces
```

For italic historical notes at the end of sections, wrap at a natural sentence/clause boundary.

### Step 6: Fix MD032 (lists need blank lines around them)

If a bold heading like `**Level 3 Breakdown:**` is immediately followed by a list with
no blank line, add a blank line between the heading text and the first list item.

### Step 7: Validate

```bash
pixi run pre-commit run markdownlint-cli2 --all-files
```

Should output: `Markdown Lint...Passed`

### Step 8: Commit (skip mojo-format if GLIBC incompatibility exists locally)

```bash
git add agents/hierarchy.md
SKIP=mojo-format git commit -m "fix: correct agent counts and markdown in hierarchy.md"
```

## Key Patterns

### Malformed Fence Pattern

```text
# WRONG - closing fence with language tag
Boilerplate Generation (Level 5)
```text          ← INVALID closing fence

# CORRECT
Boilerplate Generation (Level 5)
```              ← bare closing fence
```

### Agent Count Reconciliation

The Level 3 total = implementation specialists + code review specialists.

- **Code review specialists**: agents whose filenames contain `-review-specialist`
  (e.g., `general-review-specialist.md`, `mojo-language-review-specialist.md`)
- **Implementation specialists**: all other Level 3 agents
- **NOT included**: `code-review-orchestrator` (this is Level 2)

Example after PR #3319 consolidation (13→5 review specialists):

| Category | Count | Agents |
|----------|-------|--------|
| Implementation | 11 | implementation, test, documentation, performance, security, blog writer, numerical stability, test flakiness, PR cleanup, mojo syntax validator, CI failure analyzer |
| Code Review | 4 | general, mojo language, security, test |
| **Total L3** | **15** | |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Match closing fence with surrounding context | Used box-drawing characters from diagram as part of old_string | Box-drawing chars varied in width/encoding between Read output and Edit matcher | Read the exact lines around the closing fence and use minimal unique context (2-3 lines before) |
| Trust the plan's count directly | Used "10 implementation specialists + 5 code review" from plan doc without verifying | Plan doc was stale; actual files showed 11 + 4 | Always grep actual `.claude/agents/` files to verify counts before editing |
| Fix all fences with replace_all | Tried replace_all on ` ```text ` → ` ``` ` | Would also replace opening ` ```text ` fences used legitimately for diagrams | Fix each closing fence individually using surrounding context to distinguish from openers |
| Run `just pre-commit-all` | Tried to use justfile recipe | `just` not installed on this machine | Use `pixi run pre-commit run --all-files` directly |
| Run `pixi run npx markdownlint-cli2` | Tried direct npx invocation | `npx` not in PATH in pixi environment | Use `pixi run pre-commit run markdownlint-cli2 --all-files` instead |

## Results & Parameters

**Environment**: Linux (Debian Buster), ProjectOdyssey worktree

**Working commands**:

```bash
# Validate markdown only (fast)
pixi run pre-commit run markdownlint-cli2 --all-files

# Run all hooks except broken mojo-format (GLIBC issue on older distros)
SKIP=mojo-format git commit -m "fix: ..."

# Count agents per level
grep -r "^level:" .claude/agents/*.md | grep "level: 3" | wc -l
```

**markdownlint rules triggered in hierarchy.md**:

- `MD013` — line-length (limit: 120 chars)
- `MD032` — blanks-around-lists (blank line required before/after list)
- Malformed closing fences don't trigger markdownlint but break rendering

**Agent level distribution after PR #3319** (ProjectOdyssey):

| Level | Count |
|-------|-------|
| 0 | 1 |
| 1 | 6 |
| 2 | 4 |
| 3 | 15 |
| 4 | 6 |
| 5 | 3 |
| Total | 35 |
