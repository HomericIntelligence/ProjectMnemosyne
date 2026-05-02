# Session Notes: E2E Resource Exhaustion Fix

## Date: 2026-03-22

## Context
- haiku-2 experiment run at ~/fullruns/haiku-2/
- 7 tests (test-001 through test-007), 6 Mojo + 1 Python
- run_tests.sh with --threads 15, 3 phases (agent, diff, judge)
- Machine: WSL2, 16GB RAM, 1TB disk (77% used)

## Raw Findings

### Workspace Analysis
- 2,737 workspace directories across 7 tests
- Total: 187GB
- test-001 (Python/Hello-World): 92MB, 577 workspaces
- test-002 (Mojo/modular): 57GB, 360 workspaces
- test-003..007 (Mojo/ProjectOdyssey): 18-44GB each, 360 workspaces each
- ProjectOdyssey repo: 1.4GB, each worktree checkout: ~1.2GB

### Run State Analysis
- test-001: 600 runs, 23 judged (worktree_cleaned), 571 at diff_captured
- test-002: 360 runs, 65 judged, 294 at diff_captured
- test-003,004,006: 360 runs each, 0 judged, all at diff_captured
- test-005: 360 runs, mixed states (some still at agent_complete/replay_generated)
- test-007: 360 runs, mostly at replay_generated (earliest stage)

### Crash Pattern
- run.log ends with heartbeat messages only (process hung)
- No OOM traces in dmesg (WSL2 VM killed by Windows host)
- All model validation attempts timed out (haiku, sonnet, opus)
- Experiment was in Phase 3 (judging) when crash occurred

### Architecture
- Batch: ThreadPoolExecutor(max_workers=threads) in manage_experiment.py
- Per-experiment: tiers sequential, subtests sequential (run_tier_subtests_parallel is actually sequential)
- Agent: subprocess.Popen (claude CLI via replay.sh)
- Judge: subprocess.run (claude CLI with --allowedTools Read,Glob,Grep)
- Build pipeline: under _pipeline_lock (threading.Lock, serializes mojo build)
- Workspace: git worktree add (1.2GB per Mojo checkout)

### Key Code Paths
- stages.py:stage_create_worktree -> workspace_setup.py:_setup_workspace -> git worktree add
- stages.py:stage_execute_agent -> Popen(["bash", replay_script])
- stage_finalization.py:stage_execute_judge ->_call_judge_with_retry -> llm_judge.py:_call_claude_judge -> subprocess.run(["claude", ...])
- stage_finalization.py:stage_cleanup_worktree -> workspace_manager.cleanup_worktree (only for passing runs!)
- stages.py:stage_run_judge_pipeline -> build_pipeline.py:_run_build_pipeline (under _pipeline_lock)
