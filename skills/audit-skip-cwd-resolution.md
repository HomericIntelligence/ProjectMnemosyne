---
name: audit-skip-cwd-resolution
description: 'Documents the pattern for resolving --audit-skip file paths relative
  to CWD in migration audit scripts. Use when: (1) audit skip-list path semantics
  are unclear, (2) adding CWD-relative path resolution tests, (3) updating argparse
  help text.'
category: tooling
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Issue** | #3937 — migrate_odyssey_skills --audit mode uses hardcoded MNEMOSYNE_SKILLS_DIR |
| **Root cause** | `--audit-skip` path was resolved relative to CWD but this was undocumented, causing confusion |
| **Fix** | Updated argparse help text + added e2e test verifying CWD-relative resolution |
| **Files changed** | `scripts/migrate_odyssey_skills.py`, `tests/scripts/test_audit_migration_coverage.py` |

## When to Use

- An audit script accepts a `--audit-skip FILE` argument but the path resolution semantics are undocumented
- You need to add an end-to-end test proving that a relative skip-file path works when `cwd ≠ script directory`
- You want a minimal pattern for argparse help-text clarification without changing behavior

## Verified Workflow

### Quick Reference

```bash
# 1. Update help text in argparse definition
parser.add_argument(
    "--audit-skip",
    metavar="FILE",
    default=".audit-skip",
    help=(
        "File listing skill names to exclude from audit "
        "(one per line, default: .audit-skip). "
        "Path is resolved relative to the current working directory (CWD)."
    ),
)

# 2. Add e2e test using subprocess.run with explicit cwd=
def test_audit_skip_resolved_relative_to_cwd(self, tmp_path):
    cwd_dir = tmp_path / "run_dir"
    cwd_dir.mkdir()
    (cwd_dir / ".audit-skip").write_text("skill-w\n")

    proc = subprocess.run(
        [..., "--audit-skip", ".audit-skip"],
        capture_output=True, text=True,
        cwd=str(cwd_dir),   # CWD contains the skip file
    )
    assert proc.returncode == 0
```

### Step-by-step

1. **Locate the `--audit-skip` argparse definition** in the script.
2. **Update the `help=` string** to explicitly state "Path is resolved relative to the current working directory (CWD)." — no functional change, documentation only.
3. **Add a new test method** to the `TestMainAuditExitCodes` class (or equivalent):
   - Create a source dir with one skill whose SKILL.md contains `name: <skill>`.
   - Create an empty target dir (skill absent → MISSING without skip).
   - Create `run_dir/` with `.audit-skip` containing the skill name.
   - Run the script via `subprocess.run` with `cwd=str(run_dir)` and `--audit-skip .audit-skip` (relative).
   - Assert `returncode == 0` — the relative path was found from CWD, skill was skipped.
4. **Run the full test suite** (`pixi run python -m pytest tests/scripts/test_audit_migration_coverage.py -v`) and confirm all tests pass.
5. **Commit both files** together under a `fix(audit):` conventional commit.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Changing path resolution logic | Considered making `--audit-skip` resolve relative to script dir instead of CWD | Would break existing callers who already pass absolute paths or rely on CWD behavior | Don't change behavior — document it instead |
| Writing only a unit test | Considered mocking `load_skip_list` to unit-test the flag | Would not catch the real CWD-relative resolution end-to-end | Use subprocess + explicit `cwd=` to exercise the actual script behavior |

## Results & Parameters

**Commit message format:**

```text
fix(audit): clarify --audit-skip resolves relative to CWD and add e2e test

- Update --audit-skip help text to document CWD-relative resolution
- Add test_audit_skip_resolved_relative_to_cwd to TestMainAuditExitCodes

Closes #<issue>
```

**Test outcome:** 43 tests passed (0 failures, 0 errors).

**Key subprocess pattern for CWD-relative path tests:**

```python
proc = subprocess.run(
    [sys.executable, SCRIPT, "--audit", "--no-color",
     "--source-dir", str(source),
     "--target-dir", str(target),
     "--audit-skip", ".audit-skip"],   # relative — resolved from cwd
    capture_output=True, text=True,
    cwd=str(cwd_dir),                  # directory that contains .audit-skip
)
assert proc.returncode == 0, f"{proc.stdout}\n{proc.stderr}"
```
