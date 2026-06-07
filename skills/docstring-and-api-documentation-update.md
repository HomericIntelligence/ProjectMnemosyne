---
name: docstring-and-api-documentation-update
description: "Update, fix, and extend docstrings and API documentation in source files\
  \ to match current implementation semantics. Use when: (1) a function signature changed\
  \ and the module docstring still shows the old call, (2) memory semantics (copy vs\
  \ view) are mislabeled or inconsistent across sibling methods, (3) inline # NOTE\
  \ comments in __init__ files need promotion to docstring Note: sections, (4) a catalog\
  \ doc (backward-pass-catalog.md, testing-strategy.md) needs a new module section,\
  \ formula, or gotcha subsection, (5) placeholder 'requires implementation' language\
  \ persists after tests are written, (6) module docstrings have orphaned lowercase\
  \ continuation fragments, (7) a new dunder/trait method is undocumented, (8) a utility\
  \ function has an undocumented error-handling contract (swallows exceptions silently,\
  \ returns special error shapes on failure)."
category: documentation
date: 2026-06-05
version: "1.1.0"
user-invocable: false
history: docstring-and-api-documentation-update.history
tags:
  - docstring
  - api-docs
  - copy-vs-view
  - mojo
  - module-docstring
  - backward-pass-catalog
  - re-export
  - float16
  - placeholder
  - error-handling-contract
  - POLA
  - silent-error
---

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Skill Name** | docstring-and-api-documentation-update |
| **Category** | documentation |
| **Languages** | Mojo, Python, Markdown |
| **PR Type** | docs-only (no functional change) |
| **Risk** | Very low — docstring prose only |

## When to Use

1. A function signature changed and the module docstring example still shows the old call
   (omits a required argument, references a removed helper, etc.)
2. Memory semantics (copy vs view, `_is_view` flag) are mislabeled in docstrings or
   inconsistent across sibling methods (`slice()`, `__getitem__(Slice)`, `__getitem__(*slices)`)
3. Inline `# NOTE` or `# Note:` comments in `__init__.mojo` files need to be promoted
   to proper module docstring `Note:` sections
4. A backward-pass catalog or testing-strategy guide needs a new module section,
   mathematical formula block, or "Known Test Gotchas" subsection
5. Placeholder language ("require implementation", FIXME) persists in `__init__.mojo`
   docstrings after the corresponding tests or implementations already exist
6. A quality audit finds module docstrings with orphaned lowercase continuation fragments
   (lines starting with `and`, `or`, etc. that do not form a grammatical continuation)
7. A new trait-implementing dunder method (`__hash__`, `__eq__`, etc.) is absent from
   struct docstrings or the package `__init__` module listing
8. A utility function (especially subprocess wrappers, file I/O helpers, system utilities)
   has an undocumented error-handling contract: it silently swallows exceptions and returns
   a special value (e.g., `(False, "")` on error, `(True, stdout)` on success) instead of raising,
   violating the Principle of Least Astonishment (POLA)

## Verified Workflow

### Quick Reference

| Step | Action | Tool |
| ------ | -------- | ------ |
| 1 | Read the issue and locate target files | `gh issue view`, `Glob`, `Grep` |
| 2 | Read ALL sibling methods / related files before writing | `Read`, `Grep -C 10` |
| 3 | Classify the change type (see sub-sections below) | — |
| 4 | Apply targeted `Edit` with unique `old_string` anchors | `Edit` |
| 5 | Verify syntax (`py_compile`) or pre-commit hooks | `Bash` |
| 6 | Stage only modified files; commit with `docs(scope):` prefix | `Bash` |
| 7 | Push, open PR, enable auto-merge | `Bash`, `gh` |

### Stale Example After Signature Change

1. Locate the file with `Glob "**/module_name.mojo"` (or `.py`).
2. Read the current signature: `grep "fn function_name" path/to/file -C 5`.
3. Check every required parameter (no default value) — the example must pass all of them.
4. Find helper constructors if the example needs non-trivial inputs.
5. Edit the module docstring: show all required imports, include a minimal stub for callback
   arguments, call the target function with all required arguments.
6. Run pre-commit: `pixi run pre-commit run --files <path>`.

### Copy vs View Semantics Correction

