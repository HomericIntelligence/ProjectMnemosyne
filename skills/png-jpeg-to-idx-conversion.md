---
name: png-jpeg-to-idx-conversion
description: 'Create a Python interop script converting PNG/JPEG images to IDX binary
  format for Mojo inference pipelines. Use when: (1) a Mojo inference entry point
  expects IDX format but users only have PNG/JPEG, (2) bridging PIL/Pillow image loading
  into Mojo-native data formats, (3) replacing manual numpy workarounds with a dedicated
  CLI script.'
category: tooling
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | png-jpeg-to-idx-conversion |
| **Category** | tooling |
| **Language** | Python 3.7+ |
| **Dependencies** | Pillow (PIL) |
| **Output** | `scripts/convert_image_to_idx.py` + `tests/scripts/test_convert_image_to_idx.py` |
| **ADR** | Python justified by ADR-001 (no stdlib image IO in Mojo v0.26.1) |

## When to Use

- Mojo inference pipeline reads IDX format but users have PNG/JPEG input images
- README shows a manual PIL+numpy workaround that should be replaced with a dedicated script
- Adding Python interop for image preprocessing to an ML example directory
- Need a one-liner `python scripts/convert_image_to_idx.py input.png output.idx` for users

## Verified Workflow

### 1. Create the conversion script

Key design decisions:

- **Graceful import error**: Wrap `from PIL import Image` in try/except and print install hint
- **ADR-001 justification header**: Python is used because Mojo stdlib has no image IO
- **EMNIST transform**: `Image.TRANSPOSE` + `Image.FLIP_LEFT_RIGHT` by default (matches EMNIST model weights); `--no-emnist-transform` flag skips it
- **IDX header**: `struct.pack(">IIII", 2051, 1, 28, 28)` — big-endian, magic 2051, count 1, 28×28
- **Total output**: 16-byte header + 784 pixel bytes = 800 bytes

```python
#!/usr/bin/env python3
"""Convert PNG/JPEG image to IDX format for LeNet-5 inference.

ADR-001 Justification: Python required for PIL image decoding
(not available in Mojo v0.26.1 stdlib).
"""

import argparse
import struct
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow not installed. Install with: pip install Pillow")
    sys.exit(1)


def load_and_preprocess(image_path: Path, emnist_transform: bool) -> bytes:
    img = Image.open(image_path).convert("L")
    img = img.resize((28, 28), Image.LANCZOS)
    if emnist_transform:
        img = img.transpose(Image.TRANSPOSE).transpose(Image.FLIP_LEFT_RIGHT)
    return bytes(img.getdata())


def write_idx_image(pixel_bytes: bytes, output_path: Path) -> None:
    header = struct.pack(">IIII", 2051, 1, 28, 28)
    output_path.write_bytes(header + pixel_bytes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert PNG/JPEG to IDX format for run_infer.mojo")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--no-emnist-transform", action="store_true")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        return 1

    pixel_bytes = load_and_preprocess(args.input, not args.no_emnist_transform)
    write_idx_image(pixel_bytes, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 2. Write tests (15 tests across 3 classes)

Test classes and what they cover:

| Class | Tests |
|-------|-------|
| `TestLoadAndPreprocess` | 784-byte output, uint8 range, JPEG accepted, transform changes pixels |
| `TestWriteIdxImage` | file created, 800-byte size, IDX magic/count/rows/cols, pixel data verbatim |
| `TestMain` | end-to-end PNG, end-to-end JPEG, missing input exits 1, `--no-emnist-transform` flag |

Key testing pattern — avoid subprocess, call `main()` directly:

```python
def _run_main(self, args: list) -> int:
    old_argv = sys.argv
    try:
        sys.argv = ["convert_image_to_idx.py"] + args
        return self.main()
    finally:
        sys.argv = old_argv
```

Guard tests when Pillow is unavailable:

```python
pytestmark = pytest.mark.skipif(not PIL_AVAILABLE, reason="Pillow not installed")
```

### 3. Update README

Replace the manual numpy workaround section with a new "Converting Custom Images" section:

```markdown
## Converting Custom Images

```bash
python scripts/convert_image_to_idx.py my_digit.png my_digit.idx
pixi run mojo run -I . examples/lenet-emnist/run_infer.mojo \
    --checkpoint lenet5_weights \
    --image my_digit.idx
```
```

### 4. Run pre-commit and verify

```bash
pixi run pre-commit run --files scripts/convert_image_to_idx.py \
    tests/scripts/test_convert_image_to_idx.py \
    examples/lenet-emnist/README.md
pixi run python -m pytest tests/scripts/test_convert_image_to_idx.py -v
```

All 15 tests pass in ~1.3s. Ruff may reformat the argparse description line (line length).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `sys.path` insert in test file | Used `sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))` | Works, but test runner must be invoked from repo root | Always insert scripts path relative to `__file__`, not cwd |
| Writing IDX with `float32` pixels | Considered writing float32 values (0.0–1.0) instead of uint8 | EMNIST IDX images use uint8; run_infer.mojo normalizes internally | Keep pixel bytes as raw uint8 and let the Mojo side normalize |
| Subprocess-based CLI tests | Considered `subprocess.run(["python", script, ...])` | Adds process overhead and path resolution complexity | Call `main()` directly by patching `sys.argv` — faster and simpler |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Output size | 800 bytes (16 header + 784 pixels) |
| IDX magic | 2051 (0x00000803) |
| Image size | 28×28 pixels |
| Color mode | Grayscale (L) |
| Resize filter | `Image.LANCZOS` |
| EMNIST transform | `Image.TRANSPOSE` + `Image.FLIP_LEFT_RIGHT` |
| Test count | 15 |
| Test runtime | ~1.3s |
| Pre-commit hooks | bandit, mypy, ruff format, ruff check, markdownlint — all pass |
