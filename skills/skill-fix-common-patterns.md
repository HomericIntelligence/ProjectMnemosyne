---
name: skill-fix-common-patterns
description: "Use when: (1) tests pass locally but fail in CI due to absolute symlinks or mocks patching the wrong method, (2) FileNotFoundError from a directory path assigned but never created before write, (3) evaluation framework bugs cause agents to be scored on framework changes they didn't make, (4) checkpoint resume fails with config mismatch or shows empty completed_runs despite result files on disk, (5) judge can't verify file creation tasks because workspace state only shows directory names, (6) unittest.mock.patch targets point to stdlib global namespace instead of the call-site module, (7) Pydantic model fixtures are missing newly required fields after model evolution, (8) rerun scripts don't complete all cases due to missing run_result.json or infinite judge retry loops"
category: debugging
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Common Fix Patterns for Debugging

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-29 |
| **Objective** | Consolidated reference for recurring debugging and fix patterns across evaluation, testing, and experiment infrastructure |
| **Outcome** | Merged from 8 source skills covering CI test failures, directory creation, evaluation bugs, checkpoint issues, judge access, mock patching, Pydantic fixtures, and rerun completion |
| **Verification** | unverified |

## When to Use

- Tests pass locally but fail in CI with "file not found" for symlinked files, or mocks have no visible effect
- `FileNotFoundError` occurs intermittently in parallel execution when writing to a directory path that was assigned but never explicitly created
- Agents are incorrectly penalized in E2E evaluation for CLAUDE.md modifications they didn't make, or framework-generated files fail pre-commit hooks
- Checkpoint resume fails with "Config has changed since checkpoint" despite identical config; or `completed_runs: {}` despite 590+ result files on disk
- Judge score is very low on file creation tasks; judge reasoning mentions "cannot verify file exists"; workspace state shows `?? directory/` instead of individual files
- `patch("subprocess.run", ...)` has no effect — real subprocess still executes, causing side-effects or timeouts in isolated environments
- Pydantic validation errors appear across multiple test files after a required field was added to a data model
- Dry-run shows rerun scripts as incomplete; missing `run_result.json`; fallback judge succeeds but judgment.json not persisted

## Verified Workflow

### Quick Reference

```bash
# --- CI symlink fix ---
cd tests/fixtures/config/models
rm test-model.yaml && ln -s ../../../../config/models/_test-model.yaml test-model.yaml
cat test-model.yaml  # verify

# --- Directory creation fix ---
grep -n "problematic_dir = " scylla/path/to/file.py
# Then add: directory_path.mkdir(parents=True, exist_ok=True) immediately after assignment

# --- Audit mock patch call-site targets ---
grep -rn 'patch("subprocess\.' tests/
grep -rn 'patch("os\.' tests/

# --- Find Pydantic required field failures ---
pixi run pytest tests/ -v 2>&1 | grep "missing 1 required positional argument"

# --- Diagnose checkpoint issues ---
find <exp_dir> -type f -name "result.json" -path "*/agent/result.json" \
  -exec sh -c 'dir=$(dirname $(dirname "$1")); [ ! -f "$dir/run_result.json" ] && echo "$dir"' _ {} \;

# --- Check judge rerun status ---
pixi run python scripts/rerun_agents.py <exp_dir> --dry-run
pixi run python scripts/rerun_judges.py <exp_dir> --dry-run
```

### Fix: CI Test Failures from Absolute Symlinks

**Problem**: Symlinks with absolute paths break in CI because the workspace location differs.

```bash
# Before (broken in CI)
readlink tests/fixtures/config/models/test-model.yaml
# /home/mvillmow/ProjectScylla/config/models/_test-model.yaml

# After (works everywhere)
cd tests/fixtures/config/models
rm test-model.yaml test-model-2.yaml
ln -s ../../../../config/models/_test-model.yaml test-model.yaml
ln -s ../../../../config/models/_test-model-2.yaml test-model-2.yaml
cat test-model.yaml  # Should show file content
```

**Key takeaways**: Always use relative symlinks. Absolute paths break when workspace location changes. Separate PRs for separate concerns.

### Fix: CI Test Failures from Mocks on Wrong Method

**Problem**: Test mocks `executor.run()` but code calls `_run_with_volumes()` directly, bypassing the injected executor.

```python
# Before (doesn't work — mock has no effect)
mock_executor = MagicMock()
mock_executor.run.return_value = ContainerResult(...)
manager = JudgeContainerManager(executor=mock_executor)

# After (works — patches the actual method called)
@patch.object(JudgeContainerManager, "_run_with_volumes")
def test_run_success(self, mock_run_with_volumes: MagicMock, tmp_path: Path):
    mock_run_with_volumes.return_value = ContainerResult(...)
    manager = JudgeContainerManager()
    result = manager.run_judge(config)
```

