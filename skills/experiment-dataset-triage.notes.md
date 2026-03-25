# Session Notes: Experiment Dataset Triage

## Date: 2026-03-21

## Context
User needed to analyze ~/fullruns/haiku-2 dataset (47 experiment directories) to determine which parts were paper-ready. Dataset contained tests 001-047, but only 001-007 were relevant for the current paper.

## Key Discoveries

### Dataset Structure
- 47 timestamped experiment directories mapping to test-001 through test-047
- Multiple directories per test (resume attempts with different timestamps)
- Tests 008-047 were for a later paper — deleted to reduce noise

### Completion Assessment (Tests 001-007)
- test-001: 2 directories. Old (2026-03-04) was complete with 1 run/subtest. New (2026-03-18) had 5 runs/subtest, partially complete.
- test-002: Old complete, new marked complete but runs stuck at agent_complete (inconsistent)
- test-003: Old complete, new partially complete
- test-004 through test-007: Only new dirs, varying progress (3-95% remaining)

### Critical Finding: Stale Checkpoints
12 experiments (test-008 through test-021, dated 2026-03-18/19) showed experiment_state=complete and all tier_states=complete, but ALL runs were at replay_generated state — they were never actually executed. Batch run updated state markers but crashed before execution.

### Config Incompatibility
- Old runs: config_hash A, 1 run/subtest (120 total runs)
- New runs: config_hash B, 3-5 runs/subtest (360-600 total runs)
- Merging was not possible due to both hash and structural differences

## Decision: Delete old data, resume new runs
Since configs differed and run counts were incompatible, old directories were deleted. The new 2026-03-18 directories already had significant progress (many runs at agent_complete) and would be resumed to completion.

## Phased Execution Strategy
Script created at ~/fullruns/haiku-2/run_tests.sh with 3 phases:
1. --until agent_complete (5 threads) — agent execution
2. --until diff_captured (2 threads) — diff capture with lower parallelism
3. Full completion (5 threads) — judging and finalization
