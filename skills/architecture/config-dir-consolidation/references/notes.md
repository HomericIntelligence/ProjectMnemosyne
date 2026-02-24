# Config Directory Consolidation — Session Notes

## Context

**Date**: 2026-02-19
**Branch**: `repo_cleanup`
**Project**: ProjectScylla

## Plan Summary

The plan was to:
1. Remove `config/tiers/` entirely (18 files including 7 prompt `.md` files and `tiers.yaml`)
2. Move `tiers.yaml` (stripped of `prompt_file` refs) to `tests/claude-code/shared/tiers.yaml`
3. Remove `prompt_file` and `prompt_content` from `TierConfigLoader` and its Pydantic models
4. Remove `prompt_content` usage from executor/adapter code
5. Update path references in `TierManager`, scripts, and docs

## Why `config/tiers/` Was Being Removed

The tier prompt `.md` files (`t0-prompts.md` through `t6-super.md`) were only consumed by
the executor/adapter code path — not the primary E2E flow which composes CLAUDE.md from
blocks in `tests/claude-code/shared/blocks/`. The `TierConfigLoader` was loading these files
and populating `prompt_content`, which was then either:
- Prepended to the task prompt by `inject_tier_prompt()` in the adapter
- Set as `TIER_PROMPT` env var by the executor runner

Both of these injection mechanisms were eliminated since the block-based CLAUDE.md composition
at workspace preparation time serves the same purpose more cleanly.

## Key Implementation Details

### Constructor Signature Change

The `TierConfigLoader` constructor changed from:
```python
def __init__(self, config_dir: Path) -> None:
    self.config_dir = Path(config_dir)
    self.tiers_dir = self.config_dir / "tiers"      # points to config/tiers/
    self.tiers_file = self.tiers_dir / "tiers.yaml"
```

To:
```python
def __init__(self, tiers_dir: Path) -> None:
    self.tiers_dir = Path(tiers_dir)                 # points directly to dir with tiers.yaml
    self.tiers_file = self.tiers_dir / "tiers.yaml"
```

**Impact**: All callers that passed `Path("config")` now pass `Path("tests/claude-code/shared")`.
The `TierManager` auto-detection was the main place to update.

### Two Different `TierConfig` Classes

There are two separate `TierConfig` classes:
1. `scylla/executor/tier_config.py` — used by the executor/runner pathway
2. `scylla/e2e/models.py` — used by the E2E runner pathway

Both needed `prompt_content` (and `prompt_file` for the executor one) removed.

### Test Fixture Simplification

The `config_dir` fixture in `test_tier_config.py` created:
```
tmpdir/
  tiers/              # <-- nested "tiers" subdir
    tiers.yaml        # with prompt_file references
    t0-prompts.md     # prompt files
    t1-skills.md
    ...
```

After the change, the fixture creates:
```
tmpdir/               # <-- tmpdir IS the tiers_dir now
  tiers.yaml          # without prompt_file references
```

### Adapter Test Impact

The `test_claude_code.py::TestRun::test_run_with_tier_config` test was asserting:
```python
assert "Think step by step" in cmd[-1]
```

This assertion verified that the tier prompt was prepended to the task prompt by `inject_tier_prompt()`.
After removal, this assertion was dropped since `inject_tier_prompt()` now just returns the task prompt.

### Pre-existing Bug: `tier_config.language`

`scylla/e2e/subtest_executor.py:440` contains:
```python
pipeline_baseline = _run_build_pipeline(
    workspace=workspace,
    language=tier_config.language,   # BUG: TierConfig never had 'language'
)
```

The correct reference would be `self.config.language` (from `ExperimentConfig` which has
`language: str` at line 775 of `scylla/e2e/models.py`). This is a separate bug to fix.

## Verification Results

```
2202 passed, 8 warnings in 59.98s

All pre-commit hooks pass:
  - ruff-format-python: Passed (auto-fixed test_tier_config.py formatting)
  - ruff-check-python: Passed
  - mypy-type-check: Passed
  - markdown-lint: Passed
  - yaml-lint: Passed

grep -r "config/tiers" --include="*.py" --include="*.yaml" .
# Zero output (no references remain)

ls config/
# defaults.yaml  judge/  models/
```

## File Change Summary

### Deleted (via git rm)
- `config/tiers/tiers.yaml`
- `config/tiers/t0-prompts.md` through `t6-super.md` (7 files)
- `config/tiers/t2/01/CLAUDE.md`, `config.yaml`
- `config/tiers/t2/02/CLAUDE.md`, `config.yaml`
- `config/tiers/t2/03/CLAUDE.md`, `config.yaml`
- `config/tiers/t3/01/CLAUDE.md`, `config.yaml`
- `config/tiers/t3/02/CLAUDE.md`, `config.yaml`

### Created
- `tests/claude-code/shared/tiers.yaml` (stripped version)

### Modified
- `scylla/executor/tier_config.py` — core loader refactor
- `scylla/e2e/tier_manager.py` — path update + prompt_content removal
- `scylla/e2e/models.py` — remove prompt_content field
- `scylla/adapters/base.py` — simplify inject_tier_prompt()
- `scylla/executor/runner.py` — remove TIER_PROMPT env var
- `scripts/run_e2e_experiment.py` — update --tiers-dir default
- `scylla/e2e/runner.py` — docstring update
- `scylla/config/models.py` — comment update
- `docs/design/architecture.md` — remove Prompt Source column from tier table
- `docs/arxiv/dryrun/paper.tex` — update config/tiers path references
- `tests/unit/executor/test_tier_config.py` — full rewrite
- `tests/unit/executor/test_runner.py` — remove prompt_content from mocks
- `tests/unit/adapters/test_base.py` — rewrite injection tests
- `tests/unit/adapters/test_claude_code.py` — remove prompt content assertion
- `tests/unit/adapters/test_cline.py` — remove prompt_content
- `tests/unit/adapters/test_openai_codex.py` — remove prompt_content + assertion
- `tests/unit/adapters/test_opencode.py` — remove prompt_content
