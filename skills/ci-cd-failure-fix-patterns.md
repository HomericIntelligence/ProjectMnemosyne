---
name: ci-cd-failure-fix-patterns
description: "Concrete patterns for fixing CI failures after root cause is diagnosed. Use when: (1) CI checks fail on PR and root cause is known, (2) need to fix pre-commit/linting failures, (3) Dockerfile GID collisions on Ubuntu 24.04, (4) pre-commit bash -c hooks silently lose filenames, (5) Mojo --Werror unused return value errors, (6) split test files referenced in CI workflows, (7) tests pass locally but fail due to symlinks or mock bypass."
category: ci-cd
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# CI Failure Fix Patterns

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-03-28 | Consolidated fix patterns for CI failures once root cause is known | Operational |

Concrete, copy-paste ready fix patterns for common CI failure types. Use after diagnosis (see `ci-cd-failure-diagnosis-log-analysis`).

## When to Use

- CI checks fail on PR and you have identified the root cause
- Tests pass locally but fail in CI
- Workflow runs fail unexpectedly
- Pre-commit hooks fail on linting/formatting
- Docker builds fail with GID/UID collisions
- `bash -c` pre-commit hooks scan entire repo instead of matched files
- GitHub Actions workflows fail with "invalid SHA" or "unknown action" errors
- Mojo compilation fails with `unused return value` under `--Werror`
- Test files were split (ADR-009 pattern) but CI workflows still reference old filenames
- Tests fail due to absolute symlinks or mock bypass issues
- Mojo CI test assertion errors for edge cases

## Verified Workflow

### Quick Reference

```bash
# View PR checks
gh pr checks <pr-number>

# Get failure details
gh run view <run-id> --log-failed

# Fix pre-commit failures
pre-commit run --all-files
git add . && git commit --amend --no-edit && git push --force-with-lease

# Re-run failed jobs
gh run rerun <run-id> --failed

# Monitor CI
gh pr checks <pr-number> --watch
```

### Core Fix Workflow

1. **Check status** — view failed PR checks
2. **Get logs** — download or view failure details
3. **Reproduce** — run same commands locally
4. **Fix issue** — apply necessary changes (see patterns below)
5. **Verify** — test passes locally
6. **Push** — commit and push fix
7. **Monitor** — check CI passes

### Pattern 1: Pre-commit / Linting Failures

**Trailing whitespace / formatting**:

```bash
pre-commit run --all-files
git add .
git commit --amend --no-edit
git push --force-with-lease
```

**Markdownlint — files excluded incorrectly**:

The `.markdownlintignore` file is NOT read by pre-commit hooks. Use `exclude:` in `.pre-commit-config.yaml`:

```yaml
# Wrong: .markdownlintignore
# Correct: .pre-commit-config.yaml exclude regex
- repo: https://github.com/DavidAnson/markdownlint-cli2
  hooks:
    - id: markdownlint-cli2
      exclude: ^(notes/(plan|issues|review|blog)|\.claude/plugins)/
```

**Ruff line-length violations**:

```bash
# Find violations
ruff check <file_path>

# Fix: split long lines manually
# Before: single 107-char line comment
# After: split across two lines

# Verify
ruff check <file_path>
# Output: All checks passed!
```

**Common failure fixes**:

| Failure | Command | Fix |
|---------|---------|-----|
| Trailing whitespace | `pre-commit run --all-files` | Stage and re-commit |
| Test failure | `<package-manager> run mojo test tests/` or `pytest` | Fix code, re-run tests |
| Markdown lint | `markdownlint --fix "**/*.md"` | Commit fixes |
| Build error | Check imports/deps | Update and rebuild |
| Ruff line too long | `ruff check <file>` | Split lines |
| Docstring format | Read error | Add blank line, move closing quotes |

### Pattern 2: Dockerfile GID/UID Collision (Ubuntu 24.04)

**Symptom**: `groupadd: GID '1000' already exists` — Ubuntu 24.04 ships with the `ubuntu` user/group at UID/GID 1000.

**Fix**: Make user creation idempotent with fallback to rename:

```dockerfile
ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USER_NAME=dev

RUN groupadd -g ${GROUP_ID} ${USER_NAME} 2>/dev/null || \
    groupmod -n ${USER_NAME} $(getent group ${GROUP_ID} | cut -d: -f1) && \
    useradd -m -u ${USER_ID} -g ${GROUP_ID} -s /bin/bash ${USER_NAME} 2>/dev/null || \
    usermod -l ${USER_NAME} -d /home/${USER_NAME} -m $(id -nu ${USER_ID} 2>/dev/null || echo nobody)
```

