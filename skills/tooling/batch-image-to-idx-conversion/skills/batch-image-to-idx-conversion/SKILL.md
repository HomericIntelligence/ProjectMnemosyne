---
name: batch-image-to-idx-conversion
description: "Extend a single-image IDX converter to batch mode with --batch flag accepting a directory or glob. Use when: (1) users need to pass a whole directory of images to a Mojo inference pipeline in one shot, (2) extending png-jpeg-to-idx-conversion to multi-image IDX format, (3) the IDX reader expects count>1."
category: tooling
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | batch-image-to-idx-conversion |
| **Category** | tooling |
| **Language** | Python 3.7+ |
| **Dependencies** | Pillow (PIL), stdlib glob |
| **Output** | Extended `scripts/convert_image_to_idx.py` + `tests/scripts/test_convert_image_to_idx_batch.py` |
| **Prerequisite** | `png-jpeg-to-idx-conversion` skill (single-image baseline) |
| **PR** | HomericIntelligence/ProjectOdyssey#4775 |

## When to Use

- Users must run a single-image converter N times and want a batch shortcut
- The downstream Mojo inference pipeline reads multi-image IDX format (count=N header field)
- Adding `--batch` to an existing script that currently only handles `count=1`
- Accepting either a directory of images **or** a shell glob pattern as input

## Verified Workflow

### Quick Reference

| Step | What to do |
|------|-----------|
| 1 | Add `resolve_batch_inputs(input_arg: str) -> list` |
| 2 | Add `write_idx_images_batch(images: list, output_path: Path) -> None` |
| 3 | Add `--batch` flag to argparse; route to batch path in `main()` |
| 4 | Write 21 tests in `tests/scripts/test_convert_image_to_idx_batch.py` |
| 5 | Run `pixi run python -m pytest tests/scripts/test_convert_image_to_idx_batch.py -v` |

### 1. Add resolve_batch_inputs()

Handles two input forms: a directory path (list all image files) or a glob string (expand with `glob.glob`).
Both return a sorted list of `Path` objects for reproducibility.

```python
import glob as _glob
from pathlib import Path
import sys

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def resolve_batch_inputs(input_arg: str) -> list:
    """Resolve a directory path or glob pattern to a sorted list of image paths.

    Args:
        input_arg: Directory path or glob pattern string.

    Returns:
        Sorted list of Path objects for matched image files.

    Raises:
        SystemExit: If no matching image files are found.
    """
    input_path = Path(input_arg)

    if input_path.is_dir():
        matches = sorted(
            p for p in input_path.iterdir() if p.suffix.lower() in _IMAGE_EXTENSIONS
        )
    else:
        raw = sorted(_glob.glob(input_arg))
        matches = [Path(p) for p in raw if Path(p).suffix.lower() in _IMAGE_EXTENSIONS]

    if not matches:
        print(f"Error: No image files found for input: {input_arg}")
        sys.exit(1)

    return matches
```

**Key design decisions:**

- Distinguish directory vs glob by checking `Path.is_dir()` — avoids special-casing `*`/`?` in the string
- Filter by extension after globbing — avoids treating `.txt` or `.idx` files as images
- `sys.exit(1)` on empty result (not `return []`) — matches the error contract of the single-image path

### 2. Add write_idx_images_batch()

IDX format for N images: `[4B magic=2051][4B count=N][4B rows=28][4B cols=28][N×784B pixels]`

```python
def write_idx_images_batch(images: list, output_path: Path) -> None:
    """Write multiple 28x28 grayscale images into a single IDX file.

    IDX format (magic=2051, count=N, rows=28, cols=28):
        [4B magic][4B count][4B rows][4B cols][N * 784B pixels]

    Args:
        images: List of PIL Image objects (each 28x28 grayscale).
        output_path: Destination .idx file path.
    """
    count = len(images)
    header = struct.pack(">IIII", 2051, count, 28, 28)
    pixel_data = b"".join(bytes(img.getdata()) for img in images)
    output_path.write_bytes(header + pixel_data)
```

**Single-image equivalence**: When `count=1`, the pixel data block is identical to `write_idx_image()`.
A test verifies this explicitly (`test_single_image_pixel_data_matches_write_idx_image`).

### 3. Update main() with --batch flag

Change `input` from `type=Path` to `str` (needed for glob patterns), add `--batch` flag:

