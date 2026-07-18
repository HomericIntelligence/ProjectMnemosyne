---
name: png-jpeg-to-idx-conversion
description: "Convert PNG/JPEG images to MNIST-style IDX files for an inference pipeline, in single-image or directory/glob batch mode. Use when: (1) a model accepts IDX but users supply raster images, (2) adding a Pillow-backed CLI bridge to a Mojo or ML inference workflow, (3) writing a multi-image IDX file with a count greater than one, (4) preserving EMNIST preprocessing and reproducible input order."
category: tooling
date: 2026-07-17
version: "2.0.0"
user-invocable: false
verification: verified-ci
tags: ["idx", "image-conversion", "png", "jpeg", "pillow", "batch", "emnist", "mojo"]
history: png-jpeg-to-idx-conversion.history
---

# PNG/JPEG to IDX Conversion

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-17 |
| **Objective** | Provide a dependable PNG/JPEG-to-IDX CLI for one image or an ordered batch of images |
| **Outcome** | One conversion workflow with single-image and directory/glob batch examples |
| **Verification** | verified-ci — ProjectOdyssey PRs #3702 and #4775 |
| **History** | [absorbed batch-conversion source](./png-jpeg-to-idx-conversion.history) |

## When to Use

- An inference entry point consumes MNIST-style IDX image files but users have PNG or JPEG input
- A project needs Pillow for image decoding because the inference runtime has no suitable native image I/O
- Input must be transformed to a 28×28 grayscale image, optionally with EMNIST orientation correction
- A user needs either one output image (`count=1`) or a reproducibly ordered multi-image IDX batch (`count=N`)

## Verified Workflow

### Quick Reference

```python
def write_idx_images(images: list[Image.Image], output_path: Path) -> None:
    """Write one or more preprocessed 28×28 grayscale images as IDX."""
    header = struct.pack(">IIII", 2051, len(images), 28, 28)
    output_path.write_bytes(header + b"".join(bytes(image.getdata()) for image in images))
```

The IDX contract is always `[magic=2051][count][rows=28][cols=28][count × 784 pixel bytes]`.
For one image, `count=1` and the file is 800 bytes; for `N` images, the file is `16 + N × 784` bytes.

### Detailed Steps

1. Build a small Python CLI around Pillow, with a clear installation failure if Pillow is unavailable. Document why Python is the image-I/O bridge when the target runtime cannot decode raster images itself.
2. Load every image as grayscale (`L`), resize with `Image.LANCZOS` to 28×28, and apply the EMNIST transpose/flip by default. Expose `--no-emnist-transform` for models that do not require it.
3. Centralize IDX writing so single and batch modes share the same big-endian header and byte serialization. Do not write float pixels; the consumer expects raw uint8 pixels.
4. Keep a single-image positional-input path for the common case. Return a nonzero error when the file does not exist.
5. Add `--batch` only when one output must contain multiple images. Accept a directory or glob as a raw string, resolve it to a sorted list of `.png`, `.jpg`, and `.jpeg` paths, and exit nonzero if the result is empty.
6. In batch mode, preprocess each resolved path, optionally print its preview, and write one IDX output whose header count equals the number of images. Do not change the single-image path's behavior.
7. Test header fields, exact file size, pixel ordering, preprocessing flags, missing input, direct `main()` invocation, and the single-image equivalence of the shared writer.

### Worked Example — Single image for an EMNIST inference command

```bash
python scripts/convert_image_to_idx.py my_digit.png my_digit.idx
pixi run mojo run -I . examples/lenet-emnist/run_infer.mojo \
  --checkpoint lenet5_weights --image my_digit.idx
```

Call `main()` directly in unit tests by temporarily replacing `sys.argv`; avoid subprocess tests
for a pure argparse wrapper. Mark Pillow-dependent tests skipped when Pillow is not installed.

### Worked Example — Directory or glob batch input

```python
def resolve_batch_inputs(input_arg: str) -> list[Path]:
    input_path = Path(input_arg)
    if input_path.is_dir():
        matches = sorted(
            path for path in input_path.iterdir()
            if path.suffix.lower() in {".png", ".jpg", ".jpeg"}
        )
    else:
        matches = [
            Path(path) for path in sorted(glob.glob(input_arg))
            if Path(path).suffix.lower() in {".png", ".jpg", ".jpeg"}
        ]
    if not matches:
        raise SystemExit(1)
    return matches
```

Use `Path.is_dir()` rather than inspecting `*` or `?` characters. It correctly handles paths
whose names contain glob-like characters and prevents a directory from being mistaken for an
image file. Assert that image 0 starts at byte 16 and image 1 at `16 + 784`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Use float32 pixels | Serialized normalized floats | IDX image consumers expect uint8 and normalize themselves | Preserve raw grayscale bytes |
| Keep `type=Path` for batch input | Let argparse coerce a glob before resolution | The CLI lost the intended raw glob semantics | Use a raw string when `--batch` accepts globs |
| Identify globs by characters | Branched only on `*` or `?` | Directory paths are not glob patterns and may contain those characters | Test `Path.is_dir()` first |
| Return an empty batch | Let the caller write a zero-image IDX file | A silent empty output violates the single-image error contract | Exit nonzero in input resolution |
| Use subprocess for CLI tests | Spawned Python to test argparse | It added overhead and path-resolution complexity | Call `main()` directly with controlled argv |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| IDX magic | `2051` (`0x00000803`) |
| Dimensions | 28×28 grayscale |
| Header | `struct.pack(">IIII", 2051, count, 28, 28)` |
| Pixel order | Image-major, 784 uint8 bytes per image |
| Single output size | 800 bytes |
| Batch output size | `16 + count × 784` bytes |
| Accepted input extensions | `.png`, `.jpg`, `.jpeg`, case-insensitive |
| Batch order | Lexicographic path order |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3702 | Single-image PNG/JPEG bridge, tests and pre-commit green. |
| ProjectOdyssey | PR #4775 | Directory/glob batch mode, 21 new tests green; known unrelated baseline failures preserved. |
