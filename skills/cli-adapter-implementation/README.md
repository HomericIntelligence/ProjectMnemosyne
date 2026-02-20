# CLI Adapter Implementation Skill

**Category:** Tooling
**Created:** 2026-02-20
**Source:** Issue #744 - ProjectScylla

## Quick Start

Use this skill when adding a new CLI-based AI agent as an evaluation target in ProjectScylla.

```
"Add support for <tool> CLI in ProjectScylla"
→ Use cli-adapter-implementation skill
```

## What This Skill Provides

- **Exact file list** (3 to create, 1 to modify) — no guessing
- **Template patterns** for `_build_command()` and `_parse_token_counts()`
- **Regex pitfall** for `_api_call_fallback_pattern` double-counting
- **Test structure** (23 tests across 7 test classes)
- **Coverage threshold workaround** (`--no-cov` during dev)

## When to Use

Trigger conditions:

- Issue titled "[Feature] Add support for \<tool\>"
- New CLI agent needs T0–T6 tier benchmarking
- Need to extend `scylla/adapters/` with a new provider
- Porting another adapter (Aider, Continue, Cursor, etc.)

## Key Results

From the Goose integration session (Issue #744):

- **Adapter:** 1 new file (`goose.py`, ~115 LOC)
- **Config:** 1 YAML (`config/models/goose.yaml`)
- **Tests:** 23 tests, all passing, 100% adapter coverage
- **Regressions:** 0 (160/160 total adapter tests pass)
- **Pre-commit:** All hooks pass (ruff auto-fixes import sort)

## Workflow Overview

1. **Read** `cline.py` and `test_cline.py` as templates
2. **Create** `scylla/adapters/<name>.py` with two abstract methods
3. **Create** `config/models/<name>.yaml` with pricing
4. **Copy** `test_cline.py` → `test_<name>.py`, swap class names
5. **Update** `scylla/adapters/__init__.py` (ruff auto-sorts)
6. **Run** tests with `--no-cov`, then `pre-commit run --all-files` twice

## Key Principles

✅ **Do:**

- Use `cline.py` as the template (not `claude_code.py` — too complex)
- Set `cost_per_1k_input/output: 0.0` if tool delegates to underlying LLM
- Run pre-commit twice (first run auto-fixes, second run verifies)
- Use `--no-cov` for targeted runs (global coverage threshold causes false failures)

❌ **Don't:**

- Combine `◆` character markers with text patterns in `_api_call_fallback_pattern` when they co-occur on the same line (causes double-counting)
- Add `--model` flag to `_build_command()` if tool uses env vars for model selection
- Create `plugin.json` in the worktree — it's only needed in ProjectMnemosyne

## Files in This Skill

- `SKILL.md` - Complete workflow with verified steps and failed attempts
- `references/notes.md` - Raw session details and commands
- `README.md` - This file

## Related Skills

- `persist-automation-logs` - Log writing patterns in adapters
- `execution-stage-logging` - Log on all exit paths (success, timeout, error)
- `centralized-path-constants` - Use `AdapterConfig.output_dir` not hardcoded paths
- `coverage-threshold-tuning` - Managing global coverage thresholds

## Learn More

See `SKILL.md` for the complete verified workflow with all steps, failed attempts, and copy-paste configs.