**Diagnosis**: Read the actual code path. Search for the method that does the real work, not the injected interface.

### Fix: Directory Not Created Before Write

**Problem**: In Python, `Path` assignment does NOT create directories. Parallel execution or checkpoint/resume paths expose this race condition.

```python
# VULNERABLE — directory assigned but not created
tier_dir = self.experiment_dir / tier_id.value
# ... other operations ...
save_selection(selection, str(tier_dir / "best_subtest.json"))  # FAILS

# FIXED — create immediately after assignment
tier_dir = self.experiment_dir / tier_id.value
tier_dir.mkdir(parents=True, exist_ok=True)  # always idempotent
save_selection(selection, str(tier_dir / "best_subtest.json"))  # works
```

**Parameters**: Always use `parents=True` (create parent dirs if needed) and `exist_ok=True` (no error if already exists). Apply this pattern everywhere a path is constructed from parent + child and files will be written directly to that directory.

**Common locations**: Result directory setup in parallel executors; temporary workspace creation in multi-threaded code; checkpoint/resume systems where initialization might be skipped.

### Fix: Evaluation Framework Bugs (Framework Files in Judge Scope)

**Three patterns** that cause agents to be incorrectly penalized:

**Pattern 1 — Directory creation race condition** (see above)

**Pattern 2 — Framework files in judge patchfile**:
```python
# Before — includes CLAUDE.md modifications the agent didn't make
["git", "diff"]

# After — exclude framework-managed files with git pathspec
["git", "diff", "--", ".", ":(exclude)CLAUDE.md", ":(exclude).claude"]
["git", "diff", "--cached", "--", ".", ":(exclude)CLAUDE.md", ":(exclude).claude"]
```

**Pattern 3 — Invalid framework-generated markdown**:
```python
# Invalid (missing blank lines, no EOF newline)
suffixes.append(f"{prefix}\n{bullet_list}")

# Valid (MD022: blank line after heading; MD032: blank line before bullets; MD047: EOF newline)
suffixes.append(f"{prefix}\n\n{bullet_list}")
cleanup = "\n\n## Cleanup Requirements\n\n- Remove temporary files...\n"
```

**Prevention checklist**:
- Every directory path assignment followed by `.mkdir(parents=True, exist_ok=True)`?
- All git diff operations exclude framework files with pathspec?
- All framework-generated content passes pre-commit hooks?
- Unit tests verify framework-generated content format?
- Judge only sees agent-created changes, not framework config?

### Fix: Checkpoint Config Mismatch and Data Loss

**Issue 1 — Config mismatch**: Load config from checkpoint's saved experiment.json instead of validating CLI args:

```python
if checkpoint_path and not self._fresh:
    self.checkpoint = load_checkpoint(checkpoint_path)
    self.experiment_dir = Path(self.checkpoint.experiment_dir)
    saved_config_path = self.experiment_dir / "config" / "experiment.json"
    if saved_config_path.exists():
        self.config = ExperimentConfig.load(saved_config_path)
        # CLI args don't matter — checkpoint config wins
```

**Issue 2 — Lost worker progress (CRITICAL)**: Main process overwrites worker-saved checkpoint state on interrupt. Fix: reload from disk before saving:

```python
finally:
    if is_shutdown_requested() and checkpoint_path and checkpoint_path.exists():
        try:
            current_checkpoint = load_checkpoint(checkpoint_path)  # reload worker state
            current_checkpoint.status = "interrupted"
            save_checkpoint(current_checkpoint, checkpoint_path)
        except Exception as reload_error:
            # Fallback: save stale copy (better than nothing)
            if self.checkpoint:
                self.checkpoint.status = "interrupted"
                save_checkpoint(self.checkpoint, checkpoint_path)
```

**Issue 3 — Incomplete serialization**: Ensure ALL dataclass fields appear in `to_dict()` and `load()`. Missing fields cause subtle bugs on resume.

**Repair script pattern** for recovering lost `completed_runs` from scattered result files:
```python
for run_result_file in experiment_dir.rglob("run_result.json"):
    tier_id, subtest_id, run_dir = parse_path(run_result_file)
    run_num = int(run_dir.split("_")[1])
    with open(run_result_file) as f:
        run_data = json.load(f)
    status = "passed" if run_data.get("judge_passed") else "failed"
    completed_runs[tier_id][subtest_id][run_num] = status
```

### Fix: Judge File Access for E2E Evaluation

**Problem**: Judge scores very low on file creation tasks because workspace state only shows directory names, judge has no tool access, and Mojo commands are missing from PATH.

