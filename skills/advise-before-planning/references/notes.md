# Raw Session Notes: Advise Before Planning

## Session Details

**Date:** 2026-02-13
**Duration:** ~45 minutes
**Participants:** User + Claude Sonnet 4.5
**Repository:** ProjectScylla
**PR:** #606

## Initial Request

User provided a detailed plan to integrate the `/advise` skill into `plan_issues.py`:

```
Implement the following plan:

# Plan: Integrate /advise Skill into plan_issues.py

## Context

`scripts/plan_issues.py` bulk-plans GitHub issues by invoking Claude CLI to generate implementation plans and posting them as issue comments. Three problems need fixing:

1. **ModuleNotFoundError** when running `python scripts/plan_issues.py` directly (must use pixi env)
2. **Wrong CLI binary name** — code references `claude-code` but the actual binary is `claude`
3. **No team knowledge integration** — the planner doesn't leverage the ProjectMnemosyne skills registry before planning

The goal is a two-step planning workflow: Step 1 calls Claude to search the skills registry for relevant prior learnings (/advise), Step 2 feeds those findings into the plan generation prompt.
```

## Files Modified

| File | Changes |
|------|---------|
| `pixi.toml` | Added `plan-issues` task |
| `scylla/automation/models.py` | Added `enable_advise: bool = True` field |
| `scylla/automation/prompts.py` | Added `ADVISE_PROMPT` template and `get_advise_prompt()` |
| `scylla/automation/planner.py` | Extracted `_call_claude()`, added `_run_advise()`, refactored `_generate_plan()` |
| `scylla/automation/implementer.py` | Fixed `claude-code` → `claude` (2 locations) |
| `scripts/plan_issues.py` | Added `--no-advise` CLI flag |

## Files Created

| File | Purpose |
|------|---------|
| `tests/unit/automation/test_planner.py` | 10 tests for planner methods |
| `tests/unit/automation/test_prompts.py` | 4 tests for prompt generation |

## Implementation Timeline

1. **Step 1**: Added pixi task to `pixi.toml`
2. **Step 2**: Fixed CLI binary name (`claude-code` → `claude`) in 3 locations
3. **Step 3**: Added `enable_advise` field to `PlannerOptions`
4. **Step 4**: Created `ADVISE_PROMPT` template and helper function
5. **Step 5**: Refactored `planner.py` - extracted `_call_claude()` helper
6. **Step 6**: Added `_run_advise()` method with graceful degradation
7. **Step 7**: Enhanced `_generate_plan()` for two-step workflow
8. **Step 8**: Added `--no-advise` CLI flag to `scripts/plan_issues.py`
9. **Step 9**: Wrote comprehensive tests (14 new tests total)
10. **Step 10**: Verified all tests pass and pre-commit hooks pass

## Key Code Snippets

### Environment Variable for Nested Session Guard

```python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    check=True,
    timeout=timeout,
    env={"CLAUDECODE": ""},  # Avoid nested-session guard
)
```

**Why:** When running Claude CLI from within a Claude Code session, setting `CLAUDECODE=""` prevents warnings about nested sessions.

### Graceful Degradation Pattern

```python
def _run_advise(self, issue_number: int, issue_title: str, issue_body: str) -> str:
    try:
        # Try to run advise
        mnemosyne_root = repo_root / "build" / "ProjectMnemosyne"

        if not mnemosyne_root.exists():
            logger.warning("ProjectMnemosyne not found, skipping advise step")
            return ""

        # ... do advise work ...

    except Exception as e:
        logger.warning(f"Advise step failed: {e}")
        return ""  # Always return empty string on failure
```

**Why:** The planning workflow should work even if:

- ProjectMnemosyne repository is not cloned
- marketplace.json is missing
- Advise step times out or errors

### Context Injection Pattern

```python
# Build context with conditional advise findings
context_parts = [f"# Issue #{issue_number}: {issue_title}", "", issue_body]

if advise_findings:
    context_parts.extend([
        "",
        "---",
        "",
        "## Prior Learnings from Team Knowledge Base",
        "",
        advise_findings,
    ])

context_parts.extend(["", "---", "", prompt])
context = "\n".join(context_parts)
```

**Why:**

- Clear section separator with `---`
- Descriptive header so Claude knows this is prior context
- Placed between issue body and plan instructions (middle of prompt)
- Only inject if findings exist (avoid empty sections)

## Test Results

### Unit Tests

```bash
$ pixi run python -m pytest tests/unit/automation/ -v

============================= test session starts ==============================
collected 164 items

tests/unit/automation/test_planner.py::TestCallClaude::test_successful_call PASSED
tests/unit/automation/test_planner.py::TestCallClaude::test_empty_response PASSED
tests/unit/automation/test_planner.py::TestCallClaude::test_timeout PASSED
tests/unit/automation/test_planner.py::TestCallClaude::test_rate_limit_retry PASSED
tests/unit/automation/test_planner.py::TestCallClaude::test_system_prompt_passthrough PASSED
tests/unit/automation/test_planner.py::TestRunAdvise::test_returns_findings PASSED
tests/unit/automation/test_planner.py::TestRunAdvise::test_graceful_failure_on_error PASSED
tests/unit/automation/test_planner.py::TestRunAdvise::test_skips_when_mnemosyne_missing PASSED
tests/unit/automation/test_planner.py::TestGeneratePlan::test_plan_with_advise_findings PASSED
tests/unit/automation/test_planner.py::TestGeneratePlan::test_plan_without_advise PASSED
tests/unit/automation/test_prompts.py::test_get_implementation_prompt PASSED
tests/unit/automation/test_prompts.py::test_get_plan_prompt PASSED
tests/unit/automation/test_prompts.py::test_get_advise_prompt PASSED
tests/unit/automation/test_prompts.py::test_get_pr_description PASSED
... (150 more tests)

============================= 164 passed in 7.34s ==============================
```