1. Run `grep -n "fn slice\|fn __getitem__\|_is_view" <file>` to find all related methods.
2. Read ALL sibling methods together before writing any fix.
3. Classify each method:
   - **True view**: pointer offset, `_is_view = True`, zero bytes copied
   - **Copy with view flag**: `self.copy()` + `_is_view = True` (bug pattern)
   - **Independent copy**: fresh allocation, `_is_view = False`
4. Update only the docstring; do not change implementation logic.
5. Use precise language — "zero-copy view", "pointer offset", "independent copy",
   "`_is_view = False`", cross-reference siblings in `Notes:`.
6. For struct-level documentation, insert a Memory Semantics table between `Attributes:`
   and `Examples:` using ASCII table format (works in Mojo docstring parsers).
7. Scalar overloads (`__getitem__(Int)`) need an explicit N/A note.

### Promoting Inline NOTE to Docstring Note Section

1. `Grep pattern="# NOTE" glob="__init__.mojo"` — collect all hits.
2. Read each `__init__.mojo` fully to check whether a `Note:` section already exists.
3. Three cases:

   | Case | Action |
   | ------ | -------- |
   | Inline `# NOTE` + no docstring `Note:` | Add `Note:` section, remove inline comment |
   | Inline `# NOTE` + `Note:` exists | Expand existing section, remove redundant inline |
   | `Note:` exists, no inline comment | Verify completeness; expand if terse |

4. Preferred section order in `__init__.mojo`: `Modules:` → `Note:` → `Example:`.
5. Run `SKIP=mojo-format pixi run pre-commit run --files <file>` if local GLIBC is
   incompatible with the pinned Mojo binary.

### Backward-Pass Catalog / Dev-Guide Updates

1. Read the full target file before editing.
2. For a new MODULE section, insert **before** `## SUMMARY TABLE:` (not at end of file).
3. Always update ALL header stat lines atomically in one `Edit` call (total count,
   broadcasting fraction, stability fraction, module count).
4. For "Known Test Gotchas", insert between `## Gradient Checking` and `## Layer Deduplication`.
5. Include: Symptom, Root cause, Mathematical Proof sub-section, Safe Alternatives, Rule,
   Discovery context with PR/issue reference.
6. Use ` ```text ` for mathematical formulas and pseudocode (not ` ```mojo `).

### Float16 Accumulation Docs in Dev Guides

Insert a `### Float16 Convolution Limitations` subsection between `### Parameters`
and `### Example` under Gradient Checking. Key formula:

```text
Accumulation error ≈ n × ε_machine
  where n = kernel_area × input_channels, ε_machine ≈ 9.77e-4 (Float16)
```

Float16 safe accumulations (tolerance 1e-1): n < ~100. Exceeds tolerance for most
production convolutional layers (LeNet-5 Conv2: n=150; AlexNet Conv1: n=363).

### Module Docstring Line-Wrap Audit

```bash
grep -rn '^[a-z]' <package>/**/__init__.py <package>/**/runner.py
```

A line is an **orphaned fragment** if it is inside a module-level docstring, starts with
a coordinating conjunction or other lowercase word, and does not grammatically continue
the preceding line. Delete orphaned fragments; leave legitimate sentence wraps that would
exceed the line-length limit if merged.

### Placeholder Docstring Updates

1. Read the issue — identify which `__init__.mojo` files have placeholder language.
2. Verify test files exist and contain real (non-placeholder) assertions.
3. Replace "Placeholder…require implementation" with "implemented and passing".
4. Run pre-commit; note that GLIBC incompatibility may skip the `mojo-format` hook —
   all other hooks must pass.

### Dunder / Trait Method API Documentation

1. `Grep` for `__hash__` (or target method) with `-C 10` context.
2. Update method docstring: add trait name, algorithm note, expanded `Example:` block.
3. Update `shared/core/__init__.mojo` in two places:
   - Module listing entry — append `(ExTensor, implements Hashable via __hash__)`
   - Section comment above the import block — add one-liner note
4. Do **not** add dunder methods to the import list (they are trait implementations,
   not importable symbols).

### Documenting Silent Error-Handling Contracts in Utility Functions

