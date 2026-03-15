---
name: pil-grayscale-method-flag
description: "Add a --grayscale-method {luma,average,max} CLI flag to image preprocessing scripts using PIL. Use when: adding configurable grayscale strategies to a PIL-based script, fixing broken PIL image tests, or extending argparse CLIs with algorithm-selection flags."
category: tooling
date: 2026-03-15
user-invocable: false
---

# PIL Grayscale Method Flag

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-15 |
| Objective | Expose multiple RGB→grayscale strategies via a `--grayscale-method` CLI flag without adding dependencies |
| Outcome | Success — 3 strategies implemented, 28/28 tests pass, PR #4777 created |
| Issue | #3707 |
| Category | tooling |

## When to Use

Trigger this skill when:

- A PIL-based image script uses `convert('L')` and callers need different grayscale algorithms
- An issue asks for `--grayscale-method {luma,average,max}` (or similar algorithm-selection flags)
- Tests call `len()` on a PIL `Image` object (always wrong — PIL Images are not sequences)
- Tests pass raw `bytes` to a function that expects a `PIL.Image.Image`
- You need to implement `average` channel weighting via PIL without numpy

## Verified Workflow

### Quick Reference

| Strategy | PIL Implementation | Formula |
|----------|--------------------|---------|
| `luma` | `img.convert("L")` | 0.299R + 0.587G + 0.114B (ITU-R 601) |
| `average` | `img.convert("RGB").convert("L", matrix=(1/3, 1/3, 1/3, 0))` | (R+G+B)/3 |
| `max` | `ImageChops.lighter(ImageChops.lighter(r, g), b)` | max(R, G, B) |

### 1. Implement conversion functions

```python
from PIL import Image, ImageChops

def _convert_luma(img: "Image.Image") -> "Image.Image":
    """ITU-R 601 luma weighting — PIL default."""
    return img.convert("L")

def _convert_average(img: "Image.Image") -> "Image.Image":
    """Equal-weight mean (R+G+B)/3 via PIL convert matrix."""
    return img.convert("RGB").convert("L", matrix=(1 / 3, 1 / 3, 1 / 3, 0))

def _convert_max(img: "Image.Image") -> "Image.Image":
    """Brightest channel desaturation."""
    rgb = img.convert("RGB")
    r, g, b = rgb.split()
    return ImageChops.lighter(ImageChops.lighter(r, g), b)

_GRAYSCALE_METHODS = {
    "luma": _convert_luma,
    "average": _convert_average,
    "max": _convert_max,
}
```

### 2. Update the preprocessing function signature

Add `grayscale_method: str = "luma"` with `default="luma"` to preserve existing behaviour:

```python
def load_and_preprocess(
    image_path: Path,
    emnist_transform: bool,
    grayscale_method: str = "luma",
) -> "Image.Image":
    img = Image.open(image_path)
    img = _GRAYSCALE_METHODS[grayscale_method](img)
    img = img.resize((28, 28), Image.Resampling.LANCZOS)
    if emnist_transform:
        img = img.transpose(Image.Transpose.TRANSPOSE).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return img
```

### 3. Add the argparse flag

Use `default=None` (not `"luma"`) in argparse so you can detect "not provided" separately
and fall back to the function's default — this keeps the two layers independent:

```python
parser.add_argument(
    "--grayscale-method",
    choices=["luma", "average", "max"],
    default=None,
    help=(
        "Grayscale conversion strategy: luma (ITU-R 601, default), "
        "average ((R+G+B)/3), max (brightest channel)"
    ),
)
# ...
grayscale_method = args.grayscale_method if args.grayscale_method is not None else "luma"
img = load_and_preprocess(args.input, not args.no_emnist_transform, grayscale_method)
```

### 4. Fix common test bugs for PIL Image functions

Two bugs appear repeatedly when PIL functions return `Image.Image` objects:

**Bug 1 — `len()` on a PIL Image** (PIL Images are not sequences):

```python
# WRONG — TypeError: object of type 'Image' has no len()
self.assertEqual(len(result), 784)

# CORRECT — use getdata() to access pixel sequence
self.assertEqual(len(list(result.getdata())), 784)
# Or check size attribute directly
self.assertEqual(result.size, (28, 28))
```

**Bug 2 — Passing `bytes` to a function expecting `Image.Image`**:

```python
# WRONG — write_idx_image expects PIL Image, not bytes
pixel_bytes = bytes(784)
self.write_idx_image(pixel_bytes, out)

# CORRECT — create an actual PIL Image
img = Image.new("L", (28, 28), color=128)
self.write_idx_image(img, out)
```

### 5. Write parametric tests covering all three methods

```python
def test_all_methods_accept_grayscale_input(self) -> None:
    png = self.tmp / "gray.png"
    _make_png(png)  # already-grayscale input
    for method in ["luma", "average", "max"]:
        result = self.load_and_preprocess(png, emnist_transform=False, grayscale_method=method)
        self.assertEqual(result.size, (28, 28))

def test_max_method_equals_brightest_channel(self) -> None:
    png = self.tmp / "solid.png"
    img = Image.new("RGB", (4, 4), color=(200, 100, 50))  # R dominates
    img.save(png)
    result = self.load_and_preprocess(png, emnist_transform=False, grayscale_method="max")
    for px in result.getdata():
        self.assertEqual(px, 200)  # max(200, 100, 50) = 200

def test_average_method_pixel_value(self) -> None:
    png = self.tmp / "solid.png"
    img = Image.new("RGB", (4, 4), color=(150, 90, 60))  # avg = 100
    img.save(png)
    result = self.load_and_preprocess(png, emnist_transform=False, grayscale_method="average")
    for px in result.getdata():
        self.assertAlmostEqual(px, 100, delta=2)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `ImageChops.add` for average | `ImageChops.add(ImageChops.add(r, g, scale=1.0), b, scale=1.0)` then `point(lambda x: x/3)` | `add()` clips at 255 before the divide; for (150,90,60) → (240+60)/3=100 but intermediate (150+90)=240 clips to 255 → 255/3=85 | Never sum channels with `ImageChops.add` and divide later; use `convert("L", matrix=...)` for weighted sums |
| `argparse default="luma"` | Set `default="luma"` directly on `add_argument` | Works but couples argparse default to function default; if function default changes, they diverge silently | Use `default=None` in argparse, then resolve to `"luma"` in main() separately |
| `len(PIL_Image)` in tests | `self.assertEqual(len(result), 784)` | `PIL.Image.Image` is not a sequence; raises `TypeError: object of type 'Image' has no len()` | Always use `result.size` or `list(result.getdata())` to inspect PIL Image dimensions/pixels |

## Results & Parameters

```python
# Verified PIL convert matrix coefficients (copy-paste ready)
_convert_average = lambda img: img.convert("RGB").convert("L", matrix=(1/3, 1/3, 1/3, 0))
# matrix=(r_weight, g_weight, b_weight, offset) — all floats in [0,1] range

# Verified max channel (copy-paste ready)
_convert_max = lambda img: ImageChops.lighter(ImageChops.lighter(*img.convert("RGB").split()[:2]), img.convert("RGB").split()[2])
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4777, issue #3707 | [notes.md](../references/notes.md) |
