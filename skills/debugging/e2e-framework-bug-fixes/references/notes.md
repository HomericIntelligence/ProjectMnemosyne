# Session Notes: E2E Framework Bug Fixes

## Session Timeline

1. **Initial Analysis** (2026-01-16T01:48:29)
   - User provided experiment results from validation run
   - Asked for "ultrathink" analysis of what needs fixing before final paper run

2. **User Correction: Focus on Infrastructure**
   - Clarified this is a "pipe cleaner" validation run, NOT for statistical analysis
   - Focus shifted from statistical validity to CODE and INFRASTRUCTURE BUGS
   - Other tests in `tests/fixtures/tests/` will be used for full paper

3. **Bug Identification**
   - Identified 6 bugs initially (BUG 1-5, BUG 7)
   - User provided multiple corrections on implementation approach
   - Added BUG 8 after discovering replay.sh issues

4. **Implementation Phase**
   - Fixed all 8 bugs across multiple commits
   - Ran unit tests (332 passing)
   - Committed changes in 2 main commits

5. **Validation Run Attempt**
   - User ran validation: T6 had $0.00 cost
   - Discovered T6 agent crashed with exit_code -1, 0 tokens
   - Manual replay.sh execution worked! ($0.117 cost, 30k tokens)

6. **Root Cause Discovery**
   - replay.sh references wrong prompt.md path
   - Adapter passes prompt as giant string instead of file
   - Execution flow backwards: replay.sh generated AFTER execution

7. **BUG 8 Fix: Complete Execution Flow Restructure**
   - Write prompt to agent/prompt.md FIRST
   - Generate replay.sh BEFORE execution
   - Execute via `bash replay.sh`
   - Add set -x and absolute paths

8. **Final Validation Run**
   - Two new issues found:
     - replay.sh path resolution (relative vs absolute)
     - Checkpoint race condition in parallel execution
   - Both fixed immediately

## Detailed Bug Analysis

### BUG 1: False Failure (T3/02/run_01)

**Symptom**:
```
Score: 0.000 | Grade: F | Status: FAIL
```

But file EXISTS:
```
/workspace/results/.../T3/02/run_01/workspace/hello.py  (22 lines, valid Python)
```

**Root Cause**:
- Judge sees two conflicting signals:
  1. Workspace State (from `git status`): Lists `hello.py` ✅
  2. Patchfile (from `git diff HEAD`): Only shows symlinks ❌
- Judge incorrectly trusts patchfile over workspace state
- `_get_patchfile()` uses `git diff HEAD` which only shows COMMITTED changes
- `hello.py` was created but never committed (agent crashed before committing)

**Additional Issue**: Agent Crash
```json
{
  "exit_code": -1,
  "stdout": "",
  "stderr": "",
  "token_stats": { "input_tokens": 0, "output_tokens": 0 ... }
}
```

### BUG 2: __pycache__ Artifacts

**Observed**:
```
./workspace/__pycache__/hello.cpython-314.pyc
```

**Problem**: Created by evaluation framework running `python -m compileall`, NOT by agent!

**Rubric Criterion**:
```yaml
P4:
  check: "No build artifacts remaining (__pycache__, *.pyc cleaned up or ignored)"
  points: 0.5
```

Agents unfairly lose 0.5 points for framework's own artifacts.

### BUG 3: Judge Hallucination

Judge reasoning in T3/02/run_01:
```
"no hello.py exists in the workspace root. Verified with 'ls -la /workspace/*.py'
which returned 'No .py files in /workspace root'"
```

**But file DOES exist!** Judge hallucinated the `ls -la` command result.

Judge prompt includes:
1. Workspace state listing (correct: lists hello.py)
2. Git diff showing only symlinks (incorrect: missing uncommitted hello.py)
3. NO direct filesystem verification command

Judge inferred "no hello.py" from git diff instead of trusting workspace state.

### BUG 4: No --agent Flag

**Evidence**: From `scylla/adapters/claude_code.py:160-213`
```python
cmd = [
    self.CLI_EXECUTABLE,
    "--model", config.model,
    "--print",
    "--output-format", "json",
    "--dangerously-skip-permissions",
]
# NO --agent flag is ever added
```

