---
name: worktree-migration-testing-patterns
description: "Use when: (1) migrating command workflows from clone/rm-rf pattern to git worktree isolation, (2) batch auto-merging and rebasing open PRs, (3) writing integration tests that assert on real SKILL.md files in a worktree, (4) verifying transformation scripts are idempotent on production files."
category: tooling
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [worktree, migration, clone-to-worktree, integration-tests, idempotency, auto-merge]
---
# Worktree Migration and Testing Patterns

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-03-28 | Consolidated migration and testing skills | Merged from tooling-pr-auto-merge-worktree-command-migration, worktree-integration-test-pattern |

Covers two related patterns: (1) migrating clone-based workflows (setup + `rm -rf` teardown) to
proper git worktree lifecycle management, including batch PR auto-merge as a companion task;
(2) writing integration tests that operate on real committed SKILL.md files accessed through
worktree paths, with idempotency assertions.

## When to Use

- Command files reference `rm -rf` on shared directories like `$HOME/.agent-brain/`
- Multiple open PRs need auto-merge enabled and rebasing before a migration PR lands
- Adding regression tests for SKILL.md transformation/validation scripts
- Test module needs to import scripts that only exist in the main repo (not in worktrees)
- Verifying that fix functions are idempotent (second pass returns `modified=False`)
- Guarding against regressions on real-world file shapes vs. synthetic fixtures

## Verified Workflow

### Quick Reference

```bash
# Batch enable auto-merge on all open PRs
gh pr list --state open --json number --jq '.[].number' --limit 1000 | \
  while read pr; do gh pr merge "$pr" --auto --rebase; done

# Rebase a PR branch using a temporary worktree (avoids pre-push hooks)
git worktree add /tmp/rebase-pr-<number> origin/<branch>
git -C /tmp/rebase-pr-<number> rebase origin/main
git -C /tmp/rebase-pr-<number> push --force-with-lease origin <branch>
git worktree remove /tmp/rebase-pr-<number>

# Worktree pattern for /learn (replaces clone+rm-rf)
MNEMOSYNE_BASE="$(git rev-parse --show-toplevel)"
git -C "$MNEMOSYNE_BASE" worktree add /tmp/mnemosyne-skill-<name> -b skill/<name> origin/main
cd /tmp/mnemosyne-skill-<name>
# ... do work ...
git -C "$MNEMOSYNE_BASE" worktree remove /tmp/mnemosyne-skill-<name>
git -C "$MNEMOSYNE_BASE" worktree prune
```

### Part A: Migrating Clone-Based Workflows to Worktrees

**When a command file does this (old pattern):**
```markdown
## Clone location
Clone to: $HOME/.agent-brain/ProjectMnemosyne/

## Setup
git clone <url> $HOME/.agent-brain/ProjectMnemosyne/
cd $HOME/.agent-brain/ProjectMnemosyne/
git checkout -b skill/<name>

## Cleanup
rm -rf $HOME/.agent-brain/ProjectMnemosyne/
```

**Replace with this (worktree pattern):**
```markdown
## Work isolation
Git worktrees (ephemeral, auto-cleaned)

## Setup
MNEMOSYNE_BASE="$(git rev-parse --show-toplevel 2>/dev/null || \
  find $HOME -name '.git' -maxdepth 4 -path '*/ProjectMnemosyne/.git' | head -1 | xargs dirname)"
WORKTREE_PATH="/tmp/mnemosyne-skill-$(date +%s)"
git -C "$MNEMOSYNE_BASE" worktree add "$WORKTREE_PATH" -b skill/<name> origin/main
cd "$WORKTREE_PATH"

## Cleanup
git -C "$MNEMOSYNE_BASE" worktree remove "$WORKTREE_PATH"
git -C "$MNEMOSYNE_BASE" worktree prune
```

**Migration steps:**

1. Replace `**Clone location**` headers with `**Work isolation**: Git worktrees`
2. Replace clone+checkout setup block with: detect base repo → `git worktree add` → work in worktree
3. Replace `rm -rf` cleanup with `git worktree remove` + `git worktree prune`
4. Remove "Never delete ~/.agent-brain/" guardrail notes (worktree pattern makes deletion irrelevant)
5. Add stale worktree troubleshooting to Common Issues section
6. For **read-only commands** (e.g., /advise): keep persistent cache, just remove deletion references

**Companion task — batch PR auto-merge:**

Before merging the migration PR, unblock all stale open PRs:

```bash
# Step 1: Enable auto-merge on all open PRs
gh pr list --state open --json number --jq '.[].number' --limit 1000 | \
  while read pr; do gh pr merge "$pr" --auto --rebase; done

# Step 2: Handle errors
# "clean status" — PR was already eligible for immediate merge → retry once
# "unstable status" — CI still running → wait and retry, or let auto-merge handle it
# "Protected branch rules not configured" → gh pr edit <pr> --base main

# Step 3: Parallel rebase with worktree agents (split PRs into batches of 4-5)
# Each agent: fetch branch → rebase onto origin/main → force-push with --force-with-lease
# Uses Agent(isolation: "worktree") or manual worktree creation

# Step 4: Clean up worktrees after agents complete
git worktree prune
```

**gh pr merge error codes:**

| Error | Meaning | Action |
|-------|---------|--------|
| "clean status" | PR already eligible for merge | Retry — may have merged immediately |
| "unstable status" | CI still running | Wait and retry, or let auto-merge handle |
| "Protected branch rules not configured" | PR targets non-main branch | `gh pr edit <pr> --base main` |

### Part B: Integration Tests Against Worktree Files

**Problem**: Transformation scripts live only in the main repo checkout, not in worktrees.
Tests must import them while also accessing real SKILL.md fixture files from the worktree.

**Minimal pattern:**

