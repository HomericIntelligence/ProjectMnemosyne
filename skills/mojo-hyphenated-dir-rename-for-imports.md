---
name: mojo-hyphenated-dir-rename-for-imports
description: 'Rename hyphenated directories to underscores so Mojo can import from
  them. Use when: (1) Mojo import fails from a hyphenated directory, (2) test files
  cannot import from examples/ with hyphens, (3) renaming directories with many
  cross-codebase references.'
category: tooling
date: 2026-03-27
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - mojo
  - imports
  - directory-rename
  - hyphenated
  - examples
---

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-27 |
| **Objective** | Rename hyphenated example directories to underscores so Mojo can import from them |
| **Outcome** | 9 directories renamed, 50+ files updated, all CI passes. Filed upstream: modular/modular#6275 |
| **Verification** | verified-ci (PR #5130 merged, Comprehensive Tests pass) |

## When to Use

- Mojo cannot import from a directory with hyphens (e.g., `from examples.resnet18-cifar10.model import ...`)
- Integration tests fail with "cannot dynamically import with hyphens"
- Renaming directories that are referenced in many places (CI, docs, scripts, source code)
- Python mypy also struggles with hyphenated directory names (related: `mypy-hyphenated-dir-per-file` skill)

## Verified Workflow

### Quick Reference

```bash
# 1. Rename directories
git mv examples/old-name examples/old_name

# 2. Fix symlinks (targets are now wrong)
rm examples/renamed_dir/symlink.py
ln -s ../new_target_dir/symlink.py examples/renamed_dir/symlink.py

# 3. Delete broken symlinks
find examples/ -type l ! -exec test -e {} \; -print -delete

# 4. Find ALL remaining references (CRITICAL — there are always more than you think)
grep -rn 'old-name' --include='*.mojo' --include='*.py' --include='*.md' \
  --include='*.yml' --include='*.yaml' --include='*.toml' --include='*.ini' \
  --include='*.sh' --include='*.ipynb' . | grep -v '.git/'

# 5. Update references (use Edit with replace_all per file)
# 6. Run pre-commit: just pre-commit-all
# 7. Push to CI for validation
```

### Detailed Steps

1. **File upstream issue first** — the import limitation is a Mojo compiler bug: `gh issue create --repo modular/modular --title "Mojo cannot import from directories containing hyphens"`

2. **Rename with `git mv`** — preserves git history tracking

3. **Fix symlinks** — `git mv` renames the symlink file but NOT the target path inside it. Must delete and recreate with updated targets.

4. **Distinguish context-sensitive renames**:
   - `alexnet-cifar10` → `alexnet_cifar10` (ALWAYS rename — unique to examples/)
   - `getting-started` → `getting_started` (ONLY when `examples/getting-started`, NOT `docs/getting-started/`)
   - `mojo-patterns` → `mojo_patterns` (ONLY when `examples/mojo-patterns`, NOT `docs/core/mojo-patterns.md`)

5. **Use sub-agents for bulk updates** — 50+ files is too many for one context. Split into "inside examples/" and "outside examples/" agents.

6. **Verify with grep** — after all edits, confirm zero remaining hyphenated references in example directory context

7. **Run pre-commit** — `nbstripout` hook may modify notebooks (expected, run twice)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Blind replace_all for `getting-started` | Would have changed `docs/getting-started/` references too | `docs/getting-started/` is a separate documentation directory NOT being renamed | Always check if a hyphenated name appears in multiple contexts before global replace |
| Running full test suite locally after rename | `just test-mojo` to validate | Crashes the machine | Push to CI for full validation, use `just test-group` for targeted checks |

## Results & Parameters

### Scale

```yaml
directories_renamed: 9
files_with_references_updated: 50+
symlinks_fixed: 2  # googlenet, mobilenet download scripts
broken_symlinks_deleted: 1  # densenet121_cifar10
upstream_issue: modular/modular#6275
```

### Directories Renamed

```text
examples/alexnet-cifar10     → examples/alexnet_cifar10
examples/custom-layers       → examples/custom_layers
examples/getting-started     → examples/getting_started
examples/googlenet-cifar10   → examples/googlenet_cifar10
examples/lenet-emnist        → examples/lenet_emnist
examples/mobilenetv1-cifar10 → examples/mobilenetv1_cifar10
examples/mojo-patterns       → examples/mojo_patterns
examples/resnet18-cifar10    → examples/resnet18_cifar10
examples/vgg16-cifar10       → examples/vgg16_cifar10
```

### NOT Renamed (Important!)

```text
docs/getting-started/           — mkdocs documentation dir, NOT an examples dir
docs/core/mojo-patterns.md      — standard markdown filename
docs/advanced/custom-layers.md  — standard markdown filename
skill/tool names with hyphens   — unrelated to directory imports
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5130, CI pass, modular/modular#6275 filed | Renamed 9 dirs, updated 50+ files |
