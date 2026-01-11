# Skill: E2E Artifact Deduplication

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-11 |
| **Objective** | Consolidate duplicate artifacts in E2E evaluation output |
| **Outcome** | ✅ Success - 4 optimizations implemented, ~12KB saved per run with multiple judges |
| **Context** | ProjectScylla E2E evaluation framework |

## When to Use This Skill

Use this skill when you observe:

1. **Duplicate files across judge runs** - Same content repeated in judge_01/, judge_02/, etc.
2. **Large evaluation directories** - Result directories growing unnecessarily due to duplication
3. **Inlined content in scripts** - Long prompts embedded directly in replay scripts
4. **Per-judge artifacts for shared data** - Commands/scripts that don't vary between judges
5. **Symlinks to mutable sources** - Experiment reproducibility concerns with changing source files

## Problem Summary

E2E evaluation frameworks often generate redundant artifacts:

| Issue | Impact | Frequency |
|-------|--------|-----------|
| Judge prompts duplicated per judge | ~7KB × N judges per run | Every run with multiple judges |
| Pipeline commands per judge directory | ~5 files × N judges | Every run |
| Prompts inlined in replay scripts | ~1KB bloat per script | Every agent/judge run |
| Task prompts symlinked to source | Reproducibility risk | Every experiment |

## Verified Workflow

### Change 1: Move Pipeline Commands to Run Level

**Problem**: `run_all.sh` and related scripts duplicated in each judge subdirectory

**Solution**: Move to run-level `commands/` directory

**Files**: `src/scylla/e2e/llm_judge.py`, `src/scylla/e2e/subtest_executor.py`

```python
# In llm_judge.py - Change function signature
def _save_pipeline_commands(run_dir: Path, workspace: Path, language: str = "mojo") -> None:
    """Save all build/lint/test commands as reproducible bash scripts.

    Creates individual scripts for each tool in run_dir/commands/ directory,
    plus a run_all.sh script that executes all tools in sequence.
    Called once per run (not per judge) since results are identical.
    """
    commands_dir = run_dir / "commands"  # Changed from judge_dir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    # ... rest of implementation
```

```python
# In subtest_executor.py - Call after judge runs complete
judgment, judges = self._run_judge(
    workspace=workspace,
    task_prompt=task_prompt,
    stdout=result.stdout,
    judge_dir=judge_dir,
    language=self.config.language,
    rubric_path=rubric_path,
)

# Save pipeline commands once per run (not per judge)
from scylla.e2e.llm_judge import _save_pipeline_commands
_save_pipeline_commands(run_dir, workspace, language=self.config.language)
```

**Result**: Single `run_XX/commands/` directory instead of `run_XX/judge/judge_01/commands/`, etc.

### Change 2: Extract Agent Prompts to Separate Files

**Problem**: Agent replay scripts inline full prompt text (~1KB+)

**Solution**: Extract to `prompt.md`, reference in script

**File**: `src/scylla/e2e/command_logger.py`

```python
def save_replay_script(self) -> Path:
    """Generate an executable bash script to replay all commands.

    For Claude Code commands with prompts, extracts the prompt to a
    separate prompt.md file and references it in the replay script.
    """
    script_path = self.log_dir / "replay.sh"
    prompt_path = self.log_dir / "prompt.md"

    # ... setup code ...

    for i, log in enumerate(self.commands):
        # Check if this is a claude command with a prompt argument
        if len(log.command) > 0 and "claude" in log.command[0].lower():
            if len(log.command) > 1:
                prompt = log.command[-1]
                # Only extract if it looks like a multi-line prompt
                if len(prompt) > 100 or "\n" in prompt:
                    prompt_path.write_text(prompt)
                    # Build command referencing prompt.md instead of inlining
                    cmd_without_prompt = log.command[:-1]
                    cmd_str = " ".join(shlex.quote(arg) for arg in cmd_without_prompt)
                    lines.append(f"{cmd_str} prompt.md")
                    lines.append("")
                    continue

        # Default: quote each argument properly
        cmd_str = " ".join(shlex.quote(arg) for arg in log.command)
        lines.append(cmd_str)
```

**Result**: Agent directory has separate `prompt.md`, replay script uses `claude <opts> prompt.md`

