---
name: werror-compilation-audit
description: "Systematic parallel compilation audit of all Mojo files with --Werror to find and fix warnings treated as errors. Use when: adding --Werror to a build system, auditing hundreds of files for hidden warnings, or triaging warnings into fixable vs complex categories."
category: ci-cd
date: 2026-03-14
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | werror-compilation-audit |
| **Category** | ci-cd |
| **Language** | Mojo (v0.26.1) |
| **Trigger** | Enabling --Werror on a codebase with 400+ files, or performing a periodic warning sweep |
| **Outcome** | All fixable warnings resolved; complex warnings filed as GitHub issues with clear categorization |

## When to Use

- Adding `--Werror` to a justfile / CI build system for the first time
- A build audit reveals files were never compiled with strict warnings
- After a Mojo version upgrade that adds new warning categories
- Periodic clean-up of accumulated warnings before a major release
- When CI catches warnings that weren't caught locally due to partial compilation

## Verified Workflow

### Quick Reference

```bash
# Compile a single file with --Werror
timeout 60 pixi run mojo --Werror -I "$(pwd)" -I . "$FILE" 2>&1

# Compile a binary (for files with main())
timeout 60 pixi run mojo build --Werror -I "$(pwd)" -I . "$FILE" -o /tmp/audit_out 2>&1

# Get just warning/error lines
timeout 60 pixi run mojo --Werror -I "$(pwd)" -I . "$FILE" 2>&1 | grep -E "error:|warning:"
```

### Phase 1: Scope Discovery

Before launching agents, determine which files need auditing:

```bash
# Find all compilable test files (have main())
find tests -name "test_*.mojo" | xargs grep -l "^fn main" | sort

# Find all example/script files with main()
find examples benchmarks scripts -name "*.mojo" | grep -v "__init__" | xargs grep -l "^fn main"

# Count total scope
find tests examples -name "*.mojo" | grep -v "\.pixi\|worktrees\|build\|__init__\|\.templates" | wc -l
```

**Files to always skip:**
- `*.templates/*.mojo` — Jinja templates with `{{}}` syntax
- `*/__init__.mojo` — compiled as part of packages, not standalone
- Library files without `main()` (grep check before compiling)
- Previously filed known-broken files (linker errors, API removals)

### Phase 2: Parallel Audit Agents

Launch 6 Haiku agents in parallel, each covering ~80 files. Each agent uses this output format:

```
FILE: path/to/file.mojo
STATUS: PASS|WARNING|ERROR|SKIP
MESSAGE: (error/warning text, first 3 lines only)
---
```

Divide files by directory to minimize overlap:
- Agent 1: `tests/shared/core` (files 1-80)
- Agent 2: `tests/shared/core` (files 81+)
- Agent 3: `tests/shared/training + testing + utils`
- Agent 4: `tests/shared/data + integration + autograd + fuzz + benchmarks`
- Agent 5: `tests/models + training + configs + core + tooling + unit`
- Agent 6: `examples + benchmarks + scripts + papers`

**Agent prompt template:**
```
For each file in [FILE_LIST]:
1. Check if file has `fn main` (grep); if not, output SKIP
2. Run: timeout 60 pixi run mojo --Werror -I "/repo/root" -I . "$f" 2>&1
3. Output FILE/STATUS/MESSAGE block
4. After all files, output SUMMARY with counts
```

### Phase 3: Triage Results

Parse all agent outputs and categorize errors:

