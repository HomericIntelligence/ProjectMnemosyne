---
name: mojo-runtime-output-pattern-audit
description: "Audit Mojo source files for misleading runtime print() patterns and wire CI enforcement. Use when: extending an existing audit series to cover WARNING:, HACK:, XXX:, or Not implemented in print() calls; adding a grep-style checker script modeled on an existing one; or enforcing runtime output cleanliness in a Mojo project."
category: tooling
date: 2026-03-15
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Category** | tooling |
| **Complexity** | Low |
| **Risk** | Low (audit + one-line source fix + new enforcement script) |
| **Repo** | Any Mojo project with a `scripts/` audit pattern (e.g. ProjectOdyssey) |

Extends an in-progress comment/annotation audit series (like the #3084/#3194 NOTE/TODO/FIXME series)
to also cover misleading runtime output: `print()` calls containing `WARNING:`, `HACK:`, `XXX:`,
or placeholder messages like `Not implemented`. The pattern is: grep to find violations → fix them
→ add enforcement script modeled on the existing checker → add CI step → add tests.

## When to Use

- An audit issue requests follow-up coverage for `print('WARNING: ...')`, `print('HACK: ...')`,
  `print('XXX: ...')`, or `print('Not implemented')` patterns
- A project already has a `check_note_format.py`-style script and needs a companion for runtime output
- You need a CI step in `script-validation.yml` (or equivalent) to block new violations
- The existing checker script can serve as a structural template (same `argparse`, `SOURCE_DIRS`,
  `is_excluded`, `find_violations`, `scan_source_dirs`, `main()` exit-code interface)

## Verified Workflow

### Step 1 — Grep the full source tree for violations

```bash
# Find all banned patterns in .mojo files
grep -rn 'print.*WARNING\s*:' examples/ shared/ papers/ tests/ --include="*.mojo"
grep -rn 'print.*HACK\s*:'    examples/ shared/ papers/ tests/ --include="*.mojo"
grep -rn 'print.*XXX\s*:'     examples/ shared/ papers/ tests/ --include="*.mojo"
grep -rn -i 'print.*Not implemented' examples/ shared/ papers/ tests/ --include="*.mojo"
```

Record every hit (file + line number) before touching anything.

### Step 2 — Fix existing violations

For each violation, evaluate whether the message is legitimate:

- **Legitimate message with misleading prefix** (most common): remove only the prefix.

  ```mojo
  # Before
  print("WARNING: Gradient overflow detected, skipping parameter update")
  # After
  print("Gradient overflow detected, skipping parameter update")
  ```

- **Placeholder/stub**: replace with an appropriate message or raise an error.

### Step 3 — Create `scripts/check_runtime_output_patterns.py`

Model the script on the existing `check_note_format.py`. Required interface:

```python
BANNED_PATTERNS = [
    re.compile(r'print\([^)]*WARNING\s*:', re.IGNORECASE),
    re.compile(r'print\([^)]*HACK\s*:', re.IGNORECASE),
    re.compile(r'print\([^)]*XXX\s*:', re.IGNORECASE),
    re.compile(r'print\([^)]*Not\s+implemented', re.IGNORECASE),
]

def is_comment_line(line: str) -> bool: ...
def is_excluded(path: Path) -> bool: ...          # same EXCLUDED_DIRS as existing checker
def find_violations(search_path: Path) -> List[Tuple[Path, int, str]]: ...
def scan_source_dirs(repo_root: Path) -> List[Tuple[Path, int, str]]: ...
def main() -> int: ...  # exit 0 = clean, exit 1 = violations
```

Key detail: skip comment lines (`line.lstrip().startswith("#")`) before pattern matching,
and report each line only once (break after first matching pattern).

### Step 4 — Write tests

Create `tests/scripts/test_check_runtime_output_patterns.py` with classes:

| Test class | Coverage |
|------------|----------|
| `TestBannedPatterns` | Each banned pattern; case-insensitivity; clean print not flagged; comment line not flagged |
| `TestIsCommentLine` | Hash prefix detection; code lines; empty/blank lines |
| `TestIsExcluded` | Each excluded dir; valid source dirs |
| `TestFindViolations` | Each pattern type; comment exclusion; multi-violation; subdirs; excluded dirs; non-.mojo files; dedup |
| `TestScanSourceDirs` | Multi-dir aggregation; missing dirs |
| `TestMainExitCodes` | Exit 0 / 1 for each pattern; comment not flagged; stdout/stderr content; nonexistent dir |

Run with: `pixi run python -m pytest tests/scripts/test_check_runtime_output_patterns.py -v`

### Step 5 — Wire CI enforcement

In `.github/workflows/script-validation.yml`:

1. Add `examples/**/*.mojo` (and other source dirs) to `paths:` triggers under both `pull_request`
   and `push`.
2. Add a new step after the existing "Check for common issues" step:

```yaml
- name: Check for misleading runtime output patterns
  run: |
    python scripts/check_runtime_output_patterns.py examples/ || {
      echo "❌ Misleading runtime output patterns found"
      echo "Remove WARNING:, HACK:, XXX:, or 'Not implemented' prefixes from print() calls."
      exit 1
    }
    echo "✅ No misleading runtime output patterns found"
```

3. Add the new step to the Summary step's checklist.

### Step 6 — Update `scripts/README.md`

Add the new script entry in alphabetical order in the directory tree section:

```text
├── check_runtime_output_patterns.py    # Audit for misleading print() patterns (WARNING:, HACK:, XXX:, Not implemented)
```

### Step 7 — Verify and commit

```bash
# Verify script is clean on source dirs
python scripts/check_runtime_output_patterns.py examples/

# Run all tests
pixi run python -m pytest tests/scripts/test_check_runtime_output_patterns.py -v

# Commit
git add .github/workflows/script-validation.yml \
        examples/path/to/fixed.mojo \
        scripts/check_runtime_output_patterns.py \
        scripts/README.md \
        tests/scripts/test_check_runtime_output_patterns.py

git commit -m "feat(scripts): add runtime output pattern audit for examples/

Completes the #NNNN/#MMMM audit series by covering additional misleading
print() patterns: WARNING:, HACK:, XXX:, and 'Not implemented'.

Closes #NNNN

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Matching `WARNING:` anywhere on the line (not just in print calls) | Initial regex `r'WARNING\s*:'` without requiring `print\(` prefix | Would flag comment lines like `# WARNING: this is fine` as violations | Scope pattern to `print\([^)]*WARNING\s*:` and add an explicit `is_comment_line` check |
| Using a multiline regex to catch print() calls spanning lines | `re.compile(r'print\(.*WARNING.*\)', re.MULTILINE)` | Mojo print calls with banned prefixes are always single-line in practice; adds complexity for no gain | Keep patterns single-line — real-world violations are never multi-line print calls |
| Reporting the same line multiple times when it matches multiple patterns | No dedup inside `find_violations` | A line like `print("WARNING: HACK: ...")` would appear twice | `break` after the first matching pattern; one violation entry per line |

## Results & Parameters

**Issue**: ProjectOdyssey #3704 (follow-up to #3084/#3194 audit series)

**Violations found and fixed** (1 file):

```text
examples/lenet-emnist/run_train.mojo:302
  Before: print("WARNING: Gradient overflow detected, skipping parameter update")
  After:  print("Gradient overflow detected, skipping parameter update")
```

**Test count**: 44 unit tests, all passing in 0.39s.

**Script exit-code contract**:

- Exit 0 → no violations in scanned directory
- Exit 1 → one or more violations (details to stdout, count to stderr)

**Regex patterns (copy-paste ready)**:

```python
BANNED_PATTERNS = [
    re.compile(r'print\([^)]*WARNING\s*:', re.IGNORECASE),
    re.compile(r'print\([^)]*HACK\s*:', re.IGNORECASE),
    re.compile(r'print\([^)]*XXX\s*:', re.IGNORECASE),
    re.compile(r'print\([^)]*Not\s+implemented', re.IGNORECASE),
]
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4776, issue #3704 | [notes.md](../../references/notes.md) |