Use this pattern when a utility function (subprocess wrapper, file I/O helper, system utility)
silently swallows exceptions instead of raising, making its error contract implicit and
violating POLA (Principle of Least Astonishment).

**Symptom**: Function docstring shows success case but never documents what happens on error.
Example: `run_command()` catches `TimeoutError`, `CalledProcessError`, and `OSError` but
returns `(False, "")` instead of raising.

**Fix**: Add an explicit `Note:` section in the docstring **before** the `Returns:` section,
documenting:
1. Both success case and failure cases as separate return shapes
2. Which exceptions are swallowed and why (e.g., "to support scripts that require partial results")
3. Cross-references to helper functions if applicable (e.g., `:func:\`get_command_path\``)

**Pattern**:

```python
def run_command(cmd: str, timeout: int = 60) -> tuple[bool, str]:
    """Run a command and return stdout if successful.

    Note:
        This function has a silent error-handling contract:
        - On success (exit code 0): returns `(True, <stdout>)` with captured output
        - On non-zero exit: returns `(False, "")` — empty string, NOT stderr
        - On timeout: returns `(False, "")` — timeout treated same as non-zero exit
        - On OSError (e.g., command not found): returns `(False, "")` — no exception raised

        All exceptions (TimeoutError, CalledProcessError, OSError) are swallowed.
        Use :func:`get_command_path` to verify command availability before calling
        if early failure is preferred over silent `(False, "")` return.

    Args:
        cmd: Shell command to execute (must exist in PATH)
        timeout: Execution timeout in seconds (default 60)

    Returns:
        Tuple `(success, output)`:
        - `(True, stdout)` when exit code == 0
        - `(False, "")` when exit code != 0, timeout, or OSError
    """
```

**Key points**:
- Place `Note:` section **immediately after** the docstring summary, **before** `Args:`
- Explicitly document BOTH the success shape `(True, <stdout>)` AND all failure shapes `(False, "")`
- Explain the semantic difference: which case gets stderr vs empty string vs timeout
- If the function is a wrapper around an external tool, cross-reference utility helpers that
  can avoid the silent error (e.g., `get_command_path()` to check existence first)
- Use `:func:\`` cross-references for related functions in the same module
- This pattern works for Python 3.10+ and Mojo docstrings

**Verification**: After editing, check that existing test coverage confirms the documented
behavior. Example: if docstring claims timeout returns `(False, "")`, ensure
`test_run_command_timeout()` exists and asserts exactly that shape.

### Commit and PR Conventions

