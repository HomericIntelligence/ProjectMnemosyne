---
name: "Skill: Fix Judge File Access for E2E Evaluation"
description: "Skill: Fix Judge File Access for E2E Evaluation"
category: debugging
date: 2026-01-18
user-invocable: false
---
# Skill: Fix Judge File Access for E2E Evaluation

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-18 |
| **Objective** | Fix E2E test evaluation failures where judge cannot verify agent work on file creation tasks |
| **Outcome** | ✅ Success - T2 score improved from 0.07 (failing) to 0.77 (passing) |
| **Category** | evaluation |
| **Complexity** | Medium |

## Overview

When running E2E tests with the judge evaluating agent work, the judge was unable to properly assess tasks involving file creation (especially in new directories). This resulted in test failures even when agents completed tasks correctly.

**Symptoms**:
- Judge scores very low (0.07) despite agent creating correct files
- Judge can't verify file contents or directory structure
- Git status shows only directory names, not files inside untracked directories
- Mojo pipeline commands fail with "command not found"

**Root Causes**:
1. Workspace state only listed directory names for untracked directories, not individual files
2. Judge had no tool access to read file contents for verification
3. Mojo commands used `mojo` instead of `pixi run mojo` (missing from PATH)
4. System prompt didn't inform judge about available tools

## When to Use This Skill

Use this skill when you encounter:

1. **E2E test failures with low judge scores** despite agent appearing to complete task
2. **Judge can't verify file creation** - judge reasoning mentions "cannot verify file exists"
3. **Workspace state shows directories but not files** - e.g., `?? mojo/examples/hello-world/` instead of individual files
4. **Mojo pipeline failures** - "mojo: command not found" errors
5. **Judge mentions lacking context** to verify implementation details

**Trigger Pattern**: Judge score < 0.3 on file creation tasks where agent output looks correct

## Verified Workflow

### 1. Expand Directory Listings in Workspace State

**File**: `scylla/e2e/llm_judge.py`
**Function**: `_get_workspace_state()`

**Problem**: Git status shows `?? directory/` for untracked directories, hiding all files inside.

**Solution**: Recursively expand untracked directories to list all files:

```python
# Handle untracked directories - expand to show all files
if status == "??" and full_path.is_dir():
    for child in sorted(full_path.rglob("*")):
        if child.is_file():
            rel_path = child.relative_to(workspace)
            if not _is_test_config_file(str(rel_path)):
                lines.append(f"- `{rel_path}` (created)")
```

**Key Points**:
- Check if path is directory: `full_path.is_dir()`
- Use `rglob("*")` to recursively find all files
- Sort results for deterministic output: `sorted()`
- Filter out test config files (CLAUDE.md, .claude/)

### 2. Enable Judge Tool Access

**File**: `scylla/e2e/llm_judge.py`
**Function**: `_call_claude_judge()`

**Problem**: Judge runs via Anthropic API with only text prompt - can't read workspace files.

**Solution**: Run judge via Claude CLI with tool access:

```python
def _call_claude_judge(
    evaluation_context: str, model: str, workspace: Path | None = None
) -> tuple[str, str, str]:
    cmd = [
        "claude",
        "--model", model,
        "--print",
        "--output-format", "text",
        "--dangerously-skip-permissions",
        "--allowedTools", "Read,Glob,Grep",  # Read-only file access
        "--system-prompt-file", str(JUDGE_SYSTEM_PROMPT_FILE),
        "-p", prompt_file_path,
    ]

    # Run in workspace directory so judge can access files
    cwd = workspace if workspace else None
    result = subprocess.run(cmd, cwd=cwd, ...)
```

**Key Points**:
- Add `workspace` parameter to function signature
- Use `--allowedTools Read,Glob,Grep` for read-only access (no Write, Edit, Bash)
- Set `cwd=workspace` so judge runs in workspace directory
- Update call site: `_call_claude_judge(judge_prompt, model, workspace)`

### 3. Fix Mojo Pipeline Commands

**File**: `scylla/e2e/llm_judge.py`
**Function**: `_run_mojo_pipeline()`

**Problem**: Direct `mojo` command not in PATH - needs to run via pixi environment.

**Solution**: Change all mojo commands to use `pixi run mojo`:

