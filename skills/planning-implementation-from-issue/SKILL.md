# Planning Implementation from GitHub Issues

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-14 |
| **Objective** | Create detailed implementation plans for GitHub issues #595 (resolve 4 skipped tests and cleanup merge artifacts) |
| **Outcome** | Successfully created comprehensive plan with file-by-file breakdown, investigation steps, and verification strategy |
| **Category** | Architecture / Planning |
| **Related Issues** | #595 |

## When to Use This Skill

Use this skill when:

- GitHub issue requires implementation but approach is unclear
- Multiple test failures need systematic investigation
- Migration issues (Pydantic, library upgrades) affect multiple tests
- Need to break down complex multi-file changes into ordered steps
- Issue involves both investigation and implementation work

**Triggers:**

- User provides a GitHub issue number and asks for an implementation plan
- Issue has multiple affected files with different root causes
- Test failures have unclear origins requiring investigation
- Need to coordinate fixes across test suite and production code

## Verified Workflow

### Phase 1: Investigation & Context Gathering

1. **Read the GitHub issue** to understand:
   - Problem statement
   - Affected files/tests
   - Expected behavior
   - Success criteria

2. **Examine each affected file** using Read tool:

   ```bash
   # For skipped tests, read around the skip marker
   Read tests/unit/cli/test_cli.py offset=96 limit=30
   ```

3. **Search for patterns** across codebase:

   ```bash
   # Find all skipped tests
   Grep pattern="@pytest\.mark\.skip" path=tests/ output_mode=content

   # Find related model definitions
   Grep pattern="class RunToRerun" path=scylla/ output_mode=content
   ```

4. **Check current behavior** vs expected:

   ```bash
   # Verify actual test ID format
   ls tests/fixtures/tests/
   Read tests/fixtures/tests/test-001/test.yaml
   ```

5. **Review team knowledge** from related skills:
   - Check `.claude-plugin/skills/` for similar issues
   - Look for migration patterns (Pydantic v2, etc.)
   - Reference past test fixes

### Phase 2: Root Cause Analysis

For each affected test/file, categorize the issue:

**Common Categories:**

- **Format mismatch**: Test expects old format (e.g., "001-name" vs "test-001")
- **Pydantic migration**: Missing required fields, `.dict()` vs `.model_dump()`
- **Directory structure**: Glob patterns not matching test isolation setup
- **Mock configuration**: Mocks targeting wrong methods after refactoring

**Investigation Pattern:**

```python
# 1. Read the test
Read test_file.py offset=N limit=M

# 2. Read the implementation being tested
Grep pattern="def function_name" path=scylla/

# 3. Check model definitions for required fields
Read scylla/module/models.py

# 4. Review fixtures for completeness
Read tests/unit/module/conftest.py
```

### Phase 3: Create Structured Plan

**Required Sections:**

1. **Objective** - 2-3 sentence summary
2. **Approach** - High-level strategy and key decisions
3. **Files to Create** - New files needed (usually none for test fixes)
4. **Files to Modify** - Specific changes per file:

   ```markdown
   ### 1. tests/unit/cli/test_cli.py (Line 106-116)

   **Change**: Update test assertion to expect new format

   **Rationale**: Implementation changed to use "test-001" format

   **Specific modification**:
   ```python
   # Old
   assert "001-justfile-to-makefile" in result.output

   # New
   assert "test-001" in result.output
   ```

   ```

5. **Implementation Order** - Numbered steps with verification:

   ```markdown
   ### Step 1: Clean up merge artifacts
   ### Step 2: Fix easiest test first (CLI format)
   ### Step 3: Fix directory structure issue
   ### Step 4: Investigate and fix Pydantic migration (run test first)
   ### Step 5: Run full test suite
   ### Step 6: Commit with conventional format
   ```

6. **Verification** - How to test each change:

   ```bash
   # Individual test
   pixi run pytest tests/unit/cli/test_cli.py::TestClass::test_name -v

   # Full suite
   pixi run pytest tests/ -v

   # Check for artifacts
   find tests -name "*.orig" -type f
   ```

