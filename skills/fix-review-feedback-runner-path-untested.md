---
name: fix-review-feedback-runner-path-untested
description: Pattern for fixing a test that calls an internal delegate directly instead of through the runner entry point, when the issue requirement specifies the entry point must be exercised
category: testing
date: 2026-03-02
version: 1.0.0
user-invocable: false
---
# Skill: Fix Review Feedback — Runner Path Untested (Direct Delegate Test)

## Overview

| Item | Details |
| ------ | --------- |
| **Date** | 2026-03-02 |
| **Objective** | Add a runner-level integration test that exercises `_initialize_or_resume_experiment()` to satisfy issue requirement #3, which tests called `ResumeManager.handle_zombie()` directly instead |
| **Context** | PR #1312 review feedback for issue #1224 — zombie detection integration tests bypassed the full runner path |
| **Outcome** | ✅ One test added (`TestRunnerInitializeWithZombieCheckpoint`); 12 tests pass; pre-commit clean |
| **PR** | #1312 (review fix committed to branch `1224-auto-impl`) |

## When to Use This Skill

Use this pattern when:

1. **An issue requirement says "calls `X()`"** but the existing test calls the internal delegate of `X()` directly
2. **A reviewer flags that the full entry-point path is untested** — the code works but the integration path is never exercised
3. **A test instantiates a helper class (e.g. `ResumeManager`) directly** to avoid wiring up the parent class (`E2ERunner`)
4. **Option A vs Option B** is available: always choose Option A (add the runner-level test) over Option B (update PR description to explain why direct test is sufficient)

**Trigger phrases:**
- "issue says calls `runner._initialize_or_resume_experiment()` but test calls `handle_zombie()` directly"
- "full integration path through the runner is never exercised"
- "tests `ResumeManager` directly — runner path untested"
- "gap between issue requirement and implementation scope"

## Verified Workflow

### Step 1: Read `_initialize_or_resume_experiment()` to understand the wiring

```bash
grep -n "_initialize_or_resume_experiment\|def __init__\|class E2ERunner" scylla/e2e/runner.py | head -20
```

Key facts to note:
- `_find_existing_checkpoint()` searches `self.results_base_dir` for dirs matching `*-{experiment_id}`
- `_load_checkpoint_and_config()` loads `{experiment_dir}/config/experiment.json` if it exists
- `_write_pid_file()` writes `{experiment_dir}/experiment.pid` — safe side effect, no mocking needed

### Step 2: Construct the minimal test fixture on disk

The test must create:
1. `results_base_dir / f"{timestamp}-{experiment_id}" /` — triggers discovery
2. `exp_dir / "config" / "experiment.json"` — required by `_load_checkpoint_and_config()`
3. `exp_dir / "checkpoint.json"` — the zombie checkpoint

```python
experiment_id = "test-zombie-runner"
results_base_dir = tmp_path / "results"

# Create experiment directory matching the *-{experiment_id} discovery pattern
exp_dir = results_base_dir / f"20260101T000000-{experiment_id}"
exp_dir.mkdir(parents=True)
config_dir = exp_dir / "config"
config_dir.mkdir()

# Write a minimal experiment.json so _load_checkpoint_and_config() can restore config
experiment_config_data = {
    "experiment_id": experiment_id,
    "task_repo": "https://github.com/example/repo",
    "task_commit": "abc1234",
    "task_prompt_file": str(tmp_path / "prompt.md"),
    "language": "python",
    "tiers_to_run": [],
}
(config_dir / "experiment.json").write_text(json.dumps(experiment_config_data))

# Write a zombie checkpoint: status=running, dead PID, stale heartbeat
cp = make_checkpoint(
    status="running",
    pid=999_999_999,          # guaranteed dead — Linux max PID is 4,194,304
    last_heartbeat=_stale_heartbeat(),   # 300s ago, well past 120s timeout
    experiment_dir=str(exp_dir),
)
save_checkpoint(cp, exp_dir / "checkpoint.json")
```

### Step 3: Instantiate `E2ERunner` and call the entry point

```python
config = ExperimentConfig(
    experiment_id=experiment_id,
    task_repo="https://github.com/example/repo",
    task_commit="abc1234",
    task_prompt_file=tmp_path / "prompt.md",
    language="python",
    tiers_to_run=[],
)

tiers_dir = tmp_path / "tiers"
tiers_dir.mkdir()

runner = E2ERunner(
    config=config,
    tiers_dir=tiers_dir,
    results_base_dir=results_base_dir,
)

runner._initialize_or_resume_experiment()

assert runner.checkpoint is not None
assert runner.checkpoint.status == "interrupted"
```

### Step 4: Add the import and run the tests

```python
# Add to imports at top of test file
import json
from scylla.e2e.runner import E2ERunner
```

```bash
pixi run python -m pytest tests/integration/e2e/test_zombie_resume.py -v
```

All 12 tests (11 original + 1 new) should pass.

### Step 5: Run pre-commit and commit

```bash
pre-commit run --files tests/integration/e2e/test_zombie_resume.py
git add tests/integration/e2e/test_zombie_resume.py
git commit -m "fix: Address review feedback for PR #NNNN

Add TestRunnerInitializeWithZombieCheckpoint integration test that calls
runner._initialize_or_resume_experiment() directly, exercising the full
path from checkpoint discovery through ResumeManager.handle_zombie() to
verify zombie status is reset to 'interrupted'.

Closes #NNNN

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

| Parameter | Value |
| ----------- | ------- |
| File changed | `tests/integration/e2e/test_zombie_resume.py` |
| Lines changed | +66 insertions |
| New imports | `import json`, `from scylla.e2e.runner import E2ERunner` |
| New class | `TestRunnerInitializeWithZombieCheckpoint` |
| Tests in file | 12 (all pass) |
| Pre-commit hooks | All pass |
| Commit message prefix | `fix: Address review feedback for PR #NNNN` |

## Root Cause Pattern

When issue requirements specify "calls `runner.X()`", tests that only call the internal
delegate of `X()` satisfy unit-level correctness but leave the discovery/wiring path untested.
The reviewer is right to flag this — the runner's `_find_existing_checkpoint()` → `_load_checkpoint_and_config()` → `ResumeManager.handle_zombie()` chain could silently break if any wiring step is wrong.

**Discovery heuristic:** When an issue says "calls `runner.Y()`" but the test does:

```python
rm = ResumeManager(checkpoint, config, tier_manager)
rm.delegate_method(...)
```

...the runner's discovery and wiring of `delegate_method` is untested. Add a runner-level test.