```python
import subprocess
import sys
from pathlib import Path

def _find_scripts_dir() -> Path:
    """Resolve scripts from standard clone location or git worktree."""
    # Standard clone: $HOME/.agent-brain/ProjectMnemosyne/scripts
    standard = Path.home() / ".agent-brain" / "ProjectMnemosyne" / "scripts"
    if standard.exists():
        return standard
    # Fallback: resolve git common dir (the main repo root from any worktree)
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        capture_output=True, text=True
    )
    git_dir = Path(result.stdout.strip())
    return git_dir.parent / "scripts"

sys.path.insert(0, str(_find_scripts_dir()))
from fix_remaining_warnings import fix_skill_file, has_orphan_quick_reference
```

**Point tests at real committed fixtures (not synthetic strings):**

```python
# Use actual committed SKILL.md as the test fixture
FIXTURE = (
    Path(__file__).parent.parent / "skills" / "worktree-create.md"
)
# The fixture must be committed to the repo so CI can find it.
```

**Six-test checklist for any SKILL.md transformer:**

```python
class TestRealFileIntegration:

    def test_fixture_file_exists(self) -> None:
        """Always add this first — clear failure message if fixture is missing."""
        assert FIXTURE.exists(), f"Fixture not found: {FIXTURE}"

    def test_real_file_has_condition_before_fix(self) -> None:
        """Assert initial condition directly on real file (read-only)."""
        content = FIXTURE.read_text(encoding="utf-8")
        assert has_orphan_quick_reference(content) is True

    def test_fix_returns_modified_true(self, tmp_path: Path) -> None:
        """Always copy to tmp_path before calling mutating functions."""
        target = tmp_path / "SKILL.md"
        shutil.copy2(FIXTURE, target)
        modified, fixes = fix_skill_file(target)
        assert modified is True
        assert len(fixes) > 0

    def test_fix_removes_condition(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        shutil.copy2(FIXTURE, target)
        fix_skill_file(target)
        assert has_orphan_quick_reference(target.read_text(encoding="utf-8")) is False

    def test_round_trip_no_data_loss(self, tmp_path: Path) -> None:
        """Key content must survive the transformation."""
        original = FIXTURE.read_text(encoding="utf-8")
        target = tmp_path / "SKILL.md"
        shutil.copy2(FIXTURE, target)
        fix_skill_file(target)
        result = target.read_text(encoding="utf-8")
        assert result != original  # file was actually changed
        for snippet in ["create_worktree.sh", "git worktree list"]:
            assert snippet in result

    def test_fix_is_idempotent(self, tmp_path: Path) -> None:
        """Second pass must return modified=False with identical content."""
        target = tmp_path / "SKILL.md"
        shutil.copy2(FIXTURE, target)
        fix_skill_file(target)
        content_after_first = target.read_text(encoding="utf-8")
        modified, _ = fix_skill_file(target)
        assert modified is False
        assert target.read_text(encoding="utf-8") == content_after_first
```

**Run tests:**

```bash
pixi run python -m pytest tests/test_quick_reference_transform.py -v
# Expected: 6 passed
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `gh pr merge --auto --rebase` on "clean status" PRs | First attempt returned "Pull request is in clean status" error | PR was already eligible for immediate merge — GitHub attempted to merge | Retry once; the PR either merged or needs a second `gh pr merge --auto` call |
| Enable auto-merge on "unstable" PR | `gh pr merge 987 --auto --rebase` returned "unstable status" | CI was still running after rebase push | Wait for CI to complete, then retry |
| Single sequential rebase for 14 PRs | Considered sequential processing | Too slow for batch operations | Use 3 parallel worktree-isolated agents (batches of 4-5 PRs each) |
| Full worktree migration for read-only /advise | Considered replacing .agent-brain cache with worktrees for /advise too | Advise is read-only — worktree isolation adds complexity with no benefit | Apply KISS: keep persistent cache for read-only operations, use worktrees only for write operations |
| Relative sys.path from worktree root | `Path(__file__).parent.parent / "build" / "ProjectMnemosyne" / "scripts"` | `build/` does not exist in worktrees — only in main repo checkout | Use `git rev-parse --git-common-dir` to resolve the main repo root first |
| Edit real fixture file in mutating test | Called `fix_skill_file(FIXTURE)` directly | Modifies the committed fixture; before-state test fails on second run | Always copy to `tmp_path` before calling any mutating function |
| Single broad test | One test checking before + fix + after in sequence | Failure is hard to diagnose; unclear which assertion broke | Use separate focused test methods per assertion |

## Results & Parameters

### Migration Results (ProjectMnemosyne)

```yaml
total_prs: 14
auto_merge_enabled: 14/14
merged_during_session: 13/14
remaining: 1 (auto-merging, transient UNKNOWN state)
conflicts: 0
parallel_rebase_agents: 3
prs_per_agent: 4-5
rebase_time: ~2 minutes
```

### Files Modified for Worktree Migration

```
plugins/tooling/mnemosyne/commands/learn.md   # Primary: new worktree setup + cleanup
plugins/tooling/mnemosyne/commands/advise.md  # Minor: remove "Never delete" note
CLAUDE.md                                     # Update workflow description
```

### Integration Test Checklist

```
[ ] Fixture file is committed to repo (CI can find it)
[ ] test_fixture_file_exists() added as first test
[ ] All mutating tests use tmp_path copies
[ ] Idempotency test included
[ ] Round-trip data loss test included
[ ] _find_scripts_dir() handles both clone and worktree paths
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | 14 PRs auto-merged + worktree migration PR #991 | tooling-pr-auto-merge-worktree-command-migration 2026-03-25 |
| ProjectMnemosyne | Integration tests for fix_remaining_warnings.py | worktree-integration-test-pattern 2026-03-15 |
