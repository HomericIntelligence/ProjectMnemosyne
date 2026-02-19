# Raw Session Notes: Planning Implementation from Issue #595

## Session Context

**Date:** 2026-02-14
**Issue:** #595 - Resolve 4 skipped tests and clean up .orig artifacts
**Branch:** fix-failing-implementer-tests (starting branch)
**Outcome:** Created comprehensive implementation plan

## Issue Details

### Problem Statement

4 tests skipped in test suite + 3 merge conflict artifacts (.orig files)

### Affected Files

**Skipped Tests:**

- tests/unit/cli/test_cli.py:106
- tests/unit/e2e/test_rerun.py:497
- tests/unit/reporting/test_tables.py:608 (actually in tests/unit/analysis/test_tables.py)
- tests/unit/e2e/test_rate_limit_recovery.py:66

**Merge Artifacts:**

- tests/unit/e2e/test_rerun.py.orig
- tests/unit/analysis/test_tables.py.orig
- tests/unit/cli/test_cli.py.orig

## Investigation Steps Taken

### 1. Found Merge Artifacts

```bash
find tests -name "*.orig" -type f
# Result: 3 files found
```

### 2. Searched for Skip Markers

```bash
Grep pattern="@pytest\.mark\.skip" path=/home/mvillmow/ProjectScylla/tests
# Found all 4 skipped tests with reasons
```

### 3. Read Each Skipped Test

**test_cli.py:106-116**

- Skip reason: "Pre-existing failure - test expects old test ID format"
- Test assertion: `assert "001-justfile-to-makefile" in result.output`
- Investigation showed actual format is "test-001" from tests/fixtures/tests/

**test_rerun.py:497-550**

- Skip reason: "Pre-existing failure from incomplete Pydantic migration"
- Creates RunToRerun model instance
- Test checks that rerun moves existing run to .failed directory

**test_tables.py:608-619**

- Skip reason: "Pre-existing failure from incomplete Pydantic migration"
- Uses sample_runs_df fixture
- Tests Holm-Bonferroni correction in table02b_impl_rate_comparison

**test_rate_limit_recovery.py:66-95**

- Skip reason: "Glob pattern matching issue - works in practice but test isolation problem"
- Creates .failed/ directory structure
- Function uses rglob(".failed/*/agent/result.json")

### 4. Examined Related Code

**CLI list command** (scylla/cli/main.py:366-405)

- Loads test IDs from tests/fixtures/tests/*/test.yaml
- Uses `test_data.get("id", test_path.name)` for test ID
- Fallback hardcoded list has old format "001-justfile-to-makefile"

**Test fixtures** (tests/fixtures/tests/)

- Actual directories: test-001, test-002, test-003, etc.
- test.yaml format: `id: "test-001"`

**RunToRerun model** (scylla/e2e/rerun.py:82-92)

- Pydantic BaseModel with model_config
- Fields: tier_id, subtest_id, run_number, run_dir, status, reason
- No obvious missing required fields

**sample_runs_df fixture** (tests/unit/analysis/conftest.py)

- Complete fixture with all expected fields including impl_rate
- Generates ~140 rows of test data
- Includes token stats, duration stats, consistency, CoP

## Root Cause Analysis

### CLI Test (test_cli.py:106)

**Root Cause:** Test expects old test ID format
**Evidence:**

- Test asserts "001-justfile-to-makefile" exists in output
- Actual implementation uses "test-001" from test.yaml files
- Fallback code still has old format but isn't triggered when tests/ exists

**Fix:** Update assertion to expect "test-001"

### Rate Limit Test (test_rate_limit_recovery.py:66)

**Root Cause:** Directory structure doesn't match glob pattern
**Evidence:**

- Test creates: tmp_path / ".failed" / "run_01_attempt_01" / "agent"
- Function expects: rglob(".failed/*/agent/result.json") from experiment root
- Comment in test: "Note: _detect_rate_limit_from_results uses rglob('.failed/*/agent/result.json')"

**Fix:** Create proper directory hierarchy matching production structure

### Rerun Test (test_rerun.py:497)

**Root Cause:** Unknown - needs investigation
**Evidence:**

- Skip reason says "Pydantic migration"
- RunToRerun model appears complete
- Might be in SubTestConfig, TierConfig, or ExperimentConfig mocks

**Fix:** Run test to see actual error, then fix based on error message

### Tables Test (test_tables.py:608)

**Root Cause:** Unknown - needs investigation
**Evidence:**

- Skip reason says "Pydantic migration"
- sample_runs_df fixture looks complete
- Might be in table02b_impl_rate_comparison function implementation

**Fix:** Run test to see actual error, then fix based on error message

## Planning Decisions

### Decision 1: Order by Difficulty

**Rationale:** Start with easy wins to validate approach

1. Delete .orig files (trivial)
2. Fix CLI test (known issue, simple fix)
3. Fix rate limit test (understand pattern, medium complexity)
4. Fix Pydantic tests (need investigation, harder)

### Decision 2: Don't Guess at Pydantic Issues

**Rationale:** Without running tests, can't know exact error
**Approach:** Document investigation steps in plan

