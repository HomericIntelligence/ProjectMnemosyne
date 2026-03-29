---
name: fix-ci-compilation-and-test-failures
description: "Use when: (1) CI fails with Mojo compilation error (unknown declaration, deprecated syntax), (2) markdownlint blocks pre-commit (MD051, MD037, MD031, MD040, MD026, MD013), (3) Mojo test assertion errors from edge cases, (4) CI segfaults from UnsafePointer access through copied structs, (5) all PR CI runs fail because of broken plugins on main (missing plugin.json or YAML frontmatter)"
category: ci-cd
date: 2026-03-29
version: 2.0.0
user-invocable: false
verification: unverified
tags: []
---

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-29 |
| Objective | Consolidated CI failure fix patterns: compilation errors, lint failures, test assertion edge cases, memory safety crashes, and broken main-branch plugins |
| Outcome | Merged from 5 source skills |
| Verification | unverified |

## When to Use

- All PR CI runs fail with plugin validation errors (even PRs that don't touch plugins)
- A plugin directory exists but has no `.claude-plugin/plugin.json`
- `SKILL.md` exists but does not start with `---` (missing YAML frontmatter)
- Mojo compilation fails with `use of unknown declaration '<function_name>'` after a refactor
- `markdownlint-cli2` reports MD051, MD037, MD031, MD040, MD026, or MD013 errors
- CI is blocked on both comprehensive tests (compilation) and pre-commit (lint)
- CI failing with "Values are not equal" or similar assertion error in Mojo tests
- Test expects specific return value but implementation returns different (edge case missing)
- Segfault in `libKGENCompilerRTShared.so` during `UnsafePointer` access
- Tests pass locally but fail in CI (memory safety, Docker differences)
- Crashes after Python FFI calls (`os.makedirs()`, `pathlib.Path()`)

## Verified Workflow

### Quick Reference

```bash
# View PR checks
gh pr checks <pr-number>

# View failed run details
gh run view <run-id> --log-failed

# Verify Mojo compilation fix
pixi run mojo package -I . shared -o /tmp/shared.mojopkg

# Verify lint fixes on specific files
SKIP=mojo-format pixi run pre-commit run --files <file1> <file2>

# Full pre-commit validation
SKIP=mojo-format pixi run pre-commit run --all-files
```

### Step 1: Diagnose — Read Logs First

```bash
# 1. View CI status
gh pr checks <pr-number>

# 2. Get failure details
gh run view <run-id> --log-failed

# 3. Download logs for analysis
gh run download <run-id>
```

Common failure categories:
- `SKILL.md missing YAML frontmatter` / `Missing .claude-plugin/plugin.json` → Step 2
- `use of unknown declaration` / Mojo compilation error → Step 3
- MD051, MD037, MD031, MD040, MD026, MD013 → Step 4
- `Values are not equal` / assertion error in Mojo test → Step 5
- `exit code 139` / segfault in `libKGENCompilerRTShared.so` → Step 6

### Step 2: Fix Broken Main-Branch Plugin Validation

Run the validator locally to find all failures:

```bash
python3 scripts/validate_plugins.py plugins/
```

Look for `FAIL:` entries. Common errors:
- `Missing .claude-plugin/plugin.json`
- `SKILL.md missing YAML frontmatter (must start with ---)`
- `Missing Failed Attempts section (REQUIRED)`

Create missing `plugin.json`:

```bash
mkdir -p plugins/<category>/<name>/.claude-plugin/
```

Minimum required fields:

```json
{
  "name": "kebab-case-name",
  "version": "1.0.0",
  "description": "At least 20 characters describing trigger conditions",
  "skills": "./skills"
}
```

Add YAML frontmatter to `SKILL.md` (line 1 must be `---`):

```markdown
---
name: "skill-name"
description: "Short description"
category: <one of: training|evaluation|optimization|debugging|architecture|tooling|ci-cd|testing>
date: YYYY-MM-DD
user-invocable: false
---
```

Add a minimal Failed Attempts table if missing:

```markdown
## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
```

After fixing, rebase any blocked PRs:

```bash
# Identify open PRs blocked by the root-cause failure
gh pr list --state open

# Enable auto-merge after rebasing
gh pr merge --auto --rebase <pr-number>
```

### Step 3: Fix Mojo Compilation Errors

Find the broken reference:

```bash
grep -rn '<function_name>' shared/core/
```

Add a local private function rather than importing from another module — foundational modules (`core`) should not depend on higher-level modules (`utils`):

```mojo
fn _dtype_to_string(dtype: DType) -> String:
    if dtype == DType.float32:
        return "float32"
    # ... etc
    else:
        return "unknown"
```

Fix deprecated Mojo syntax:

| Deprecation | Old | New |
|-------------|-----|-----|
| Pointer offset | `ptr.offset(n)` | `ptr + n` |
| Type alias | `alias X = Y` | `comptime X = Y` |
| Docstring format | Missing period in Returns | Add `.` at end |

Verify compilation:

```bash
pixi run mojo package -I . shared -o /tmp/shared.mojopkg
# Warnings are OK; errors are not
```

### Step 4: Fix Markdown Lint Errors

| Rule | Issue | Fix |
|------|-------|-----|
| MD051 | Link fragment points to non-existent heading | Remove link or fix anchor |
| MD037 | Spaces inside emphasis markers (`* text*`) | Escape asterisks with `\*` if used as math operators |
| MD031 | Missing blank line before/after code block | Add blank line between closing ``` and `---` |
| MD040 | Fenced code block without language | Add `text`, `bash`, `yaml`, etc. |
| MD026 | Trailing punctuation in heading | Remove colon from heading text |
| MD013 | Line exceeds 120 characters | Break line at natural boundary |

Verify fix:

```bash
# Run on specific files first (fast feedback)
SKIP=mojo-format pixi run pre-commit run --files <file1> <file2>

# Full validation
SKIP=mojo-format pixi run pre-commit run --all-files

# Or using npx directly
npx markdownlint-cli2 --fix "**/*.md"
```

### Step 5: Fix Mojo Test Assertion Errors

1. Check CI status: `gh pr checks <pr-number>`
2. Get failed logs: `gh run view <run-id> --log-failed`
3. Locate the failing test in logs (grep for `FAILED`, `error:`, `assertion`)
4. Read the test file to understand what value is expected
5. Read the implementation to identify why it returns an unexpected value
6. Apply minimal fix — typically add early return for edge cases:

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
8. Run pre-commit to validate formatting: `pixi run pre-commit run --all-files`
9. Commit with conventional format: `fix(scope): description`
10. Push and monitor CI: `gh pr checks <pr-number> --watch`

### Step 6: Fix Memory Safety Failures (Mojo Segfaults)

**Root cause**: Accessing `UnsafePointer` fields through a struct copy created by list indexing (`list[i].field`).

Why it crashes:
1. `tensors[i].tensor` returns a **copy** via `__copyinit__`
2. Copy shares `_data` pointer via refcount
3. Python interop (`os.makedirs()`, `pathlib.Path()`) can interfere with pointer validity
4. When `bytes_to_hex()` accesses the pointer later, it may be invalid → segfault

**Fix A — Create local copy (recommended)**:

```mojo
fn save_tensor(tensor: ExTensor, filepath: String, name: String = "") raises:
    # Create local copy to ensure stable data pointer
    # Prevents issues when tensor is accessed through List[NamedTensor]
    var local_tensor = tensor

    var numel = local_tensor.numel()
    var dtype_size = get_dtype_size(local_tensor.dtype())
    var total_bytes = numel * dtype_size
    var hex_data = bytes_to_hex(local_tensor._data, total_bytes)
```

**Fix B — Add null check (defense in depth)**:

```mojo
fn bytes_to_hex(data: UnsafePointer[UInt8], num_bytes: Int) -> String:
    # Defensive null check for pointer safety
    if not data:
        return ""
    # ... rest of function
```

Use both fixes together for defense in depth.

After fixing, run pre-commit to catch formatting issues introduced during the fix:

```bash
pixi run mojo format <modified-file>.mojo
pixi run pre-commit run --all-files
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fix MD051 by changing `#pre-commit` to `#pre-commit-1` | Assumed GitHub auto-dedup suffix for duplicate anchors | The heading wasn't duplicated — `#pre-commit` was the correct anchor | Always check actual heading count before guessing dedup suffixes |
| Fix MD037 by removing spaces around `*` | Changed `grad_output * alpha` to `grad_output *alpha` | This created emphasis markers wrapping `alpha, ...` | Use `\*` to escape asterisks used as math multiplication operators |
| Fix without reading logs | Guessed at fix based on error message | Missed root cause, fixed wrong thing | Always read full CI logs first |
| Push untested fix | Committed fix without local verification | Introduced new CI failure | Always test locally before pushing |
| Fix multiple issues at once | Changed multiple things in one commit | Hard to debug which fix worked | Fix one issue at a time |
| Ignore warnings | Focused only on errors | Warnings became errors later | Fix all warnings; follow zero-warnings policy |
| Treating all CI failures as PR-related | Initially considered fixing flaky test failures | Failures were `mojo: error: execution crashed` — a pre-existing infra issue | Check `main` branch CI history to distinguish pre-existing flaky failures from PR regressions |
| Importing `_dtype_to_string` from `utils` | Added cross-module import in `core` | Creates wrong-direction dependency; `core` must not depend on `utils` | Add a local private copy prefixed with `_` instead of importing upward |

## Results & Parameters

### Common CI Failures Reference

| Failure | Command | Fix |
|---------|---------|-----|
| Trailing whitespace | `just pre-commit-all` | Stage and re-commit |
| Mojo compilation error | `pixi run mojo package -I . shared -o /tmp/shared.mojopkg` | Fix declaration/import |
| Markdown lint | `SKIP=mojo-format pixi run pre-commit run --all-files` | Fix per MD rule table |
| Test assertion error | `<package-manager> run mojo run <test-file>` | Add edge case handling |
| Segfault (exit 139) | Check for `list[i].field._data` patterns | Add local copy before pointer access |
| Plugin validation | `python3 scripts/validate_plugins.py plugins/` | Add `plugin.json` / frontmatter |

### Mojo Architecture Rule

When a function exists in `shared/utils/` but is needed in `shared/core/`, create a local private copy prefixed with `_`. The `core` module is foundational and must not depend on `utils`.

### Memory Safety Defensive Guidelines

1. Always create local copies before accessing `UnsafePointer` fields
2. Add null checks at pointer access boundaries
3. Avoid accessing pointers through collection indices (`list[i].tensor._data`)
4. Test in CI environment — local tests may not catch memory issues (Docker uses stricter protections)

### Plugin Validation Fix Checklist

- [ ] Run `python3 scripts/validate_plugins.py plugins/` and note all `FAIL:` lines
- [ ] Create missing `.claude-plugin/plugin.json` with required fields (name, version, description ≥20 chars)
- [ ] Add `---` YAML frontmatter to `SKILL.md` files that are missing it
- [ ] Add `## Failed Attempts` table where missing
- [ ] Re-run validator: `ALL VALIDATIONS PASSED`
- [ ] Rebase or enable auto-merge for blocked PRs