```python
# Before
subprocess.run(["mojo", "build", "."], ...)

# After
subprocess.run(["pixi", "run", "mojo", "build", "."], ...)
```

**Affected Commands**:
- `mojo build .` → `pixi run mojo build .`
- `mojo format --check .` → `pixi run mojo format --check .`
- `mojo test` → `pixi run mojo test`

**Also Update**: Generated replay scripts in `_save_pipeline_commands()`:

```bash
#!/usr/bin/env bash
cd "$WORKSPACE"
pixi run mojo build .
```

### 4. Update Judge System Prompt

**File**: `config/judge/system_prompt.md`
**Section**: `<workspace_inspection_rules>`

**Problem**: Judge doesn't know it has tool access.

**Solution**: Add note about tool capabilities:

```markdown
**Tool Access**: You have access to Read, Glob, and Grep tools to inspect
workspace files directly. Use these tools when you need to verify file contents,
search for patterns, or examine code structure. The "Workspace State" section
shows what files exist, but you can read their full contents using the Read
tool to verify implementation details.
```

### 5. Enhance Patchfile Section (Optional)

**File**: `scylla/judge/prompts.py`
**Function**: `build_task_prompt()`

**Enhancement**: Add note that patchfile doesn't show new files:

```python
if patchfile and patchfile not in ("(no changes detected)", ...):
    sections.append(
        f"## Git Diff (Patchfile)\n\n"
        f"*Note: This shows changes to tracked files. "
        f"For new files, use the Read tool to view their contents.*\n\n"
        f"```diff\n{patchfile}\n```"
    )
```

## Failed Attempts

**None** - All planned fixes worked on first implementation.

The plan was well-researched by comparing successful test-001 (Python tasks) with failing test-002 (Mojo tasks), which revealed the exact gaps.

## Results & Parameters

### Before Fix
```
T0: PASS (score: 0.63)
T1: PASS (score: 0.63)
T2: FAIL (score: 0.07) ❌
```

### After Fix
```
T0: PASS (score: 0.61)
T1: PASS (score: 0.70, CoP: $0.48) - Best cost efficiency
T2: PASS (score: 0.77, CoP: $0.82) ✅ - Highest quality
```

**Improvement**: T2 score 0.07 → 0.77 (10x improvement, +0.70)

### Configuration Parameters

**Judge Tool Allowlist**:
```bash
--allowedTools Read,Glob,Grep  # Read-only, no Write/Edit/Bash
```

**Mojo Pipeline Commands**:
```bash
pixi run mojo build .
pixi run mojo format --check .
pixi run mojo test
```

**Workspace State Expansion**:
```python
# Recursively expand directories
for child in sorted(full_path.rglob("*")):
    if child.is_file():
        rel_path = child.relative_to(workspace)
        if not _is_test_config_file(str(rel_path)):
            lines.append(f"- `{rel_path}` (created)")
```

**Test Execution**:
```bash
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-002 \
  --tiers T0 T1 T2 --runs 1 -v --max-subtests 1
```

## Key Insights

1. **Judge needs workspace access**: Text-only prompts insufficient for file verification - judges need read tools
2. **Directory expansion critical**: Git status output must be expanded to show all files, not just directory names
3. **Environment commands**: Use `pixi run` prefix for all Mojo commands in test environments
4. **System prompt documentation**: Always document tool capabilities in system prompts
5. **Verification gap analysis**: Compare passing/failing tiers to identify exact capabilities missing

## Related Files

- `scylla/e2e/llm_judge.py` - Core judge implementation
- `scylla/judge/prompts.py` - Prompt building logic
- `config/judge/system_prompt.md` - Judge evaluation instructions
- `tests/fixtures/tests/test-002/` - Test case that exposed the issue

## Success Criteria

When applying this skill, you've succeeded if:

1. ✅ Judge scores improve significantly (0.07 → 0.77)
2. ✅ All tiers pass evaluation
3. ✅ Workspace state shows individual files, not just directories
4. ✅ Mojo pipeline commands execute successfully
5. ✅ Judge can verify file contents in reasoning
6. ✅ No "cannot verify" statements in judge output

## Tags

`evaluation` `judge` `e2e-testing` `file-access` `mojo` `workspace-state` `tool-access` `pixi`