### Change 3: Consolidate Judge Prompts Per Run

**Problem**: Same judge prompt written to each judge subdirectory

**Solution**: Write once to `run_XX/judge_prompt.md`, share across judges

**File**: `src/scylla/e2e/llm_judge.py`

```python
def _save_judge_logs(
    judge_dir: Path,
    prompt: str,
    response: str,
    result: JudgeResult,
    model: str,
    workspace: Path | None = None,
    raw_stdout: str = "",
    raw_stderr: str = "",
    language: str = "mojo",
) -> None:
    judge_dir.mkdir(parents=True, exist_ok=True)

    # Save the prompt to run level (shared by all judges) - write once
    # judge_dir is e.g. run_01/judge/judge_01/, so go up 2 levels to get run_dir
    run_dir = judge_dir.parent.parent
    judge_prompt_path = run_dir / "judge_prompt.md"
    if not judge_prompt_path.exists():
        judge_prompt_path.write_text(prompt)

    # ... rest of implementation ...

    # Update replay script to reference shared prompt
    replay_content = f"""#!/usr/bin/env bash
# Replay judge evaluation

set -euo pipefail

JUDGE_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"

# Re-run Claude CLI with the same prompt and model (shared judge_prompt.md at run level)
claude \\
  --model {model} \\
  --prompt "$JUDGE_DIR/../../judge_prompt.md" \\
  > "$JUDGE_DIR/response.txt"

echo "Judge response saved to $JUDGE_DIR/response.txt"
"""
```

**Result**: Single `run_XX/judge_prompt.md` file, judges reference `../../judge_prompt.md`

### Change 4: Use Immutable Task Prompt Copies

**Problem**: Task prompts symlinked to source tree (can change after experiment)

**Solution**: Copy to experiment directory for immutability

**Files**: `src/scylla/e2e/runner.py`, `src/scylla/e2e/subtest_executor.py`

```python
# In runner.py - Copy instead of symlink
def _copy_grading_materials(self, experiment_dir: Path) -> None:
    # Copy task prompt (immutable snapshot for reproducibility)
    prompt_path = experiment_dir / "prompt.md"
    if self.config.task_prompt_file.exists():
        import shutil
        shutil.copy(self.config.task_prompt_file, prompt_path)
        logger.debug(f"Copied task prompt to {prompt_path}")
```

```python
# In subtest_executor.py - Symlink to experiment copy when possible
resource_suffix = self.tier_manager.build_resource_suffix(subtest)
prompt_file = run_dir / "task_prompt.md"

if resource_suffix:
    # Resource suffix modifies the prompt - must write full content
    task_prompt = f"{task_prompt}\n\n{resource_suffix}"
    prompt_file.write_text(task_prompt)
else:
    # No modification - symlink to experiment-level copy for deduplication
    experiment_prompt = self.experiment_dir / "prompt.md"
    if experiment_prompt.exists():
        prompt_file.symlink_to(experiment_prompt.resolve())
    else:
        # Fallback: write full content if experiment copy doesn't exist
        prompt_file.write_text(task_prompt)
```

**Result**: Experiment-level copy ensures reproducibility, run-level symlinks when possible

## Failed Attempts

### ❌ Attempt 1: Writing judge_prompt.md to judge/ subdirectory

**What we tried**: Initially placed `judge_prompt.md` at `run_01/judge/judge_prompt.md`

```python
# WRONG - places file in judge/ subdir
run_dir = judge_dir.parent  # Only goes up 1 level
judge_prompt_path = run_dir / "judge_prompt.md"
```

**Why it failed**:
- `judge_dir` is `run_01/judge/judge_01/`
- `judge_dir.parent` is `run_01/judge/` (still inside judge directory)
- Should be at `run_01/judge_prompt.md` (run level, not in judge/ subdir)

**Fix**: Go up 2 levels instead of 1

```python
# CORRECT - places file at run level
run_dir = judge_dir.parent.parent  # Goes up 2 levels
judge_prompt_path = run_dir / "judge_prompt.md"
```

**Lesson**: Carefully trace directory structures when using `parent` navigation. The judge directory has deeper nesting than expected (`run_XX/judge/judge_01/` = 3 levels deep).

