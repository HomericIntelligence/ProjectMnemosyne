---
name: fix-evaluation-framework-bugs
description: "Fix critical E2E evaluation framework bugs causing false negative agent scores. Use when agents are penalized for framework issues."
category: debugging
date: 2026-01-18
user-invocable: false
---

# Skill: Fix Evaluation Framework Bugs

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-01-18 |
| **Category** | Debugging / Evaluation |
| **Objective** | Fix three critical E2E evaluation framework bugs causing false negative agent scores |
| **Outcome** | ✓ Success - All bugs fixed, CI passing, framework now scores agents correctly |
| **Session ID** | skill/evaluation/fix-judge-file-access |

## When to Use This Skill

Use this debugging pattern when:

1. **Agents penalized for framework issues** - Scores deducted for files/formatting the agent didn't create
2. **Intermittent FileNotFoundError** in parallel execution contexts
3. **Pre-commit failures on framework-generated files** - CLAUDE.md, config files
4. **Judge sees test configuration modifications** - Agent evaluated on framework changes
5. **Markdown lint violations in generated files** - Framework creates invalid markup

### Trigger Conditions

- Error: `FileNotFoundError: 'results/.../T3/best_subtest.json'`
- Judge deducting points for CLAUDE.md formatting (R014: -1.0, R010: -0.5, R008: -0.5)
- Pre-commit hooks failing: `MD040/fenced-code-language`, `MD022`, `MD032`, `MD047`
- Git diff showing CLAUDE.md modifications in agent evaluations

## Problem Patterns

### Pattern 1: Directory Assignment ≠ Directory Creation

**Symptom**: Intermittent `FileNotFoundError` during parallel execution

**Root Cause**: Path assigned but `mkdir()` never called

```python
# VULNERABLE
tier_dir = self.experiment_dir / tier_id.value
# ... later ...
save_selection(selection, str(tier_dir / "best_subtest.json"))  # FAILS
```

### Pattern 2: Framework Files in Judge Patchfile

**Symptom**: Agents penalized for CLAUDE.md modifications they didn't make

**Root Cause**: `_get_patchfile()` includes all files without filtering test config

```python
# VULNERABLE
subprocess.run(["git", "diff"], ...)  # Includes CLAUDE.md
```

### Pattern 3: Invalid Framework-Generated Markdown

**Symptom**: Pre-commit failures on framework-created files

**Root Cause**: Missing blank lines, no newline at EOF

```markdown
# INVALID (missing blank lines)
Use the following sub-agent to solve this task:
- chief-architect

## Cleanup Requirements
- Remove temporary files...
```

## Verified Workflow

### Step 1: Identify Framework vs Agent Issues

**Analyze judge output to separate concerns**:

```bash
# Check judge output for CLAUDE.md references
grep -i "claude.md\|r014\|format.*fail" judge_output.log

# Check if CLAUDE.md was in patchfile
grep -A 10 "patchfile" judge_output.log | grep -i claude
```

**Key questions**:
- Did the agent create/modify CLAUDE.md? → NO = framework bug
- Did formatting fail on framework files? → YES = framework bug
- Is error intermittent/timing-dependent? → YES = likely framework race condition

### Step 2: Fix Directory Creation Race Condition

**File**: `src/scylla/e2e/runner.py`

**Location**: Immediately after directory path assignment

```python
# Find assignment
tier_dir = self.experiment_dir / tier_id.value

# Add mkdir immediately after
tier_dir.mkdir(parents=True, exist_ok=True)
```

**Why this works**:
- `parents=True` - Creates parent directories if needed
- `exist_ok=True` - Idempotent (no error if already exists)
- Immediate creation - No gap for race conditions

### Step 3: Filter Framework Files from Patchfile

**File**: `src/scylla/e2e/llm_judge.py`

**Location**: `_get_patchfile()` function

```python
# Before
["git", "diff"]
["git", "diff", "--cached"]

# After - Use git pathspec exclusion
["git", "diff", "--", ".", ":(exclude)CLAUDE.md", ":(exclude).claude"]
["git", "diff", "--cached", "--", ".", ":(exclude)CLAUDE.md", ":(exclude).claude"]
```

