# Skill: Retrospective Integration into Automation Pipeline

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-13 |
| **Category** | Automation |
| **Objective** | Integrate `/retrospective` skill into `implement_issues.py` to automatically capture learnings |
| **Outcome** | ✅ Success - Full implementation with comprehensive test coverage |
| **PR** | https://github.com/HomericIntelligence/ProjectScylla/pull/609 |

## When to Use This Skill

- **Capture session context automatically** - Resume Claude Code sessions for post-implementation tasks
- **Extract session IDs from Claude CLI** - Parse JSON output to get session identifiers  
- **Add optional pipeline phases** - Integrate new phases into existing automation workflows
- **Implement graceful degradation** - Add non-blocking features that enhance but don't break pipelines
- **Design opt-in features** - Add capabilities disabled by default to avoid disrupting workflows

## Verified Workflow

### 1. Capture Session ID from Claude CLI JSON Output

```python
result = run(["claude", "--message", prompt, "--output-format", "json"], ...)
try:
    data = json.loads(result.stdout)
    return data.get("session_id")
except (json.JSONDecodeError, AttributeError):
    logger.warning("Could not parse session_id")
    return None
```

**Key**: Use `.get()` for graceful None return, log warnings but never fail pipeline

### 2. Resume Session to Run Retrospective with Proper Permissions

**Critical**: When resuming a session to run `/retrospective`, you MUST provide tool permissions for git and gh commands:

```python
run([
    "claude",
    "--resume", session_id,
    "/skills-registry-commands:retrospective commit the results and create a PR",
    "--print",
    "--tools", "Bash",
    "--allowedTools", "Bash(git:*)",
    "--allowedTools", "Bash(gh:*)"
], cwd=worktree_path, timeout=600)
```

**Key Points**:
- Use `/skills-registry-commands:retrospective` as the command (not `--message`)
- Add explicit instructions: "commit the results and create a PR"
- `--print` mode for non-interactive execution
- `--tools "Bash"` enables Bash tool
- `--allowedTools "Bash(git:*)"` permits all git commands
- `--allowedTools "Bash(gh:*)"` permits all gh CLI commands
- Without these permissions, retrospective cannot commit to ProjectMnemosyne

**Wrong approach** (will fail to commit):
```python
# ❌ Missing tool permissions
run([
    "claude", "--resume", session_id, "--message",
    "Use the /skills-registry-commands:retrospective skill..."
], ...)
```

### 3. Add New Phase to Pydantic State Model

```python
class ImplementationPhase(str, Enum):
    RETROSPECTIVE = "retrospective"  # Add to enum

class ImplementationState(BaseModel):
    session_id: str | None = None  # Add optional field with None default
```

**Key**: New fields must have defaults for backward compatibility with persisted state

### 4. Integrate into Pipeline with Conditional Logic

```python
if self.options.enable_retrospective and state.session_id:
    state.phase = ImplementationPhase.RETROSPECTIVE
    self._save_state(state)
    self._run_retrospective(state.session_id, worktree_path, issue_number)
```

**Key**: Check both feature flag AND required data, always mark COMPLETED even if retrospective fails

## Failed Attempts

### ❌ Testing Claude CLI JSON Output in Nested Session

**Tried**: Running `claude --print "Hello" --output-format json` in test

**Failed**: `"Error: Claude Code cannot be launched inside another Claude Code session"`

**Why**: By design to prevent resource conflicts and crashes

**Solution**: Mock subprocess calls in unit tests, validate JSON parsing logic separately

### ❌ Resuming Session Without Tool Permissions

**Tried**: Using `--message` flag to invoke retrospective without explicit tool permissions

**Failed**: Retrospective runs but cannot commit to ProjectMnemosyne or create PR

**Why**: Resumed sessions need explicit `--allowedTools` for git/gh operations

**Solution**: Use command-style invocation with `--tools` and `--allowedTools` flags

## Results & Parameters

| Component | Value | Rationale |
|-----------|-------|-----------|
| Session resume timeout | 600s | Retrospective involves cloning + PR creation |
| Implementation timeout | 1800s | Complex implementations need generous timeout |
| Phase ordering | After CREATING_PR, before COMPLETED | Work saved but state not finalized |
| Default flag state | False | Opt-in to avoid disrupting workflows |
| Error handling | Log warning, never raise | Non-blocking enhancement |
| Tool permissions | Bash(git:*), Bash(gh:*) | Required for committing and creating PRs |

### Test Coverage

```bash
178 passed in 7.39s  # All automation tests pass
All checks passed     # Pre-commit hooks pass
```

### Usage

```bash
# With retrospective enabled
python scripts/implement_issues.py --epic 123 --retrospective
```

## Reusable Patterns

### Extract JSON CLI Output
```python
try:
    data = json.loads(result.stdout)
    value = data.get("key")
except (json.JSONDecodeError, AttributeError):
    return None
```

### Resume Session with Tool Permissions
```python
run([
    "claude",
    "--resume", session_id,
    "/skill-name command arguments",
    "--print",
    "--tools", "Bash",
    "--allowedTools", "Bash(git:*)",
    "--allowedTools", "Bash(gh:*)"
], cwd=worktree_path, timeout=600)
```

### Non-Blocking Optional Phase
```python
try:
    execute_optional_feature()
except Exception as e:
    logger.warning(f"Feature failed: {e}")
    # Don't re-raise
```

## Tags

`automation` `claude-cli` `session-management` `pipeline-integration` `graceful-degradation` `tool-permissions`
