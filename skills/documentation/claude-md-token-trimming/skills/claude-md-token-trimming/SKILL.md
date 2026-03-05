---
name: claude-md-token-trimming
description: "Trim CLAUDE.md token consumption by moving verbose sections to .claude/shared/ files with summary links. Use when: CLAUDE.md exceeds 1200+ lines, sections have detailed examples duplicating dedicated docs, or reducing context overhead is needed."
category: documentation
date: 2026-03-05
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Goal** | Reduce CLAUDE.md line count without losing critical information |
| **Input** | Bloated CLAUDE.md with verbose example-heavy sections |
| **Output** | Trimmed CLAUDE.md (≤1400 lines) + new `.claude/shared/*.md` files |
| **Result** | 33% token reduction (1786 → 1199 lines) in one session |

## When to Use

Trigger this skill when:

1. CLAUDE.md grows beyond ~1200 lines (loaded on every Claude Code interaction)
2. Sections contain long code-block examples that explain concepts (not rules)
3. Content duplicates or elaborates on dedicated docs in `.claude/shared/` or `docs/dev/`
4. Token overhead is visibly slowing context utilization

Do NOT trim:

- CRITICAL RULES sections (PR workflow, branch protection, never-push-to-main)
- Decision trees used in every interaction
- Quick reference tables (e.g., Thinking Budget, Hook Types)
- Any section prefixed with `⚠️` or containing enforcement language

## Verified Workflow

### 1. Audit sections by category

Read CLAUDE.md headings with line numbers to categorize each section:

```bash
grep -n "^##\|^###\|^####" CLAUDE.md
```

Classify each section as:
- **Keep full**: Critical rules, decision trees, quick-ref tables
- **Trim examples**: Keep bullets/tables, remove code-block examples
- **Move + link**: Pure reference content that belongs in `.claude/shared/`

### 2. For move + link sections

Create `.claude/shared/<section-name>.md` with full content, then replace
the CLAUDE.md section with a 2-5 line summary + link:

```markdown
### Output Style Guidelines

Use repo-relative file paths with line numbers for code references. Structure PR/issue comments with
`## Summary`, `## Changes Made`, `## Files Modified`, `## Verification` sections.

See [Output Style Guidelines](.claude/shared/output-style-guidelines.md) for complete examples.
```

### 3. For trim-examples sections

Remove markdown code-block examples that illustrate points already stated in bullet
form. Keep:
- Bullet lists of when/when-not
- Tables (budget, hook types, tool selection)
- Decision trees (text-art `├─` style)

Remove:
- ` ```markdown ` code blocks showing "GOOD" vs "BAD" examples
- ` ```yaml ` examples for hooks/config
- ` ```python ` examples for tool calls
- Prose "Example — When to Use X" blocks

### 4. Verify line count and linting

```bash
wc -l CLAUDE.md  # Must be ≤1400
SKIP=mojo-format pre-commit run --all-files  # Markdown Lint must pass
```

Note: `mojo-format` fails on this system due to GLIBC version mismatch — skip it.
The hook failure is pre-existing and unrelated to markdown changes.

### 5. Files to create for this project

| New File | Content Moved From |
|----------|-------------------|
| `.claude/shared/output-style-guidelines.md` | Output Style Guidelines section (~148 lines) |
| `.claude/shared/tool-use-optimization.md` | Tool Use Optimization + Agentic Loop Patterns (~219 lines) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `just pre-commit-all` directly | Tried `just --list` and `just pre-commit-all` | `just` not in PATH in this shell environment | Use `pre-commit` directly from `.pixi/envs/default/bin/pre-commit` |
| Running `pixi run just pre-commit-all` | Pixi doesn't expose `just` as a run target | `just: command not found` inside pixi env | Run pre-commit directly, not via just |
| Running `pixi run markdownlint-cli2` | Tried to lint markdown directly | `markdownlint-cli2: command not found` as pixi task | Use `pre-commit run --all-files` which invokes it correctly |
| Editing main repo instead of worktree | Made all CLAUDE.md edits to `/home/mvillmow/Odyssey2/CLAUDE.md` | Worktree at `.worktrees/issue-3158/` tracks a different branch | Must `cp` changes from main repo to worktree, or edit worktree directly |

## Results & Parameters

### Line count reduction achieved

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| CLAUDE.md total lines | 1,786 | 1,199 | 587 lines (33%) |
| Output Style Guidelines | ~148 lines | 4 lines + link | ~144 lines |
| Tool Use Optimization | ~103 lines | 4 lines + link | ~99 lines |
| Agentic Loop Patterns | ~116 lines | 5 lines + link | ~111 lines |
| Extended Thinking examples | ~25 lines | 0 lines | ~25 lines |
| Agent Skills examples | ~37 lines | ~3 lines | ~34 lines |
| Hooks YAML examples | ~42 lines | 0 lines | ~42 lines |
| Cross-References + Further Reading | ~17 lines | 0 lines | ~17 lines |
| Testing Strategy | ~113 lines | 5 lines + link | ~108 lines |
| Skill Delegation Patterns | ~45 lines | 4 lines | ~41 lines |

### Pre-commit invocation (workaround for GLIBC environment)

```bash
# Works — skips mojo-format which fails due to GLIBC version mismatch
SKIP=mojo-format /path/to/.pixi/envs/default/bin/pre-commit run --all-files
```

### Key preservation rules

Always keep in CLAUDE.md (never move to shared):
- `## ⚠️ CRITICAL RULES` section in full
- Git workflow with concrete `gh pr create` examples
- Commit message format with HEREDOC example
- `### Mojo Development Guidelines` (Critical Patterns table)
- All `### Pre-Commit Hook Policy - STRICT ENFORCEMENT` content
