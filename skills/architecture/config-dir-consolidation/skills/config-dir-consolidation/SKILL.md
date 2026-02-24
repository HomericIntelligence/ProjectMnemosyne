---
name: config-dir-consolidation
description: "Move config files from a dedicated config/ directory into tests/ when config is only consumed by test infrastructure. Use when: config dir contains files superseded by a test-side system, loaders have hardcoded config/ paths, or a legacy config directory needs full elimination."
category: architecture
date: 2026-02-19
user-invocable: false
---

# Config Directory Consolidation

Eliminate a legacy `config/` directory by moving its contents into `tests/` (or another appropriate location) and updating all consumers. Includes removing dead fields from models, adapters, and test files.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-19 |
| **Category** | architecture |
| **Objective** | Move `config/tiers/` into `tests/claude-code/shared/`, strip `prompt_file`/`prompt_content` from tier config system |
| **Outcome** | SUCCESS — 18 files deleted, 15 modified, 2202 tests passing, zero regressions |

## When to Use

Use this skill when:

- A `config/` subdirectory contains files only consumed by the test or eval infrastructure
- A newer system (e.g., `tests/claude-code/shared/`) supersedes the config directory
- Loader classes have hardcoded paths to `config/<subdir>/`
- Model classes carry fields that are no longer populated (e.g., `prompt_content`, `prompt_file`)
- You want a clean single source of truth in one location

Trigger conditions:

- `grep -r "config/tiers" --include="*.py" --include="*.yaml"` returns hits in loader/runner code
- A model field is set to `None` everywhere it's used or only populated from a deleted source
- The config directory has `.md` files only used as prompts injected at runtime (superseded by CLAUDE.md composition)

## Verified Workflow

### Step 1: Audit the old config directory

```bash
# List all files to understand scope
find <config-dir>/ -type f | sort

# Find all references to the path in Python/YAML
grep -r "<config-dir>" --include="*.py" --include="*.yaml" .
```

**Key insight**: Check whether any field added to the old config (like `prompt_file`) is still actively consumed downstream, or just carried as dead weight.

### Step 2: Create the stripped YAML at the new location

Copy the YAML config file to the new location, removing any fields that referenced the deleted files (e.g., `prompt_file` lines). Keep all structural/behavioral fields (`name`, `description`, `tools_enabled`, `delegation_enabled`).

```bash
# New location
cp <config-dir>/tiers.yaml tests/claude-code/shared/tiers.yaml
# Then edit to remove prompt_file lines
```

### Step 3: Refactor the loader class

In the loader (`TierConfigLoader` or equivalent):

1. Change constructor param from `config_dir: Path` → `tiers_dir: Path` (point directly at the dir containing the YAML, no nesting)
2. Remove: `self.config_dir`, `self.tiers_dir = self.config_dir / "tiers"` pattern
3. Simplify to: `self.tiers_dir = Path(tiers_dir)`, `self.tiers_file = self.tiers_dir / "tiers.yaml"`
4. Remove prompt file loading from `get_tier()` — all the `if tier_def.prompt_file:` / `prompt_file.read_text()` logic
5. Remove `prompt_file` and `prompt_content` fields from `TierDefinition` and `TierConfig` models

### Step 4: Update the auto-detection path in managers

Any class that auto-detects the config directory (e.g., `TierManager.__init__`) needs its fallback path updated:

```python
# Before
config_dir = Path(__file__).parent.parent.parent / "config"
self.tier_config_loader = TierConfigLoader(config_dir)

# After
config_dir = Path(__file__).parent.parent.parent / "tests" / "claude-code" / "shared"
self.tier_config_loader = TierConfigLoader(config_dir)
```

Also remove any `prompt_content=global_tier_config.prompt_content` from downstream `TierConfig()` construction.

### Step 5: Remove prompt injection from adapters/runners

If the deleted fields were used for runtime injection (e.g., prepending a system prompt to task prompts, or setting an env var):

- **Adapter**: Simplify `inject_tier_prompt()` to just `return task_prompt`
- **Runner**: Remove `if tier_config.prompt_content: env_vars["TIER_PROMPT"] = ...`

### Step 6: Update model classes

Remove the dead fields from all model classes:

- `TierDefinition`: remove `prompt_file: str | None`
- `TierConfig` (executor): remove `prompt_file: Path | None`, `prompt_content: str | None`
- `TierConfig` (e2e/models.py): remove `prompt_content: str | None = None` + `to_dict()` entry

### Step 7: Update tests

