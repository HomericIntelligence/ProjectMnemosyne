---
name: tooling-parallel-worktree-bulk-issue-execution
description: "Pattern for triaging GitHub issues by complexity and executing low-complexity items in parallel using worktree-isolated agents. Use when: (1) a repo has many open issues to process, (2) you need to classify issues by effort level, (3) you want to execute multiple independent fixes simultaneously with separate branches and PRs."
category: tooling
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags: [github-issues, parallel-agents, worktree, bulk-operations, triage, automation]
---

# Parallel Worktree Bulk Issue Execution

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-24 |
| **Objective** | Analyze 35 open GitHub issues, classify by complexity (LOW/MEDIUM/HIGH), and execute all LOW items simultaneously using parallel worktree-isolated agents |
| **Outcome** | Successfully created 12 PRs in parallel, all LOW-complexity issues resolved in a single session |

## When to Use

- Repository has 10+ open issues that need triage and execution
- Many issues are independent and touch different files (no merge conflicts)
- You want to maximize throughput by running fixes in parallel
- Issues span mechanical changes (config, docs, text edits) that can be done without deep design

## Verified Workflow

### Quick Reference

```bash
# 1. Fetch all issues
gh issue list --repo ORG/REPO --state open --limit 100 --json number,title,body,labels

# 2. Classify with parallel Explore agents (up to 3)
# Split issues across agents by number range

# 3. Launch parallel worktree agents (one per LOW issue)
# Each agent: branch -> fix -> commit -> push -> PR

# 4. Handle failures manually in main session
```

### Detailed Steps

1. **Fetch all open issues** using `gh issue list` with JSON output
2. **Launch 2-3 Explore agents in parallel** to read issue bodies and assess complexity:
   - LOW: mechanical changes, config files, text edits, < 30 min
   - MEDIUM: requires design decisions, touches multiple files with logic, 1-3 hours
   - HIGH: architectural changes, significant new code, complex dependencies, > 3 hours
3. **Identify dependencies** between issues (e.g., pyproject.toml blocks ruff/mypy setup)
4. **Verify no file conflicts** among LOW issues before parallel execution
5. **Launch worktree-isolated agents** (one per LOW issue) with explicit instructions:
   - Branch naming: `fix/<issue-number>-<short-name>`
   - Read the issue body first via `gh issue view`
   - Make changes, commit with `Closes #NNN`
   - Push and create PR with `gh pr create`
6. **Monitor completions** and handle failures (content filters, edge cases) manually
7. **Verify all PRs** created successfully with `gh pr list`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Content filter on CODE_OF_CONDUCT.md | Sub-agent tried to write Contributor Covenant text | API content filtering policy blocked the output (twice) | Governance documents with conduct/harassment language may trigger content filters — handle these in the main session where you can write shorter, adapted versions |
| Sub-agent retrospective | Asked completed agents to run /learn | Agents are one-shot — once they return results, their context is gone | Sub-agents cannot run follow-up commands after completion; capture learnings from the main session instead |
| Branch already exists from failed agent | Retry agent tried to create same branch name | Previous failed agent had already pushed the branch | Use `-v2` suffix or delete remote branch before retrying with same name |

## Results & Parameters

### Session Statistics

- **Issues analyzed**: 35
- **LOW complexity**: 12 (34%)
- **MEDIUM complexity**: 14 (40%)
- **HIGH complexity**: 8 (23%) + 1 meta-tracking
- **PRs created**: 12/12 (100%)
- **Agent failures**: 1 (content filter on CODE_OF_CONDUCT.md, resolved manually)
- **Wall-clock time**: ~6 minutes for all 12 parallel agents

### Complexity Classification Heuristics

```yaml
LOW (< 30 min):
  - Adding entries to .gitignore
  - Creating boilerplate docs (CONTRIBUTING, CHANGELOG, SECURITY)
  - Creating GitHub templates (issue, PR)
  - Pinning action versions to SHA
  - Fixing trailing commas or typos
  - Adding .editorconfig / .pre-commit-config.yaml
  - Removing dead code references (UUID cleanup)
  - Adding simple fields to existing scripts

MEDIUM (1-3 hours):
  - DRY refactoring across 3+ files
  - Adding CI pipeline steps (linting, type checking)
  - Creating JSON schemas
  - Auditing and relocating orphaned files
  - Fixing hardcoded paths with new strategy

HIGH (3+ hours):
  - Creating pyproject.toml / pixi.toml (packaging foundation)
  - Building test infrastructure from scratch
  - Rewriting marketplace generators for new formats
  - Tasks with 3+ blocking dependencies
```

### Key Constraints

- **Max parallel agents**: 12 worked fine; each gets its own worktree
- **File conflicts**: Verify LOW issues touch different files before parallelizing
- **Content filters**: Governance/conduct documents may need manual handling
- **Branch cleanup**: User handles branch deletion (do not auto-delete)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | 35 open issues, 12 LOW executed in parallel | PRs #959-#971 |
