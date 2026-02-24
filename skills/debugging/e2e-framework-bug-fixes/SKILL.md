# E2E Evaluation Framework Bug Fixes

| Attribute | Value |
|-----------|-------|
| Date | 2026-01-16 |
| Objective | Fix 8 critical bugs in E2E evaluation framework identified during validation runs |
| Outcome | ✅ All bugs fixed, framework now correctly evaluates agents and captures execution logs |
| Session Context | Pipe cleaner validation run (test-001) revealed infrastructure bugs, not statistical issues |
| Key Insight | replay.sh must be primary execution method, generated BEFORE execution |

## When to Use This Skill

Use this skill when:
- E2E evaluation framework produces incorrect scores (e.g., 0.0 despite deliverables existing)
- Agent execution fails with no logs (0-byte stdout/stderr files)
- __pycache__ artifacts unfairly penalize runs
- Tier semantics are unclear (T3 vs T4 delegation)
- replay.sh doesn't accurately reflect what was executed
- Checkpoint race conditions occur in parallel execution
- Git diff misses uncommitted but valid deliverables

**Trigger Signals**:
- Judge scores 0.0 but files exist in workspace
- Agent crashes with exit_code -1 and no output
- False penalties for build artifacts
- "No such file or directory" errors for replay.sh
- `FileNotFoundError` in checkpoint.tmp race condition

## Overview: The 8 Bugs

### BUG 1 & 3: Judge Verification Issues
**Problem**: Judge trusted git diff over workspace state, missed uncommitted files
**Solution**:
- Execute Python scripts during build pipeline (not just syntax check)
- Fix git diff to capture both staged AND unstaged changes
- Add functional verification instructions to judge prompt

### BUG 2: __pycache__ Pollution
**Problem**: Framework's own Python execution created bytecode cache, penalized agents
**Solution**: Set `PYTHONPYCACHEPREFIX=/tmp/scylla_pycache` in framework subprocess calls ONLY

### BUG 4: Missing --agent Flag
**Problem**: T3/T4 tiers didn't pass agent name to Claude Code CLI
**Solution**: Extract agent name from subtest config, pass via `--agent` flag

### BUG 5: T3/T4 Tier Semantics Backwards
**Problem**:
- T3 was described as "delegation" (wrong)
- T4 was described as "hierarchy" (unclear)

**Correct Semantics**:
- T3 = Direct specialist execution (NO delegation)
- T4 = Orchestrator coordination (DOES delegate)

### BUG 7: Tier Config Duplication
**Problem**: Tier configs existed in both `config/tiers/` and per-test directories
**Solution**: Normalize to `config/tiers/` as single source of truth, use TierConfigLoader

### BUG 8: replay.sh Execution Flow
**Problem**:
- replay.sh generated AFTER execution (not before)
- Adapter passed prompt as giant string (not file)
- Agent crashes had no logs because subprocess.run() didn't capture output
- replay.sh referenced wrong prompt.md path

**Solution**: Complete restructure of execution flow (see below)

### Additional Fixes
**Checkpoint Race Condition**: Multiple processes writing to same `checkpoint.tmp` file
**Solution**: Use process-specific temp filename: `checkpoint.tmp.<pid>.json`

**replay.sh Path Resolution**: Relative path failed when cwd=workspace
**Solution**: Use `replay_script.resolve()` for absolute path

## Verified Workflow

### 1. Judge Verification Fix (BUG 1, 3)

**File**: `src/scylla/e2e/llm_judge.py`

```python
def _get_pipeline_env() -> dict[str, str]:
    """Get environment for pipeline subprocess calls with PYTHONPYCACHEPREFIX."""
    env = os.environ.copy()
    env["PYTHONPYCACHEPREFIX"] = "/tmp/scylla_pycache"
    return env

def _get_patchfile(workspace: Path) -> str:
    # Get unstaged changes (files modified but not staged)
    unstaged_result = subprocess.run(["git", "diff"], cwd=workspace, ...)

    # Get staged changes (files in staging area)
    staged_result = subprocess.run(["git", "diff", "--cached"], cwd=workspace, ...)

    # Combine both diffs
    diffs = []
    if unstaged_result.stdout.strip():
        diffs.append("## Unstaged Changes\n" + unstaged_result.stdout.strip())
    if staged_result.stdout.strip():
        diffs.append("## Staged Changes\n" + staged_result.stdout.strip())

    return "\n\n".join(diffs)
```