For each test file referencing the removed fields:

```bash
grep -r "prompt_content\|prompt_file" tests/ --include="*.py" -l
```

- **Fixture functions**: Remove `tiers/` nested dir creation, remove prompt `.md` file creation, remove `prompt_file` from YAML content. Rename `config_dir` fixture → `tiers_dir`, update `TierConfigLoader(tiers_dir)` calls.
- **Unit tests**: Remove assertions on `prompt_content` / `prompt_file`. If a test was verifying injection behavior that no longer exists, replace with a simpler test verifying the method returns the prompt unchanged.
- **Integration tests**: Update the hardcoded path from `config` to `tests/claude-code/shared`.
- **Mock fixtures in runner tests**: Remove `prompt_content=None` from `MagicMock()` calls.

### Step 8: Delete the old directory

```bash
git rm -r <config-dir>/
```

Verify the parent `config/` only contains the expected remaining subdirs:

```bash
ls config/
# Expected: defaults.yaml  judge/  models/
```

### Step 9: Update docs and scripts

- Scripts with `default=Path("config/tiers")` → update to new path
- Architecture docs with tables listing prompt sources → remove the "Prompt Source" column
- LaTeX/paper files with hardcoded paths → update
- Inline comments and docstrings in loader/manager files

### Step 10: Verify

```bash
# All tests pass
pixi run python -m pytest tests/ --no-cov -q

# Pre-commit clean
pre-commit run --all-files

# Zero config/tiers references in .py and .yaml
grep -r "config/tiers" --include="*.py" --include="*.yaml" .

# Config dir has only expected contents
ls config/
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Keeping `config_dir` as param name in loader | Confusing — loader no longer needs `config/` parent, just the dir with `tiers.yaml` | Rename param to `tiers_dir` to match what it actually points to |
| Forgetting `to_dict()` when removing model field | Would have caused JSON serialization tests to fail | Always search for `"field_name"` string literals, not just `field_name` attribute references |
| Only updating the loader constructor signature | Auto-detection in `TierManager.__init__` still pointed to old path | Search for all hardcoded path computations referencing the old dir |

## Results & Parameters

### Files Deleted

```text
config/tiers/           # Entire directory (18 files)
  tiers.yaml            # Moved to tests/claude-code/shared/tiers.yaml (stripped)
  t0-prompts.md         # Deleted
  t1-skills.md          # Deleted
  ... (7 prompt .md files total)
  t2/, t3/ subdirs      # Legacy per-tier subtests (superseded by tests/ system)
```

### Files Modified

| File | Change |
|------|--------|
| `scylla/executor/tier_config.py` | Remove `prompt_file`/`prompt_content`, rename param to `tiers_dir` |
| `scylla/e2e/tier_manager.py` | Update auto-detection path, remove `prompt_content=...` |
| `scylla/e2e/models.py` | Remove `prompt_content` from `TierConfig` |
| `scylla/adapters/base.py` | Simplify `inject_tier_prompt()` to return unchanged |
| `scylla/executor/runner.py` | Remove `TIER_PROMPT` env var injection |
| `scripts/run_e2e_experiment.py` | Update `--tiers-dir` default |
| `tests/unit/executor/test_tier_config.py` | Full rewrite to match new API |
| `tests/unit/executor/test_runner.py` | Remove `prompt_content=None` from mocks |
| `tests/unit/adapters/test_base.py` | Rewrite injection tests |
| `tests/unit/adapters/test_claude_code.py` | Remove prompt assertions |
| `tests/unit/adapters/test_cline.py` | Remove `prompt_content` |
| `tests/unit/adapters/test_openai_codex.py` | Remove `prompt_content` + assertion |
| `tests/unit/adapters/test_opencode.py` | Remove `prompt_content` |

### Pre-existing Bug Discovered

During E2E dry run, found a pre-existing `AttributeError: 'TierConfig' object has no attribute 'language'` in `subtest_executor.py:440`. This was present on `main` before this branch — `TierConfig` never had a `language` field. The fix: change `tier_config.language` → `self.config.language` (the `ExperimentConfig` has this field at line 775). This bug is unrelated to the consolidation work but worth fixing separately.

### New File

```yaml
# tests/claude-code/shared/tiers.yaml (stripped of prompt_file lines)
tiers:
  T0:
    name: "Prompts"
    description: "System prompt ablation ..."
    tools_enabled: null
    delegation_enabled: false
  T1:
    ...
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | `repo_cleanup` branch, PR from plan | [notes.md](../references/notes.md) |