| Category | Pattern | Action |
|----------|---------|--------|
| **PASS** | Exit 0 | No action |
| **SIMPLE_UNUSED_VAR** | `assignment to 'x' was never used` | Fix: `_ = expr` or remove |
| **SIMPLE_UNUSED_LOOP** | `for i in range(...)` with `i` unused | Fix: `for _ in range(...)` |
| **SIMPLE_DOCSTRING_PERIOD** | `description should end with '.'` | Fix: add period to docstring |
| **SIMPLE_DOCSTRING_CAPITAL** | `should begin with a capital letter` | Fix: capitalize first letter |
| **SIMPLE_ALIAS_DEPRECATED** | `'alias' is deprecated, use 'comptime'` | Fix: replace `alias` with `comptime` |
| **SIMPLE_CARET_TRANSFER** | `transfer from an owned value has no effect` | Fix: remove `^` from return |
| **SIMPLE_UNUSED_RETURN** | `'TypeName' value is unused` | Fix: `_ = expr` |
| **SIMPLE_EXCEPT_VAR** | `except e:` with `e` never used | Fix: `except:` |
| **KNOWN_LINKER_LM** | `undefined reference to 'fmaxf@@GLIBC'` | Skip; already filed |
| **KNOWN_FP8_API** | `DType.from_float32()` removed | Skip; already filed |
| **COMPLEX_TYPE_MISMATCH** | `cannot implicitly convert 'T' to 'U'` | File new issue |
| **COMPLEX_MISSING_ARG** | `missing N required positional arguments` | File new issue |
| **COMPLEX_NONCOPYABLE** | `cannot synthesize fieldwise init` | File new issue |
| **COMPLEX_IF_TRUE** | `if statement with constant condition` | File new issue |
| **RUNTIME_FAILURE** | Test output + non-zero exit (not compile error) | File new issue |
| **TIMEOUT** | Exit 124 / hangs >60s | Retry 3x; if still fails, file new issue |

### Phase 4: Apply Simple Fixes

Fix simple warnings immediately. Common patterns:

```mojo
# UNUSED VARIABLE - replace with _
# Before:
var output = result[0]
# After:
_ = result[0]

# UNUSED LOOP VARIABLE
# Before:
for i in range(100 - 1, -1, -1):
    lst.append(0)
# After:
for _ in range(100 - 1, -1, -1):
    lst.append(0)

# DOCSTRING MISSING TRAILING PERIOD
# Before:
    """Args:
        x: Input tensor
    """
# After:
    """Args:
        x: Input tensor.
    """

# DOCSTRING LOWERCASE START - use Python regex to bulk-fix
python3 -c "
import re
with open('file.mojo') as f: content = f.read()
new = re.sub(r'(?<=\"\"\")([a-z])', lambda m: m.group(1).upper(), content)
with open('file.mojo', 'w') as f: f.write(new)
"

# ALIAS DEPRECATED
# Before:
alias NUM_ITERATIONS = 100
# After:
comptime NUM_ITERATIONS = 100

# EXCEPT VARIABLE UNUSED
# Before:
except e:
    raise Error("message")
# After:
except:
    raise Error("message")

# UNUSED RETURN VALUE (method returning non-void)
# Before:
callback.on_epoch_end(state)
# After:
_ = callback.on_epoch_end(state)

# IF TRUE SCOPE - use explicit ownership drop instead
# Before:
if True:
    var view = tensor.reshape(shape)
    assert_true(view._is_view, "msg")
# After:
var view = tensor.reshape(shape)
assert_true(view._is_view, "msg")
_ = view^  # Explicitly drop to release scope
```

### Phase 5: File Issues for Complex Errors

For each complex error category, file a GitHub issue:

```bash
gh issue create \
  --title "fix: <component> <error description>" \
  --label "implementation" \
  --body "$(cat <<'EOF'
## Problem
[file.mojo:line:col: error: exact error message]

## Root Cause
[Explain why this fails]

## Fix Options
1. [Option A]
2. [Option B]

## Affected Files
- path/to/file1.mojo
- path/to/file2.mojo

## Context
Found during comprehensive --Werror compilation audit (PR #NNNN).
EOF
)"
```

### Phase 6: Commit and Push

Commit in logical batches by fix type:

```bash
git add [files with docstring fixes]
git commit -m "fix: resolve --Werror docstring formatting warnings (Round N)"

git add [files with unused var fixes]
git commit -m "fix: resolve --Werror unused variable warnings (Round N)"
```

### Phase 7: Verify

