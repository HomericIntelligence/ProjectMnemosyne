# Session Notes: Post-Audit Hygiene Implementation

**Date**: 2026-03-13
**Project**: ProjectScylla
**Audit score**: A- (89%)

## Audit Findings vs Reality

The audit reported several issues; several were false positives:

- Empty cd/, clone/, gh/, repo/ dirs → NOT present, already cleaned up
- SECURITY.md missing → NOT missing, existed as untracked file
- ProjectMnemosyne/ at root → NOT at root, properly in build/
- 11 manual to_dict() → CONFIRMED in scylla/e2e/models.py
- 6 silent except catches → CONFIRMED across 4 files
- pyproject.toml URL mismatch → CONFIRMED mvillmow vs HomericIntelligence
- 40 local skills in .claude-plugin/ → CONFIRMED (out of scope for this PR)

## Files Modified

- `pyproject.toml` lines 55-58: 3 URL fixes
- `SECURITY.md`: staged from untracked
- `scylla/e2e/checkpoint.py`: 2 catches (lines ~570, ~694)
- `scylla/e2e/tier_action_builder.py`: 1 catch (line ~191)
- `scylla/e2e/agent_runner.py`: 1 catch (line ~91)
- `scylla/e2e/rate_limit.py`: 2 catches (lines ~120, ~421)
- `scylla/e2e/models.py`: TokenStats.to_dict() → model_dump()

## Key Technical Details

### model_dump() migration

TokenStats was the only safe candidate:
- 4 fields, all int, all map directly to output dict keys
- No Path, no Enum, no computed properties

All other to_dict() methods in models.py retained custom implementations:
- SubTestConfig: Path→str, Enum list→value list
- TierConfig: Enum→value, nested list
- JudgeResultSummary: passes through (could theoretically use model_dump())
- E2ERunResult: computed properties (tokens_input, tokens_output), Path→str, nested
- SubTestResult: Enum→value, nested list, complex rate_limit_info inline dict
- TierBaseline: Enum→value, Path→str
- ResourceManifest: passes through (could use model_dump())
- TierResult: Enum→value, nested dict, computed property (cost_of_pass)
- ExperimentConfig: Enum list→value list, Path→str, excludes ephemeral fields
- ExperimentResult: Enum→value, nested

### ruff BLE001

Initially added `# noqa: BLE001` to broad except catches, then realized:
- ruff select in pyproject.toml: `["E", "F", "W", "I", "N", "D", "UP", "S101", "B", "SIM", "C4", "C901", "RUF"]`
- "B" = flake8-bugbear, NOT flake8-blind-except (BLE)
- `warn_unused_ignores = true` in mypy — unused noqa comments cause warnings
- Removed all noqa comments after realizing they were unnecessary

### pip-audit stash conflict

First commit attempt:
1. Staged: pyproject.toml + SECURITY.md (left pixi.lock unstaged)
2. pre-commit ran pip-audit → modified pixi.lock
3. pre-commit tried to restore stash of unstaged pixi.lock → conflict
4. Hook reported "Failed" despite "no vulnerabilities found"

Fix: staged pixi.lock before second commit attempt → succeeded.

### Branch push limit

HomericIntelligence has a repo rule: "Pushes can not update more than 2 branches or tags."
Trying `git push -u origin branch1 branch2 branch3` → all 3 rejected.
Solution: push one at a time with sequential `git push` calls.

## PR Results

- PR #1482: https://github.com/HomericIntelligence/ProjectScylla/pull/1482 (quick wins)
- PR #1483: https://github.com/HomericIntelligence/ProjectScylla/pull/1483 (exception logging)
- PR #1484: https://github.com/HomericIntelligence/ProjectScylla/pull/1484 (model_dump)
- All 1548 tests passing
- Auto-merge enabled on all 3
