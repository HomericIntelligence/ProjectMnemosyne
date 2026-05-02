---
name: extend-reexport-audit-to-sibling-packages
description: 'Extend a Mojo re-export limitation audit from one package to sibling
  packages, promoting inline # NOTE comments to module docstring Note: sections. Use
  when: (1) a follow-up issue asks to audit packages not covered by a prior re-export
  audit, (2) inline # NOTE comments in __init__.mojo files need to be promoted to
  docstring Note: sections, (3) a package re-exports from a sibling package and needs
  import guidance documented.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# Skill: extend-reexport-audit-to-sibling-packages

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-15 |
| Objective | Extend re-export audit from `shared/training/` to `shared/core/` and `shared/autograd/`, promoting inline `# NOTE` comments to proper docstring `Note:` sections |
| Outcome | Success — `shared/core/__init__.mojo` got a `Note:` section (inline `# NOTE` removed); `shared/autograd/__init__.mojo` had its `Note:` section expanded; all subpackages clean |
| Category | documentation |
| Related Skills | `mojo-reexport-limitation-audit` (original audit on `shared/training/`), `mojo-note-to-docstring` (inline NOTE → docstring promotion) |

## When to Use

Use this skill when:

- A GitHub issue is a follow-up to an earlier re-export audit (e.g., "audit #3210 only covered
  `shared/training/`; now check `shared/core/` and `shared/autograd/`")
- An `__init__.mojo` file has an inline `# NOTE` comment about `__all__` or re-export mechanics
  that should be promoted to a proper module docstring `Note:` section
- A package re-exports symbols from a sibling package (e.g., `shared/autograd/` pulling in
  backward passes from `shared/core/`) and the import guidance is undocumented
- The docstring `Note:` section is present but terse and needs expansion to cover cross-package
  re-exports

## Verified Workflow

### 1. Read the issue and prior audit context

```bash
gh issue view <number> --comments
```

Also read the parent/sibling issue that did the original audit to understand what pattern
was established.

### 2. Locate all `__init__.mojo` files in the packages to audit

```
Glob pattern="shared/core/**/__init__.mojo"
Glob pattern="shared/autograd/**/__init__.mojo"
```

### 3. Grep for inline NOTE comments

```
Grep pattern="# NOTE" glob="__init__.mojo" output_mode="content"
```

Two types of hits to look for:

- `# NOTE(#NNNN, Mojo vX.Y.Z): ...` — issue-tagged comment, promote to docstring
- `# Note: ...` — lowercase variant, same treatment
- In-block comments after import groups — these are the ones to promote or remove

### 4. Read each `__init__.mojo`

Check whether each file already has a `Note:` section in its module docstring or not.

**Three cases:**

| Case | Action |
| ------ | -------- |
| Inline `# NOTE` + no docstring `Note:` | Add `Note:` section to docstring, remove inline comment |
| Inline `# NOTE` + docstring `Note:` exists | Expand existing `Note:` section, remove redundant inline |
| Docstring `Note:` exists, no inline comment | Verify content is complete; expand if terse |

### 5. Write the `Note:` section content

For a package that re-exports cleanly (no chain limitation), use this template:

```mojo
Note:
    Mojo v0.26.1+ automatically exports all imported symbols to package consumers.
    No ``__all__`` equivalent is needed — any symbol imported in this file is
    automatically available to users of ``<package>``. See issue #<NNNN>.

    Re-exports from ``<package>`` work cleanly with no chain limitation.
    Callers may import directly from the parent package:

    ```mojo
    from <package> import <Symbol1>, <Symbol2>
    ```

    The chain limitation described in #<prior-issue> only applies to importing from the
    ``<top-level>`` package (e.g. ``from <top-level> import <Symbol>``), not from
    ``<package>`` or its submodules directly.
```

For a package that re-exports from a sibling package (like `shared/autograd/` re-exporting
from `shared/core/`), additionally document:

```mojo
    This module also re-exports selected backward functions from ``<sibling.package>``
    (<description>) so callers can import them from a single location.
    These re-exports work cleanly — there is no chain limitation when
    importing from ``<this.package>`` directly.

    Import from ``<this.package>`` (works):

    ```mojo
    from <this.package> import <Symbol>
    from <this.package> import <sibling_symbol_reexported>
    ```

    Importing from the ``<top-level>`` package is subject to the chain
    limitation described in #<prior-issue> and should be avoided.
```

### 6. Check subpackages too

Don't forget subpackages under the audited packages:

```
Grep pattern="# NOTE" glob="**/__init__.mojo"
```

For ProjectOdyssey, the subpackages checked were:

- `shared/core/types/__init__.mojo` — already had a `Note:` section ✅
- `shared/core/layers/__init__.mojo` — no inline NOTE, no limitation ✅
- `shared/core/ops/__init__.mojo` — no inline NOTE, no limitation ✅

If a subpackage has no inline NOTE and no re-export limitation, no change is needed.

### 7. Run pre-commit on changed files

```bash
SKIP=mojo-format pixi run pre-commit run --files <file1> <file2>
```

Use `SKIP=mojo-format` if local GLIBC version is incompatible with the pinned Mojo version.
All other hooks (trailing-whitespace, end-of-file, check-yaml, mixed-line-ending) should pass.

### 8. Commit, push, create PR

```bash
git add shared/core/__init__.mojo shared/autograd/__init__.mojo
git commit -m "docs(shared): add Note: sections to core and autograd __init__ docstrings

Closes #<number>"
git push -u origin <branch>
gh pr create --title "docs(shared): ..." --body "Closes #<number>" --label documentation
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Adding `Note:` after `Example:` block | Placed `Note:` section after the `Example:` section in `shared/core/__init__.mojo` | The `Note:` section ended up between `Modules:` and `Example:`, which is the correct ordering — this wasn't a failure, just required verifying Mojo docstring section ordering | Place `Note:` before `Example:` in module docstrings for consistency with the `shared/training/__init__.mojo` pattern |
| Expanding `Note:` in `shared/autograd/__init__.mojo` without reading first | Almost started editing without reading the full file | `shared/autograd/__init__.mojo` already had a `Note:` section — if we'd added another one it would have been a duplicate | Always read the full `__init__.mojo` before deciding whether to add or expand |

## Results & Parameters

### Files changed in issue #3727

- `shared/core/__init__.mojo` — added `Note:` section to docstring (before `Example:`), removed
  inline `# NOTE(#3751, Mojo v0.26.1)` comment at the bottom
- `shared/autograd/__init__.mojo` — expanded existing `Note:` section to document cross-package
  re-exports; removed redundant inline `# Note:` comment at the bottom

### Docstring section ordering

For `__init__.mojo` module docstrings, the preferred section order is:

```
"""Module Title.

Module description.

Modules:  (or Core Components:)
    ...

Note:
    ...

Example:
    ...

Status: (optional)
    ...
"""
```

### Grep patterns to find inline NOTEs in init files

```
# Find issue-tagged NOTEs:
Grep pattern="# NOTE\(#" glob="__init__.mojo" output_mode="content"

# Find any NOTE comment in init files:
Grep pattern="# NOTE" glob="__init__.mojo" output_mode="content"

# Find lowercase Note: inline comments:
Grep pattern="^# Note:" glob="__init__.mojo" output_mode="content"
```

### Pre-commit with GLIBC workaround

```bash
SKIP=mojo-format pixi run pre-commit run --files shared/core/__init__.mojo shared/autograd/__init__.mojo
```

Expected output: all hooks pass (Mojo Format: Skipped, everything else: Passed).
