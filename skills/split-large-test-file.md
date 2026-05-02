---
name: split-large-test-file
description: Split a monolithic test file exceeding the Edit tool's ~25K token limit
  into focused sub-modules, preserving test count and git history
category: testing
date: 2026-03-02
version: 1.0.0
user-invocable: false
---
# Split Large Test File Into Sub-modules

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-03-02 |
| **Objective** | Split `tests/unit/e2e/test_manage_experiment.py` (4212 lines, ~25K+ tokens) into four focused sub-modules |
| **Outcome** | ✅ 119 tests preserved across 4 files; all pass; git history kept; PR #1293 merged |
| **PR** | HomericIntelligence/ProjectScylla#1293 |

## Overview

The Edit tool fails on files exceeding ~25K tokens because it requires a prior `Read` call that
also hits the token limit. When a test file grows beyond this threshold, the only options are:
(1) use `bash cat-append` workarounds, or (2) split the file into focused sub-modules.

This skill documents the repeatable, safe workflow for option 2.

**Context**: `test_manage_experiment.py` grew to 4212 lines with 40 test classes covering parser,
cmd_run, cmd_repair, and cmd_visualize. Splitting by functional area — matching the source module's
command groups — produces files of ~700–2800 lines each, well within the Edit tool's limit.

## When to Use This Skill

Invoke when ANY of the following is true:

- A test file exceeds ~3000 lines (approaching the ~25K token threshold)
- The Edit tool fails with a context/token error when editing a test file
- `Read` of the test file returns truncated content
- A single test file covers 3+ distinct functional areas of the source module
- CI reports test discovery issues due to a monolithic file

## Verified Workflow

### Step 0 — Capture Baseline Test Count

```bash
pixi run python -m pytest tests/unit/e2e/test_manage_experiment.py --collect-only -q 2>&1 | tail -3
# Record "N tests collected" — ALL split files must collectively match this number
```

### Step 1 — Audit the File Structure

```bash
grep -n "^class Test" tests/unit/e2e/test_manage_experiment.py
wc -l tests/unit/e2e/test_manage_experiment.py
```

