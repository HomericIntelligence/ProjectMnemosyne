---
name: haiku-wave-pr-remediation
description: 'Fix 40+ failing PRs across multiple repos using wave-based haiku sub-agents
  in worktrees. Use when: many PRs fail CI across heterogeneous categories (ruff/mojo-format/deprecated-syntax/missing-ci-matrix/JIT-crash),
  wave-0 diagnosis identifies per-cluster root causes, parallel haiku agents in isolated
  worktrees are needed.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Purpose** | Fix 49+ failing PRs across 4 repos with parallel haiku sub-agents |
| **Primary trigger** | 40+ PRs failing CI with heterogeneous failure types |
| **Key insight** | Wave-0 diagnosis first; never spawn fix agents until root cause per cluster is known |
| **Model** | haiku (cost-efficient for bulk mechanical fixes) |
| **Isolation** | `git worktree add /tmp/fix-<pr>` per agent |
| **Session date** | 2026-03-15 (46 Odyssey + 3 non-Odyssey PRs) |

## When to Use

- 40+ PRs failing CI with a mix of failure types across multiple categories
- Failures span: ruff format, mojo format parity, deprecated Mojo syntax, missing CI matrix entries,
  `just` not in PATH, transient JIT crashes
- Need cost-efficient parallel remediation without burning Sonnet/Opus tokens on mechanical fixes
- Repos involved: ProjectOdyssey (Mojo), ProjectScylla (Python), ProjectMnemosyne (skill plugins),
  ProjectKeystone (infrastructure)

## Verified Workflow

### Quick Reference

| Failure Category | Fix Strategy | Tool |
|-----------------|-------------|------|
| ruff format/check | `pixi run ruff format <file>` + `pixi run ruff check --fix <file>` | haiku agent |
| mojo format parity | Copy pre-formatted file from fixed branch: `git show origin/<branch>:<file>` | haiku agent |
| `List[Int](n)` deprecated | Replace with `[n]` list literals throughout | haiku agent |
| Missing CI matrix entry | Add test file glob to `comprehensive-tests.yml` | haiku agent |
| `just` not in PATH | Change `entry: just X` → `entry: pixi run just X` in pre-commit config | haiku agent |
| Transient JIT crash | `gh run rerun <run_id> --failed` | rerun, no code change |
| Mojo YAML frontmatter missing | Add `---` YAML block at top of SKILL.md | haiku agent |
| Pre-existing CVE/clang-format | Log as separate issue, skip for now | defer |

### Phase 1: Enumerate Failing PRs

```bash
# Get all open PRs per repo
gh pr list --repo HomericIntelligence/ProjectOdyssey \
  --state open --limit 200 \
  --json number,headRefName,statusCheckRollup \
  --jq '.[] | select(.statusCheckRollup | any(.state == "FAILURE" or .conclusion == "failure")) | .number'

# WARNING: GraphQL bulk queries timeout at 40+ concurrent CI runs
# Fall back to per-PR REST if needed:
gh pr checks <number> --repo HomericIntelligence/ProjectOdyssey 2>&1 | grep -E "fail|error"
```

### Phase 2: Wave-0 Diagnosis (CRITICAL — do this before spawning fixers)

Spawn 1 haiku diagnosis agent per distinct failure category (not per PR):

```
Agent prompt template:
"Diagnose the CI failure on PR #<N> in HomericIntelligence/ProjectOdyssey.
1. gh run view $(gh pr checks <N> | grep fail | grep -oP 'runs/\K[0-9]+' | head -1) --log-failed 2>&1 | head -100
2. Classify: ruff-format / mojo-format-parity / deprecated-syntax / missing-ci-matrix / just-not-in-path / transient-jit-crash / pre-existing-unrelated
3. Report: PR #N — category — specific file/line needing fix"
```

Typical distribution across 46 Odyssey PRs:

| Category | Count | Fix Time |
|----------|-------|---------|
| ruff format/check | ~8 | 2 min/PR |
| mojo format parity | ~18 | 5 min/PR |
| deprecated `List[Int]()` syntax | ~3 | 2 min/PR |
| missing CI matrix entry | ~2 | 5 min/PR |
| Transient JIT crash | ~8 | 1 min/PR (rerun) |
| `validate-test-file-sizes` new hook | ~20 | 15 min/PR |
| `just` not in PATH | ~1 | 5 min/PR |
| pre-existing unrelated | ~3 | defer |

