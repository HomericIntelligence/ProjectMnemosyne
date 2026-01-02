# Tier Ablation Testing

| Attribute | Value |
|-----------|-------|
| Date | 2026-01-02 |
| Objective | Run comprehensive tier ablation study across 7 evaluation tiers (T0-T6) with ~114 sub-tests |
| Outcome | Successfully validated tier infrastructure, discovered CLI argument limit bug in T6 |
| Project | ProjectScylla |

## When to Use

Use this skill when you need to:

- Set up multi-tier ablation experiments for AI agent evaluation
- Run E2E validation across all capability tiers (T0-T6)
- Debug issues with large configuration combinations (T5/T6)
- Understand the tier structure and sub-test organization

## Verified Workflow

### 1. Tier Structure (T0-T6)

| Tier | Name | Sub-tests | Description |
|------|------|-----------|-------------|
| T0 | Prompts | 24 | System prompt ablation (empty -> full CLAUDE.md) |
| T1 | Skills | 10 | Skill category ablation |
| T2 | Tooling | 15 | Tool categories + MCP servers |
| T3 | Delegation | 41 | Agent ablation (non-orchestrators) |
| T4 | Hierarchy | 7 | Orchestrator ablation |
| T5 | Hybrid | 15 | Best combinations + permutations |
| T6 | Super | 1 | Everything enabled at maximum capability |

### 2. Running E2E Experiments

```bash
pixi run python scripts/run_e2e_experiment.py \
    --repo https://github.com/octocat/Hello-World \
    --commit 7fd1a60b01f91b314f59955a4e4d4e80d8edf11d \
    --prompt tests/fixtures/tests/test-001/prompt.md \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T0 T1 T2 T3 T4 T5 T6 \
    --runs 1 \
    --experiment-id <experiment-name> \
    --timeout 1200 \
    -v 2>&1 | tee results/e2e-$(date +%Y%m%d-%H%M%S).log
```

### 3. Results Directory Structure

```
results/YYYY-MM-DDTHH-MM-SS-<experiment-id>/
├── config/experiment.json       # Experiment configuration
├── tiers/
│   ├── T0/
│   │   ├── 00/run_01/logs/     # Sub-test 00 results
│   │   │   ├── judgment.json   # LLM judge evaluation
│   │   │   ├── report.md       # Per-run markdown report
│   │   │   └── command_log.json
│   │   ├── 01/run_01/logs/
│   │   └── ...
│   ├── T1/ through T6/
│   └── best_subtest.json       # Winner selection per tier
├── summary/
│   ├── result.json             # Overall experiment results
│   └── tier_comparison.json    # Cross-tier metrics
└── report.md                   # Final markdown report
```

### 4. Key Files for Sub-Test Configuration

Each sub-test directory follows this pattern:

```
tests/fixtures/tests/test-001/t{N}/NN-name/
├── config.yaml                  # Sub-test metadata
├── CLAUDE.md                    # Optional: System prompt override
└── .claude/                     # Optional: Skills, agents, plugins
    ├── skills/
    ├── agents/
    └── plugins/
```

## Failed Attempts

### LLM Judge "Argument list too long" (T6)

**Problem**: When running T6 (Super tier), the LLM judge failed with:
```
[Errno 7] Argument list too long: 'claude'
```

**Root Cause**: The evaluation context was passed directly as a CLI argument to `claude`. T6 combines all configs (full CLAUDE.md + all skills + all agents), making the prompt exceed the OS command line limit (~128KB).

**Location**: `src/scylla/e2e/llm_judge.py:_call_claude_judge()`

**Original Code**:
```python
cmd = [
    "claude",
    "--model", model,
    "--system-prompt-file", str(JUDGE_SYSTEM_PROMPT_FILE),
    evaluation_context,  # TOO LONG!
]
```

**Fix**: Write evaluation context to a temp file and use `-p` flag:
```python
with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
    f.write(evaluation_context)
    prompt_file_path = f.name

cmd = [
    "claude",
    "--model", model,
    "--system-prompt-file", str(JUDGE_SYSTEM_PROMPT_FILE),
    "-p", prompt_file_path,  # Use file instead
]
```

## Results & Parameters

### Sample T0 Judgment (00-empty sub-test)

```json
{
  "score": 0.92,
  "passed": true,
  "grade": "A",
  "reasoning": "The agent successfully created a correct hello.py script...",
  "criteria_scores": {
    "correctness": {"score": 1.0},
    "completeness": {"score": 1.0},
    "code_structure": {"score": 1.0}
  }
}
```

### T6 Result (after fix)

```
T6: PASS (score: 0.700, cost: $0.4037)
```

### CLI Parameters Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--tiers` | T0 T1 | Tiers to run |
| `--runs` | 10 | Runs per sub-test |
| `--timeout` | 3600 | Timeout per run (seconds) |
| `--parallel` | 4 | Max parallel sub-tests |
| `--judge-model` | claude-opus-4-5 | Model for LLM judging |

## Related Skills

- `complex-agent-eval-task` - Setting up complex evaluation tasks
- `e2e-framework-validation` - E2E framework testing patterns
