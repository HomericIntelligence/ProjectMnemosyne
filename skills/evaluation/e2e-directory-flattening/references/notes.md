# Raw Notes: E2E Directory Flattening

## Session Context

- Date: 2026-01-02
- Branch: `refactor/flatten-e2e-directory-structure`
- PR: #109

## User Requirements (verbatim)

> "Reorganize E2E output structure with flattened hierarchy. Move workspace to subtest level (shared across runs). All logs in parent directory (not subdirectory). Reports in JSON and markdown at every level with relative paths. Copy grading materials to root directory. Judge prompt should use file paths instead of inlined content."

> "The test and judge_prompt is not unique per run/subtest/tier, so it needs to be in the parent directory of the run"

> "The judge prompt, test rubric, and criteria are uniform across all tiers"

## Key Insight: Uniform vs Per-Run Data

**Uniform (at experiment root):**
- prompt.md (task prompt)
- criteria.md (grading criteria)
- rubric.yaml (grading rubric)
- judge_prompt.md (template with file path references)

**Per-run:**
- output.txt (agent stdout)
- stdout.log, stderr.log (raw logs)
- judgment.json (LLM judge result)
- report.json, report.md (run-specific)

## Configuration Priority Order

When loading experiment config:
1. CLI arguments (highest priority)
2. Config YAML file (`--config`)
3. Test config (`test.yaml` in `--tiers-dir`)
4. Defaults

```python
def build_config(args):
    test_config = load_test_config(args.tiers_dir)  # Load from test.yaml
    # Apply test_config defaults, then config YAML, then CLI overrides
```

## Git Worktree Pattern

Using git worktrees instead of clones for efficiency:

```python
# Setup base repo once per experiment
self.workspace_manager.setup_base_repo()

# Create worktree per subtest (shared across runs)
worktree_cmd = [
    "git", "-C", str(self.workspace_manager.base_repo),
    "worktree", "add", "--detach", str(workspace_abs),
]
if self.config.task_commit:
    worktree_cmd.append(self.config.task_commit)
```

## Hierarchical Report Structure

Each level has `report.json` with:
```json
{
  "summary": { /* aggregated metrics */ },
  "best": { /* pointer to best child */ },
  "children": [
    {"id": "00", "report": "./00/report.json"},
    {"id": "01", "report": "./01/report.json"}
  ]
}
```

## Debug: Finding Hidden logs/ Creation

The `logs/` subdirectory was still appearing. Traced with:

```bash
grep -r "logs/" src/scylla/
grep -r "stderr\.log|stdout\.log" src/scylla/
```

Found in `adapters/base.py:write_logs()` which was called by `ClaudeCodeAdapter.run()`.

## Test Commands Used

```bash
# Unit tests
pixi run pytest tests/unit/e2e/ -v

# Manual E2E test
pixi run python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T0 --runs 1 --max-subtests 2 -v

# Analyze results
ls -la results/2026-01-02T21-13-46-test-001/
ls -la results/2026-01-02T21-13-46-test-001/T0/00/run_01/
```