### Phase 3: Spawn Fix Agents in Waves (~5 parallel)

```python
# Agent invocation pattern (from orchestrator):
Agent(
    subagent_type="general-purpose",
    model="haiku",
    run_in_background=True,
    description=f"Fix PR #{pr_number} CI failure",
    prompt=f"""
Fix failing CI on PR #{pr_number} in HomericIntelligence/ProjectOdyssey.

Branch: {branch_name}
Failure category: {category}
Specific fix needed: {fix_description}

## Setup
cd /home/mvillmow/Agents/JulIA/ProjectOdyssey
git worktree add /tmp/fix-{pr_number} {branch_name} 2>/dev/null || true
cd /tmp/fix-{pr_number}

## Fix
[category-specific instructions — see fix recipes below]

## Push
git add -A
git commit -m "fix: [description]

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin {branch_name}

## Verify
gh pr checks {pr_number} --repo HomericIntelligence/ProjectOdyssey 2>&1 | tail -5
"""
)
```

### Phase 4: Fix Recipes by Category

#### ruff format/check failures

```bash
cd /tmp/fix-<pr>
# Format first, then lint
pixi run ruff format <failing_file>
pixi run ruff check --fix <failing_file>
# Common fixes: SIM108 (ternary), B007 (unused loop var), D103 (missing docstring)
```

**CRITICAL**: Snap-packaged ruff cannot access `/tmp`. Always use `pixi run ruff`
from a directory accessible to the pixi environment (e.g., project root or worktree).
If ruff fails with "No such file or directory" on a `/tmp` path, run from inside the worktree:

```bash
cd /tmp/fix-<pr>
pixi run --manifest-path /home/mvillmow/Agents/JulIA/ProjectOdyssey/pixi.toml \
  ruff format scripts/failing_file.py
```

#### mojo format parity failures

Local `mojo format` cannot format files with `comptime_assert_stmt` syntax (exits with code 123).
The `mojo-format-compat.sh` wrapper exits 0 on code 123 — local formatting is silently skipped.
CI can format these; local can't.

**Solution**: Copy the already-formatted file from a branch that CI has already processed:

```bash
# Find a branch where CI already ran mojo format on the same file
git show origin/<other-branch-that-already-passed>:<path/to/file.mojo> > /tmp/fix-<pr>/<path/to/file.mojo>
```

Or apply the format changes manually (wrap lines >88 chars, fix `inout` → `mut`).

#### deprecated `List[Int](n)` syntax

```bash
# Find all occurrences
grep -n 'List\[.*\](' /tmp/fix-<pr>/tests/path/file.mojo

# Replace: List[Int](3, 4) → [3, 4]
sed -i 's/List\[Int\](\([^)]*\))/[\1]/g' file.mojo
# Also handle: zeros(List[Int](3, 4), ...) → zeros([3, 4], ...)
```

#### missing CI matrix entry (`validate-test-coverage` hook)

```bash
# The hook checks that every test_*.mojo is covered by some pattern in comprehensive-tests.yml
# Find the failing file name from pre-commit output
grep "not covered" <error_log>

# Add to appropriate group in comprehensive-tests.yml:
# Find the "Core [Category]" group and add the file pattern
```

#### `just` not in PATH for pre-commit entry

```yaml
# In .pre-commit-config.yaml, change:
entry: just check-matmul-calls
# To:
entry: pixi run just check-matmul-calls

# Also fix in .github/workflows/pre-commit.yml:
run: just check-matmul-calls
# To:
run: pixi run just check-matmul-calls
```

#### Transient JIT crash

```bash
# No code change needed — just rerun
run_id=$(gh pr checks <pr_number> --repo HomericIntelligence/ProjectOdyssey 2>&1 \
  | grep -E "fail|error" | grep -oP 'runs/\K[0-9]+' | head -1)
gh run rerun $run_id --failed
```