**Why not `--force`?** `groupadd --force` only suppresses the error but doesn't rename the group. `groupmod -n` renames the existing group.

**Test locally**:
```bash
docker build --build-arg USER_ID=1000 --build-arg GROUP_ID=1000 -t test .
```

### Pattern 3: Pre-commit bash -c Arg Passing

**Symptom**: Pre-commit hook scans entire repo instead of matched files.

**Root cause**: When pre-commit passes filenames to a `bash -c` hook, the first argument becomes `$0` (the script name), NOT part of `$@`. If only one file matches, `$@` is empty.

**Broken**:
```yaml
entry: bash -c 'grep -rn "cargo" "$@"'
# Pre-commit calls: bash -c '...' Dockerfile
# $0 = Dockerfile, $@ = (empty), grep reads stdin/cwd
```

**Fixed**:
```yaml
entry: bash -c 'grep -rn "cargo" "$@"' --
# Pre-commit calls: bash -c '...' -- Dockerfile
# $0 = --, $@ = Dockerfile
```

**Test the fix**:
```bash
bash -c 'echo "$@"' -- Dockerfile  # Should print "Dockerfile"
bash -c 'echo "$@"' Dockerfile     # Prints nothing! $0 consumed the arg
```

**Rule**: ALWAYS end `bash -c` entries with `' --'` to preserve positional args.

### Pattern 4: Invalid Pinned Action SHAs

**Symptom**: `Error: Could not find actions/checkout@<sha>`.

**Fix**: Cross-reference valid SHAs from other workflow files in the repo:

```bash
grep -r "actions/checkout@" .github/
grep -r "actions/cache@" .github/
```

Use the SHA that appears most frequently (or is confirmed correct by other passing workflows).

| Action | Version | Example Confirmed SHA |
|--------|---------|----------------------|
| `actions/checkout` | v4 | `8e8c483db84b4bee98b60c0593521ed34d9990e8` |
| `actions/cache` | v5 | `cdf6c1fa76f9f475f3d7449005a359c84ca0f306` |

### Pattern 5: Split Test Files (ADR-009)

**Symptom**: CI workflow runs `just test-group "path" "test_foo.mojo"` but the file was split into `test_foo_part1.mojo` and `test_foo_part2.mojo`.

**Fix locations** (must update all three):

1. GitHub Actions workflow file:
   ```yaml
   # Before
   just test-group "tests/path/samplers" "test_sequential.mojo"
   # After
   just test-group "tests/path/samplers" "test_sequential_part1.mojo test_sequential_part2.mojo"
   ```

2. `run_all_tests.mojo` imports:
   ```mojo
   # Before
   from tests.shared.data.samplers.test_sequential import (...)
   # After
   from tests.shared.data.samplers.test_sequential_part1 import (...)
   ```

3. `comprehensive-tests.yml` matrix (if applicable)

### Pattern 6: Mojo --Werror Unused Return Values

**Symptom**: `error: unused return value` in benchmark or test files.

**Fix**: Prefix bare calls with `_ =`:

```mojo
# Before (compile error under --Werror)
sgd_step(model, grads, lr)
adam_step(model, grads, lr, m, v, t)

# After
_ = sgd_step(model, grads, lr)
_ = adam_step(model, grads, lr, m, v, t)
```

**Detection**:
```bash
grep -n "sgd_step\|adam_step\|fn.*-> Tuple" tests/shared/benchmarks/
# Add "_ = " prefix to each
sed -i 's/^    sgd_step/    _ = sgd_step/g' <file>
```

### Pattern 7: Test Passes Locally But Fails in CI (Symlinks/Mocks)

**Absolute symlinks break in CI**:

```bash
# Before (broken in CI)
/home/user/ProjectName/config/models/_test-model.yaml

# After (works everywhere)
../../../../config/models/_test-model.yaml

# Fix
cd tests/fixtures/config/models
rm test-model.yaml
ln -s ../../../../config/models/_test-model.yaml test-model.yaml
cat test-model.yaml  # Verify
```

**Mock bypass — mocking wrong method**:

If code calls `_run_with_volumes()` directly, `mock_executor.run()` won't intercept it:

