# Session Notes - Fix implement_issues.py

## Timeline of Fixes

### Issue 1: Git Status Parsing (ests/unit/...)

**Error**: `Command '['git', 'add', 'ests/unit/analysis/test_tables.py', ...]' returned non-zero exit status 128`

**Root cause**: Line parsing issue

```python
# Position 0: index status
# Position 1: working tree status
# Position 2: space separator
# Position 3+: filename

# WRONG: Removes first character
filename_part = line[3:].strip()

# RIGHT: Position 3 is already correct
filename_part = line[3:]
```

### Issue 2: Branch Already Exists

**Error**: `fatal: a branch named '595-auto-impl' already exists`

**Solution**: Check branch existence before creating worktree

```python
result = run(["git", "rev-parse", "--verify", branch_name], check=False)
if result.returncode == 0:
    # Branch exists, reuse it
    run(["git", "worktree", "add", worktree_path, branch_name])
else:
    # Create new branch
    run(["git", "worktree", "add", "-b", branch_name, worktree_path, base])
```

### Issue 3: Branch Not Pushed

**Error**: `Branch 595-auto-impl not found on origin. Claude may not have pushed`

**Original approach** (too strict):

```python
if not branch_on_remote:
    raise RuntimeError("Not pushed")
```

**Better approach** (fallback):

```python
if not branch_on_remote:
    logger.warning("Not pushed, pushing now...")
    run(["git", "push", "-u", "origin", branch_name])
```

### Issue 4: Import Error

**Error**: `cannot import name 'gh_call' from 'scylla.automation.github_api'`

**Fix**: Use `_gh_call` (private function) and parse JSON:

```python
from .github_api import _gh_call
result = _gh_call(["pr", "list", "--head", branch_name, "--json", "number"])
pr_data = json.loads(result.stdout)
```

## Key Learnings

1. **Automation should be resilient**: Don't fail on things you can fix automatically
2. **Parse carefully**: Understand exact format before adding operations like `.strip()`
3. **Fallback > Fail**: Verify-and-fallback pattern is more robust than strict verification
4. **Clear errors**: Log stderr/stdout when commands fail for easier debugging
5. **Permission flags matter**: `--permission-mode dontAsk` prevents automation from hanging

## Claude Code Integration Pattern

```python
# 1. Write prompt to file (supports multiline better than --message)
prompt_file.write_text(prompt)

# 2. Run with critical flags
result = run([
    "claude",
    str(prompt_file),
    "--output-format", "json",  # For programmatic parsing
    "--permission-mode", "dontAsk",  # No interactive prompts
    "--allowedTools", "Read,Write,Edit,Glob,Grep,Bash",  # Explicit permissions
])

# 3. Parse session_id from JSON
data = json.loads(result.stdout)
session_id = data.get("session_id")

# 4. Verify and fallback
if not pushed:
    push()
if not pr_created:
    create_pr()
```

## Test Results

All 199 automation tests pass ✅

- 18 worktree manager tests
- 25 implementer tests
- 6 prompt tests
- 150+ other automation tests

## PR Summary

**PR #624**: 6 commits

1. Fix git status parsing
2. Move git ops to Claude
3. Reuse existing branches
4. Add error logging
5. Make PR creation robust
6. Fix import error

Total lines: +147 -41