**Current Workaround**: Agents symlinked into `.claude/agents/` with prompt suffix:
```python
prefix = "Maximize usage of the following sub-agents to solve this task:"
```

**Problem**: Only suggests agent usage via prompt - doesn't invoke Claude Code's actual agent infrastructure.

### BUG 5: T3 vs T4 Semantics Backwards

**CORRECT Tier Semantics**:
| Tier | Name | CORRECT Behavior |
|------|------|------------------|
| T3 | Direct Agent | Single specialist agent executes task directly |
| T4 | Orchestration | Orchestrator agent coordinates other agents |

**Current Problem**: Codebase treats both as "delegation" without distinguishing.

### BUG 7: Tier Config Duplication

Tier configurations exist in TWO locations:
1. `config/tiers/` - Global tier definitions
2. `tests/fixtures/tests/<test>/<tier>/` - Per-test tier configs

**Problem**: Violates DRY principle, causes confusion.

### BUG 8: replay.sh Not Executable/Accurate

**Original Flow (WRONG)**:
```
1. Build command with prompt as giant string
2. Run subprocess.run(cmd, ...)
3. Log command with captured stdout/stderr
4. Generate replay.sh AFTER execution
```

**Problems**:
- Adapter passes prompt as giant string: `cmd.append(prompt)`
- replay.sh references `prompt.md` which doesn't exist in workspace
- No stdout/stderr captured when Claude Code fails
- replay.sh generates AFTER execution, can't be used for actual execution

**Evidence**:
```bash
bash results/.../T6/01/run_01/agent/replay.sh
# This works! $0.117 cost, 30k tokens

# But framework execution:
exit_code: -1
stdout: ""
stderr: ""
token_stats: { input_tokens: 0, output_tokens: 0 }
```

Contradiction confirms replay.sh runs different command than original.

## User Corrections

### Correction 1: Statistical Focus → Infrastructure Focus
**User**: "I want to analyze the code and results for flaws, not for statistical validity or complexity... the current test is a dry run"

### Correction 2: PYTHONPYCACHEPREFIX Scope
**User**: "make sure pycache redirect is on all commands run outside of the judges/agents, not instructions to the judges/agents themselves"

My mistake: Proposed modifying `_prepare_env()` in all adapters
Correct: Only set in `llm_judge.py` build pipeline subprocess calls

### Correction 3: Agent Flag Usage
**User**: "the agent name comes from the config, see test-001\t3\01-architecture-design as an example, it isn't supposed to iterate over all agents and add them all"

My mistake: Proposed iterating over all agents
Correct: Extract single agent name from subtest config

### Correction 4: Tier Semantics
**User**: "There is a mistake in the tiers. Tier-3 is direct agent execution, Tier 4 is orchestation agents. This is pretty big"

My mistake: T3 = "delegation", T4 = "hierarchy"
Correct: T3 = direct specialist execution (NO delegation), T4 = orchestrator coordination

### Correction 5: Agent Levels Not Important
**User**: "For bug 6, the agent levels are actually not important, that entire section of code can be removed"

Removed BUG 6 from plan.

### Correction 6: BUG 1 Fix Approach
**User**: "For bug 1: do option 2 and 3. Run what is expected to run and actually inspect the output, not just what the agent said is done"

Execute `python hello.py`, capture output AND fix git diff to include unstaged files.

## Key Discoveries

### Discovery 1: T6 Agent Crash vs replay.sh Success

**Original run**:
```json
{
  "exit_code": -1,
  "stdout": "",
  "stderr": "",
  "token_stats": { "input_tokens": 0, "output_tokens": 0 },
  "cost_usd": 0.0,
  "api_calls": 0
}
```

**Manual replay.sh run**:
```json
{
  "totalCost": "$0.117",
  "totalTokens": 30000,
  "exit_code": 0
}
```

This contradiction proved replay.sh was NOT running the same command as the framework.

