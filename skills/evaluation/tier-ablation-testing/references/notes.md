# Raw Session Notes: Tier Ablation Testing

## Session Context

- **Date**: 2026-01-02
- **Project**: ProjectScylla
- **Task**: Extend test-001 to all tiers (T0-T6) with comprehensive sub-tests

## Implementation Summary

### Files Modified

#### Core Infrastructure
- `src/scylla/e2e/models.py` - Updated TierID docstrings
- `src/scylla/e2e/tier_manager.py` - Updated sub-test discovery for all tiers
- `src/scylla/e2e/llm_judge.py` - Fixed CLI argument limit bug

#### Configuration
- `config/tiers/tiers.yaml` - Redefined all 7 tiers
- `config/tiers/t0-prompts.md` through `t6-super.md` - Tier descriptions

#### Test Fixtures (140 sub-test directories)
```
tests/fixtures/tests/test-001/
├── t0/ (24 sub-tests: 00-empty through 23-B18)
├── t1/ (10 sub-tests: skill categories)
├── t2/ (15 sub-tests: tools + MCP)
├── t3/ (41 sub-tests: delegation agents)
├── t4/ (7 sub-tests: orchestrators)
├── t5/ (15 sub-tests: hybrid combinations)
└── t6/ (1 sub-test: everything enabled)
```

### Key Discoveries

1. **TierManager discovery works for all tiers**: The pattern `NN-name/` is correctly matched for sub-test directories.

2. **T0 special handling**: Sub-tests 00-empty and 01-vanilla have special workspace preparation (remove CLAUDE.md).

3. **Inheritance pattern**: `extends_previous: true` in config.yaml enables copying baseline from previous tier's winner.

4. **LLM judge reliability**: Opus model required for accurate judging; Sonnet/Haiku produce inconsistent results.

## Commands Used

### Running single tier validation
```bash
pixi run python scripts/run_e2e_experiment.py \
    --tiers T0 --runs 1 --experiment-id test-001-t0
```

### Running all tiers
```bash
pixi run python scripts/run_e2e_experiment.py \
    --tiers T0 T1 T2 T3 T4 T5 T6 --runs 1 --experiment-id test-001-all
```

### Checking progress during run
```bash
find results/*/tiers -name "judgment.json" | wc -l
ls results/*/tiers/
```

## Error Logs

### T6 CLI Argument Error (before fix)
```
2026-01-02 10:21:05 [WARNING] scylla.e2e.llm_judge: LLM judge failed, using fallback: [Errno 7] Argument list too long: 'claude'
```

### T6 Success (after fix)
```
T6: PASS (score: 0.700, cost: $0.4037)
Frontier CoP: $0.4037
```

## Partial Results from T0 Run (22/24 completed)

All sub-tests passing with scores ranging 0.85-0.95:
- 00-empty: A (0.92)
- 01-vanilla: A (0.90)
- 02-critical-only: A (0.88)
- ... (similar results for remaining sub-tests)

## Related Issues/PRs

- PR #108: feat: extend test-001 to all tiers (T0-T6) with comprehensive sub-tests