Group classes by functional area (matching the source module's command/function groups).
Use a Python script to compute exact section boundaries:

```python
from pathlib import Path

lines = Path("tests/unit/e2e/test_manage_experiment.py").read_text().splitlines(keepends=True)
for i, line in enumerate(lines):
    if line.strip().startswith("class Test"):
        print(f"L{i+1}: {line.rstrip()}")
```

### Step 2 — Check for Naming Conflicts

```bash
ls tests/unit/e2e/test_manage_experiment*.py
```

Confirm none of the planned destination filenames already exist.

### Step 3 — git mv Original to the Largest Split File

Preserve git history by renaming the original to the sub-module with the most content:

```bash
git mv tests/unit/e2e/test_manage_experiment.py \
       tests/unit/e2e/test_manage_experiment_cmd_run.py
```

This preserves the richest history on the file that contains the most test classes.
All other sub-modules are new files (no prior history to preserve).

### Step 4 — Determine Exact Section Boundaries

Use a Python script to find separator-comment boundaries (0-indexed):

```python
from pathlib import Path

lines = Path("tests/unit/e2e/test_manage_experiment_cmd_run.py").read_text().splitlines(keepends=True)

def find_section_start(class_start_idx):
    i = class_start_idx - 1
    while i >= 0 and lines[i].strip() == "":
        i -= 1
    while i >= 0 and lines[i].strip().startswith("#"):
        i -= 1
    return i + 1  # First line of the separator comment block

class_starts = {}
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("class Test"):
        cls_name = stripped.split("(")[0].replace("class ", "").rstrip(":")
        class_starts[cls_name] = i
        sec = find_section_start(i)
        print(f"  {cls_name}: class=L{i+1}, section_start=L{sec+1}")
```

### Step 5 — Create New Files Using Python Extraction

**Critical**: Do NOT manually copy-paste. Use a Python script to extract sections by line index.
This avoids transcription errors across thousands of lines.

```python
from pathlib import Path

src = Path("tests/unit/e2e/test_manage_experiment_cmd_run.py")
lines = src.read_text().splitlines(keepends=True)

# Define section boundaries as {class_name: (start_0idx, end_0idx_exclusive)}
sec = {
    "TestBuildParser": (64, 352),
    "TestCmdRepair": (755, 899),
    # ... all classes mapped
}

def get_section(cls_name):
    s, e = sec[cls_name]
    return "".join(lines[s:e])

# Build each new file: header + concatenated sections
parser_content = PARSER_HEADER + "".join(get_section(c) for c in parser_classes)
Path("tests/unit/e2e/test_manage_experiment_parser.py").write_text(parser_content)
```

### Step 6 — Rewrite the Renamed File (Strip Moved Classes)

Overwrite the `git mv`'d file with only the classes that belong to it:

```python
cmd_run_content = CMD_RUN_HEADER + "".join(
    "".join(lines[sec[c][0]:sec[c][1]]) for c in cmd_run_classes
)
Path("tests/unit/e2e/test_manage_experiment_cmd_run.py").write_text(cmd_run_content)
```

### Step 7 — Write Correct Headers for Each New File

Each new file needs its own header with appropriate imports. Audit which symbols each
section actually uses before writing imports (avoid importing unused names):

```bash
# Check what each section imports
sed -n '70,760p' tests/unit/e2e/test_manage_experiment_cmd_run.py | \
  grep -E "from manage_experiment import|cmd_repair|cmd_visualize" | sort -u
```

**Key rule**: Only import at module level what the file's classes use at module level.
Local imports inside test methods (e.g., `from manage_experiment import cmd_run`) stay local.

### Step 8 — Verify Import Resolution

Check how the project resolves script imports — often via `pyproject.toml`:

```toml
# pyproject.toml
[tool.pytest.ini_options]
pythonpath = [".", "scripts"]
```

If `pythonpath` includes `scripts/`, no `sys.path.insert` is needed in test files.
**Do NOT add `sys.path.insert` if `pyproject.toml` already handles it.**

### Step 9 — Per-File Smoke Test (Collect Only)

```bash
for f in test_manage_experiment_parser test_manage_experiment_cmd_repair \
          test_manage_experiment_cmd_visualize test_manage_experiment_cmd_run; do
  pixi run python -m pytest tests/unit/e2e/${f}.py --collect-only -q 2>&1 | tail -2
done
```

Verify collected counts sum to the baseline N.

### Step 10 — Run All Four Files Together

```bash
pixi run python -m pytest \
  tests/unit/e2e/test_manage_experiment_parser.py \
  tests/unit/e2e/test_manage_experiment_cmd_repair.py \
  tests/unit/e2e/test_manage_experiment_cmd_visualize.py \
  tests/unit/e2e/test_manage_experiment_cmd_run.py \
  -q 2>&1 | tail -5
```

All tests must pass. Count must match baseline exactly.

### Step 11 — Full Suite

```bash
pixi run python -m pytest tests/unit/ -q 2>&1 | tail -5
```

### Step 12 — Pre-commit Hooks

```bash
pre-commit run --files \
  tests/unit/e2e/test_manage_experiment_parser.py \
  tests/unit/e2e/test_manage_experiment_cmd_repair.py \
  tests/unit/e2e/test_manage_experiment_cmd_visualize.py \
  tests/unit/e2e/test_manage_experiment_cmd_run.py
```

Run twice if hooks auto-fix files (ruff format/check will reformat new files on first run).

### Step 13 — Commit and PR

```bash
git add tests/unit/e2e/test_manage_experiment_parser.py \
        tests/unit/e2e/test_manage_experiment_cmd_repair.py \
        tests/unit/e2e/test_manage_experiment_cmd_visualize.py \
        tests/unit/e2e/test_manage_experiment_cmd_run.py

git commit -m "refactor(tests): split test_manage_experiment.py into focused sub-modules"
git push -u origin <branch>
gh pr create --title "[Refactor] Split test_manage_experiment.py into sub-modules" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

**Baseline**: 119 tests collected

**Split**:
| File | Tests | Lines | Classes |
| --- | --- | --- | --- |
| `test_manage_experiment_parser.py` | 35 | ~760 | 5 |
| `test_manage_experiment_cmd_run.py` | 53 | ~2800 | 30 |
| `test_manage_experiment_cmd_repair.py` | 7 | ~160 | 2 |
| `test_manage_experiment_cmd_visualize.py` | 24 | ~680 | 3 |
| **Total** | **119** | **~4400** | **40** |

**Splitting strategy**: By command group matching source module (`build_parser`, `cmd_run`,
`cmd_repair`, `cmd_visualize`). Each file is independently runnable with no shared conftest.

**Git history**: Preserved on `test_manage_experiment_cmd_run.py` via `git mv`. The other
three files are new (no prior history to preserve — they contain content that was always
embedded in the original file).

**Full suite after split**: 3584 passed, 1 skipped; coverage 67.46% (above 9% floor and 75% unit threshold).

**Ruff auto-fixed**: 30 errors across 3 new files on first `pre-commit run` (unused imports,
formatting). Running hooks twice (or checking that they auto-fixed) is expected.

## Splitting Decision Guide

| Criteria | Split Strategy |
| --- | --- |
| Source has distinct command groups (cmd_run, cmd_repair) | One file per command |
| Source has a large parser/argument section | Separate `_parser` file |
| Helper classes (e.g., `TestFindCheckpointPath`) | Group with the command that uses the helper |
| Edge case classes (e.g., `TestCmdRepairEdgeCases`) | Same file as main class |
| Target file > 2500 lines after split | Split further or merge smaller groups |

## Related Skills

- `move-loose-test-files` — Moving test files to new locations (vs. splitting one file)
- `manage-experiment-audit` — Deep audit of manage_experiment.py test coverage
- `close-script-test-gap-cmd-run-repair` — Adding missing tests to cmd_run / cmd_repair