### Phase 4: Document Investigation Steps

**For issues requiring investigation** (Pydantic migrations, unclear failures):

```markdown
**Investigation steps:**
1. Run the test to see actual error
2. Check if ModelName has new required fields
3. Add missing fields to test fixture instantiation
```

**Key principle**: Don't guess - run the test first to see the actual error.

## Parameters & Configuration

### Commands Used

```bash
# Find merge artifacts
find tests -name "*.orig" -type f

# Search for skip markers
grep -r "@pytest.mark.skip" tests/unit/ --include="*.py"

# Run specific test
pixi run pytest tests/unit/module/test_file.py::TestClass::test_name -v

# Run full suite
pixi run pytest tests/ -v

# Pre-commit validation
pre-commit run --all-files
```

### Plan Structure Template

```markdown
# Implementation Plan: [Issue Title]

## Objective
[2-3 sentence summary]

## Approach
### High-Level Strategy
[Overall strategy]

### Key Decisions
- Decision 1 with rationale
- Decision 2 with rationale

## Files to Create
[List with descriptions or "None"]

## Files to Modify
### 1. path/to/file.py (Line X-Y)
**Change**: [What to change]
**Rationale**: [Why]
**Specific modification**: [Code diff]

## Implementation Order
### Step 1: [Task]
[Commands and verification]

### Step 2: [Task]
[Commands and verification]

## Verification
### Individual Test Verification
[Commands for each test]

### Full Test Suite Verification
[Commands for full validation]

### Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Dependencies and Integration Points
[Related code, models, fixtures]

## Risk Mitigation
[Strategies to avoid breaking changes]
```

## What Worked

### ✅ Systematic Investigation Before Planning

**Pattern:**

1. Read GitHub issue for full context
2. Examine each affected file (Read with offset/limit)
3. Search for patterns (Grep for skip markers, class definitions)
4. Check actual behavior vs expected (ls, Read yaml files)
5. Review team knowledge (read related skills)

**Why it worked:**

- Avoided assumptions about root causes
- Discovered different issues require different fixes
- Found actual test ID format ("test-001") vs expected ("001-justfile-to-makefile")
- Identified Pydantic migration as common theme

### ✅ Categorizing Root Causes

**Pattern:**
Group similar issues together:

- Format mismatches (CLI test)
- Pydantic migrations (rerun, tables tests)
- Directory structure (rate limit test)

**Why it worked:**

- Enabled ordering fixes from easiest to hardest
- Identified reusable patterns (Pydantic migration steps)
- Made verification strategy clearer

### ✅ Documenting "Investigation Required" Steps

**Pattern:**
For unclear failures, don't guess - plan to investigate:

```markdown
**Investigation steps:**
1. Run the test to see actual error
2. Check if ModelName has new required fields
3. Add missing fields to test fixture instantiation
```

**Why it worked:**

- Avoids making wrong assumptions in the plan
- Sets expectation that some fixes need runtime verification
- Documents the investigation process for future reference

### ✅ Ordering Fixes by Difficulty

**Pattern:**

1. Cleanup (delete .orig files) - trivial
2. Simple assertion update (CLI test) - easy, known fix
3. Directory structure fix (rate limit test) - medium, understand pattern
4. Pydantic investigation (rerun, tables) - hard, need to run tests first

**Why it worked:**

- Early wins build confidence
- Isolates complex issues to later steps
- Each success validates the investigation approach

### ✅ Specific File Paths and Line Numbers

**Pattern:**

```markdown
### 1. tests/unit/cli/test_cli.py (Line 106-116)
**Change**: Update assertion
```

**Why it worked:**

- Eliminates ambiguity about what to change
- Makes implementation straightforward
- Easy to verify changes are in the right place

## Failed Attempts

### ❌ Initially Tried to Fix Without Reading Code

**What happened:**
Started to plan fixes based only on skip reason messages without examining actual code.

**Why it failed:**

