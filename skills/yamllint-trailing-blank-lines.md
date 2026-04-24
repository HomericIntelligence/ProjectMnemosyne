---
name: yamllint-trailing-blank-lines
description: "Use when: (1) yamllint CI fails with 'too many blank lines (1 > 0)' at end of file, (2) conflict resolution leaves trailing blank lines in YAML files, (3) ensuring YAML files have exactly one newline at EOF."
category: ci-cd
date: 2026-04-23
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [yaml, yamllint, lint, trailing-blank-lines, eof, ci, github-actions]
---

# yamllint Trailing Blank Lines at EOF

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-23 |
| **Objective** | Fix yamllint CI failure caused by trailing blank lines at end of YAML files |
| **Outcome** | Stripping trailing blank lines fixed the yamllint error; CI passed |
| **Verification** | verified-ci |

## When to Use

- yamllint CI fails with: `too many blank lines (N > 0)` pointing to a line near EOF
- YAML files were edited during conflict resolution and have extra blank lines at the end
- `.yamllint.yml` extends default configuration (which sets `max-end: 0`)
- Batch editing YAML files and ensuring EOF compliance

## Verified Workflow

### Quick Reference

```bash
# Find YAML files with trailing blank lines
find . -name "*.yml" -o -name "*.yaml" | xargs grep -lP '\n\n$'

# Fix a single file: strip trailing blank lines, keep exactly one trailing newline
python3 -c "
import sys
with open(sys.argv[1]) as f:
    content = f.read()
fixed = content.rstrip() + '\n'
with open(sys.argv[1], 'w') as f:
    f.write(fixed)
" path/to/file.yml

# Fix all YAML files in .github/workflows/
for f in .github/workflows/*.yml; do
  python3 -c "
import sys
with open(sys.argv[1]) as f: content = f.read()
with open(sys.argv[1], 'w') as f: f.write(content.rstrip() + '\n')
" "$f"
done

# Verify with yamllint
yamllint .github/workflows/ci.yml
```

### Detailed Steps

1. Identify the failing file from the yamllint error:
   ```
   .github/workflows/ci.yml:488:1 [empty-lines] too many blank lines (1 > 0)
   ```
   Line 488 at column 1 means EOF has a trailing blank line.

2. Fix with Python one-liner (handles all edge cases including Windows CRLF):
   ```python
   content.rstrip() + '\n'
   ```

3. Run yamllint to confirm:
   ```bash
   yamllint -c .yamllint.yml .github/workflows/ci.yml
   ```

4. If many files are affected (e.g., after merge conflict resolution):
   ```bash
   # Fix all YAML files recursively
   find . -name "*.yml" -not -path "./.git/*" | while read f; do
     python3 -c "
   import sys
   with open(sys.argv[1]) as f: c = f.read()
   with open(sys.argv[1], 'w') as f: f.write(c.rstrip() + '\n')
   " "$f"
   done
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Removing conflict markers without checking trailing whitespace | Resolved git merge conflict in ci.yml, removed markers | Left a trailing blank line that conflict resolution introduced | Always run yamllint after conflict resolution on YAML files; check for trailing blank lines specifically |
| `sed -i '${/^$/d}' file.yml` | Tried to delete last blank line with sed | Fragile — only deletes one blank line; fails if there are multiple; also fails on macOS sed | Use Python `content.rstrip() + '\n'` — handles any number of trailing blank lines portably |

## Results & Parameters

### yamllint Configuration — Default empty-lines Rule

```yaml
# .yamllint.yml (extends default)
extends: default
rules:
  line-length:
    max: 120
```

The `extends: default` setting includes `empty-lines: {max: 2, max-start: 0, max-end: 0}`.
`max-end: 0` means zero blank lines at EOF are allowed — exactly one trailing newline is required.

### Error Message Pattern

```
path/to/file.yml:488:1 [empty-lines] too many blank lines (1 > 0)
```

Where `488:1` is the line number of the EOF — one line past the last content line.

### When This Happens Most

- Git merge conflict resolution adds a trailing blank line after the final `>>>>>>> HEAD` marker is removed
- CI that extends yamllint defaults (common in HomericIntelligence repos)
- Any automated editor that adds a trailing newline on top of an existing one

### One-liner for Any File

```python
# Idempotent — safe to run on any text file
python3 -c "
import sys
p = sys.argv[1]
with open(p) as f: c = f.read()
with open(p, 'w') as f: f.write(c.rstrip() + '\n')
" path/to/file.yml
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| AchaeanFleet | CI repair — conflict resolution left trailing blank line in .github/workflows/ci.yml | 2026-04-23; yamllint passed after fix |
