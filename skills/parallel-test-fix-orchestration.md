---
name: parallel-test-fix-orchestration
description: 'Orchestrate mass parallel test fixes using worktree-isolated agents
  with one PR per fix. Use when: CI has many independent test failures that need systematic
  resolution.'
category: ci-cd
date: 2026-03-18
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
| ----------- | ------- |
| **Scope** | Mass CI test failure resolution |
| **Scale** | 10-50+ failing test files per session |
| **Parallelism** | Up to 10 concurrent worktree agents |
| **Output** | One PR per failing test file, auto-merge enabled |
| **Duration** | 5-15 minutes for 45 agents (wall clock) |

## When to Use

- CI comprehensive test suite has 10+ failing test files
- Failures span multiple categories (compile errors, runtime errors, permission issues)
- Each test file can be fixed independently (no shared source file conflicts)
- You want clean, reviewable, single-purpose PRs rather than one mega-PR
- Test failures are caused by API drift, not fundamental architectural issues

## Verified Workflow

### Quick Reference

```
1. Explore source APIs to build a "current truth" reference
2. Categorize failures (compile vs runtime vs permission vs source bug)
3. Launch agents in waves of 5-10, each in isolation: worktree
4. Each agent: branch → read test → read source → fix → commit → push → PR → auto-merge
5. Monitor completions, verify PR count matches failure count
```

### Step 1: Build API Reference

Before launching any agents, read the current source modules that tests depend on. This prevents agents from guessing at APIs.

Key files to read:
- Package `__init__.mojo` files (show what's exported and from where)
- Core type definitions (constructors, method signatures)
- Test assertion helpers (parameter order, types)

### Step 2: Categorize Failures

Group failures into categories to write better agent prompts:

| Category | Typical Fix | Agent Complexity |
| ---------- | ------------- | ----------------- |
| **Wrong import path** | Change `from X import Y` → `from Z import Y` | Simple (~30s) |
| **API signature change** | Add missing arg, wrap type, reorder params | Simple (~60s) |
| **Docstring formatting** | Capitalize, add periods | Trivial (~20s) |
| **Missing import** | Add import line | Trivial (~20s) |
| **Constructor change** | Update call pattern | Medium (~90s) |
| **Removed method** | Rewrite test using current API | Complex (~3min) |
| **Runtime assertion failure** | Investigate source vs test expectations | Complex (~5min) |
| **Source bug** | Fix source code, not test | Complex (~10min) |
| **Permission denied** | Change paths to /tmp/ | Simple (~30s) |

### Step 3: Launch Agents in Waves

```
Agent(
  subagent_type="general-purpose",
  isolation="worktree",
  run_in_background=True,
  prompt="""
  Fix failing test: <path>
  Error: <exact error message>
  Root cause: <your analysis from Step 1>
  Current API: <signatures from Step 1>

  Workflow:
  1. git checkout -b fix/<N>-<name> main
  2. Read the test file
  3. Read the source module
  4. Fix the test (or source if it's a bug)
  5. Commit, push, create PR with --label testing
  6. gh pr merge --auto --rebase
  """
)
```

**Critical**: Include the current API signatures in each agent prompt. Agents without this context will waste time re-discovering what you already know.

### Step 4: Monitor and Verify

- Agents report PR URLs on completion
- Check for duplicate PR numbers (agents may accidentally reuse branches)
- Verify all agents completed: count completed notifications vs launched count
- Check `gh pr list --state open --label testing` for the full list

### Step 5: Post-Merge Verification

```bash
# After all PRs merge, verify CI passes
gh run list --branch main --limit 1
# Clean up worktrees
git worktree prune
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Launch all 45 agents simultaneously | Tried launching all agents at once in a single message | Tool call limits and context pressure; some agents got minimal context | Launch in waves of 5-10 to give each agent adequate prompt detail |
| Fix tests without reading source first | Early agents tried fixing tests based only on error messages | Agents guessed wrong APIs, produced incorrect fixes | Always explore source APIs first and include signatures in agent prompts |
| Assume all failures are test-only | Categorized all failures as "fix the test" | 4 were real source bugs (missing else branch, ignored step field, wrong offset, stub method) | Read source carefully; runtime assertion failures often indicate real source bugs |
| Single agent prompt template | Used identical prompt structure for all categories | Simple import fixes got over-detailed prompts; complex bugs got under-detailed | Tailor prompt complexity to failure category |
| Letting agents investigate Docker setup independently | Each permission-error agent investigated Dockerfile/entrypoint independently | Duplicated investigation work across 7 agents | Fix shared infrastructure (Docker entrypoint) as Wave 0 prerequisite, then verify in later wave |

## Results & Parameters

### Session Results

- **45 PRs created** in ~15 minutes wall clock
- **30 compile error fixes** (import paths, type casts, missing args, docstrings)
- **8 runtime/source bug fixes** (4 real source bugs discovered)
- **7 permission/environment fixes** (Docker paths → /tmp)
- **0 failures** — all agents completed successfully

### Agent Configuration

```yaml
agent_type: general-purpose
isolation: worktree          # Each agent gets isolated git worktree
run_in_background: true      # Non-blocking, notified on completion
wave_size: 5-10              # Concurrent agents per wave
```

### Source Bugs Discovered

These were categorized as "test failures" but were actually source code bugs:

1. **ExTensor._set_float64/_set_float32**: Missing `else` branch — integer dtype values silently discarded
2. **ExTensor.__getitem__(*slices)**: Step field from Slice objects completely ignored
3. **ExTensor.__getitem__(Int)**: Used raw memory offset instead of stride-aware for non-contiguous views
4. **TrainingLoop.run_epoch**: Was a PythonObject stub, never iterated batches

### Key Metrics

| Metric | Value |
| -------- | ------- |
| Total agents launched | 45 |
| Success rate | 100% |
| Avg agent duration (simple) | 45-90 seconds |
| Avg agent duration (complex) | 3-12 minutes |
| Longest agent (conv gradient) | ~12 minutes |
| PRs with source fixes | 4 |
| PRs with test-only fixes | 41 |