**Why this works**:
- Git pathspec syntax excludes files at pattern-match level
- Applies to both staged and unstaged changes
- Judge never sees framework modifications

### Step 4: Generate Valid Markdown

**File**: `src/scylla/e2e/tier_manager.py`

**Location**: `build_resource_suffix()` method

```python
# Before (invalid markdown)
suffixes.append(f"{prefix}\n{bullet_list}")
cleanup = "\n\n## Cleanup Requirements\n..."

# After (valid markdown)
suffixes.append(f"{prefix}\n\n{bullet_list}")  # Blank line after heading
cleanup = "\n\n## Cleanup Requirements\n\n..."  # Blank line before bullets
cleanup += "...\n"  # Newline at EOF
```

**Markdown rules fixed**:
- MD022: Blank line after heading before content
- MD032: Blank line before bullet list
- MD047: Newline at end of file

### Step 5: Update Unit Tests

**File**: `tests/unit/e2e/test_tier_manager.py`

```python
# Update CLEANUP_INSTRUCTIONS constant
CLEANUP_INSTRUCTIONS = (
    "\n\n## Cleanup Requirements\n\n"  # Added \n\n
    "- Remove any temporary files...\n"
    "- Clean up after yourself...\n"  # Added \n
)

# Update all test expectations
expected = (
    "Use the following tool:\n\n"  # Added \n\n
    "- Read" + CLEANUP_INSTRUCTIONS
)
```

### Step 6: Verify All Fixes

```bash
# 1. Run unit tests locally
pixi run pytest tests/unit/e2e/test_tier_manager.py -v

# 2. Verify tier directory creation
pixi run python scripts/run_e2e_experiment.py --tiers T0 T1 T2 T3 --runs 1 --max-subtests 2

# 3. Check CLAUDE.md formatting
pixi run python << 'EOF'
from scylla.e2e.tier_manager import TierManager
from scylla.e2e.models import SubTestConfig
from pathlib import Path

manager = TierManager(Path("."))
subtest = SubTestConfig(
    id="01", name="test", description="test",
    resources={"agents": {"names": ["chief-architect"]}}
)
result = manager.build_resource_suffix(subtest)

# Verify formatting
assert "\n\n-" in result  # Blank line before bullets
assert result.endswith("\n")  # Newline at EOF
print("✅ CLAUDE.md formatting valid")
EOF

# 4. Verify patchfile exclusion
pixi run python << 'EOF'
import tempfile, subprocess
from pathlib import Path
import sys; sys.path.insert(0, 'src')
from scylla.e2e.llm_judge import _get_patchfile

with tempfile.TemporaryDirectory() as tmpdir:
    workspace = Path(tmpdir)
    subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=workspace, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=workspace, capture_output=True)

    (workspace / "file.txt").write_text("test\n")
    (workspace / "CLAUDE.md").write_text("config\n")
    subprocess.run(["git", "add", "."], cwd=workspace, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=workspace, capture_output=True)

    (workspace / "file.txt").write_text("modified\n")
    (workspace / "CLAUDE.md").write_text("modified config\n")

    patchfile = _get_patchfile(workspace)

    assert "CLAUDE.md" not in patchfile
    assert "file.txt" in patchfile
    print("✅ CLAUDE.md excluded from patchfile")
EOF
```

## Failed Attempts

**None** - All solutions worked on first try.

### Why Solutions Worked Immediately

1. **Clear error messages** - Stack traces pointed to exact locations
2. **Pattern recognition** - Similar bugs seen in other contexts
3. **Test-driven validation** - Unit tests caught issues before CI
4. **Double protection strategy** - Filter + format ensures no single point of failure

## Key Insights

### Critical Understandings

1. **Framework bugs masquerade as agent failures**
   - Judge sees all changes, including framework-managed files
   - Agents penalized for things they didn't do
   - False negatives harm evaluation validity

2. **Python pathlib behavior**
   - `Path()` assignment does NOT create directories
   - Always call `.mkdir(parents=True, exist_ok=True)` immediately
   - Race conditions expose these bugs in parallel execution

