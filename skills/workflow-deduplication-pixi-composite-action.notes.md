# Session Notes: CI Workflow Deduplication (Issue #3149)

## Context

- Repository: HomericIntelligence/ProjectOdyssey
- Issue: #3149 - Consolidate CI workflows (26 -> ~15)
- Branch: 3149-auto-impl
- PR: #3663

## What Was Done

### Starting state

- 24 workflows (23 yml + README.md)
- 9 workflows had inline `prefix-dev/setup-pixi@v0.9.4` setup blocks
- Composite actions `setup-pixi` and `pr-comment` already existed but underused
- `dependency-audit.yml` was a standalone weekly audit workflow

### Changes Made

1. Replaced inline Pixi setup in 9 workflows with `./.github/actions/setup-pixi`
2. Merged `dependency-audit.yml` jobs into `security.yml` with event guards
3. Deleted `dependency-audit.yml`
4. Added `schedule`, push path filters, and `issues: write` to `security.yml`

### Final state

- 22 workflows (21 yml + README.md)
- Zero inline `prefix-dev/setup-pixi` references
- Pre-commit: all hooks passed

## Key Discoveries

- The Edit tool fails with "File has not been read yet" even if the file was read
  in a prior tool-use response. Must read AND edit in the same response.
- Using `rm` with semicolons/newlines in a single Bash call caused shell to
  interpret echo text as filenames, deleting workflow files accidentally.
- `git restore .github/workflows/` after accidental deletion wiped all uncommitted
  edits (restored from HEAD). Had to redo all changes with a Python bulk-replace script.
- Python bulk replacement (`content.replace(old, new)`) is more reliable than
  multiple Edit tool calls for this pattern.

## Bulk Replacement Script Used

```python
OLD = "      - name: Set up Pixi\n        uses: prefix-dev/setup-pixi@v0.9.4\n        with:\n          pixi-version: latest\n          cache: true"
NEW = "      - name: Set up Pixi\n        uses: ./.github/actions/setup-pixi"

files = [
    ".github/workflows/mojo-version-check.yml",
    ".github/workflows/pre-commit.yml",
    ".github/workflows/test-data-utilities.yml",
    ".github/workflows/test-gradients.yml",
    ".github/workflows/script-validation.yml",
    ".github/workflows/type-check.yml",
    ".github/workflows/paper-validation.yml",
    ".github/workflows/release.yml",
    ".github/workflows/dependency-audit.yml",
]

for f in files:
    content = open(f).read()
    count = content.count(OLD)
    if count > 0:
        content = content.replace(OLD, NEW)
        open(f, 'w').write(content)
        print(f"Updated {count}x: {f}")
```