- Skip reasons were vague ("Pre-existing failure")
- Couldn't determine actual root cause from message alone
- Would have created incomplete plan

**Fix:**
Read each affected test file and understand:

- What the test is actually checking
- What the implementation does
- Why the assertion might be failing

**Lesson:**
Always read the actual code before planning fixes - don't trust summary messages.

### ❌ Assumed All Skips Had Same Root Cause

**What happened:**
Initially thought all 4 skipped tests were Pydantic migration issues because of commit 38a3df1 mention.

**Why it failed:**

- CLI test was actually a format mismatch (test IDs changed)
- Rate limit test was a directory structure issue
- Only 2/4 were actually Pydantic-related

**Fix:**
Investigate each test individually - different symptoms can have different causes even in related issues.

**Lesson:**
Don't over-generalize - examine each affected component separately.

### ❌ Tried to Plan Pydantic Fixes Without Running Tests

**What happened:**
Attempted to guess what Pydantic fields were missing by reading model definitions.

**Why it failed:**

- Models can be complex with inherited fields
- Required fields might be in validators or computed properties
- Can't know the exact error without running the test

**Fix:**
For investigation-required fixes, plan includes "run test first to see error" as explicit step.

**Lesson:**
For unclear failures, plan the investigation, don't try to solve it in the plan.

## Results & Verification

### Plan Deliverables

**Created:**

- Comprehensive implementation plan for issue #595
- 7 ordered implementation steps
- File-by-file modification strategy
- Verification commands for each step
- Risk mitigation strategies

**Structure:**

```
1. Clean merge artifacts (trivial)
2. Fix CLI test format (easy - known fix)
3. Fix rate limit directory structure (medium)
4. Investigate & fix rerun Pydantic issue (hard)
5. Investigate & fix tables Pydantic issue (hard)
6. Run full test suite
7. Commit with conventional format
```

### Verification Commands

```bash
# Verify artifacts removed
find tests -name "*.orig" -type f

# Test individual fixes
pixi run pytest tests/unit/cli/test_cli.py::TestListCommand::test_list_basic -v
pixi run pytest tests/unit/e2e/test_rate_limit_recovery.py::TestRateLimitDetection::test_detects_from_failed_directory -v

# Full suite
pixi run pytest tests/ -v

# Pre-commit validation
pre-commit run --all-files
```

### Success Metrics

- [ ] Plan covers all 4 skipped tests
- [ ] Plan includes .orig file cleanup
- [ ] Each fix has specific file/line references
- [ ] Investigation steps documented for unclear issues
- [ ] Verification strategy defined
- [ ] Ordered from easiest to hardest

## Related Skills

- **fix-ci-test-failures** - Fixing tests that fail in CI but pass locally
- **fix-pydantic-required-fields** - Handling Pydantic v2 migration issues
- **pr-merge-conflict-resolution** - Cleaning up .orig files after merges
- **pydantic-model-dump** - Using `.model_dump()` instead of `.dict()`

## When NOT to Use This Skill

Don't use for:

- Simple single-test fixes with obvious solutions
- Issues with clear implementation already defined
- Trivial changes (typos, formatting)
- When user wants implementation, not planning

**Instead:**

- For simple fixes: Just fix them directly
- For implementation requests: Use /feature-dev or implement directly
- For trivial changes: Make the change without planning phase

## Key Takeaways

1. **Always investigate before planning** - Read code, run searches, understand current behavior
2. **Categorize root causes** - Different issues need different fixes
3. **Order by difficulty** - Start with easy wins, isolate complex issues
4. **Document investigation steps** - Don't guess at Pydantic/migration issues
5. **Be specific** - File paths, line numbers, exact code changes
6. **Plan verification** - How to test each step individually and collectively
7. **Read actual code** - Don't trust skip messages or commit descriptions alone

## Future Improvements

- Create template for test migration issues (Pydantic v1→v2)
- Document common skip reasons and their typical fixes
- Build checklist for "investigation required" vs "known fix" classification
- Add examples of good vs bad investigation approaches