```bash
# Commit format
git commit -m "docs(scope): <what was documented>

<One sentence: why — what implicit behaviour is now explicit.>

Closes #<issue>
"

# PR and auto-merge
gh pr create --title "docs(scope): ..." --body "Closes #<issue>"
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Guessing signatures from memory | Wrote function signature without reading source | Line numbers and parameter names were wrong (`GradientTriple` vs `Tuple[ExTensor, ExTensor, ExTensor]`) | Always read the actual source — use `Grep` for line number, then `Read` the docstring |
| Updating header denominator inconsistently | Updated total count but not the fractions | Broadcasting and stability fractions showed wrong denominators | Update ALL four header stat lines atomically in one Edit call |
| Inserting MODULE section after Summary Table | Placed new module at end of catalog file | Breaks reading flow — catalog is organized by module before summary | Always insert before `## SUMMARY TABLE:` |
| Copying old docstring example verbatim | Kept stale pattern without checking new signature | Did not demonstrate the new required argument at all | Always grep the actual function signature before writing the example |
| Omitting the callback stub in example | Showed `run_epoch_with_batches(loader, callbacks)` without `step` | Signature requires `step_fn: fn(ExTensor, ExTensor) raises -> ExTensor` | Check every parameter with no default value |
| Treating all three slice methods as identical | Assumed `__getitem__(Slice)` was also a view | The 1D `__getitem__(Slice)` always copies; `slice()` and `__getitem__(*slices)` are views | Read the implementation before writing docstrings |
| Renaming test function without updating call site | Renamed `test_slice_is_view` but forgot `main()` | Would have caused a compile error | Always grep for all call sites when renaming a function |
| Fixing implementation instead of docstring | Considered changing `__getitem__(*slices)` to use pointer offset | Multi-dim slices produce non-contiguous data; simple offset is insufficient without stride metadata | Check whether the bug is in the docs or the code first |
| Adding `Note:` after `Example:` block | Placed `Note:` section after `Example:` | Correct ordering is `Note:` before `Example:` | Place `Note:` before `Example:` in module docstrings |
| Expanding `Note:` without reading first | Started editing `shared/autograd/__init__.mojo` | File already had a `Note:` section — would have created a duplicate | Always read the full `__init__.mojo` before deciding to add or expand |
| Assuming tests needed writing | Began planning new test functions | Test files already had real implementations from a prior PR | Always read existing test files before writing new ones |
| Searching for `__hash__` without context | Grepped for `__hash__` alone | Found the method but missed the minimal existing `Example:` block | Always read `-C 10` context to see the full docstring before editing |
| Trying to add `__hash__` to import list | Considered adding `__hash__` as an explicit re-export | Dunder methods are not importable symbols — they are trait implementations | Document dunders via comments and docstrings, not import lists |
| Reading full `extensor.mojo` with `Read` | Attempted `Read` on the full file | File exceeds 25K token limit, read fails | Use `Grep -C` for targeted reads; use `offset`+`limit` for specific line ranges |
| Staging with `git add -A` | Added all untracked files | Picked up `__pycache__/` directories | Always use `git add <specific-file>` for docstring-only changes |
| Duplicate content in testing-patterns.md | Wrote the full gotcha there as well | `testing-patterns.md` already had the per-layer warning | Always read ALL docs files first to avoid duplication |
| Using ` ```mojo ` for math derivation block | Typed the Kratzert formula as mojo code | Block looked odd; `text` is correct for mathematical formulas | Use ` ```text ` for mathematical formulas and pseudocode |
| Using `just pre-commit-all` | Ran `just` command for pre-commit | `just` not in PATH on this system | Use `pixi run pre-commit run --all-files` instead |
| Trying markdownlint-cli2 via `pixi run npx` | `pixi run npx markdownlint-cli2 ...` | `npx: command not found` in this environment | Rely on pre-commit hooks rather than running markdownlint manually |
| Documenting only success return in Returns: | Wrote `Returns: (bool, str) tuple with stdout` without specifying both success and failure shapes | Callers unsure what `(False, "")` means — why empty string and not stderr? | Always document BOTH success case `(True, stdout)` AND all failure cases `(False, "")` in separate bullets within Returns: or Note: |
| Placing Note: after Returns: section | Put error-handling contract in Note: at the end of docstring | Callers read Returns: first without seeing the critical exception-swallowing contract; POLA violation persists | Place Note: section **immediately after summary**, **before Args:** — makes silent error contract discoverable before callers see return types |
| Assuming existing tests don't cover swallowed exceptions | Didn't verify test coverage for timeout / OSError paths | Could document a contract that tests don't actually exercise | Always read existing test file (e.g., `test_run_command.py`) and find TestRunCommand::test_timeout and TestRunCommand::test_failing_command to confirm contract is covered before finalizing docstring |

## Results & Parameters

### Key Docstring Patterns

**Copy-returning slice method:**

```mojo
fn __getitem__(self, slice: Slice) raises -> Self:
    """Get slice of 1D tensor [start:end] or [start:end:step].

    Returns:
        New tensor containing a **copy** of the sliced data. The result
        does not share memory with the original tensor.

    Notes:
        This method always returns a copy (`_is_view = False`), regardless
        of step value. For memory-efficient batch extraction, use `slice()`
        which returns a true view.
    """
```

**View-returning slice method:**

```mojo
fn slice(self, start: Int, end: Int, axis: Int = 0) raises -> ExTensor:
    """Extract a slice along the specified axis.

    Returns:
        A new tensor view that shares memory with the original tensor.
        Modifying the view will affect the original tensor.

    Notes:
        This method returns a **true view** (shared memory). The data pointer
        is offset into the original buffer and the reference count is
        incremented to keep the buffer alive.
    """
```

**Memory Semantics table for struct docstring (ASCII, Mojo-safe):**