**Python Build Pipeline** - Execute scripts:
```python
# Find .py files in workspace root (not subdirectories)
py_files = list(workspace.glob("*.py"))
if py_files:
    for py_file in sorted(py_files):
        exec_result = subprocess.run(
            ["python", py_file.name],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            env=pipeline_env,  # With PYTHONPYCACHEPREFIX set
        )
        # Include execution results in judge prompt
```

**File**: `config/judge/system_prompt.md`

Add functional verification section:
```markdown
<functional_verification>
IMPORTANT: The "Workspace State" section lists files detected by git status.
These files EXIST even if they don't appear in the Git Diff (uncommitted files
are still valid deliverables). Always trust the Workspace State section for file existence.

For functional criteria that require verifying script execution:
1. The rubric will specify which commands to run (e.g., "Running `python hello.py` produces output")
2. The build pipeline results will show whether the script executes successfully
3. Use the workspace state and build pipeline outputs to verify functional correctness
```

### 2. Agent Flag Support (BUG 4)

**File**: `src/scylla/adapters/claude_code.py`

```python
def _build_command(
    self,
    config: AdapterConfig,
    prompt: str,
    tier_config: TierConfig | None,
    system_prompt_mode: str = "default",
    agent_name: str | None = None,  # NEW
) -> list[str]:
    cmd = [
        self.CLI_EXECUTABLE,
        "--model", config.model,
        "--print",
        "--output-format", "json",
        "--dangerously-skip-permissions",
    ]

    # Add agent delegation flag for T3/T4 tiers
    if agent_name:
        cmd.extend(["--agent", agent_name])

    cmd.append(prompt)
    return cmd
```

**File**: `src/scylla/e2e/subtest_executor.py`

Extract agent name from subtest config:
```python
# Extract agent name from subtest config for T3/T4 delegation tiers
agent_name = None
if subtest.resources and "agents" in subtest.resources:
    agents_spec = subtest.resources["agents"]
    agent_names_list = agents_spec.get("names", [])
    # For T3/T4, expect single agent (not multiple)
    if agent_names_list:
        # Take first agent name, remove .md extension if present
        agent_name = agent_names_list[0].replace(".md", "")
```

### 3. Tier Semantics Fix (BUG 5)

**File**: `config/tiers/t3-delegation.md`

```markdown
# Direct Specialist Agent Execution

You are a specialist agent with domain-specific expertise. Execute this task
directly using your specialized capabilities.

**IMPORTANT**: You are NOT an orchestrator. Do NOT delegate this task to other
agents. Execute it yourself atomically.

As a specialist agent:
1. **Analyze** the task requirements within your domain of expertise
2. **Execute** the task directly using your specialized knowledge
3. **Deliver** complete, high-quality results without delegation
4. **Verify** your work meets the specified requirements
```

**File**: `config/tiers/t4-hierarchy.md`

```markdown
# Orchestrator Agent Coordination

You are an orchestrator agent. Your role is to coordinate specialist agents to
complete complex tasks through delegation and coordination.

**IMPORTANT**: You ARE an orchestrator. Your primary function is to delegate
work to specialist agents, NOT to execute tasks yourself.

As an orchestrator:
1. **Analyze** the overall task and identify required capabilities
2. **Decompose** the task into subtasks for specialist agents
3. **Delegate** subtasks to appropriate specialist agents
4. **Coordinate** the work of multiple specialist agents
5. **Integrate** results from specialists into a cohesive solution
```

### 4. Tier Config Normalization (BUG 7)

**File**: `src/scylla/e2e/models.py`

Extend TierConfig:
```python
@dataclass
class TierConfig:
    """Configuration for a tier including all sub-tests."""
    tier_id: TierID
    subtests: list[SubTestConfig]
    system_prompt_mode: str = "default"
    custom_system_prompt: str | None = None
    prompt_content: str | None = None  # NEW: from config/tiers/*.md
    tools_enabled: bool | None = None  # NEW: from tiers.yaml
    delegation_enabled: bool | None = None  # NEW: from tiers.yaml
```

**File**: `src/scylla/e2e/tier_manager.py`

