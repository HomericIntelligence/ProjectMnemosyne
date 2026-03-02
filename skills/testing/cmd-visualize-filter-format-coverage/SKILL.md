# cmd_visualize Filter × Format Coverage Tests

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-02 |
| Objective | Add explicit test coverage for `--tier` filter combined with `--format` options in `cmd_visualize()` |
| Outcome | SUCCESS — 6 new tests added, 22/22 `TestCmdVisualize` tests pass, 125/125 file-level tests pass |
| Category | testing |
| Source Project | ProjectScylla |
| PR | HomericIntelligence/ProjectScylla#1290 |
| Issue | HomericIntelligence/ProjectScylla#1163 |

## When to Use This Skill

Use this skill when:
- Auditing test coverage across a **filter × format** combination matrix for a CLI command
- Tests exist for individual flags (`--tier`, `--format json`) but lack cross-product combinations
- A follow-up issue says "closer audit may reveal gaps" in coverage
- You need to add non-disruptive tests (no production code changes) to a mature test class

## Verified Workflow

### Step 1: Read the Existing Test Class

Before writing anything, read the existing test class to understand:
- The `_make_checkpoint_file()` helper signature (what fields are required/optional)
- Which combinations are **already** tested
- Which format produces what output (tree, table, JSON)

```bash
grep -n "def test_" tests/unit/e2e/test_manage_experiment.py | grep -i visualize
```

### Step 2: Read the Implementation

Read `cmd_visualize()` and each `_visualize_*()` helper:
- `_visualize_json()` — applies `tier_filter` to all three state dicts
- `_visualize_table()` — iterates `run_states`, skips non-matching tiers
- `_visualize_tree()` — iterates `tier_states`, skips non-matching tiers
- `_visualize_states_table()` — used by `--states-only` path, independent of `--format`

Key insight: `--states-only` takes its **own rendering path** before `fmt` is read — so
`--states-only --format table` still uses `_visualize_states_table()`, not `_visualize_table()`.

### Step 3: Build the Gap Matrix

Draw a matrix of format × filter combinations and mark existing coverage:

| Format | No filter | `--tier T0` | `--tier T99` (nonexistent) |
|--------|-----------|-------------|---------------------------|
| tree (default) | ✅ covered | ✅ covered | ❌ gap |
| table | ✅ covered | ❌ gap | ❌ gap |
| json | ✅ covered | ❌ gap | ❌ gap |
| --states-only (any format) | ✅ covered | ✅ covered | — |
| --states-only + explicit --format | ❌ gap | — | — |

### Step 4: Write Tests — One per Gap Cell

Each test follows the same structure:
1. Call `self._make_checkpoint_file(tmp_path, ...)` with multi-tier data
2. Parse args with `parser.parse_args(["visualize", str(tmp_path), "--format", fmt, "--tier", tier])`
3. Call `result = cmd_visualize(args)` and assert `result == 0`
4. Capture stdout with `capsys.readouterr().out`
5. Assert presence/absence of tier names (and for JSON, parse with `json.loads()`)

**JSON filter tests** — assert on parsed dict, not string presence:
```python
data = json.loads(out)
assert "T0" in data["tier_states"]
assert "T1" not in data["tier_states"]
assert data["tier_states"] == {}  # when filter matches nothing
```

**Table filter tests** — assert tier ID strings in/absent from text:
```python
assert "T0" in out
assert "T1" not in out
```

**Nonexistent tier filter** — table still prints header row, no data rows:
```python
assert "TIER" in out   # header always present
assert "T0" not in out  # no matching data
```

**`--states-only` overrides `--format`** — confirm RESULT column absent:
```python
assert "TIER" in out
assert "STATE" in out
assert "RESULT" not in out
```

### Step 5: Verify Tests Pass

```bash
pixi run python -m pytest tests/unit/e2e/test_manage_experiment.py::TestCmdVisualize -v
# Should show: 22 passed
```

Then run the full file:
```bash
pixi run python -m pytest tests/unit/e2e/test_manage_experiment.py -q
# Should show: 125 passed
```

### Step 6: Commit and Create PR

```bash
git add tests/unit/e2e/test_manage_experiment.py
git commit -m "test(cli): add cmd_visualize filter×format coverage tests

Closes #1163"
git push -u origin 1163-auto-impl
gh pr create --title "[Test] Add cmd_visualize filter×format coverage tests" \
  --body "Closes #1163"
gh pr merge --auto --rebase
```

## Failed Attempts

### 1. Looking for a separate visualize test file
**What was tried**: `glob tests/**/*visualize*` expecting a dedicated test file.
**Why it failed**: Tests live inside the monolithic `test_manage_experiment.py` under `TestCmdVisualize`.
**Solution**: Search for the class name directly: `grep -n "TestCmdVisualize" tests/unit/e2e/test_manage_experiment.py`.

### 2. Assuming `--states-only --format table` uses `_visualize_table()`
**What was tried**: Initial assumption that `--format` would always route to the corresponding renderer.
**Why it was wrong**: `cmd_visualize()` checks `args.states_only` **first**, before reading `args.output_format`. The states-only path is completely independent.
**Solution**: Read `cmd_visualize()` source before writing assertions.

## Results & Parameters

### Tests Added (6)

| Test Method | Scenario | Key Assertion |
|-------------|----------|---------------|
| `test_visualize_json_tier_filter` | `--format json --tier T0` with T0+T1 data | T1 absent from JSON `tier_states` + `run_states` |
| `test_visualize_json_tier_filter_nonexistent` | `--format json --tier T99` | `tier_states == {}`, `run_states == {}` |
| `test_visualize_table_tier_filter` | `--format table --tier T0` | "T0" in out, "T1" not in out |
| `test_visualize_table_tier_filter_nonexistent` | `--format table --tier T99` | "TIER" header present, "T0" not in out |
| `test_visualize_states_only_overrides_format` | `--states-only --format table` | "RESULT" not in out |
| `test_visualize_tier_filter_excludes_all_tree` | `--tier T99` (tree) | experiment_id present, "T0" not in out |

### Test Count Change

| Metric | Before | After |
|--------|--------|-------|
| `TestCmdVisualize` tests | 16 | 22 |
| `test_manage_experiment.py` total | 119 | 125 |

### Key Code Location

```
tests/unit/e2e/test_manage_experiment.py  — TestCmdVisualize class
scripts/manage_experiment.py:1368         — cmd_visualize()
scripts/manage_experiment.py:1260         — _visualize_json()
scripts/manage_experiment.py:1223         — _visualize_table()
scripts/manage_experiment.py:1153         — _visualize_tree()
scripts/manage_experiment.py:1316         — _visualize_states_table()
```

## Related Skills

- `testing/test-implementation-gap-analysis` — General approach for closing test-impl gaps
- `testing/cli-deep-audit-and-fix` — Systematic CLI test auditing
- `testing/close-script-test-gap-cmd-run-repair` — Prior session on script cmd coverage gaps