```text
Memory Semantics:
    +----------------------------+----------+---------------------+------------------------------+
    | Method                     | Returns  | _is_view            | Memory                       |
    +----------------------------+----------+---------------------+------------------------------+
    | slice(start, end, axis)    | ExTensor | True  (view)        | Shared — zero-copy           |
    | __getitem__(Slice)         | ExTensor | False (copy)        | Independent — data copied    |
    | __getitem__(*slices)       | ExTensor | False (copy)        | Independent — data copied    |
    | __getitem__(Int)           | Float32  | N/A (scalar result) | Scalar value, not a tensor   |
    +----------------------------+----------+---------------------+------------------------------+
```

**Backward-pass catalog MODULE section template:**

```markdown
## MODULE N: FILENAME.MOJO

**Module Overview**: One-line description
**Total Backward Functions**: N

### 1. function_name_backward

**Location**: `path/to/file.mojo` line NNN
**Signature**:

` `` `mojo
fn function_name_backward(...) raises -> ReturnType
` `` `

**Return Type**: `ReturnType` — description

### Mathematical Formula

` `` `text
Backward pass:
    grad_x = ...
` `` `

### Numerical Stability

- Epsilon (default `1e-5`) added inside `sqrt` to prevent division by zero

---
```

**`__init__.mojo` Note: section template (re-export):**

```mojo
Note:
    Mojo v0.26.1+ automatically exports all imported symbols to package consumers.
    No ``__all__`` equivalent is needed. See issue #<NNNN>.

    Re-exports from ``<package>`` work cleanly with no chain limitation.
    Callers may import directly from the parent package:

    ```mojo
    from <package> import <Symbol1>, <Symbol2>
    ```
```

**Placeholder update pattern:**

```text
# BEFORE (stale)
Placeholder import tests in tests/shared/test_imports.mojo require implementation.

# AFTER (accurate)
Import tests in tests/shared/test_imports.mojo are implemented and passing.
```

**Utility function with silent error-handling contract** (Python/system utilities):

```python
def run_command(cmd: str, timeout: int = 60) -> tuple[bool, str]:
    """Execute a shell command and return stdout if successful.

    Note:
        This function silently swallows all exceptions — it does not raise on error.
        Instead, all error conditions return `(False, "")`:

        - Exit code != 0: `(False, "")`  — use :func:`get_command_path` to check
          command existence first if you prefer early failure
        - Timeout exceeded: `(False, "")` — no exception raised
        - Command not found (OSError): `(False, "")` — not raised, checked via return
        - Any other subprocess error: `(False, "")` — errors suppressed

    Args:
        cmd: Shell command to execute (string, must exist in PATH)
        timeout: Maximum execution time in seconds (default 60)

    Returns:
        Tuple `(success, output)`:
        - `(True, stdout_str)` when command exits with code 0
        - `(False, "")` when command exits non-zero, times out, or cannot be found
    """
```

### Validation Commands

```bash
# Python syntax check
python3 -m py_compile scripts/<script>.py

# Mojo pre-commit (skip mojo-format if GLIBC incompatible)
SKIP=mojo-format pixi run pre-commit run --files <file>

# Full pre-commit
pixi run pre-commit run --all-files

# Orphaned fragment audit
grep -rn '^[a-z]' <package>/**/__init__.py <package>/**/runner.py
```

### Float16 Accumulation Reference Table

| Layer | Formula | n | Float16 error | Exceeds tol 1e-1? |
| ------- | --------- | --- | -------------- | ------------------- |
| LeNet-5 Conv1 | 5² × 1 | 25 | ~2.4e-2 | Borderline |
| LeNet-5 Conv2 | 5² × 6 | 150 | ~1.5e-1 | Yes |
| AlexNet Conv1 | 11² × 3 | 363 | ~3.5e-1 | Yes |
| AlexNet Conv2 | 5² × 64 | 1,600 | ~1.6 | Yes |
| AlexNet Conv3 | 3² × 192 | 1,728 | ~1.7 | Yes |

Float16 machine epsilon ≈ 9.77e-4; safe accumulations (tol=1e-1): n < ~102.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Multiple issues (copy/view, catalog, fp16, re-export) | see history |
| ProjectScylla | Issue #1364, PR #1397 (module docstring line-wrap audit) | see history |