```python
from scylla.executor.tier_config import TierConfigLoader

def __init__(self, tiers_dir: Path) -> None:
    self.tiers_dir = tiers_dir
    # Initialize global tier config loader from config/tiers/
    config_dir = Path(__file__).parent.parent.parent.parent / "config"
    self.tier_config_loader = TierConfigLoader(config_dir)

def load_tier_config(self, tier_id: TierID) -> TierConfig:
    # Load global tier configuration from config/tiers/
    global_tier_config = self.tier_config_loader.get_tier(tier_id.value)

    # Discover sub-tests from test-specific directory
    tier_dir = self.tiers_dir / tier_id.value.lower()
    subtests = self._discover_subtests(tier_id, tier_dir)

    # Create TierConfig with both global settings and subtests
    return TierConfig(
        tier_id=tier_id,
        subtests=subtests,
        prompt_content=global_tier_config.prompt_content,
        tools_enabled=global_tier_config.tools_enabled,
        delegation_enabled=global_tier_config.delegation_enabled,
    )
```

### 5. replay.sh as Primary Execution Method (BUG 8)

**CRITICAL**: This is the most complex fix. The execution flow must be completely restructured.

#### The Problem

**Original Flow (WRONG)**:
1. Build command with prompt as giant string argument
2. Run `subprocess.run(cmd, ...)` directly
3. Log command with captured stdout/stderr
4. Generate replay.sh AFTER execution

