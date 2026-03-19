---
name: cli-visualize-subcommand
description: Pattern for adding a visualize/inspect subcommand to a CLI experiment
  management tool
category: tooling
date: 2026-02-24
version: 1.0.0
user-invocable: false
---
# CLI Visualize Subcommand

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-24 |
| Objective | Add `visualize` subcommand to `manage_experiment.py` that reads checkpoint.json and renders experiment state hierarchy |
| Outcome | SUCCESS — merged to main (PR #1101), 16 tests, 78.19% coverage |

## When to Use

- Adding state inspection/visualization to a CLI experiment management tool
- Implementing tree/table/JSON renderers for hierarchical state data
- Supporting batch directory mode (inspect multiple experiment directories at once)
- Adding filter flags (`--tier`, `--states-only`) to state viewers
- Implementing ANSI color in CLI output without external dependencies

## Verified Workflow

### 1. Add helper functions (before the subcommand function)

```python
def _color(text: str, code: str, enabled: bool) -> str:
    """Wrap text in ANSI escape codes if color is enabled."""
    if not enabled:
        return text
    return f"\033[{code}m{text}\033[0m"

def _state_color(state: str, enabled: bool) -> str:
    """Color a state string based on semantic meaning."""
    # ANSI color codes — must be lowercase to pass ruff N806
    green = "32"
    red = "31"
    yellow = "33"
    dim = "2"
    terminal_states = {"complete", "passed", "worktree_cleaned", "aggregated"}
    failed_states = {"failed", "interrupted", "rate_limited"}
    pending_states = {"pending", "initializing"}
    if state in terminal_states:
        return _color(state, green, enabled)
    if state in failed_states:
        return _color(state, red, enabled)
    if state in pending_states:
        return _color(state, dim, enabled)
    return _color(state, yellow, enabled)

def _find_checkpoint_paths(path: Path) -> list[Path]:
    """Resolve path to one or more checkpoint.json files."""
    if path.is_file():
        return [path]
    if path.is_dir():
        direct = path / "checkpoint.json"
        if direct.exists():
            return [direct]
        # Batch mode: one-level deep only
        found = sorted(path.glob("*/checkpoint.json"))
        return found
    return []
```

### 2. Tree renderer — correct connector logic

```python
# CORRECT: use r"\--" for last child, "+--" for non-last
# Note: do NOT add trailing space to connector strings (causes double-space in f-strings)
tier_prefix = r"  \--" if is_last_tier else "  +--"
sub_connector = r"\--" if is_last_sub else "+--"
run_connector = r"\--" if is_last_run else "+--"
```

### 3. `--states-only` pattern for unified multi-experiment table

Collect all checkpoints first, then render a single table (so header prints once):

```python
if args.states_only:
    loaded = []
    for cp_path in checkpoint_paths:
        try:
            loaded.append(load_checkpoint(cp_path))
        except Exception as e:
            logger.error(f"Failed to load checkpoint {cp_path}: {e}")
            any_error = True
    if loaded:
        _visualize_states_table(loaded, tier_filter, use_color)
    return 1 if any_error else 0
```

In the table renderer, omit EXP column for single experiment, add it for batch:
```python
multi = len(checkpoints) > 1
if multi:
    print(f"{'EXP':<16}{'TIER':<6}{'SUBTEST':<12}{'RUN':<5}{'STATE'}")
else:
    print(f"{'TIER':<6}{'SUBTEST':<12}{'RUN':<5}{'STATE'}")
```

### 4. Argparse registration pattern

```python
def _add_visualize_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", type=Path, help="Path to checkpoint.json or experiment directory")
    parser.add_argument("--format", choices=["tree", "table", "json"], default="tree", dest="output_format")
    parser.add_argument("--tier", action="append", default=None, help="Filter to specific tier(s) (repeatable)")
    parser.add_argument("-v", "--verbose", action="store_true", default=False)
    parser.add_argument("--states-only", action="store_true", default=False,
        help="Show states-only table: EXP / TIER / SUBTEST / RUN / STATE (no result column)")
```

### 5. Test pattern

```python
class TestCmdVisualize:
    def _make_checkpoint_file(self, path, experiment_id="test-exp", experiment_state="complete",
        tier_states=None, subtest_states=None, run_states=None, completed_runs=None, ...):
        checkpoint_data = {
            "version": "3.1", "experiment_id": experiment_id,
            "experiment_dir": str(path), "experiment_state": experiment_state,
            "tier_states": tier_states or {}, ...
        }
        (path / "checkpoint.json").write_text(json.dumps(checkpoint_data))

    def test_visualize_tree_format(self, tmp_path, capsys):
        self._make_checkpoint_file(tmp_path, ...)
        args = build_parser().parse_args(["visualize", str(tmp_path)])
        result = cmd_visualize(args)
        assert result == 0
        out = capsys.readouterr().out
        assert "T0" in out
```

## Failed Attempts

| Attempt | What Failed | Why | Fix |
|---------|-------------|-----|-----|
| Uppercase ANSI code variables | `GREEN = "32"` caused ruff N806 | ruff requires function-scope variables to be lowercase | Rename to `green`, `red`, `yellow`, `dim` |
| Trailing space in connector prefix | `r"  \-- "` produced double-space in f-string | Prefix already ended with space, format string added another | Remove trailing space: `r"  \--"` |
| Long f-string in verbose block | `f"  Duration: {_format_duration(started, last_updated)}"` hit E501 (111 chars) | 100-char line limit | Extract to intermediate: `dur = _format_duration(...); duration = f"  Duration: {dur}"` |
| Long run label f-string | `f"{run_cont} {connector} run_{int(run_num_str):02d} [{run_state}]{result_str}"` hit E501 | 102 chars | Extract: `run_label = f"run_{...}"; print(f"... {run_label} ...")` |
| Long test docstring | Exceeded 100 chars | ruff E501 | Shorten docstring |
| Identical ternary branches | `"+--" if is_last else "+--"` — all connectors were same | Copy-paste error; both branches produced identical strings | Fix to `r"\--" if is_last else "+--"` |

## Results & Parameters

### `--until replay_generated` (stop before Claude executes)

```bash
pixi run python scripts/manage_experiment.py run \
  --config tests/fixtures/tests/test-001 \
  --tiers T0 --runs 1 --max-subtests 1 \
  --until replay_generated --results-dir ~/dryrun5 -v
```

RunState pipeline: `... -> PROMPT_WRITTEN -> REPLAY_GENERATED -> [AGENT EXECUTES] -> AGENT_COMPLETE -> ...`

### Visualize commands

```bash
# Tree view (default) — batch mode
pixi run python scripts/manage_experiment.py visualize ~/dryrun3/

# Table format
pixi run python scripts/manage_experiment.py visualize ~/dryrun3/ --format table

# States only (pipeline stage, no pass/fail)
pixi run python scripts/manage_experiment.py visualize ~/dryrun3/ --states-only

# Filter to one tier + JSON
pixi run python scripts/manage_experiment.py visualize ~/dryrun3/ --format json --tier T0

# Verbose (timestamps, duration, PID)
pixi run python scripts/manage_experiment.py visualize ~/dryrun3/ -v
```

### Test count
- 16 tests in `TestCmdVisualize`
- Full suite: 3086 passed, 78.19% coverage

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1101, merged 2026-02-24 | [notes.md](../../references/notes.md) |