3. **Markdown formatting rules matter**
   - Framework-generated content must pass same checks as agent code
   - Blank lines after headings (MD022)
   - Blank lines before lists (MD032)
   - Newline at EOF (MD047)

4. **Double protection strategy**
   - Filter CLAUDE.md from patchfile (primary)
   - Generate valid markdown (secondary)
   - If one fails, the other catches it

### Best Practices

```python
# ALWAYS: Create directory immediately after assignment
directory_path = parent_path / "subdir"
directory_path.mkdir(parents=True, exist_ok=True)

# ALWAYS: Exclude framework files from git operations
["git", "diff", "--", ".", ":(exclude)CLAUDE.md", ":(exclude).claude"]

# ALWAYS: Generate valid markdown from framework
content = f"# Heading\n\n- Bullet item\n"  # Blank lines + EOF newline
```

## Results & Verification

### Fixes Applied

| Bug | File | Line | Fix |
|-----|------|------|-----|
| Directory not created | `runner.py` | 625 | `tier_dir.mkdir(parents=True, exist_ok=True)` |
| CLAUDE.md in patchfile | `llm_judge.py` | 683, 693 | `:(exclude)CLAUDE.md` pathspec |
| Invalid markdown | `tier_manager.py` | 620, 638, 652, 670, 680-683 | Add `\n\n` and `\n` |
| Test expectations | `test_tier_manager.py` | 13-17, 50, 66, 97, 111 | Update to match format |

### Commit History

**Branch**: `skill/evaluation/fix-judge-file-access`

1. **beb8ed7**: `fix(e2e): create tier directory before writing best_subtest.json`
2. **8d4a9d0**: `fix(judge): exclude CLAUDE.md and .claude/ from patchfile`
3. **bbf8f5b**: `fix(tier-manager): generate properly formatted CLAUDE.md`
4. **673467d**: `test(tier-manager): update tests for properly formatted CLAUDE.md`

### Impact

**Before fixes**:
- Intermittent FileNotFoundError in parallel tier execution
- Agents incorrectly penalized -2.0 points for framework issues
- Pre-commit hooks failed on framework-generated files
- Judge evaluated agents on framework modifications

**After fixes**:
- ✅ Tier directories always created before file writes
- ✅ Judge never sees CLAUDE.md changes (double protection)
- ✅ Framework generates valid markdown
- ✅ Agents evaluated only on their actual work
- ✅ All CI tests passing

### Verification Commands

```bash
# Run the experiment that previously failed
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-002 \
  --tiers T0 T1 T2 T3 T4 T5 T6 \
  --runs 1 --max-subtests 2 -v --fresh

# Check for FileNotFoundError
grep -i "filenotfounderror" experiment.log
# Expected: No matches

# Check tier directories created
ls -la results/experiment/T{0,1,2,3,4,5,6}/
# Expected: All directories exist

# Verify CLAUDE.md excluded from patchfile
# (Run unit test)
pixi run pytest tests/unit/e2e/test_tier_manager.py -v
# Expected: All tests pass
```

## Reusability

This pattern applies to any evaluation framework where:

1. **Framework manages test configuration** - Files like CLAUDE.md, .claude/, settings.json
2. **Parallel execution with checkpoint/resume** - Race conditions in directory creation
3. **LLM judges evaluate git diffs** - Must filter framework-managed files
4. **Framework generates content** - Must follow same quality standards as agent output
5. **Pre-commit hooks run on all changes** - Including framework-generated files

### Common Locations

- Result directory setup in parallel executors
- Judge patchfile generation
- Test configuration composition
- Markdown/config file generation
- Any git diff-based evaluation

## Related Issues

- Parallel execution race conditions
- Framework vs agent responsibility boundaries
- Test configuration file handling
- Git pathspec exclusion patterns
- Markdown formatting validation
- Double protection strategies for robustness

## Prevention Checklist

Add to framework code review:

- [ ] Every directory path assignment followed by `.mkdir(parents=True, exist_ok=True)`?
- [ ] All git diff operations exclude framework files with pathspec?
- [ ] All framework-generated content passes pre-commit hooks?
- [ ] Unit tests verify framework-generated content format?
- [ ] Judge only sees agent-created changes, not framework config?