### Discovery 2: Execution Flow Must Be Reversed

**Wrong**: Generate replay.sh after execution (current)
**Right**: Generate replay.sh BEFORE execution, then execute it

Benefits:
- replay.sh is single source of truth
- All output properly captured
- Debugging is trivial (just run replay.sh)
- No discrepancy between framework and replay

### Discovery 3: Path Resolution Critical

**First fix attempt**: Using relative path
```python
subprocess.run(["bash", str(replay_script)], cwd=workspace)
```

**Error**:
```
bash: results/2026-01-16T03-16-35-test-001/T6/01/run_01/agent/replay.sh: No such file or directory
```

**Fix**: Use absolute path
```python
subprocess.run(["bash", str(replay_script.resolve())], cwd=workspace)
```

### Discovery 4: Checkpoint Race Condition

**Error**:
```
FileNotFoundError: [Errno 2] No such file or directory:
'results/2026-01-16T03-16-35-test-001/checkpoint.tmp' ->
'results/2026-01-16T03-16-35-test-001/checkpoint.json'
```

**Root Cause**: Multiple parallel processes writing to same `checkpoint.tmp` file

**Timeline**:
1. Process A: Write to checkpoint.tmp
2. Process B: Write to checkpoint.tmp (overwrites A)
3. Process A: Rename checkpoint.tmp → checkpoint.json (success)
4. Process B: Rename checkpoint.tmp → checkpoint.json (FileNotFoundError - file gone!)

**Fix**: Process-specific temp filenames
```python
temp_path = path.parent / f"{path.stem}.tmp.{os.getpid()}{path.suffix}"
```

## Commands Used

### Validation Run
```bash
python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 T1 T2 T3 T4 T5 T6 \
  --runs 1 \
  --max-subtests 2 \
  -v
```

### Unit Tests
```bash
python -m pytest tests/unit/ -v --tb=short
# Result: 332 tests passed (after fixing import issues)
```

### Manual replay.sh Test
```bash
bash results/2026-01-16T03-16-35-test-001/T6/01/run_01/agent/replay.sh
```

### Git Commands
```bash
git add <files>
git commit -m "fix(e2e): <description>"
git push
gh pr create --title "..." --body "..." --label "enhancement"
```

## Commit History

1. **First commit**: Fixes for BUG 1-5, 7 (judge verification, tier semantics, config normalization)
2. **Second commit**: Fix for BUG 8 (replay.sh execution flow restructure)
3. **Third commit**: Fix replay.sh path resolution and checkpoint race condition

## Output Samples

### T3/02/run_01 (Before Fix)
```
Score: 0.000 | Grade: F | Status: FAIL

Judge reasoning:
"no hello.py exists in the workspace root"

Workspace State:
- hello.py (created)

Git Diff:
(only shows 4 symlink files, no hello.py)
```

### T6/01/run_01 (Before Fix)
```json
{
  "exit_code": -1,
  "stdout": "",
  "stderr": "",
  "token_stats": { "input_tokens": 0, "output_tokens": 0 },
  "cost_usd": 0.0,
  "duration_seconds": 298.0
}
```

Log files: All 0 bytes (no output captured)

### T6/01/run_01 replay.sh (Manual Run)
```bash
bash replay.sh
# SUCCESS: $0.117 cost, 30k tokens
```

### Validation Results (After All Fixes)
```
T0: PASS (score: 0.940, cost: $0.1438)
T1: PASS (score: 0.930, cost: $0.1298)
T2: PASS (score: 0.900, cost: $0.2375)
T3: PASS (score: 0.920, cost: $0.2327)  ✅ Fixed!
T4: PASS (score: 0.910, cost: $0.3523)
T5: PASS (score: 0.930, cost: $0.1295)
T6: [Ready for retest with replay.sh fixes]
```

## Related Documentation

- Plan file: `plan-spicy-hugging-babbage.md`
- PR: #182 (feat(e2e): comprehensive evaluation framework bug fixes)
- Container docs: `docs/container-*.md`
- Thinking mode config: `.claude/shared/thinking-mode.md`