```bash
# Run the justfile test recipe (uses --Werror internally)
just test-mojo

# Or compile spot-check a sampling
for f in tests/shared/core/test_*.mojo; do
  timeout 60 pixi run mojo --Werror -I "$(pwd)" -I . "$f" 2>&1 | grep "error:" && echo "FAIL: $f" || true
done
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single sequential compilation script | Ran all 498 files in one bash loop | Took >8 hours; each file takes 30-60s to compile | Split into 6 parallel Haiku agents covering ~80 files each |
| `alias x = val` for unused variable fix | Changed `var x = val` to `alias x = val` | Mojo 0.26.1 reports `alias` is deprecated in function bodies | Use `var x = val; _ = x` or just `_ = val` directly |
| `for _ in range(...)` with `replace_all` | Tried to replace all loop vars at once | Multiple different variable names; regex too broad | Target specific line numbers from compiler error output |
| `sed` replacement of method-call patterns | Used sed to add `_ = ` prefix to callback calls | Regex didn't match all variable name patterns | Use Python with exact line numbers from error output |
| Fixing `if True:` with inline scope removal | Simply removed `if True:` block wrapper | Variables created inside still needed to go out of scope for the test to work | Use explicit `_ = var^` ownership drop pattern to manually trigger destruction |
| Using `except e:` → `_ = e` | Tried to capture the exception in `_` | Mojo syntax doesn't support `except _:` | Use bare `except:` (no binding at all) |
| `mojo build` for test files | Used build command for all files | Test files use `raises` and test assertions; `mojo` (not build) is correct | Use `mojo --Werror` for test files; `mojo build --Werror` only for examples/scripts with main() |
| 60s timeout for large AlexNet tests | Applied 60s timeout uniformly | Some AlexNet tests require 90-120s to compile legitimately | Use 90s for model e2e tests; 60s for unit/shared tests; flag genuine hangs (>120s) as issues |

## Results & Parameters

### Compilation Command

```bash
# For test files (mojo runner):
timeout 60 pixi run mojo --Werror -I "/home/mvillmow/ProjectOdyssey" -I . "$FILE" 2>&1

# For binary files (examples with main):
timeout 60 pixi run mojo build --Werror -I "/home/mvillmow/ProjectOdyssey" -I . "$FILE" -o /tmp/audit_out 2>&1
```

### Round 2 Audit Results (2026-03-14)

| Scope | Files | PASS | Fixed | Issues Filed |
|-------|-------|------|-------|-------------|
| tests/shared/core (1-80) | 80 | 76 | 4 | — |
| tests/shared/core (81+) | 133 | 124 | 5 | #4523, #4524, #4525, #4526 |
| tests/shared/training+testing+utils | 123 | 106 | 14 | #4520, #4521, #4522 |
| tests/shared/data+integration+autograd | 74 | 71 | 2 | — |
| tests/models+training+configs+core | 72 | 61 | 9 | #4519 |
| examples+benchmarks+scripts | 56 | 24 | 1 | #4514, #4515 (existing), #4519 |
| **Total** | **538** | **462** | **35** | **8 new issues** |

### Warning Categories Found

```
SIMPLE_DOCSTRING_PERIOD:    ~12 files  (trailing period missing)
SIMPLE_DOCSTRING_CAPITAL:   ~8 files   (lowercase start)
SIMPLE_UNUSED_VAR:          ~10 files  (var never read)
SIMPLE_UNUSED_RETURN:       ~8 files   (CallbackSignal discarded)
SIMPLE_EXCEPT_VAR:          ~3 files   (except e: unused)
SIMPLE_ALIAS_DEPRECATED:    ~1 file    (alias → comptime)
SIMPLE_CARET_TRANSFER:      ~2 files   (^ on return has no effect)
COMPLEX_TYPE_MISMATCH:      ~3 files   (Float32→Float64, DataLoader→PythonObject)
COMPLEX_IF_TRUE:            ~4 files   (scope pattern)
COMPLEX_MISSING_ARG:        ~2 files   (API signature changed)
COMPLEX_NONCOPYABLE:        ~2 files   (fieldwise init)
COMPLEX_LINKER_LM:          ~18 files  (known issue #4514)
COMPLEX_FP8_BF8_API:        ~2 files   (known issue #4515)
RUNTIME_FAILURE:            ~1 file    (slicing 1D only)
TIMEOUT_HANG:               ~1 file    (alexnet_layers_part4)
```

### Files to Always Skip in Audit

```
tests/models/test_vgg16_e2e.mojo       # JIT heap corruption (#4511)
.templates/**/*.mojo                    # Jinja templates with {{}} syntax
**/__init__.mojo                        # Package init files
tests/helpers/fixtures.mojo            # Library file (no main)
tests/helpers/utils.mojo               # Library file (no main)
tests/shared/conftest.mojo             # Library file (no main)
tests/shared/fixtures/**/*.mojo        # Library fixture files
.pixi/**                               # Pixi environment
worktrees/**                           # Git worktrees
build/**                               # Build outputs
```