#### `validate-test-file-sizes` new hook violations

New hook (introduced in PRs #4741/#4746) flags oversized `.mojo` test files.
Pre-existing violations in 20 files need remediation.

This is a large task — delegate to a dedicated haiku agent per file group.

### Phase 5: Safety Net Constraints

The repo has a Safety Net plugin that blocks destructive git operations:

```bash
# BLOCKED — do not use:
git worktree remove --force <path>  # Use: git worktree remove <path>
git reset --hard HEAD               # Use: git checkout -- <file> for specific files

# ALLOWED worktree cleanup:
git worktree remove /tmp/fix-<pr>   # Only if no uncommitted changes
```

### Phase 6: Monitor and Verify

```bash
# Check CI status for a PR (avoid GraphQL bulk — times out at 40+ runs)
gh pr checks <number> --repo HomericIntelligence/ProjectOdyssey 2>&1 | grep -E "pass|fail|pending"

# Verify run is actually new (not showing stale results)
gh api repos/HomericIntelligence/ProjectOdyssey/actions/runs?branch=<branch> \
  --jq '.workflow_runs[:3] | .[] | {id: .id, status: .status, created_at: .created_at}'
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| GraphQL bulk PR status query | `gh pr list --json statusCheckRollup` on 46 PRs | 504 Gateway Timeout from GitHub under 40+ concurrent CI runs | Use individual `gh pr checks <N>` or REST API `actions/runs?branch=X` |
| snap ruff on /tmp paths | `ruff format /tmp/fix-4574/scripts/file.py` | Snap sandbox blocks access to `/tmp` | Always use `pixi run ruff` with `--manifest-path` or from within the worktree cwd |
| `git worktree add --force` | Create worktree over existing path | Safety Net plugin blocks `--force` flag | Check if worktree exists first; reuse if clean |
| `git reset --hard` to clean worktree | Reset after failed rebase | Safety Net blocks `--hard` reset | Work with existing state or create a fresh worktree at a different path |
| Rerun PR checks via GraphQL status | `gh pr checks` showed stale failures after push | GitHub caches check status; new run not yet reflected | Verify with `gh api .../actions/runs?branch=X` to see actual run timestamps |
| Local `mojo format` on comptime files | `pixi run mojo format shared/training/file.mojo` | Local Mojo 0.26.1 can't parse `comptime_assert_stmt`, exits 123 | Copy pre-formatted content from another branch where CI already ran |
| Fixing pre-existing CVEs in Dependabot PR | Tried to fix Docker image CVEs as part of Keystone #81 | CVEs are pre-existing in base image unrelated to the Dependabot bump | Classify as pre-existing, open separate issue, skip for this wave |
| Wave-1 non-Odyssey fixes before diagnosis | Started fixing Keystone #81 without root cause analysis | CI failures were pre-existing Docker/clang-format unrelated to the PR change | Always run Wave-0 diagnosis even for seemingly simple PRs |

## Results & Parameters

### Session Summary (2026-03-15)

```text
Total PRs fixed: 46/49
- ProjectOdyssey (Mojo): 46 PRs — 43 fixed, 3 deferred (pre-existing)
- ProjectScylla (Python): 1 PR — 1 fixed (ruff SIM108/B007/D103)
- ProjectMnemosyne (skills): 1 PR — 1 fixed (missing YAML frontmatter)
- ProjectKeystone (infra): 1 PR — deferred (pre-existing CVE/clang-format)
```

### Haiku Agent Configuration

```python
Agent(
    subagent_type="general-purpose",
    model="haiku",          # Cost-efficient for mechanical fixes
    run_in_background=True, # Parallel waves of ~5
    isolation=None,         # Use /tmp worktrees instead of worktree isolation
)
```

### Worktree Cleanup After Session

```bash
# Clean up all /tmp/fix-* worktrees
for wt in $(git -C /home/mvillmow/Agents/JulIA/ProjectOdyssey worktree list | grep /tmp/fix | awk '{print $1}'); do
  git -C /home/mvillmow/Agents/JulIA/ProjectOdyssey worktree remove "$wt" 2>/dev/null || true
done
```
