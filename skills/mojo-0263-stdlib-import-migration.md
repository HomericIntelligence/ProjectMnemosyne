---
name: mojo-0263-stdlib-import-migration
description: "Mojo 0.26.3 migration: stdlib modules require std. prefix and escaping keyword was removed. Use when: (1) upgrading from Mojo 0.26.1/0.26.2 to 0.26.3, (2) seeing 'module not found' errors for testing/sys/memory imports, (3) seeing 'unknown keyword escaping' errors."
category: ci-cd
date: 2026-04-09
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [mojo, 0.26.3, stdlib, migration, imports, escaping, bulk-fix]
---

# Mojo 0.26.3: stdlib Import Qualification and escaping Keyword Removal

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-09 |
| **Objective** | Fix compile errors when upgrading Mojo to 0.26.3 |
| **Outcome** | Successful — 92 test files fixed, zero --Werror errors |
| **Verification** | verified-local — CI pending |

## When to Use

- Upgrading a codebase from Mojo 0.26.1 or 0.26.2 to 0.26.3
- Seeing compile errors: `module 'testing' not found` or similar for stdlib modules
- Seeing: `unknown keyword 'escaping'` in function type signatures
- Bulk-migrating a large test suite (50+ files)

## Verified Workflow

### Quick Reference

```bash
# Fix unqualified stdlib imports
find . -name "*.mojo" -exec python3 -c "
import re, sys
content = open(sys.argv[1]).read()
fixed = re.sub(
    r'^(from\s+)(testing|sys|memory|collections|algorithm|math|random|time|utils|os|bit)(\s+import\b)',
    r'\1std.\2\3', content, flags=re.MULTILINE)
if fixed != content:
    open(sys.argv[1], 'w').write(fixed)
    print('Fixed:', sys.argv[1])
" {} \;

# Fix raises escaping -> raises
find . -name "*.mojo" | xargs grep -l "raises escaping" | while read f; do
  sed -i 's/raises escaping/raises/g' "$f"
done

# Verify zero errors
pixi run mojo package --Werror -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ': error:'
```

### Detailed Steps

1. **Find all affected files**: `grep -rl "^from testing import\|^from sys import\|raises escaping" tests/ shared/`
2. **Apply stdlib prefix fix** using the Python script above (handles multiline-safe regex)
3. **Apply escaping removal** using sed
4. **Special case — name collisions**: If a local module is named the same as a stdlib module
   (e.g., `std` imported from `shared.core.reduction`), alias it:
   `from shared.core.reduction import std as std_op`
5. **Verify**: `pixi run mojo package --Werror -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ': error:'`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Manual file edits | Editing each file one by one | 92+ files to change — impractical | Use bulk Python/sed script |
| `sed -i 's/from testing/from std.testing/'` | Simple sed substitution | Matches partial strings in comments or middle of identifiers | Use regex with word boundaries: `^from\s+testing\s+import` |
| Keeping `escaping` | Leaving `raises escaping` as-is | Mojo 0.26.3 removed the keyword entirely — compile error | Must remove `escaping` unconditionally |

## Results & Parameters

**Affected stdlib modules requiring `std.` prefix in 0.26.3**:

```text
testing     → std.testing
sys         → std.sys
memory      → std.memory
collections → std.collections
algorithm   → std.algorithm
math        → std.math
random      → std.random
time        → std.time
utils       → std.utils
os          → std.os
bit         → std.bit
```

**Name collision example** (`std` as local name):

```mojo
# BEFORE (broken — 'std' is now the stdlib namespace):
from shared.core.reduction import std, mean

# AFTER:
from shared.core.reduction import std as std_op, mean
# then replace std( with std_op( in the file
```

**Scale**: In ProjectOdyssey, this affected 92 test files for import qualification
and 17 files for `raises escaping`.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Mojo 0.26.3 migration, branch fix-ci-root-causes | 92 files import-fixed, 17 files escaping-fixed; package --Werror clean |