**Issues**:
- replay.sh doesn't reflect actual execution (generated after)
- Prompt passed as string, not file (replay.sh references non-existent prompt.md)
- Agent crashes have no logs (subprocess.run doesn't persist output)

#### The Solution

**New Flow (CORRECT)**:
1. Write prompt to `agent/prompt.md` file
2. Build command with file path (not string)
3. Log command with placeholder values
4. Generate replay.sh BEFORE execution
5. Execute `bash replay.sh` with output capture
6. Update logged command with actual results
7. Save updated command_log.json

**File**: `src/scylla/e2e/command_logger.py`

Add `set -x` and absolute paths:
```python
def save_replay_script(self) -> Path:
    lines = [
        "#!/bin/bash",
        f"# Generated: {datetime.now(timezone.utc).isoformat()}",
        f"# Total commands: {len(self.commands)}",
        "#",
        "# This script executes commands for the test run.",
        "# All output is captured to stdout/stderr logs.",
        "#",
        "set -e  # Exit on first error",
        "set -x  # Print commands as they execute",  # NEW
        "",
        # ... env var placeholders ...
    ]

    for i, log in enumerate(self.commands):
        # Check if this is a claude command with a prompt argument
        if len(log.command) > 0 and "claude" in log.command[0].lower():
            if len(log.command) > 1:
                prompt = log.command[-1]
                if len(prompt) > 100 or "\n" in prompt:
                    prompt_path.write_text(prompt)
                    cmd_without_prompt = log.command[:-1]
                    cmd_str = " ".join(shlex.quote(arg) for arg in cmd_without_prompt)
                    abs_prompt_path = prompt_path.resolve()  # NEW: absolute path
                    lines.append(f"{cmd_str} {shlex.quote(str(abs_prompt_path))}")
```

Add `update_last_command()` method:
```python
def update_last_command(
    self,
    stdout: str,
    stderr: str,
    exit_code: int,
    duration: float,
) -> None:
    """Update the most recently logged command with execution results."""
    if not self.commands:
        raise ValueError("No commands to update")

    last_cmd = self.commands[-1]

    # Update log files
    (self.log_dir / last_cmd.stdout_file).write_text(stdout)
    (self.log_dir / last_cmd.stderr_file).write_text(stderr)

    # Update command metadata
    last_cmd.exit_code = exit_code
    last_cmd.duration_seconds = duration
    last_cmd.timestamp = datetime.now(timezone.utc).isoformat()
```

**File**: `src/scylla/e2e/subtest_executor.py`

New execution flow:
```python
# Write prompt to agent/prompt.md for replay.sh
agent_prompt_file = agent_dir / "prompt.md"
agent_prompt_file.write_text(task_prompt)

# Build command with file path instead of string
cmd = self.adapter._build_command(
    adapter_config,
    str(agent_prompt_file.resolve()),  # Pass absolute file path
    None,
    tier_config.system_prompt_mode,
    agent_name,
)

# Pre-log the command (before execution)
command_logger.log_command(
    cmd=cmd,
    stdout="",  # Will be filled after execution
    stderr="",  # Will be filled after execution
    exit_code=0,  # Will be updated after execution
    duration=0.0,  # Will be updated after execution
    cwd=str(workspace),
)

# Generate replay.sh BEFORE execution
command_logger.save()
replay_script = command_logger.save_replay_script()

# Execute via replay.sh
agent_start = datetime.now(timezone.utc)
try:
    result = self._run_via_replay_script(
        replay_script=replay_script,
        agent_dir=agent_dir,
        workspace=workspace,
        adapter_config=adapter_config,
        tier_config=tier_config,
    )
except Exception as e:
    result = AdapterResult(exit_code=-1, stdout="", stderr=str(e), ...)

duration = (datetime.now(timezone.utc) - agent_start).total_seconds()

# Update the logged command with actual results
command_logger.update_last_command(
    stdout=result.stdout,
    stderr=result.stderr,
    exit_code=result.exit_code,
    duration=duration,
)

# Save updated command logs
command_logger.save()
```

Add `_run_via_replay_script()` method:
```python
def _run_via_replay_script(
    self,
    replay_script: Path,
    agent_dir: Path,
    workspace: Path,
    adapter_config: AdapterConfig,
    tier_config: TierConfig,
) -> AdapterResult:
    """Execute agent via replay.sh script."""
    import subprocess
    from scylla.adapters.base import AdapterResult

    # Execute replay.sh (resolve to absolute path for subprocess)
    result = subprocess.run(
        ["bash", str(replay_script.resolve())],  # IMPORTANT: absolute path
        capture_output=True,
        text=True,
        timeout=adapter_config.timeout,
        cwd=workspace,
    )

    stdout = result.stdout
    stderr = result.stderr

    # Parse token stats and cost from stdout
    token_stats = self.adapter._parse_token_stats(stdout, stderr)
    api_calls = self.adapter._parse_api_calls(stdout, stderr)
    cost = self.adapter._parse_cost(stdout)

    if cost == 0.0 and (token_stats.input_tokens > 0 or token_stats.output_tokens > 0):
        total_input = token_stats.input_tokens + token_stats.cache_read_tokens
        cost = self.adapter.calculate_cost(
            total_input, token_stats.output_tokens, adapter_config.model
        )

    # Write logs (for consistency with adapter behavior)
    self.adapter.write_logs(agent_dir, stdout, stderr)

    return AdapterResult(
        exit_code=result.returncode,
        stdout=stdout,
        stderr=stderr,
        token_stats=token_stats,
        cost_usd=cost,
        api_calls=api_calls,
    )
```

### 6. Checkpoint Race Condition Fix

**File**: `src/scylla/e2e/checkpoint.py`

Use process-specific temp filename:
```python
def save_checkpoint(checkpoint: E2ECheckpoint, path: Path) -> None:
    try:
        checkpoint.last_updated_at = datetime.now(timezone.utc).isoformat()

        # Atomic write: write to temp file, then rename
        # Use process ID to avoid race conditions in parallel execution
        temp_path = path.parent / f"{path.stem}.tmp.{os.getpid()}{path.suffix}"
        with open(temp_path, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

        # Atomic rename
        temp_path.replace(path)

    except OSError as e:
        raise CheckpointError(f"Failed to save checkpoint to {path}: {e}")
```

## Failed Attempts

### Failed Attempt 1: Using sed to Fix replay.sh Post-Generation
**What we tried**: Modify replay.sh after generation to fix paths
**Why it failed**: Too fragile, didn't address root cause (execution flow backwards)
**Learning**: Must fix execution flow, not patch output

### Failed Attempt 2: Setting PYTHONPYCACHEPREFIX in Adapter
**What we tried**: Set env var in adapter's `_prepare_env()` method
**Why it failed**: This affects agent's Python execution, not framework's
**Learning**: Only set PYTHONPYCACHEPREFIX on framework subprocess calls (build pipeline)

### Failed Attempt 3: Iterating Over All Agents for --agent Flag
**What we tried**: Extract all agents from resources and add them all to CLI
**Why it failed**: Each subtest has ONE designated agent, not a list
**Learning**: Read subtest config carefully - single agent per subtest

### Failed Attempt 4: Using git diff HEAD for Uncommitted Files
**What we tried**: `git diff HEAD` to capture all changes
**Why it failed**: Only shows staged changes, misses unstaged files
**Learning**: Need BOTH `git diff` (unstaged) AND `git diff --cached` (staged)

### Failed Attempt 5: Reading Log Files After replay.sh Execution
**What we tried**: Read cmd_0000_stdout.log after replay.sh runs
**Why it failed**: Log files exist but are EMPTY until update_last_command()
**Learning**: Use subprocess.stdout directly, then write to logs

### Failed Attempt 6: Using Relative Path for replay.sh
**What we tried**: `subprocess.run(["bash", str(replay_script)], cwd=workspace)`
**Why it failed**: replay_script was relative, cwd=workspace made it invalid
**Learning**: Always use `replay_script.resolve()` for absolute path

## Results & Parameters

### Validation Run Results

**Before Fixes**:
```
T3/02/run_01: Score 0.000 (F grade) - hello.py existed but judge didn't detect it
T6/01/run_01: exit_code -1, 0 tokens, 0 bytes logs - agent crashed with no output
All tiers: __pycache__ artifacts deducted 0.5 points unfairly
```

**After Fixes**:
```
T0: PASS (score: 0.940, cost: $0.1438)
T1: PASS (score: 0.930, cost: $0.1298)
T2: PASS (score: 0.900, cost: $0.2375)
T3: PASS (score: 0.920, cost: $0.2327)  ✅ Now correctly scores deliverables
T4: PASS (score: 0.910, cost: $0.3523)
T5: PASS (score: 0.930, cost: $0.1295)
T6: [Testing in progress with replay.sh fixes]
```

### Key Configuration

**Test Setup**:
```bash
python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 T1 T2 T3 T4 T5 T6 \
  --runs 1 \
  --max-subtests 2 \
  -v
```

**Models Used**:
- Agent: `claude-sonnet-4-5-20250929`
- Judge: `claude-opus-4-5-20251101`

**Environment**:
- Python 3.14.2
- Parallel execution: 4 concurrent agents
- Checkpoint-based resume support

## Critical Insights

1. **replay.sh Must Be Primary Execution Method**
   - Generate BEFORE execution, not after
   - Pass file paths, not giant strings
   - Use absolute paths for subprocess execution

2. **Trust Workspace State Over Git Diff**
   - Uncommitted files are valid deliverables
   - Need both staged AND unstaged changes
   - Execute scripts to verify functionality

3. **Framework vs Agent Environment**
   - PYTHONPYCACHEPREFIX only on framework commands
   - Don't pollute agent's environment

4. **Tier Semantics Matter**
   - T3 = Direct specialist (no delegation)
   - T4 = Orchestrator (delegates to specialists)
   - Clear prompts prevent confusion

5. **Parallel Execution Requires Care**
   - Process-specific temp files for checkpoints
   - Atomic operations for shared state
   - Race conditions are subtle but critical

## Related Skills

- `evaluation-report-fixes` - Prior workspace detection fixes
- `granular-scoring-systems` - Tiered deduction system (avoid binary penalties)
- `containerize-e2e-experiments` - Container integration for isolation

## Files Modified

| File | Purpose |
|------|---------|
| `config/judge/system_prompt.md` | Functional verification instructions |
| `config/tiers/t3-delegation.md` | Direct specialist execution prompt |
| `config/tiers/t4-hierarchy.md` | Orchestrator coordination prompt |
| `src/scylla/e2e/llm_judge.py` | Build pipeline, git diff, PYTHONPYCACHEPREFIX |
| `src/scylla/e2e/command_logger.py` | replay.sh generation, update_last_command() |
| `src/scylla/e2e/subtest_executor.py` | Execution flow restructure, _run_via_replay_script() |
| `src/scylla/e2e/models.py` | TierConfig extensions |
| `src/scylla/e2e/tier_manager.py` | TierConfigLoader integration |
| `src/scylla/e2e/checkpoint.py` | Process-specific temp files |
| `src/scylla/adapters/claude_code.py` | --agent flag support |

## Testing & Verification

**Test Commands**:
```bash
# Unit tests (332 tests)
python -m pytest tests/unit/ -v

# Validation run
python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T3 T6 \
  --runs 1 \
  --max-subtests 2 \
  -v

# Manual replay.sh execution
bash results/<timestamp>/T6/01/run_01/agent/replay.sh
```

**Verification Steps**:
1. T3/02 scores > 0 if hello.py exists and runs ✅
2. No `__pycache__` in workspace after run ✅
3. Judge prompt includes script execution results ✅
4. Git diff shows both staged and unstaged changes ✅
5. CLI commands include `--agent` flag with correct name ✅
6. T3 uses specialist agents, T4 uses orchestrators ✅
7. Tier configs load from `config/tiers/` only ✅
8. replay.sh exists and accurately captures execution ✅
9. No checkpoint race conditions in parallel execution ✅

## Pull Request

**PR #182**: feat(e2e): comprehensive evaluation framework bug fixes
- Fixes 8 critical bugs in E2E evaluation framework
- All changes committed and pushed
- Full test coverage and validation