```python
# Before (doesn't work)
mock_executor = MagicMock()
mock_executor.run.return_value = ContainerResult(...)
manager = SomeManager(executor=mock_executor)

# After (works)
@patch.object(SomeManager, "_run_with_volumes")
def test_run_success(self, mock_run_with_volumes: MagicMock, tmp_path: Path):
    mock_run_with_volumes.return_value = ContainerResult(...)
    manager = SomeManager()
```

### Pattern 8: Mojo Test Assertion / Edge Case Failures

**Symptom**: `Values are not equal`, test expects empty list or specific value but implementation returns different.

**Step-by-step fix**:
1. Run `gh pr checks <pr-number>` to identify failing jobs
2. Run `gh run view <run-id> --log-failed` to see detailed error
3. Locate failing test in logs by grepping for "FAILED", "error:", or "assertion"
4. Read the test file to understand what it expects
5. Read the implementation to identify why it returns unexpected value
6. Apply minimal fix — add early return for edge cases:

```mojo
fn some_function(input: List[T]) -> List[U]:
    # Handle empty inputs - return empty result
    if len(input) == 0:
        return List[U]()

    # Initialize max/min to -1 (not 0) so empty lists give correct result
    var max_val = -1
    # ... rest of implementation
```

7. Run test locally: `<package-manager> run mojo run <test-file>`
8. Run pre-commit: validate formatting passes
9. Commit with conventional format: `fix(scope): description`

### Pattern 9: Test Assertion Values Updated

**When source code values change (e.g., pricing updates), update test expectations**:

```python
# Before
assert cost == pytest.approx(0.018)

# After (match new behavior)
assert cost == pytest.approx(0.0183)
```

### Pattern 10: Memory Safety Failures (Mojo UnsafePointer)

**Symptom**: Segfault in `libKGENCompilerRTShared.so`, exit code 139, tests pass locally but crash in CI.

**Root cause**: Accessing `_data` through `list[i].field` creates a copy. The copy's pointer may be invalid after Python interop.

**Fix A: Create local copy (recommended)**:

```mojo
fn save_tensor(tensor: ExTensor, filepath: String, name: String = "") raises:
    # Create local copy to ensure stable data pointer
    var local_tensor = tensor
    var hex_data = bytes_to_hex(local_tensor._data, total_bytes)
```

**Fix B: Add null check (defense in depth)**:

```mojo
fn bytes_to_hex(data: UnsafePointer[UInt8], num_bytes: Int) -> String:
    if not data:
        return ""
    # ... rest of function
```

**Defensive coding rules**:
1. Always create local copies before accessing UnsafePointer fields
2. Add null checks at pointer access boundaries
3. Avoid accessing pointers through collection indices (`list[i].tensor._data`)
4. Test in CI environment — local tests may not catch memory issues

### Pattern 11: Rebase and Force Push After Fixes

```bash
git fetch origin
git rebase origin/main
git push --force-with-lease origin <branch-name>
```

If rebase has conflicts from cherry-picked commits already in main:

```bash
git rebase --reapply-cherry-picks origin/main
```

**Check if content already merged before rebasing**:

```bash
git log origin/main..<branch>
# If empty or shows only already-squashed content, close as superseded
```

### Pattern 12: Identify Required vs Optional Checks

Before fixing anything, determine which CI checks are required for merge:

```bash
gh api repos/<owner>/<repo>/branches/main/protection/required_status_checks \
  --jq '.contexts[]'
```

