# Raw Notes — phantom-dir-reference-fix

## Session: 2026-02-22

### Issue
GitHub issue #848: README.md and CONTRIBUTING.md referenced `tests/integration/` which does not exist.

### Specific phantom references found

**README.md line 347:**
```
- **Integration Tests** (2 files): End-to-end workflow testing
```

**README.md line 366:**
```
pixi run pytest tests/integration/ -v
```

**CONTRIBUTING.md line 118:**
```
# Create tests in tests/unit/ or tests/integration/
```

**CONTRIBUTING.md line 239:**
```
pixi run pytest tests/integration/ -v   # Integration tests
```

### Actual test structure
Integration-style tests are in `tests/unit/analysis/`:
- `test_integration.py`
- `test_cop_integration.py`
- `test_duration_integration.py`

### Scope clarification
`docs/arxiv/dryrun/raw/T6/01/run_01/workspace/.claude/skills/phase-test-tdd/SKILL.md` and companion shell scripts also contain `tests/integration` references, but these are archived dryrun workspace snapshots and were explicitly out of scope per the issue.

### Verification command (from issue success criteria)
```bash
grep -r "tests/integration" docs/ README.md CONTRIBUTING.md
```
Returns no results after fix (ignoring docs/arxiv/ snapshots).