**Fix 1 — Expand directory listings**:
```python
if status == "??" and full_path.is_dir():
    for child in sorted(full_path.rglob("*")):
        if child.is_file():
            rel_path = child.relative_to(workspace)
            if not _is_test_config_file(str(rel_path)):
                lines.append(f"- `{rel_path}` (created)")
```

**Fix 2 — Enable judge tool access via Claude CLI**:
```python
cmd = [
    "claude", "--model", model, "--print",
    "--output-format", "text",
    "--dangerously-skip-permissions",
    "--allowedTools", "Read,Glob,Grep",  # Read-only, no Write/Edit/Bash
    "--system-prompt-file", str(JUDGE_SYSTEM_PROMPT_FILE),
    "-p", prompt_file_path,
]
result = subprocess.run(cmd, cwd=workspace, ...)  # run in workspace directory
```

**Fix 3 — Use pixi for Mojo commands**:
```python
# Before: subprocess.run(["mojo", "build", "."], ...)
# After:
subprocess.run(["pixi", "run", "mojo", "build", "."], ...)
subprocess.run(["pixi", "run", "mojo", "format", "--check", "."], ...)
```

**Fix 4 — Update judge system prompt** to document available tools:
```markdown
**Tool Access**: You have access to Read, Glob, and Grep tools to inspect workspace files
directly. Use these tools when you need to verify file contents, search for patterns, or
examine code structure.
```

### Fix: Mock Patch Call-Site Targets

> **Core Rule**: Patch where the name is **used**, not where it is **defined**.

| Import Style | Call Style | Correct Patch Target |
| --- | --- | --- |
| `import subprocess` | `subprocess.run(...)` | `"<calling_module>.subprocess.run"` |
| `from subprocess import run` | `run(...)` | `"<calling_module>.run"` |
| `import time` | `time.sleep(...)` | `"time.sleep"` (module object attr, works globally) |

**Audit incorrect patches**:
```bash
grep -rn 'patch("subprocess\.' tests/
grep -rn 'patch("os\.' tests/
grep -rn 'patch("shutil\.' tests/
grep -rn 'patch("pathlib\.' tests/
```

**Apply fix with replace_all**:
```
# Edit with replace_all=true:
old_string: patch("subprocess.run",
new_string: patch("scylla.adapters.base_cli.subprocess.run",
```

**Exception**: `time.sleep` — patching `"time.sleep"` patches the attribute on the `time` module object in `sys.modules`, so all callers see the same patched attribute. This works globally.

**Add to CI quality gate**:
```bash
grep -rn 'patch("subprocess\.run"' tests/ && echo "ERROR: Use call-site patch targets" && exit 1 || true
```

### Fix: Pydantic Required Fields in Test Fixtures

After a required field is added to a Pydantic model, ALL test fixtures must be updated — both Python instantiations and YAML/JSON data files.

1. Identify the missing field: run `pixi run pytest tests/ -v` and look for `missing 1 required positional argument: 'field_name'`
2. Locate the model definition: `grep -r "class ExperimentConfig" <package>/`
3. Update ALL Python test fixtures:
   ```python
   config = ExperimentConfig(
       experiment_id="test-001",
       language="python",  # ADDED - new required field
       ...
   )
   ```
4. Update ALL YAML/JSON fixtures:
   ```yaml
   id: "001-test"
   language: mojo  # ADDED - new required field
   ...
   ```
5. Verify: `pixi run pytest tests/ -v`

**Prevention**: When adding required fields, immediately run full test suite; update all fixtures before committing; consider `Optional[str] = "default"` instead of `str` for non-critical fields; document purpose with comments.

### Fix: Rerun Completion Failures

**Issue 1 — Missing run_result.json not regenerated** — add handling for runs where `agent/result.json` and `judge/result.json` exist but `run_result.json` is missing:

```python
agent_result = json.load(open(agent_dir / "result.json"))
judge_result = json.load(open(judge_dir / "result.json"))
agent_timing = json.load(open(agent_dir / "timing.json"))
judge_duration_total = sum(
    json.load(open(jdir / "timing.json")).get("judge_duration_seconds", 0.0)
    for jdir in sorted(judge_dir.glob("judge_*"))
    if (jdir / "timing.json").exists()
)
# Note: tokens_input = input_tokens + cache_read_tokens (not just input_tokens)
```

**Issue 2 — Judge crashes when workspace directory cleaned up**:
```python
# Before (crashes if workspace deleted)
cwd = workspace if workspace else None

# After (graceful fallback — judge has full context in prompt already)
cwd = None
if workspace and workspace.exists():
    cwd = workspace
```