Only fix failures in required checks. Optional checks (e.g., benchmarks, performance tests) will not block merging even if they fail.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fix without reading logs | Guessed at fix based on error message | Missed root cause, fixed wrong thing | Always read full CI logs first |
| Push untested fix | Committed fix without local verification | Introduced new CI failure | Always test locally before pushing |
| Fix multiple issues at once | Changed multiple things in one commit | Hard to debug which fix worked | Fix one issue at a time |
| Ignore warnings | Focused only on errors | Warnings became errors later | Fix all warnings, follow zero-warnings policy |
| Added paths to `.markdownlintignore` | Expected pre-commit hook to read the ignore file | pre-commit's markdownlint-cli2 hook uses `args:` config, not `.markdownlintignore` | Always use `exclude:` regex in `.pre-commit-config.yaml` |
| Used `groupadd --force` | Tried --force flag to suppress GID exists error | --force doesn't rename the group, subsequent useradd fails with wrong group name | Use groupmod -n to rename existing group instead |
| Running `mojo format` locally on incompatible host | Tried to auto-format Mojo files | Local Mojo version has `comptime_assert_stmt` bug causing formatter crash | Apply Mojo format changes manually from CI diff output on incompatible hosts |
| Committing without fixing pre-commit hook | Tried to commit with broken no-cargo-in-docker hook | Hook scans entire repo including .pixi binaries, exits 1 on false positives | Fix the hook first — the `--` placeholder is essential for bash -c hooks |
| Used `git checkout <branch>` to switch branches | Expected standard git checkout | Safety Net hook blocked `git checkout` for branch switching | Use `git switch <branch>` instead |
| Used `git branch -D <branch>` to delete merged branch | Standard force-delete | Safety Net blocked `-D` (force delete) | Use `git branch -d <branch>` (safe delete) |
| Fixed PR by rebasing with new commits | Branch had commits already squash-merged into main | Rebase produced diverged history with duplicate content | Check if branch content already exists in main via `git log origin/main..<branch>` |
| Tried to fix baseline failures on PRs | Failures appeared on PR CI | Same failures existed on `main` — not PR-specific | Always check `main` CI status first |
| Committing directly to main | Fixed CI failure on wrong branch | Main branch is protected and requires PR; violates project workflow | Always verify current branch: `git branch --show-current` |
| Running tests without correct environment | Tests failed with `ModuleNotFoundError: No module named 'pandas'` | Analysis tests require `analysis` environment; default environment missing deps | Check `pixi.toml` for feature-specific environments |

## Results & Parameters

### Diagnosis and Fix Commands Cheat Sheet

```bash
# Get PR status
gh pr checks <PR_NUMBER>

# View workflow logs
gh run view <RUN_ID> --log
gh run view --job=<JOB_ID> --log

# Search logs for errors
gh run view --job=<JOB_ID> --log | grep -E "FAILED|ERROR"

# Check main branch CI history
gh run list --branch main --limit 5
gh run list --branch main --workflow test.yml --status success --limit 1

# Verify fixes locally
ruff check <file>
pre-commit run --all-files
pixi run pytest <test_path> -v
pixi run pytest tests/unit/analysis/ -v

# Fix workflow (when on wrong branch)
git branch --show-current
git reset --soft HEAD~1
git stash
gh pr checkout <PR>
git stash pop
git add <files> && git commit -m "fix: ..." && git push
```

### Required CI Checks (ProjectOdyssey)

```text
- pre-commit
- security-report
- Mojo Package Compilation
- Code Quality Analysis
- secret-scan
```

Benchmark and performance checks are NOT required.

### pre-commit Config Exclusion Pattern

```yaml
# Exclude multiple directory patterns
exclude: ^(notes/(plan|issues|review|blog)|\.claude/plugins)/
```

### Mojo Unused Return Fix Template

```bash
# Find all bare calls to functions returning Tuple
grep -n "^\s*sgd_step\|^\s*adam_step\|^\s*<fn_name>" <file>
# Add "_ = " prefix to each
sed -i 's/^    sgd_step/    _ = sgd_step/g' <file>
```

### Dockerfile Idempotent User Creation (Copy-Paste)

```dockerfile
# Idempotent user creation for Ubuntu 24.04+ (GID 1000 pre-exists)
ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USER_NAME=dev

RUN groupadd -g ${GROUP_ID} ${USER_NAME} 2>/dev/null || \
    groupmod -n ${USER_NAME} $(getent group ${GROUP_ID} | cut -d: -f1) && \
    useradd -m -u ${USER_ID} -g ${GROUP_ID} -s /bin/bash ${USER_NAME} 2>/dev/null || \
    usermod -l ${USER_NAME} -d /home/${USER_NAME} -m $(id -nu ${USER_ID} 2>/dev/null || echo nobody)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #336 pre-commit + test failures | Ruff, pytest approx fix |
| ProjectOdyssey | PR #4897 Dockerfile + pre-commit hook | GID 1000 collision, bash -c --fix |
| ProjectOdyssey | PR #4494 CI matrix JIT crash handling | continue-on-error for flaky groups |
| ProjectOdyssey | PR #3109 memory safety segfault | UnsafePointer local copy + null check |
| ProjectOdyssey | PR #4898 Mojo --Werror compile | alias→comptime 2-line fix |
| ProjectOdyssey | PR #3050 confusion matrix edge case | Empty input early return |
| ProjectScylla | PR #191 symlink + mock bypass | Relative symlinks, patch.object |
