---
name: replace-printf-emoji-with-python-script
description: 'Replace fragile shell printf emoji byte-escape encoding in CI workflows
  with a dedicated Python script. Use when: CI workflow uses printf with \xf0\x9f
  byte escapes for emoji, or report-building shell steps need to be made locale-independent.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | `printf '\xf0\x9f\x93\x8a ...'` in shell CI steps is locale/shell-dependent and fragile |
| **Solution** | Python script with plain UTF-8 string literals; invoked as a single workflow `run:` line |
| **Language** | Python 3 |
| **Test framework** | pytest with `tmp_path` fixtures |
| **Pre-commit hooks** | ruff-format, ruff-check auto-fix on first commit; clean on second |

## When to Use

- A GitHub Actions workflow uses `printf` with `\xf0\x9f` (or similar) byte sequences to embed emoji
- CI report-building steps span multiple shell lines and are hard to read/maintain
- You need the same comment marker used in both the file content and a YAML field (emoji in YAML unicode escapes `\U0001F...` can also drift)
- The project already has a `scripts/` directory with Python automation scripts

## Verified Workflow

1. **Read the workflow file** — locate the fragile `printf` step and identify:
   - What content is being written (header, body, footer)
   - The output filename
   - Any related YAML fields referencing the same emoji string (e.g. `comment-marker`)

2. **Create `scripts/build_<report>.py`** with:
   - `HEADER` and `FOOTER` as plain Python string constants (UTF-8 literals, no escapes)
   - `build_comment(input_file: Path, output_file: Path) -> int` function
   - `main()` with `argparse` CLI (`--input-file`, `--output-file`)
   - Returns `0` on success, `1` if input file missing (with stderr message)

3. **Write pytest tests** in `tests/unit/scripts/test_build_<report>.py`:
   - Happy path: header + content + footer present in output
   - Missing input file: returns non-zero, no output file created
   - Empty input file: header and footer still present
   - No byte-escape check: assert `b"\xf0\x9f"` not in `output.read_bytes()`

4. **Update the workflow** — replace the multi-line `printf` block with:
   ```yaml
   run: python scripts/build_<report>.py --input-file <in> --output-file <out>
   ```
   Also update any `comment-marker:` YAML fields referencing the same emoji to plain ASCII.

5. **Run pre-commit** — ruff-format and ruff-check will auto-fix the new script on first attempt.
   Stage the reformatted files and commit again (second attempt passes cleanly).

6. **Run tests** — `pixi run python -m pytest tests/unit/scripts/ -v`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| First commit | Staged all files and ran `git commit` | ruff-format reformatted `build_pr_comment.py` and ruff-check fixed an import order issue; pre-commit hook modified files and aborted | Re-stage the linter-modified files and run `git commit` again — second attempt passes cleanly |
| Database lock on second commit | Immediately retried the commit after first failure | SQLite pre-commit DB was locked from the previous hook run | Wait briefly or just retry; the lock clears on its own |
| Emoji in `comment-marker` YAML field | Initially left `"\U0001F4CA Test Metrics Report"` in the workflow YAML | The marker is used to find existing bot comments; keeping it as a unicode escape is inconsistent with the plain-text file content | Update the marker to plain ASCII to match the new header string |

## Results & Parameters

### Script template

```python
#!/usr/bin/env python3
"""Build PR comment markdown from <input> content.

Usage:
    python scripts/build_<report>.py --input-file <in>.md --output-file <out>.md
"""

import argparse
import sys
from pathlib import Path

HEADER = "## Report Title\n\n"
FOOTER = "\n\n---\n*Footer note*\n"


def build_comment(input_file: Path, output_file: Path) -> int:
    """Build the output file from input content."""
    if not input_file.exists():
        print(f"Error: input file not found: {input_file}", file=sys.stderr)
        return 1
    output_file.write_text(HEADER + input_file.read_text(encoding="utf-8") + FOOTER, encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", required=True, type=Path)
    parser.add_argument("--output-file", required=True, type=Path)
    args = parser.parse_args()
    return build_comment(args.input_file, args.output_file)


if __name__ == "__main__":
    sys.exit(main())
```

### Workflow replacement

```yaml
# Before (fragile):
- name: Build report
  run: |
    {
      printf '## \xf0\x9f\x93\x8a Report Title\n\n'
      cat input.md
      printf '\n\n---\n*Footer*\n'
    } > output.md

# After (robust):
- name: Build report
  run: python scripts/build_report.py --input-file input.md --output-file output.md
```

### Test pattern

```python
def test_no_emoji_byte_escapes(tmp_path: Path) -> None:
    metrics = tmp_path / "in.md"
    metrics.write_text("data\n", encoding="utf-8")
    out = tmp_path / "out.md"
    build_comment(metrics, out)
    assert b"\xf0\x9f" not in out.read_bytes()
```