```python
parser.add_argument(
    "input",
    help="Input PNG/JPEG file (single mode) or directory/glob pattern (--batch mode)",
)
parser.add_argument(
    "--batch",
    action="store_true",
    help="Batch mode: accept a directory or glob pattern and write a multi-image IDX file",
)

# ...

if args.batch:
    image_paths = resolve_batch_inputs(args.input)
    images = []
    for path in image_paths:
        img = load_and_preprocess(path, emnist_transform)
        if args.preview:
            print(f"\n--- Preview: {path.name} ---")
            preview_ascii_art(img)
        images.append(img)
    write_idx_images_batch(images, args.output)
    print(f"Converted {len(images)} image(s) -> {args.output} (28x28 grayscale IDX, count={len(images)})")
    return 0

# Single-image path unchanged below...
input_path = Path(args.input)
```

**Critical**: Change `input` argparse type from `type=Path` to no type (raw `str`) so glob
patterns with `*` are not coerced to a Path object before `resolve_batch_inputs` can handle them.

### 4. Write tests (21 tests across 3 classes)

| Class | Count | What it covers |
|-------|-------|----------------|
| `TestResolveBatchInputs` | 8 | Sorted dir listing, JPEG inclusion, non-image exclusion, glob expansion, glob non-image filter, empty dir exits, no-match glob exits, returns Path objects |
| `TestWriteIdxImagesBatch` | 8 | File created, magic=2051, count=N for N∈{1,3,10}, rows=28, cols=28, size=16+N×784, N=1 matches single-mode pixels, pixel ordering |
| `TestBatchMain` | 5 | End-to-end directory, end-to-end glob, missing dir exits nonzero, `--no-emnist-transform`, single mode unchanged |

Key test helper — `_read_header()` avoids duplicating struct.unpack calls:

```python
def _read_header(path: Path) -> tuple:
    """Read IDX header fields (magic, count, rows, cols) from file."""
    data = path.read_bytes()
    return struct.unpack(">IIII", data[:16])
```

Verify pixel ordering explicitly:

```python
def test_pixel_data_order(self) -> None:
    img0 = Image.new("L", (28, 28), color=10)
    img1 = Image.new("L", (28, 28), color=200)
    out = self.tmp / "order.idx"
    self.write_idx_images_batch([img0, img1], out)
    data = out.read_bytes()
    self.assertEqual(data[16:16 + 784], bytes([10] * 784))
    self.assertEqual(data[16 + 784:16 + 784 * 2], bytes([200] * 784))
```

### 5. Pre-existing failures are not regressions

The existing `TestWriteIdxImage` tests were already failing before this change (they pass `bytes`
to `write_idx_image` which calls `img.getdata()` — a test/implementation mismatch from the prior
session). Confirm this by checking out main before running, then verify only your new tests fail
to establish the baseline:

```bash
# Verify pre-existing failures
git stash
pixi run python -m pytest tests/scripts/test_convert_image_to_idx.py -v --tb=no -q
git stash pop

# Then confirm your new tests all pass
pixi run python -m pytest tests/scripts/test_convert_image_to_idx_batch.py -v
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `input` as `type=Path` for batch | Kept `type=Path` on the `input` argparse argument | Glob patterns like `"images/*.png"` coerced to a Path before `resolve_batch_inputs` could parse them | Change `input` type to plain `str` when accepting glob patterns |
| Detecting glob vs directory by `*`/`?` in string | Checked if `*` or `?` present in input string to decide directory vs glob | Fails for directory paths that happen to contain those chars; also `Path("foo/bar")` is a dir not a glob | Use `Path.is_dir()` as the primary branch — cleaner and unambiguous |
| `return []` on empty match | Returned empty list and let caller handle | Caller `main()` would silently write a 0-image IDX file | `sys.exit(1)` in `resolve_batch_inputs` itself, consistent with single-image error handling |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Batch IDX header | `struct.pack(">IIII", 2051, N, 28, 28)` |
| File size formula | `16 + N × 784` bytes |
| Pixel ordering | Sequential: image 0 at offset 16, image 1 at offset 800, etc. |
| Extensions accepted | `.png`, `.jpg`, `.jpeg` (case-insensitive) |
| Sort order | Lexicographic by filename (for reproducibility) |
| New test count | 21 |
| Total test runtime | ~0.5s |
| Pre-existing failures | 10 (unrelated to this change — test/impl mismatch from prior session) |
