---
name: checkpoint-state-machine-resume
description: "Canonical patterns for checkpoint-based resume and recovery across long-running workflows: state-machine guards, intermediate-state recovery, until-resume past-state fixes, experiment-recovery tools, housekeeping verification, completion verification. Use when: (1) building a workflow that must resume mid-run after failure, (2) diagnosing a resume that loads a stale or non-terminal checkpoint, (3) adding completion-verification gates to issue/experiment workflows, (4) integrating retrospective hooks after a recovery operation."
category: tooling
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-local
history: checkpoint-state-machine-resume.history
tags: [merged, checkpoint, resume, state-machine, recovery, workflow-gate]
---
# Checkpoint State Machine Resume

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-05-18 |
| Objective | Canonical patterns for checkpoint/resume workflows across state machines, experiments, and issue lifecycle |
| Outcome | Merged from 5 skills — verified across ProjectScylla and ProjectOdyssey |
| Version | 1.0.0 (M13 consolidation, Epic #1771) |

## When to Use

Apply this skill when:

1. **Building a resumable workflow** — state machine needs to survive mid-run failures and restart cleanly
2. **Diagnosing a stale-checkpoint resume crash** — run loads a checkpoint but fails because it is already past the expected state
3. **Fixing `--until` / early-stop semantics** — equality check `==` misses runs already past the target state
4. **Recovering interrupted experiments** — selectively re-run only failed/incomplete agents or judges, not the full experiment
5. **Verifying housekeeping issues** — git branch/worktree/GitHub artifact cleanup that may already be done out-of-band
6. **Closing orphaned GitHub issues** — PR auto-close automation failed to trigger after merge
7. **Auditing technical debt** — FIXME/TODO comments reference closed issues and need re-tracking

## Verified Workflow

### Part A — `--until` Past-State Fix (state machine guard)

#### A1. Audit All `--until` Check Sites

```python
# BAD: equality misses runs already past the target
if current_run_state == self.config.until_run_state:
    continue

# BAD: in-loop break misses runs already past target
if until_state is not None and new_state == until_state:
    break
```

#### A2. Add an O(1) State-Ordering Helper

```python
# state_machine.py — after _RUN_STATE_SEQUENCE definition
_RUN_STATE_INDEX: dict[RunState, int] = {
    state: idx for idx, state in enumerate(_RUN_STATE_SEQUENCE)
}

def is_at_or_past_state(current: RunState, target: RunState) -> bool:
    """True if current is at or past target in the normal run sequence.

    States outside the sequence (FAILED, RATE_LIMITED) return False so
    they are never silently skipped.
    """
    cur_idx = _RUN_STATE_INDEX.get(current)
    tgt_idx = _RUN_STATE_INDEX.get(target)
    if cur_idx is None or tgt_idx is None:
        return False
    return cur_idx >= tgt_idx
```

#### A3. Early-Return Guard in `advance_to_completion()`

```python
def advance_to_completion(self, tier_id, subtest_id, run_num, actions, until_state=None):
    if until_state is not None:
        current = self.get_state(tier_id, subtest_id, run_num)
        if is_at_or_past_state(current, until_state):
            logger.info(
                f"[{tier_id}/{subtest_id}/run_{run_num:02d}] "
                f"Already at or past --until target: {until_state.value} "
                f"(current: {current.value})"
            )
            return current
    # ... existing while loop ...
```

#### A4. Fix the Pre-Loop Skip Check

```python
# Before (equality — misses past states):
if current_run_state == self.config.until_run_state:
    continue

# After (ordering — catches past states too):
from <package>.state_machine import is_at_or_past_state
if is_at_or_past_state(current_run_state, self.config.until_run_state):
    logger.debug(
        f"Skipping — already at or past --until: "
        f"{self.config.until_run_state.value} (current: {current_run_state.value})"
    )
    continue
```

#### A5. Regression Test

```python
def test_until_skips_run_already_past_target(self, tmp_path: Path) -> None:
    cp = make_checkpoint(
        run_states={"T0": {"00": {"1": RunState.DIFF_CAPTURED.value}}},
    )
    cp_path = tmp_path / "checkpoint.json"
    save_checkpoint(cp, cp_path)
    sm = _build_run_sm(cp, cp_path)
    actions_called: list[RunState] = []

    def tracking_action(state: RunState):
        def _action(): actions_called.append(state)
        return _action

    actions = {s: tracking_action(s) for s in RunState if not is_terminal_state(s)}
    final = sm.advance_to_completion(
        "T0", "00", 1, actions, until_state=RunState.REPLAY_GENERATED
    )
    assert final == RunState.DIFF_CAPTURED  # unchanged
    assert actions_called == []             # nothing ran
```

---

### Part B — Experiment Recovery (selective re-run)

#### B1. Status Classification System

Build distinct enums for execution phases. Use file-existence checks — no process execution needed.

**Agent statuses** (`RunStatus`):

| Status | Meaning |
|--------|---------|
| `completed` | Agent + judge + `run_result.json` all present |
| `results` | Agent finished but `agent/result.json` missing — regenerate only |
| `failed` | Agent ran but failed |
| `partial` | Agent started but incomplete |
| `missing` | Run never started |

**Judge statuses** (`JudgeStatus`):

| Status | Meaning |
|--------|---------|
| `complete` | Agent + judge both valid |
| `missing` | Agent succeeded, judge never ran |
| `failed` | Judge ran but failed |
| `partial` | Judge started but incomplete |
| `agent_failed` | Agent failed — cannot judge |

#### B2. File-Based Classification

```python
def _classify_run_status(run_dir: Path) -> RunStatus:
    if not run_dir.exists():
        return RunStatus.MISSING
    agent_dir = run_dir / "agent"
    agent_output  = agent_dir / "output.txt"
    agent_result  = agent_dir / "result.json"   # CRITICAL — contains token stats + cost
    agent_timing  = agent_dir / "timing.json"
    agent_cmd_log = agent_dir / "command_log.json"
    run_result    = run_dir   / "run_result.json"

    if (agent_output.exists() and agent_output.stat().st_size > 0
            and agent_result.exists() and run_result.exists()):
        return RunStatus.COMPLETED

    if (agent_output.exists() and agent_output.stat().st_size > 0
            and agent_timing.exists() and agent_cmd_log.exists()
            and (not run_result.exists() or not agent_result.exists())):
        return RunStatus.RESULTS
    # ... remaining statuses
```

#### B3. Fast `results`-Status Regeneration (no agent execution)

```python
stdout    = (agent_dir / "stdout.log").read_text()
cmd_log   = json.loads((agent_dir / "command_log.json").read_text())
stdout_j  = json.loads(stdout.strip())
usage     = stdout_j.get("usage", {})

result_data = {
    "exit_code": cmd_log["commands"][0]["exit_code"],
    "stdout": stdout,
    "token_stats": {
        "input_tokens":               usage.get("input_tokens", 0),
        "output_tokens":              usage.get("output_tokens", 0),
        "cache_creation_input_tokens":usage.get("cache_creation_input_tokens", 0),
        "cache_read_input_tokens":    usage.get("cache_read_input_tokens", 0),
    },
    "cost_usd": stdout_j.get("total_cost_usd", 0.0),
    "api_calls": 1,
}
with open(agent_dir / "result.json", "w") as f:
    json.dump(result_data, f, indent=2)
```

Speed: 1 130 files in ~4 s — pure JSON I/O.

#### B4. CLI Design (consistent across agent + judge scripts)

```bash
--dry-run              # Preview without executing
--status <status>      # Filter by status (repeatable)
--tier <tier>          # Filter by tier
--subtest <subtest>    # Filter by subtest
--runs <nums>          # Comma-separated run numbers
-v, --verbose          # Verbose logging
```

---

### Part C — Housekeeping Verification (git / GitHub artifacts)

Use when an issue describes **pure cleanup** with no code deliverables.

#### C1. Confirm Prerequisite PR is Merged

```bash
gh pr view <PR-number> --json state,mergedAt,mergeCommit
git fetch origin
```

If not yet merged, post a blocking comment and stop.

#### C2. Check All Artifacts

```bash
git worktree list | grep <issue-name>
git branch -a | grep <branch-name>
git ls-remote --heads origin <branch-name>
gh issue view <issue-number> --json state
```

#### C3. Perform Remaining Cleanup

```bash
git worktree remove .worktrees/<name>  && git worktree prune
git branch -d <branch-name>
git push origin --delete <branch-name> && git remote prune origin
gh issue close <number> --comment "Closing as superseded by ..."
```

#### C4. Post Verification Comment

```bash
gh issue comment <issue-number> --body "$(cat <<'EOF'
## Cleanup Verification
- PR #<N> merged
- Issue #<N> closed
- `<branch-name>` branch deleted
- `<worktree-path>` worktree removed
No further action required.
EOF
)"
```

#### C5. Empty Verification Commit + PR

```bash
git commit --allow-empty -m "chore(cleanup): verify <description>

Refs #<issue-number>

Co-Authored-By: Claude <noreply@anthropic.com>"

git push -u origin <branch-name>
gh pr create --title "chore(cleanup): verify <description>" \
  --body "Verification task for issue #<N>. All cleanup already complete. Refs #<N>."
```

Pre-commit hooks skip cleanly on empty commits (no files to check).

---

### Part D — Issue Completion Verification (orphaned open issues)

Use when GitHub's auto-close automation failed after a PR merged.

#### D1. Read Issue Context

```bash
gh issue view <number> --comments
```

Issue comments often contain implementation plans confirming completion.

#### D2. Check Git History

```bash
git log --oneline -10
git log origin/main --oneline --grep="<number>" -5
git log origin/main --stat <commit-hash>
```

#### D3. Verify the Closing PR

```bash
gh pr list --search "<number>" --state all --limit 10 \
    --json number,title,state,mergedAt
gh pr view <PR-number> --json body,closingIssuesReferences
```

`closingIssuesReferences` confirms GitHub detected `Closes #<N>` even when automation failed.

#### D4. Manually Close

```bash
gh issue close <number> --comment "<summary of completed work>"
```

#### D5. Clean Up

```bash
rm .claude-prompt-<number>.md
git status
```

---

### Part E — Technical Debt Tracking (FIXME/TODO audit)

#### E1. Discovery

```bash
grep -rn "FIXME\|TODO" --include="*.py" --include="*.mojo" --exclude-dir='.*' .
grep -oP "FIXME\(#\K\d+" --include="*.mojo" -r . | sort -u
gh issue view <number> --json state -q '.state'
```

#### E2. Create Category Issues

```bash
gh label list --limit 50   # check available labels first

gh issue create \
  --title "[Category] Brief description" \
  --body "$(cat <<'EOF'
## Summary
...
## Files Affected
- `path/to/file:line` — description
## Acceptance Criteria
- [ ] ...
## Previous Issues
Replaces closed #XXXX
EOF
)" \
  --label "existing-label"
```

#### E3. Create Tracking Epic

```bash
gh issue create \
  --title "[Epic] Technical Debt Resolution" \
  --body "$(cat <<'EOF'
## Objective
Track and resolve all stale FIXME/TODO comments.
## Child Issues
- [ ] #XXXX — Category 1
- [ ] #YYYY — Category 2
EOF
)"
```

#### E4. Update Source Comments

Use `replace_all` for bulk updates: `FIXME(#OLD)` → `FIXME(#NEW)`.

Verify after:

```bash
grep -rn "#OLD_NUMBER" --include="*.mojo" --exclude-dir='.*' .
# should return empty
```

---

### Quick Reference

| Scenario | Key Entry Point | Critical Gotcha |
|----------|----------------|-----------------|
| Resume crashes past `--until` target | `is_at_or_past_state()` + early-return guard | Use `>=` index comparison, not `==` |
| Classify interrupted experiment runs | `_classify_run_status()` file checks | Always include `agent/result.json` check |
| Regenerate missing metadata fast | Inline JSON from `stdout.log` + `command_log.json` | Do NOT call `regenerate_experiment()` — it reruns judges |
| Housekeeping issue already done | `git ls-remote` + `gh issue view` + empty commit | Use `--allow-empty`; pre-commit hooks skip gracefully |
| Orphaned open issue | `gh pr view --json closingIssuesReferences` | Check both `closingIssuesReferences` AND git log |
| FIXME/TODO audit | `grep -rn` → `gh issue create` per category | Run `gh label list` first; use existing labels only |
| Config field evolution | Check plural vs singular (`judge_models` vs `judge_model`) | Use `paths.py` canonical file list |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|---------------|---------------|----------------|
| `==` equality for `--until` state check | `current_state == until_state` to skip already-done runs | Misses runs past the target; causes crash when context not restored | Use `is_at_or_past_state()` with index ordering; add guard at both the pre-loop site and inside `advance_to_completion()` |
| Classify runs without `agent/result.json` | Only checked `output.txt`, `timing.json`, `run_result.json` | 1,091 runs appeared "complete" but lacked token stats + cost metadata | Always verify ALL required files; use canonical `paths.py` definitions |
| Call `regenerate_experiment(rejudge=True)` for `results` status | Used the existing broad-scope regeneration function | Function ran full judge + rebuild pipeline, not just file creation | Inline targeted operations to avoid unwanted side effects from broad-scope functions |
| Verbose CLI status names | `agent-complete-missing-results`, `never-started`, etc. | Users found them confusing and hard to type repeatedly | Short single-word status names (`results`, `missing`, `partial`, `failed`, `completed`) |
| Access `config.judge_model` (singular) | Called attribute directly | `ExperimentConfig` evolved to `judge_models` (plural list) for consensus voting | Always check current data model; singular → plural migrations require codebase-wide audit |
| Searching for code on housekeeping issue | Looked for source files to modify | Pure git/GitHub cleanup needed no code changes | Read issue category first; "clean up worktree/branch" = check external state, not source |
| Delete branch locally without checking remote | Ran `git branch -d <name>` first | Branch was already gone locally but check is incomplete | Check `git branch -a` AND `git ls-remote` for both local + remote presence |
| Use verbose FIXME labels without checking repo | Created issues with arbitrary label names | `gh issue create` fails with `label not found` | Run `gh label list --limit 50` before creating any issues |

## Results & Parameters

### Performance Reference

| Operation | Time | Execution Type |
|-----------|------|---------------|
| Classify 1,130 runs | ~1 s | File-existence checks only |
| Regenerate 1,130 `agent/result.json` | ~4 s | JSON I/O only — no agents |
| Re-run single agent | ~30 s | Claude Code execution |
| Re-run single judge | ~20 s | Judge evaluation |

### State Machine Design Decisions

1. **`_RUN_STATE_INDEX` at module load** — avoids O(n) `list.index()` in hot paths; sequence is static so precomputation is safe.
2. **`is_at_or_past_state` returns `False` for FAILED/RATE_LIMITED** — terminal states outside the normal sequence should not be silently skipped by `--until` logic; they are handled by `is_complete()`.
3. **Defense in depth** — pre-loop check in the executor is the first guard; early-return inside `advance_to_completion()` is the second, covering callers that bypass the executor.

### Example Recovery Commands

```bash
# Agent recovery
<package-manager> run python scripts/rerun_agents.py <experiment-dir>/ --dry-run
<package-manager> run python scripts/rerun_agents.py <experiment-dir>/ --status failed
<package-manager> run python scripts/rerun_agents.py <experiment-dir>/ --status results  # fast

# Judge recovery
<package-manager> run python scripts/rerun_judges.py <experiment-dir>/ --dry-run
<package-manager> run python scripts/rerun_judges.py <experiment-dir>/ --status missing
<package-manager> run python scripts/rerun_judges.py <experiment-dir>/ --status failed --judge-model opus

# Combined filters
<package-manager> run python scripts/rerun_agents.py <experiment-dir>/ --tier T0 --runs 1,3,5
```

### Housekeeping Issue Quick Commands

```bash
# Verify all artifacts in one pass
git fetch origin
gh pr view <PR> --json state,mergedAt
git worktree list | grep <name>
git ls-remote --heads origin <branch>
gh issue view <number> --json state
```

## Verified On

| Project | Context | Notes |
|---------|---------|-------|
| ProjectScylla | PR fixing `--until` resume bug | 3172 tests pass; coverage 78.29% |
| ProjectOdyssey | Issue #3377, PR #4044 | Housekeeping verification for worktree/branch cleanup |
| ProjectOdyssey | Issue #594, PR #680 | Orphaned issue closure after auto-close automation failure |
| ProjectOdyssey | FIXME/TODO audit — issues #3008–#3016 | 20+ source files updated; Epic #3016 created |
