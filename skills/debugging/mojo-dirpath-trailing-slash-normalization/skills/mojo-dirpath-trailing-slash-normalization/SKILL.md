---
name: mojo-dirpath-trailing-slash-normalization
description: "Fix double-slash path construction in Mojo when dirpath has a trailing slash. Use when: (1) save_named_tensors/load_named_tensors produces paths like 'checkpoint//file.weights', (2) os.listdir or file open fails due to double slashes, (3) docstring examples show trailing slash but function concatenates '/' + filename unconditionally."
category: debugging
date: 2026-03-15
user-invocable: false
---

## Overview

| Property | Value |
|----------|-------|
| Issue | `dirpath + "/" + filename` produces double slashes when `dirpath` already ends with `/` |
| Symptom | Paths like `"checkpoint//weights.weights"` written or read; may silently work on Linux but is incorrect |
| Root Cause | No normalization of trailing slash before constructing file paths |
| Fix | `var normalized = String(dirpath.rstrip("/"))` at function entry; use `normalized` for all path ops |
| Key Gotcha | `String.rstrip("/")` returns `StringSlice`, not `String` — must wrap with `String(...)` |

## When to Use

- A Mojo function takes a `dirpath: String` and concatenates `dirpath + "/" + filename`
- Docstring examples show a trailing slash (`"checkpoint/"`) but the function doesn't strip it
- `os.listdir(dirpath)` or `open(filepath)` is called with a double-slash path
- Issue report mentions follow-up from a serialization PR about path normalization
- You see `"dir//file"` in error messages or test output

## Verified Workflow

### Step 1: Identify the bug site

Search for functions that concatenate `dirpath + "/"`:

```bash
grep -n 'dirpath + "/"' shared/utils/serialization.mojo
```

Both `save_named_tensors` (for file writes) and `load_named_tensors` (for `os.listdir` and file reads)
will have this pattern.

### Step 2: Verify rstrip is available

Test that `String.rstrip(chars)` works in the pinned Mojo version:

```bash
cat > /tmp/test_rstrip.mojo << 'EOF'
fn main():
    var s = String("hello/")
    print(s.rstrip("/"))   # prints: hello
    var s2 = String("hello//")
    print(s2.rstrip("/"))  # prints: hello
EOF
pixi run mojo /tmp/test_rstrip.mojo
```

Expected output: `hello` on both lines.

### Step 3: Apply the fix

At the **top** of each affected function, before any path usage:

```mojo
var normalized = String(dirpath.rstrip("/"))
```

Then replace every use of `dirpath` that constructs paths or passes to OS calls
with `normalized`. Example for `save_named_tensors`:

```mojo
fn save_named_tensors(tensors: List[NamedTensor], dirpath: String) raises:
    var normalized = String(dirpath.rstrip("/"))

    if not create_directory(normalized):
        raise Error("Failed to create directory: " + normalized)

    for i in range(len(tensors)):
        var filename = tensors[i].name + ".weights"
        var filepath = normalized + "/" + filename
        save_tensor(tensors[i].tensor, filepath, tensors[i].name)
```

And for `load_named_tensors`:

```mojo
fn load_named_tensors(dirpath: String) raises -> List[NamedTensor]:
    var result: List[NamedTensor] = []
    var normalized = String(dirpath.rstrip("/"))

    try:
        var entries = os.listdir(normalized)
        # ...
        for i in range(len(weight_files)):
            var filepath = normalized + "/" + weight_files[i]
            # ...
```

### Step 4: Update docstrings

Add a note to the `dirpath` arg documentation:

```mojo
    Args:
            dirpath: Directory containing .weights files.
                Trailing slashes are accepted and normalized automatically.
```

### Step 5: Write regression tests

Add three tests covering all slash combinations:

```mojo
fn test_save_named_tensors_trailing_slash() raises:
    """Save with trailing slash, load without."""
    # ...
    save_named_tensors(tensors, test_dir + "/")
    var loaded = load_named_tensors(test_dir)
    assert_equal(len(loaded), 1, "Should load 1 tensor")

fn test_load_named_tensors_trailing_slash() raises:
    """Save without trailing slash, load with."""
    # ...
    save_named_tensors(tensors, test_dir)
    var loaded = load_named_tensors(test_dir + "/")
    assert_equal(len(loaded), 1, "Should load 1 tensor")

fn test_save_load_trailing_slash_round_trip() raises:
    """Both save and load with trailing slash."""
    # ...
    save_named_tensors(tensors, test_dir + "/")
    var loaded = load_named_tensors(test_dir + "/")
    assert_equal(len(loaded), 1, "Should load 1 tensor")
```

Register all three in `main()`.

### Step 6: Run tests and create PR

```bash
just test-group tests/shared/utils test_serialization.mojo

git add shared/utils/serialization.mojo tests/shared/utils/test_serialization.mojo
git commit -m "fix(serialization): normalize trailing slash in dirpath for load/save_named_tensors"
git push -u origin <branch>
gh pr create --title "fix(serialization): normalize trailing slash in dirpath" --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Use `rstrip("/")` result directly | `if not create_directory(dirpath.rstrip("/"))` | Mojo's `rstrip` returns `StringSlice`, not `String`; `create_directory` expects `String` — compile error: "cannot be converted from 'StringSlice[dirpath]' to 'String'" | Always wrap `rstrip()` result with `String(...)` when passing to functions that expect `String` |
| Check `mojo -c` for quick REPL test | `pixi run mojo -c 'var s = ...'` | Mojo does not support the `-c` flag (unlike Python) | Use a temp `.mojo` file for quick one-off Mojo tests |

## Results & Parameters

### The StringSlice Gotcha

`String.rstrip(chars)` in Mojo 0.26.1 returns `StringSlice[...]` not `String`.
Any function that takes `String` will fail to compile without an explicit conversion:

```mojo
# WRONG - compile error
var normalized = dirpath.rstrip("/")
create_directory(normalized)  # error: cannot convert StringSlice to String

# CORRECT
var normalized = String(dirpath.rstrip("/"))
create_directory(normalized)  # works
```

### Quick Validation Script

```bash
cat > /tmp/test_rstrip.mojo << 'EOF'
fn main():
    var s = String("hello/")
    print(s.rstrip("/"))
    var s2 = String("hello//")
    print(s2.rstrip("/"))
    var s3 = String("/hello/")
    print(s3.rstrip("/"))
EOF
pixi run mojo /tmp/test_rstrip.mojo
# Expected:
# hello
# hello
# /hello
```

### Test Pattern for All Slash Combinations

Always cover all three cases to prevent regressions:

| Test | Save | Load | Verifies |
|------|------|------|---------|
| `test_save_..._trailing_slash` | `dir + "/"` | `dir` | save normalization |
| `test_load_..._trailing_slash` | `dir` | `dir + "/"` | load normalization |
| `test_save_load_..._round_trip` | `dir + "/"` | `dir + "/"` | both paths normalized |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3791, PR #4800 | [notes.md](../references/notes.md) |
