---
name: mojo-binary-file-read-bytes-not-string
description: "Use f.read_bytes() instead of f.read() when reading binary files in Mojo 0.26.3. Use when: (1) reading binary file formats like IDX/MNIST that contain non-UTF-8 bytes, (2) getting 'Cannot construct a String from invalid UTF-8 data' crash on file read, (3) trying to use 'rb' open mode which doesn't exist in Mojo 0.26.3."
category: debugging
date: 2026-05-03
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: ["mojo", "binary", "file-io", "idx", "mnist", "utf8", "read_bytes"]
---

# Mojo Binary File Read: Use read_bytes() Not read()

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-03 |
| **Objective** | Read binary files (IDX/MNIST format) in Mojo 0.26.3 without UTF-8 crash |
| **Outcome** | Successful — training pipeline ran end-to-end after fix |
| **Verification** | verified-local (CI validation pending on PR #5351) |

## When to Use

- Reading any binary file format in Mojo 0.26.3 (IDX, raw pixel data, serialized weights, etc.)
- Encountering `"Cannot construct a String from invalid UTF-8 data"` crash on `f.read()`
- Attempting `open(filepath, "rb")` which raises `"Invalid open mode"` at runtime
- Processing MNIST/EMNIST datasets that use IDX format with magic number bytes 0x00-0xFF
- Any file read where bytes in range 0x80-0xFF or null bytes (0x00) are expected

## Verified Workflow

### Quick Reference

```mojo
# CORRECT: Use read_bytes() for binary files
var content: List[UInt8]
with open(filepath, "r") as f:
    content = f.read_bytes()
var file_size = len(content)
var data_bytes = content.unsafe_ptr()  # UnsafePointer[UInt8] — works as before
```

### Detailed Steps

1. Open the file with `open(filepath, "r")` — the `"rb"` mode does NOT exist in Mojo 0.26.3
2. Call `f.read_bytes()` instead of `f.read()` — returns `List[UInt8]`, skips UTF-8 validation
3. Replace `var content: String` declarations with `var content: List[UInt8]`
4. Use `len(content)` for byte count — same API as String
5. Use `content.unsafe_ptr()` for raw pointer access — yields `UnsafePointer[UInt8]`, same type
   as `String.unsafe_ptr()`, so downstream pointer-based code works without changes

**Key insight**: `read_bytes()` ignores text encoding entirely even though the file is opened
with `"r"` mode. The mode string only affects write behavior; `read_bytes()` always reads raw.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `open(filepath, "rb")` | Used binary open mode as in Python | Mojo 0.26.3 raises `"Invalid open mode"` at runtime — only `"r"`, `"w"`, `"rw"`, `"a"` are valid | No `"rb"` mode exists; mode string is not a Python-compatible flag |
| `open(filepath, "r") + f.read()` | Default text read | Crashes with `"Cannot construct a String from invalid UTF-8 data"` on first non-UTF-8 byte (e.g., 0x00 magic number in IDX header) | `f.read()` returns a `String` which strictly validates UTF-8; unusable for binary data |

## Results & Parameters

**Fix applied to** `shared/data/formats/idx_loader.mojo` in ProjectOdyssey — three functions:

- `load_idx_labels`
- `load_idx_images`
- `load_idx_images_rgb`

**Before (broken):**

```mojo
var content: String
with open(filepath, "r") as f:
    content = f.read()
var file_size = len(content)
var data_bytes = content.unsafe_ptr()
```

**After (fixed):**

```mojo
var content: List[UInt8]
with open(filepath, "r") as f:
    content = f.read_bytes()
var file_size = len(content)
var data_bytes = content.unsafe_ptr()
```

**Verification result**: Training pipeline ran end-to-end — 1 epoch, 113,600 training samples,
18,800 test samples from EMNIST dataset.

**Type compatibility**: Both `String.unsafe_ptr()` and `List[UInt8].unsafe_ptr()` return
`UnsafePointer[UInt8]`, so all downstream pointer arithmetic and memory reads work unchanged.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | IDX format loader for MNIST/EMNIST datasets | PR #5351, `shared/data/formats/idx_loader.mojo` |