```markdown
**Investigation steps:**
1. Run the test to see actual error
2. Check if ModelName has new required fields
3. Add missing fields to test fixture instantiation
```

### Decision 3: Update Tests, Not Production Code

**Rationale:** CLI test expects old format, but new format is intentional
**Exception:** If production code has actual bugs, fix them

### Decision 4: Verify Each Fix Individually

**Rationale:** Isolate failures, don't batch test runs
**Commands:**

```bash
pixi run pytest tests/unit/cli/test_cli.py::TestListCommand::test_list_basic -v
pixi run pytest tests/unit/e2e/test_rate_limit_recovery.py::TestRateLimitDetection::test_detects_from_failed_directory -v
```

## Team Knowledge Referenced

From `.claude-plugin/skills/`:

### fix-ci-test-failures

- Use relative symlinks, not absolute
- Mock actual methods called, not constructor dependencies
- Run tests locally first

### fix-pydantic-required-fields

- Replace `.to_dict()` with `.model_dump()`
- Update ALL test fixtures when models gain required fields
- Check error messages for missing field names

### pydantic-model-dump

- Pydantic v2 migration pattern
- `.dict()` deprecated, use `.model_dump()`

### pr-merge-conflict-resolution

- .orig file cleanup patterns during merge conflicts

## Commands Used

```bash
# Find merge artifacts
find tests -name "*.orig" -type f

# Search for skip markers
Grep pattern="@pytest\.mark\.skip" path=tests/ output_mode=content

# Read test files
Read tests/unit/cli/test_cli.py offset=96 limit=30
Read tests/unit/e2e/test_rerun.py offset=487 limit=30
Read tests/unit/analysis/test_tables.py offset=598 limit=30
Read tests/unit/e2e/test_rate_limit_recovery.py offset=56 limit=30

# Check test fixtures
ls tests/fixtures/tests/
Read tests/fixtures/tests/test-001/test.yaml

# Find model definitions
Grep pattern="class RunToRerun" path=scylla/ output_mode=content
Read scylla/e2e/rerun.py offset=82 limit=20

# Find fixtures
Grep pattern="def sample_runs_df" path=tests/unit/analysis/ output_mode=content
Read tests/unit/analysis/conftest.py

# Find CLI implementation
Glob pattern="**/cli/*.py" path=scylla/
Grep pattern="def list" path=scylla/cli/ output_mode=content
Read scylla/cli/main.py offset=366 limit=40
```

## Plan Structure Created

### Sections Included

1. **Objective** - Brief description
2. **Approach** - High-level strategy and key decisions
3. **Files to Create** - None for test fixes
4. **Files to Modify** - 5 files with specific changes:
   - test_cli.py (update assertion)
   - test_rate_limit_recovery.py (fix directory structure)
   - test_rerun.py (investigate & fix Pydantic)
   - test_tables.py (investigate & fix Pydantic)
   - (delete .orig files)
5. **Implementation Order** - 7 numbered steps
6. **Verification** - Individual and full suite commands
7. **Dependencies and Integration Points** - Related code
8. **Risk Mitigation** - Strategies to avoid breaking changes

### For Each File to Modify

- **Change**: What to change
- **Rationale**: Why this change is needed
- **Specific modification**: Code diff or specific steps
- **Investigation steps**: For unclear issues

## Verification Strategy

### Individual Test Commands

```bash
pixi run pytest tests/unit/cli/test_cli.py::TestListCommand::test_list_basic -v
pixi run pytest tests/unit/e2e/test_rate_limit_recovery.py::TestRateLimitDetection::test_detects_from_failed_directory -v
pixi run pytest tests/unit/e2e/test_rerun.py::TestRerunWorkflow::test_rerun_single_run_moves_existing_to_failed -v
pixi run pytest tests/unit/analysis/test_tables.py::test_table02b_holm_bonferroni_correction_applied -v
```

### Full Suite Commands

```bash
pixi run pytest tests/ -v
pixi run pytest tests/ -v | grep -i "skipped"
find tests -name "*.orig" -type f
pre-commit run --all-files
```

### Success Criteria

- [ ] All 4 previously skipped tests now pass
- [ ] Zero .orig files in repository
- [ ] Full test suite passes with no new failures
- [ ] Pre-commit hooks pass
- [ ] Commit message follows conventional format

## Lessons Learned

### What Worked

1. ✅ Systematic investigation before planning
2. ✅ Reading actual code, not just skip messages
3. ✅ Categorizing root causes
4. ✅ Ordering fixes by difficulty
5. ✅ Documenting investigation steps for unclear issues
6. ✅ Being specific with file paths and line numbers

### What Didn't Work

1. ❌ Initially tried to plan without reading code
2. ❌ Assumed all skips had same root cause
3. ❌ Tried to guess Pydantic fixes without running tests

### Key Insights

- Skip reason messages are often vague - read the actual code
- Different tests can fail for different reasons even in related issues
- For migration issues, plan the investigation, don't try to solve it in the plan
- Start with easy wins to validate approach
- Be specific - file paths, line numbers, exact changes

## Next Steps (Not Executed in This Session)

1. Implement the plan (separate session)
2. Run verification commands
3. Create commit with conventional format
4. Update this skill based on implementation outcomes