### ❌ Attempt 2: Using single `../` in judge replay script

**What we tried**: Used `../judge_prompt.md` in judge replay script

```bash
claude \
  --model {model} \
  --prompt "$JUDGE_DIR/../judge_prompt.md" \  # WRONG - looks in judge/ dir
  > "$JUDGE_DIR/response.txt"
```

**Why it failed**:
- `JUDGE_DIR` is `run_01/judge/judge_01/`
- `../` goes to `run_01/judge/`
- But `judge_prompt.md` is at `run_01/` (one more level up)

**Fix**: Use `../../` to go up two levels

```bash
claude \
  --model {model} \
  --prompt "$JUDGE_DIR/../../judge_prompt.md" \  # CORRECT
  > "$JUDGE_DIR/response.txt"
```

**Lesson**: Match the relative path depth to the directory structure. If file is 2 levels up, use `../../`.

## Results & Parameters

### Final Directory Structure

```
experiment_dir/
├── prompt.md                    # COPY of original (immutable)
└── T0/00/run_01/
    ├── judge_prompt.md          # Written ONCE (7KB, shared)
    ├── task_prompt.md           # Symlink or full copy
    ├── commands/                # At run level
    │   ├── run_all.sh
    │   ├── python_check.sh
    │   ├── python_format.sh
    │   ├── python_test.sh
    │   └── precommit.sh
    ├── agent/
    │   ├── replay.sh            # "claude <opts> prompt.md"
    │   └── prompt.md            # Extracted (1.1KB)
    └── judge/
        ├── judge_01/
        │   ├── replay.sh        # References ../../judge_prompt.md
        │   ├── response.txt
        │   └── judgment.json
        └── judge_02/
            └── replay.sh        # References ../../judge_prompt.md
```

### Space Savings

| Optimization | Before | After | Savings per Run |
|-------------|--------|-------|-----------------|
| Judge prompts | 7KB × N judges | 7KB × 1 | ~7KB × (N-1) judges |
| Pipeline commands | 5 files × N judges | 5 files × 1 | ~5 files × (N-1) |
| Agent prompts | Inlined (~1KB) | Extracted | Better readability |
| Task prompts | Multiple copies | Shared via symlink | Varies by tier |

**Example with 3 judges**: ~14KB + 10 files saved per run

### Verification Command

```bash
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 --max-subtests 1 --runs 1 \
  --add-judge sonnet-4-5 --add-judge haiku-4-5 \
  -v
```

### Expected Outcomes

1. ✅ Single `run_XX/commands/` directory (not per judge)
2. ✅ Single `run_XX/judge_prompt.md` file (not per judge)
3. ✅ Agent `replay.sh` references `prompt.md` file
4. ✅ Experiment `prompt.md` is a copy (not symlink)
5. ✅ All replay scripts work correctly
6. ✅ All judges complete successfully

### Test Results

- **Exit code**: 0 (success)
- **Score**: 0.900 (excellent quality)
- **Judges**: Opus, Sonnet, Haiku all working
- **Duration**: ~12 minutes for multi-judge run

## Key Insights

1. **Understand directory nesting depth**: When using `parent` navigation, trace the full path to ensure you're at the right level
2. **Extract large strings from scripts**: Improves readability and makes diffs cleaner
3. **Share read-only artifacts**: If content is identical across runs/judges, write once and reference
4. **Copy for immutability**: Symlinks to source trees can change; copies ensure reproducibility
5. **Test with multiple judges**: Essential to verify prompt sharing and deduplication work correctly

## Related Files

- `src/scylla/e2e/llm_judge.py` - Judge prompt consolidation, pipeline commands
- `src/scylla/e2e/command_logger.py` - Agent prompt extraction
- `src/scylla/e2e/runner.py` - Experiment-level prompt copying
- `src/scylla/e2e/subtest_executor.py` - Run-level task prompt handling, pipeline command orchestration

## References

- PR: #176 on HomericIntelligence/ProjectScylla
- Branch: `refactor/judge-prompt-consolidation`
- Commit: `24e1642` - refactor(e2e): Consolidate duplicate artifacts in evaluation output
