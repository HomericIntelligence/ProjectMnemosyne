# Parallel Worktree Workflow

| Attribute | Value |
|-----------|-------|
| **Date** | 2025-02-09 |
| **Objective** | Execute multiple independent tasks in parallel using git worktrees and sub-agents |
| **Outcome** | ✅ Successfully completed 3 issues in parallel (480, 483, 490) with 193 new tests and 4 PRs |
| **Context** | ProjectScylla code quality improvements - writing tests and refactoring |

## When to Use This Skill

Use this approach when:
- **Multiple independent tasks** need to be completed simultaneously
- **No shared file conflicts** between tasks (different modules/directories)
- **Time is critical** - need to parallelize work
- **Clean isolation** is required - each task in its own environment
- **Multiple PRs** will be created from the work

**Don't use when**:
- Tasks modify the same files (conflicts likely)
- Tasks have dependencies on each other
- Single sequential task is sufficient

## Verified Workflow

### Phase 1: Setup Git Worktrees

Create separate worktrees for each parallel task:

```bash
# For issue #480
git worktree add ../worktree-480 -b 480-add-core-discovery-tests

# For issue #483
git worktree add ../worktree-483 -b 483-add-config-tests

# For issue #490
git worktree add ../worktree-490 -b 490-consolidate-calculate-cost

# Verify worktrees created
git worktree list
```

**Expected output**:
```
/home/user/ProjectScylla      main
/home/user/worktree-480       480-add-core-discovery-tests
/home/user/worktree-483       483-add-config-tests
/home/user/worktree-490       490-consolidate-calculate-cost
```

### Phase 2: Launch Parallel Sub-Agents

Launch all sub-agents simultaneously in background mode:

```
Task tool with subagent_type="general-purpose" for each issue
Use run_in_background=true for parallel execution
Each agent gets:
- GitHub issue number and context
- Worktree path to work in
- Specific deliverables and success criteria
- Testing requirements
```

**Agent 1 Prompt Template**:
```
You are working on GitHub Issue #480: [Title].

## Your Task
[Specific task description]

## Setup Instructions
1. Create git worktree: `git worktree add ../worktree-480 -b 480-branch-name`
2. Work in that worktree: `cd ../worktree-480`
3. [Specific setup steps]
4. Run tests: `pixi run python -m pytest tests/... -v`
5. Commit with message: "type(scope): description for #480"
6. Push branch and create PR linked to issue #480

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] All tests pass
- [ ] Pre-commit hooks pass
```

**Critical**: Each agent must:
- Work exclusively in their assigned worktree
- Create their own branch
- Push their branch independently
- Create their own PR

### Phase 3: Monitor Progress

Track agents without blocking:

```bash
# Check agent output files (optional)
tail -f /tmp/claude-1000/tasks/<agent-id>.output

# Wait for completion notifications
# System will notify when each agent completes
```

**Notifications received**:
- `Agent <id> completed` with summary
- Individual agent transcripts available at output file paths

### Phase 4: Cleanup Worktrees

After all PRs are created and pushed:

```bash
# List worktrees
git worktree list

# Remove each worktree
git worktree remove ../worktree-480
git worktree remove ../worktree-483
git worktree remove ../worktree-490

# Verify cleanup
git worktree list  # Should show only main worktree
```

**Important**: Only remove worktrees AFTER:
- All commits are pushed
- All PRs are created
- No uncommitted work remains

## Failed Attempts

### ❌ Attempt 1: Sequential Task Execution
**What we tried**: Process issues one at a time with single agent
**Why it failed**: Would take 3x longer (each task took ~5 minutes)
**Lesson**: Use parallelization when tasks are independent

### ❌ Attempt 2: Parallel Agents Without Worktrees
**What we tried**: Launch multiple agents in same repository
**Why it failed**: Risk of file conflicts, harder to track which agent is doing what
**Lesson**: Worktrees provide clean isolation

### ❌ Attempt 3: Complex In-Place Refactoring (God Class)
**What we tried**: Immediately decompose 2269-line file during audit
**Why it failed**: Too risky for single session, high chance of breaking tests
**Lesson**: For complex refactoring, file GitHub issue + add known-issue comment instead of immediate fix

## Results & Verified Parameters

### Parallel Execution Results

| Agent | Issue | Task | Time | Output |
|-------|-------|------|------|--------|
| a46cc18 | #480 | Core/Discovery tests | 5min 8s | 113 tests, PR #494 |
| a2bf18d | #483 | Config tests | 3min 10s | 67 tests, PR #492 |
| a2dcb18 | #490 | Consolidate calculate_cost | 4min 33s | Refactoring, PR #493 |

**Total time**: ~5 minutes (parallel) vs ~15 minutes (sequential)
**Efficiency gain**: 3x speedup

### Agent Configuration

```python
Task(
    subagent_type="general-purpose",
    description="Short task description (3-5 words)",
    prompt="""
    Detailed multi-line prompt with:
    - Issue context
    - Worktree setup instructions
    - Specific deliverables
    - Success criteria
    - Testing requirements
    """,
    run_in_background=True  # CRITICAL for parallel execution
)
```

### Worktree Branch Naming

```
Format: <issue-number>-<kebab-case-description>

Examples:
- 480-add-core-discovery-tests
- 483-add-config-tests
- 490-consolidate-calculate-cost
```

### PR Creation Pattern

Each agent should create PR with:
```bash
gh pr create \
  --title "type(scope): Brief description" \
  --body "Closes #<issue-number>" \
  --label "appropriate-label"

gh pr merge --auto --rebase  # Enable auto-merge
```

## Recovery from Failures

### Issue: Sub-Agent Gets Stuck
**Symptom**: No progress for >10 minutes
**Solution**:
```bash
# Check output
tail -f /tmp/claude-1000/tasks/<agent-id>.output

# If truly stuck, can resume or kill and restart
```

### Issue: Agent Encounters Merge Conflict
**Symptom**: Git push fails due to conflicts
**Solution**: This shouldn't happen with proper worktree isolation, but if it does:
```bash
cd ../worktree-xxx
git fetch origin main
git rebase origin/main
# Resolve conflicts
git rebase --continue
git push --force-with-lease
```

### Issue: Pre-Existing Test Failures Block CI
**Symptom**: New PRs fail CI due to unrelated test failures
**Solution**:
1. Create separate branch to fix pre-existing failures
2. Fix the failing tests
3. Create PR for test fixes first
4. Once merged, rebase other PRs on updated main

**Example**: We encountered this with 5 failing analysis tests - created PR #495 to fix them first.

## Success Metrics

This workflow is working if:
- ✅ All agents complete without errors
- ✅ Each agent creates independent PR
- ✅ No file conflicts between PRs
- ✅ All PRs pass CI checks
- ✅ Time to completion is ~1/N of sequential (where N = number of parallel tasks)

## Anti-Patterns to Avoid

❌ **Don't** work on same files in multiple agents
❌ **Don't** remove worktrees before pushing commits
❌ **Don't** forget to enable auto-merge on PRs
❌ **Don't** use worktrees for dependent tasks (use sequential execution instead)
❌ **Don't** mix parallel and sequential work - choose one approach per batch

## Related Skills

- `pr-workflow` - How to create and manage PRs
- `github-issue-workflow` - Reading and writing GitHub issues
- `test-driven-development` - Writing tests first

## Tags

`#parallel` `#worktrees` `#sub-agents` `#efficiency` `#git` `#workflow`
