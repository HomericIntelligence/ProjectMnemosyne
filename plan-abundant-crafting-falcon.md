# Plan: Consolidate Duplicate Artifacts in E2E Evaluation Framework

## Summary

Reduce redundant file duplication in the E2E evaluation output structure by:
1. Running `run_all.sh` once per run (not per judge)
2. Making agent `replay.sh` reference `prompt.md` instead of inlining content
3. Writing judge prompt once per run directory (not per judge)
4. Keeping task prompts in root test directory via symlinks

## Current State (Problems)

| Artifact | Current Location | Duplication |
|----------|-----------------|-------------|
| `run_all.sh` | `run_XX/judge/judge_01/commands/` | Copied per judge (identical content) |
| Agent `replay.sh` | `run_XX/agent/replay.sh` | Inlines full prompt text |
| Judge `prompt.md` | `run_XX/judge/judge_XX/prompt.md` | Copied per judge (identical content) |
| Task prompt | `run_XX/task_prompt.md` | Full copy in every run dir |

## Proposed Structure

```
experiment_dir/
├── prompt.md                    # COPY of original task prompt (immutable snapshot)
└── T0/
    └── 01/
        └── run_01/
            ├── task_prompt.md   # Symlink -> ../../prompt.md
            ├── judge_prompt.md  # Written ONCE (shared by all judges)
            ├── commands/        # MOVED UP from judge_XX/commands/
            │   ├── run_all.sh
            │   ├── python_check.sh
            │   └── ...
            ├── agent/
            │   ├── replay.sh    # References task_prompt.md
            │   └── prompt.md    # Agent prompt file (new)
            └── judge/
                └── judge_01/
                    ├── replay.sh    # References ../judge_prompt.md
                    ├── response.txt
                    └── judgment.json
```

## Implementation Plan

### Change 1: Move `run_all.sh` to run level

**File:** `src/scylla/e2e/llm_judge.py`

- Modify `_save_pipeline_commands()` to accept `run_dir` instead of `judge_dir`
- Move the call from `_save_judge_logs()` to a higher level in the judge orchestration
- Write to `run_XX/commands/` instead of `run_XX/judge/judge_01/commands/`
- Update judge `replay.sh` to reference `../../commands/run_all.sh` if needed

### Change 2: Make agent `replay.sh` reference `prompt.md`

**File:** `src/scylla/e2e/command_logger.py`

- Modify `save_replay_script()` to write the prompt to a separate `prompt.md` file
- Change the replay script to use `claude <options> prompt.md` (claude reads from file directly)
- The logged command history can still include the inline version for debugging

### Change 3: Write judge prompt once per run

**File:** `src/scylla/e2e/llm_judge.py`

- In `_save_judge_logs()`, write `prompt.md` to `run_XX/judge_prompt.md` (run level, not in judge/ subdir)
- Check if file already exists before writing (skip if already written by prior judge)
- Update judge `replay.sh` to reference `../judge_prompt.md` instead of `./prompt.md`

### Change 4: Use symlinks for task prompts in run dirs

**File:** `src/scylla/e2e/subtest_executor.py`

- In `_execute_single_run()` (lines 828-829), change from copying full content to creating a symlink to the experiment-level `prompt.md`
- Handle case where resource_suffix is appended (must write full file in that case, not symlink)

**File:** `src/scylla/e2e/runner.py`

- In `_copy_grading_materials()`, change from symlink to full copy for `prompt.md`:
  ```python
  # Before: symlink to source
  # After: copy content to create immutable snapshot
  shutil.copy(task_prompt_file, experiment_dir / "prompt.md")
  ```
- This ensures experiment results are reproducible even if source files change

## Files to Modify

| File | Changes |
|------|---------|
| `src/scylla/e2e/llm_judge.py` | Changes 1 & 3: Move commands dir, consolidate judge prompt to `judge_prompt.md` |
| `src/scylla/e2e/command_logger.py` | Change 2: Separate prompt file for agent replay |
| `src/scylla/e2e/subtest_executor.py` | Change 4: Symlink task prompts to experiment-level copy |
| `src/scylla/e2e/runner.py` | Change 4: Copy (not symlink) task prompt for immutability |

## Edge Cases

1. **Resource suffix appended to task prompt**: When `resource_suffix` is added (line 825), the modified prompt differs from original - must write full file in this case
2. **Judge prompt differences**: All judges in a run get the same prompt (task + output + workspace state), but different runs may have different outputs - prompt consolidation is per-run only
3. **Resume behavior**: Ensure consolidated files don't break resume functionality
4. **Backward compatibility**: Old results directories won't have new structure

## Verification

1. Run E2E experiment with multiple judges:
   ```bash
   pixi run python scripts/run_e2e_experiment.py \
     --tiers-dir tests/fixtures/tests/test-001 \
     --tiers T0 --runs 2 \
     --add-judge sonnet-4-5 --add-judge haiku-4-5
   ```

2. Verify structure:
   - `run_XX/commands/` exists (not in judge subdirs)
   - `run_XX/judge_prompt.md` exists (shared by all judges)
   - `run_XX/task_prompt.md` is a symlink to `experiment_dir/prompt.md`
   - `experiment_dir/prompt.md` is a copy (not symlink) of original
   - Agent `replay.sh` references separate prompt file

3. Verify replay scripts work:
   ```bash
   cd results/latest/T0/00/run_01
   bash commands/run_all.sh
   bash agent/replay.sh
   bash judge/judge_01/replay.sh  # Should reference ../judge_prompt.md
   ```

4. Run tests:
   ```bash
   pixi run pytest tests/unit/e2e/ -v
   ```
