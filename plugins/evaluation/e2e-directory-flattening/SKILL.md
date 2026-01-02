# E2E Directory Flattening

| Field | Value |
|-------|-------|
| Date | 2026-01-02 |
| Objective | Flatten E2E results directory structure, share workspaces, generate hierarchical reports |
| Outcome | Successfully flattened structure with JSON+markdown reports at every level |
| Project | ProjectScylla |

## When to Use

Use this skill when:
- E2E results directories have excessive nesting (e.g., `tiers/T0/` instead of `T0/`)
- Runs are duplicating workspace setup (git clone per run instead of shared)
- You need hierarchical reports with relative links at every level
- Grading materials are duplicated across runs instead of stored once at root
- You want to add CLI options to limit subtests for testing

## Verified Workflow

### Phase 1: Directory Structure Changes

**Before:**
```
results/<experiment>/
├── tiers/
│   └── T0/
│       └── 00/
│           └── run_01/
│               ├── workspace/     # Duplicated per run
│               └── logs/
│                   ├── stdout.log
│                   └── stderr.log
```

**After:**
```
results/<experiment>/
├── prompt.md              # Grading materials at root (uniform)
├── criteria.md
├── rubric.yaml
├── judge_prompt.md
├── report.json            # Hierarchical reports
├── report.md
└── T0/                    # Flat tier directories
    ├── report.json
    ├── report.md
    └── 00/
        ├── workspace/     # Shared across runs
        ├── report.json
        ├── report.md
        └── run_01/
            ├── output.txt
            ├── stdout.log  # Directly in run_dir
            ├── stderr.log
            └── report.json
```

### Phase 2: Key Code Changes

1. **Flatten tier paths** (`runner.py`):
   ```python
   # Before
   tier_dir = self.experiment_dir / "tiers" / tier_id.value
   # After
   tier_dir = self.experiment_dir / tier_id.value
   ```

2. **Share workspace at subtest level** (`subtest_executor.py`):
   ```python
   def run_subtest(...):
       # Create workspace once at subtest level
       workspace = results_dir / "workspace"
       self._setup_workspace(workspace, command_logger)

       for run_num in range(...):
           # Pass shared workspace to each run
           run_result = self._execute_single_run(..., workspace=workspace)
   ```

3. **Remove logs/ subdirectory** (`adapters/base.py`):
   ```python
   def write_logs(self, output_dir, stdout, stderr, agent_log=None):
       # Write directly to output_dir, not output_dir/logs/
       output_dir.mkdir(parents=True, exist_ok=True)
       (output_dir / "stdout.log").write_text(stdout)
       (output_dir / "stderr.log").write_text(stderr)
   ```

4. **Copy grading materials to root** (`runner.py`):
   ```python
   def _copy_grading_materials(self, experiment_dir):
       shutil.copy2(self.config.task_prompt_file, experiment_dir / "prompt.md")
       # Copy criteria.md, rubric.yaml if they exist
       # Create judge_prompt.md template with file path references
   ```

### Phase 3: Hierarchical Reports

Generate JSON + markdown reports at every level with relative links:

```python
# run_report.py - Add functions:
def save_run_report_json(run_dir, run_number, score, grade, passed, cost, duration)
def save_subtest_report(subtest_dir, subtest_id, result: SubTestResult)
def save_tier_report(tier_dir, tier_id, result: TierResult)
def save_experiment_report(experiment_dir, result: ExperimentResult)
```

Each report includes `children` array with relative paths to child reports.

### Phase 4: CLI Option for Testing

Add `--max-subtests` to limit subtests per tier:

```python
# models.py
max_subtests: int | None = None  # Max sub-tests per tier (None = all)

# runner.py
if self.config.max_subtests is not None:
    tier_config.subtests = tier_config.subtests[:self.config.max_subtests]
```

## Failed Attempts

### 1. Judge prompt per-run (incorrect)

**What was tried:** Initially placed `judge_prompt.md` in each run directory.

**Why it failed:** The judge prompt, criteria, and rubric are uniform across ALL tiers/subtests/runs. Duplicating them wastes space and makes updates harder.

**Solution:** Place grading materials at experiment root level once.

### 2. Missed logs/ subdirectory in base.py

**What was tried:** Updated `subtest_executor.py` to pass run_dir directly, but logs still appeared in `logs/` subdirectory.

**Why it failed:** The `write_logs()` method in `adapters/base.py` was creating the `logs/` subdirectory independently.

**Solution:** Update `base.py:write_logs()` to write directly to `output_dir` instead of `output_dir/logs/`.

### 3. Workspace per-run (inefficient)

**What was tried:** Originally each run created its own workspace via git clone.

**Why it failed:** Extremely slow - cloning repository N times per subtest. Also wastes disk space.

**Solution:** Use git worktrees at subtest level, shared across all runs.

## Results & Parameters

### CLI Usage

```bash
# Quick validation (1 tier, 1 run, 2 subtests max)
pixi run python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T0 --runs 1 --max-subtests 2

# Full run with defaults from test.yaml
pixi run python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T0 T1 T2
```

### Files Modified

| File | Change |
|------|--------|
| `runner.py` | Flatten tier paths, copy grading materials, limit subtests |
| `subtest_executor.py` | Workspace at subtest level, run_dir directly |
| `adapters/base.py` | Remove logs/ subdirectory |
| `models.py` | Add `max_subtests` field |
| `run_report.py` | Add hierarchical report functions |
| `llm_judge.py` | Add `build_judge_prompt_with_paths()` |

### Test Verification

```bash
pixi run pytest tests/unit/e2e/ -v  # All 27 tests pass
```