### Pre-commit Hooks

```bash
$ pre-commit run --all-files

Check for shell=True (Security)..........................................Passed
Ruff Format Python.......................................................Passed
Ruff Check Python........................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check for Large Files....................................................Passed
Fix Mixed Line Endings...................................................Passed
```

## CLI Verification

```bash
$ pixi run plan-issues --help

usage: plan_issues.py [-h] --issues ISSUES [ISSUES ...] [--dry-run] [--force]
                      [--parallel N] [--system-prompt SYSTEM_PROMPT]
                      [--no-skip-closed] [--no-advise] [-v]

options:
  --no-advise           Skip the advise step (don't search team knowledge base
                        before planning)
```

## Design Decisions Log

### Decision 1: Advise Defaults ON

**Rationale:** Team knowledge should be leveraged by default. Users can opt-out with `--no-advise` if needed.

**Alternatives considered:**

- ❌ Default OFF with `--enable-advise` flag - Requires users to remember to enable it
- ❌ Auto-detect ProjectMnemosyne - Too implicit, hard to debug

### Decision 2: Direct File Reading vs Slash Command

**Rationale:** `--print` mode is non-interactive, so slash commands don't work. Instead, instruct Claude to read marketplace.json directly.

**Alternatives considered:**

- ❌ Spawn interactive session for `/advise` - Too heavyweight, slower
- ❌ Parse marketplace.json in Python - Less flexible, can't leverage Claude's search capabilities

### Decision 3: Graceful Degradation vs Hard Failure

**Rationale:** Planning should work even without team knowledge. Warn but don't block.

**Alternatives considered:**

- ❌ Fail hard if ProjectMnemosyne missing - Breaks workflow unnecessarily
- ❌ Silent fallback - Users won't know advise step was skipped

### Decision 4: Extract _call_claude() Helper

**Rationale:** DRY principle - both advise and plan steps need same subprocess + retry logic.

**Alternatives considered:**

- ❌ Inline subprocess calls - Code duplication
- ❌ Separate advise and plan callers - Inconsistent retry behavior

## Learnings

### What Worked Well

1. **Comprehensive test coverage** - 10 tests for new functionality caught edge cases
2. **Graceful degradation pattern** - Feature works with or without ProjectMnemosyne
3. **DRY helper extraction** - `_call_claude()` reused cleanly in both steps
4. **Clear section headers** - "Prior Learnings from Team Knowledge Base" makes context obvious

### What Could Be Improved

1. **Documentation** - Could add example of advise output to SKILL.md
2. **Metrics** - Could track how often advise finds relevant skills vs "None found"
3. **Caching** - Could cache marketplace.json reads across multiple issues in same batch

### Surprises

1. **CLAUDECODE env var** - Didn't know nested session guard existed
2. **--print vs --message** - CLI flag naming wasn't obvious from docs
3. **Linter improvements** - Pre-commit auto-upgraded to parenthesized context managers (Python 3.10+)

## Future Enhancements

Potential follow-up work:

1. **Advise metrics dashboard** - Track which skills are found most often
2. **Skill relevance scoring** - Weight skills by how closely they match the issue
3. **Multi-repository support** - Search multiple knowledge bases (ProjectMnemosyne, ProjectOdyssey, etc.)
4. **Advise caching** - Cache marketplace reads for batch operations
5. **Skill templates** - Generate skill scaffolding from advise findings

## Related Issues/PRs

- PR #606: feat(automation): Integrate /advise skill into plan_issues.py
- Related to ProjectMnemosyne skills marketplace design
- Builds on existing `plan_issues.py` bulk planning infrastructure

## Session Artifacts

**Branch:** `integrate-advise-skill-plan-issues`
**Commit:** `d5cd588`
**PR:** <https://github.com/HomericIntelligence/ProjectScylla/pull/606>
**Auto-merge:** Enabled (will merge on CI pass)

**Files changed:** 9 files, 491 insertions(+), 47 deletions(-)

- 7 modified files
- 2 new test files

## Commands Used

```bash
# Development
pixi run python -m pytest tests/unit/automation/test_planner.py -v
pixi run python -m pytest tests/unit/automation/test_prompts.py -v
pixi run python -m pytest tests/unit/automation/ -v
pre-commit run --all-files

# Git workflow
git checkout -b integrate-advise-skill-plan-issues
git add <files>
git commit -m "feat(automation): Integrate /advise skill into plan_issues.py"
git push -u origin integrate-advise-skill-plan-issues

# PR creation
gh pr create --title "..." --body "..."
gh pr merge --auto --rebase 606

# Verification
pixi run plan-issues --help
```