**Issue 3 — Fallback judge infinite retry** (returns result but doesn't save `judgment.json`):
```python
except Exception as e:
    fallback_result = _fallback_judge(agent_output)
    if actual_judge_dir:
        json.dump({
            "judge_duration_seconds": judge_duration,
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "failed": True, "fallback": True,
        }, open(actual_judge_dir / "timing.json", "w"), indent=2)
        judgment_data = fallback_result.to_dict()
        judgment_data["fallback"] = True
        judgment_data["fallback_reason"] = str(e)
        json.dump(judgment_data, open(actual_judge_dir / "judgment.json", "w"), indent=2)
    return fallback_result
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Mocking `executor.run()` | Injected mock executor and set `executor.run.return_value` | Code called `_run_with_volumes()` directly, bypassing the executor | Read the actual code path; mock the method that is actually called |
| Not creating directories explicitly | Relying on child operations to create parent directories implicitly | Child operations only run on some code paths; parallel execution exposes the gap | Always call `.mkdir(parents=True, exist_ok=True)` immediately after path assignment |
| `--Werror` asymmetry (local vs CI) | Tests compile locally without errors | CI uses `--Werror`; deprecation warnings become errors | Reproduce locally with CI flags: `pixi run mojo --Werror -I "$(pwd)" <test_file>` |
| Broad mock targets for subprocess | Used `patch("subprocess.run", ...)` globally | Mock had no effect in worktree/isolated environments | Patch at the call-site module: `patch("<module>.subprocess.run", ...)` |
| `@pytest.mark.skipif` at class level | Used class-level decorator to skip when optional dep missing | `pytest.importorskip` at class level skips entire module at collection time (0 tests collected) | Use `pytest.importorskip()` inside individual test methods |
| Checkpoint config validation via CLI args | Compared user-provided CLI args against saved checkpoint hash | User couldn't remember exact original args; hash mismatch blocks resume | Load config from saved experiment.json in checkpoint; CLI args are irrelevant on resume |
| Main process saves `self.checkpoint` on interrupt | Main process had stale `completed_runs: {}` but saved it on SIGINT | Workers had saved progress to disk; main process overwrote it | Always reload checkpoint from disk before saving on interrupt |
| Judge text-only API call for file verification | Sent text prompt to Anthropic API without tool access | Judge couldn't verify file contents for creation tasks | Use Claude CLI with `--allowedTools Read,Glob,Grep` and set `cwd=workspace` |
| Not persisting fallback judge result | Fallback returned in-memory result without saving `judgment.json` | Next rerun classified the slot as failed and retried indefinitely | Always persist every result path, including fallback paths |
| Using `input_tokens` alone for token calculation | Used `agent_result["token_stats"]["input_tokens"]` | Cache read tokens were not included; total was 33 instead of 195768 | `tokens_input = input_tokens + cache_read_tokens` |

## Results & Parameters

### Symlink Fix Commands (copy-paste)

```bash
cd tests/fixtures/config/models
rm test-model.yaml test-model-2.yaml
ln -s ../../../../config/models/_test-model.yaml test-model.yaml
ln -s ../../../../config/models/_test-model-2.yaml test-model-2.yaml
```

### Directory Creation Best Practice

```python
# ALWAYS follow this pattern
directory_path = parent_path / "subdir"
directory_path.mkdir(parents=True, exist_ok=True)
# Now safe to write files
(directory_path / "file.json").write_text(data)
```

### Mock Patch Targets (ProjectScylla)

| File | Old Target | New Target |
| ------ | --- | --- |
| `test_claude_code.py` | `subprocess.run` | `scylla.adapters.claude_code.subprocess.run` |
| `test_cline.py` | `subprocess.run` | `scylla.adapters.base_cli.subprocess.run` |
| `test_goose.py` | `subprocess.run` | `scylla.adapters.base_cli.subprocess.run` |
| `test_openai_codex.py` | `subprocess.run` | `scylla.adapters.base_cli.subprocess.run` |
| `test_opencode.py` | `subprocess.run` | `scylla.adapters.base_cli.subprocess.run` |

### Judge E2E Evaluation Recovery

| Tier | Score Before | Score After |
| ------ | ------------- | ------------- |
| T2 (file creation) | 0.07 | 0.77 |

**Judge tool allowlist**: `--allowedTools Read,Glob,Grep` (read-only, no Write/Edit/Bash)

### Rerun Completion Verification

```bash
# Agent completion
pixi run python scripts/rerun_agents.py <exp_dir> --dry-run
# Expected: ✓ completed: N, ⚠ results: 0, ✗ failed: 0

# Judge completion
pixi run python scripts/rerun_judges.py <exp_dir> --dry-run
# Expected: judge_01: ✓ complete: N ✗ failed: 0 (for all judges)
```
