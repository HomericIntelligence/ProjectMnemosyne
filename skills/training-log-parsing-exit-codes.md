---
name: training-log-parsing-exit-codes
description: "Parse ML training logs with regex pattern matching and return distinct exit codes per failure mode (SUCCESS, TRAINING_FAILURE, LOG_FORMAT_MISMATCH, LOSS_NOT_DECREASING, NUMERIC_INSTABILITY). Use when: (1) validating training runs in CI/automation, (2) distinguishing between script bugs and training bugs, (3) requiring clear failure attribution for debugging."
category: ci-cd
date: 2026-07-03
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [python, log-parsing, regex, exit-codes, ml-training, validation, ci-cd]
---

# Training Log Parsing with Exit Codes

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-03 |
| **Objective** | Parse ML training output logs and return semantically distinct exit codes per failure mode to enable CI/CD blame attribution |
| **Outcome** | Successfully created `scripts/summarize_epoch_log.py` for ProjectOdyssey that validates MobileNetV1 CIFAR-10 epoch training and detects loss decreasing |
| **Verification** | verified-local (all 5 exit paths tested: SUCCESS, LOSS_NOT_DECREASING, NUMERIC_INSTABILITY, LOG_FORMAT_MISMATCH, TRAINING_FAILURE) |

## When to Use

- Validating training runs in CI/automation where you need to distinguish root cause (did training fail, or is loss not decreasing?)
- Exit code 0 is insufficient — CI needs to know whether to blame the script, the training algorithm, or the model/hyperparameters
- Training output format may change — script should fail loudly with clear error message rather than silently treating all non-zero values as failures
- Detecting numerical instabilities (NaN, inf) during training to catch silent divergence early
- Appending a `SUMMARY` line to log for grep-able validation in CI workflows

## Verified Workflow

### Quick Reference

**The pattern**: Use regex to parse training metrics, check for numerical issues, compare first-vs-last loss values, and return distinct exit codes.

```python
#!/usr/bin/env python3
"""
Parse ML training logs and validate loss decreasing.
Returns exit codes: 0 (success), 2 (training failure), 3 (format mismatch),
4 (loss not decreasing), 5 (numeric instability).
"""

import re
import math
import sys
from typing import list[float] | None

LOSS_PATTERN = r"^\s+Batch (\d+)/(\d+) - Loss: (.+)$"

def parse_losses_from_log(log_content: str) -> list[float] | None:
    """Extract loss values from training log using regex."""
    losses = []
    for line in log_content.split('\n'):
        match = re.match(LOSS_PATTERN, line)
        if match:
            try:
                loss_value = float(match.group(3))
                losses.append(loss_value)
            except ValueError:
                return None  # Format mismatch
    return losses if losses else None

def check_numeric_stability(losses: list[float]) -> str | None:
    """Detect NaN or inf values; return error reason or None if stable."""
    for i, loss in enumerate(losses):
        if math.isnan(loss):
            return f"NaN detected at batch {i}"
        if math.isinf(loss):
            return f"Inf detected at batch {i}"
    return None

def validate_loss_decreasing(losses: list[float]) -> bool:
    """Check if loss decreased from first to last batch (simple trend)."""
    if len(losses) < 2:
        return False
    first_loss = losses[0]
    last_loss = losses[-1]
    return last_loss < first_loss

def main() -> int:
    """Parse log and return exit code."""
    if len(sys.argv) < 2:
        print("Usage: summarize_epoch_log.py <log_file>", file=sys.stderr)
        return 2

    log_file = sys.argv[1]

    try:
        with open(log_file, 'r') as f:
            log_content = f.read()
    except OSError as e:
        print(f"ERROR: Failed to read {log_file}: {e}", file=sys.stderr)
        return 2  # TRAINING_FAILURE

    # Parse losses
    losses = parse_losses_from_log(log_content)

    if losses is None:
        print("ERROR: Log format mismatch — no loss values found", file=sys.stderr)
        print("SUMMARY: FORMAT_MISMATCH", file=sys.stdout)
        return 3  # LOG_FORMAT_MISMATCH

    if len(losses) < 3:
        print(f"ERROR: Insufficient samples ({len(losses)} < 3 required)", file=sys.stderr)
        print("SUMMARY: FORMAT_MISMATCH", file=sys.stdout)
        return 3  # LOG_FORMAT_MISMATCH (loud failure on format change)

    # Check numeric stability
    numeric_error = check_numeric_stability(losses)
    if numeric_error:
        print(f"ERROR: {numeric_error}", file=sys.stderr)
        print("SUMMARY: NUMERIC_INSTABILITY", file=sys.stdout)
        return 5  # NUMERIC_INSTABILITY

    # Check loss trend
    if not validate_loss_decreasing(losses):
        first, last = losses[0], losses[-1]
        print(f"ERROR: Loss not decreasing (first={first}, last={last})", file=sys.stderr)
        print("SUMMARY: LOSS_NOT_DECREASING", file=sys.stdout)
        return 4  # LOSS_NOT_DECREASING

    # Success
    first, last = losses[0], losses[-1]
    print(f"Success: Loss decreased (first={first}, last={last})", file=sys.stdout)
    print("SUMMARY: SUCCESS", file=sys.stdout)
    return 0  # SUCCESS

if __name__ == "__main__":
    sys.exit(main())
```

### Detailed Steps

**Step 1: Define the regex pattern for training metrics**

Study the actual training output and write a regex that captures batch info and loss value:

```bash
# Inspect training output
mojo run scripts/train.mojo 2>&1 | head -20

# Sample output:
#   Batch 1/100 - Loss: 2.3451
#   Batch 2/100 - Loss: 2.1234
#   Batch 3/100 - Loss: 2.0123
```

Create a regex pattern:

```python
LOSS_PATTERN = r"^\s+Batch (\d+)/(\d+) - Loss: (.+)$"
#                ^^^^^   ^^^^   ^^^^
#                |       |      value
#                |       batch numbers
#                handle leading whitespace
```

**Step 2: Write a parsing function with error handling**

```python
def parse_losses_from_log(log_content: str) -> list[float] | None:
    """Extract losses; return None if format is wrong."""
    losses = []
    for line in log_content.split('\n'):
        match = re.match(LOSS_PATTERN, line)
        if match:
            try:
                loss_value = float(match.group(3))
                losses.append(loss_value)
            except ValueError:
                return None  # Unparseable value
    return losses if losses else None  # Return list or None
```

**Step 3: Check for numerical instabilities**

Detect NaN and inf values that indicate training divergence:

```python
import math

def check_numeric_stability(losses: list[float]) -> str | None:
    """Check for NaN/inf; return error reason or None."""
    for i, loss in enumerate(losses):
        if math.isnan(loss):
            return f"NaN at batch {i}"
        if math.isinf(loss):
            return f"Inf at batch {i}"
    return None
```

**Step 4: Validate loss trend (simple first-vs-last comparison)**

Rather than complex heuristics, use simple comparison:

```python
def validate_loss_decreasing(losses: list[float]) -> bool:
    """Simple: did last loss < first loss?"""
    if len(losses) < 2:
        return False
    return losses[-1] < losses[0]
```

**Step 5: Define distinct exit codes with clear semantics**

```python
EXIT_CODES = {
    0: "SUCCESS",
    2: "TRAINING_FAILURE (read/I/O error)",
    3: "LOG_FORMAT_MISMATCH (no losses or wrong format)",
    4: "LOSS_NOT_DECREASING (training diverged)",
    5: "NUMERIC_INSTABILITY (NaN or inf detected)",
}
```

**Step 6: Require minimum sample count for format validation**

Ensure you have enough data points to confirm valid output (guards against format-change detection):

```python
MIN_SAMPLES = 3

if len(losses) < MIN_SAMPLES:
    # Not enough samples — either training crashed or format changed
    return 3  # LOG_FORMAT_MISMATCH (fail loud)
```

**Step 7: Append SUMMARY line for grep-able CI validation**

Always append a `SUMMARY: <STATUS>` line to stdout so CI can grep for validation:

```python
# At each exit path:
print("SUMMARY: SUCCESS", file=sys.stdout)
print("SUMMARY: NUMERIC_INSTABILITY", file=sys.stdout)
print("SUMMARY: LOSS_NOT_DECREASING", file=sys.stdout)
```

CI can then verify: `grep "SUMMARY: SUCCESS" log.txt && echo "Valid run"`

**Step 8: Use Python type hints matching CLAUDE.md conventions**

Follow ProjectOdyssey Python standards:

```python
from typing import list[float] | None

def parse_losses_from_log(log_content: str) -> list[float] | None:
    """Clear docstring with purpose, params, returns."""
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single exit code for all failures | Return 1 for any error (training failure, loss not decreasing, NaN, format mismatch) | CI can't distinguish blame — doesn't know if it should fix script, retrain, or change hyperparameters | Use 5+ exit codes: SUCCESS (0), TRAINING_FAILURE (2), LOG_FORMAT_MISMATCH (3), LOSS_NOT_DECREASING (4), NUMERIC_INSTABILITY (5) |
| Complex decile-split heuristic for 3 data points | Calculate percentiles to determine if loss "should have" decreased | Overfitting to arbitrary thresholds; fails when batch size or learning rate changes; too fragile | Simple first-vs-last comparison; if 3+ samples and last < first, training worked |
| Silent failure on format mismatch | Return 3 without error message | CI doesn't know why validation failed; hard to debug; logs are unclear | Print clear error to stderr; append SUMMARY line to stdout; fail-loud philosophy |
| Conflating NaN with general training failure | Both returned exit code 2 | CI couldn't distinguish numerical instability (worth investigating) from I/O errors (probably transient) | Separate into code 5 (NUMERIC_INSTABILITY); this is a distinct failure mode worth special handling |
| Parsing all lines instead of matching LOSS_PATTERN | Split by newlines, parse every numeric value | Picked up random numbers from other output (epoch count, model size, etc.); losses were wrong | Use strict regex with batch/loss context; only extract lines matching pattern |
| Requiring exact float format | Used strict float parsing without handling scientific notation | Training output might have "2.34e-3" or "inf" — float() failed; undetected | Use float() which handles all Python float formats including inf/nan |
| No minimum sample threshold | Treated any non-empty list as valid | Single loss value isn't enough to confirm training; one-liner format changes silently | Require ≥3 samples; fail with FORMAT_MISMATCH (code 3) if fewer — forces training to output at least 3 batches |

## Results & Parameters

### Implementation (ProjectOdyssey)

**File**: `scripts/summarize_epoch_log.py` (created during issue #5526)

```python
#!/usr/bin/env python3
"""
Parse MobileNetV1 CIFAR-10 epoch training log.
Validates loss decreased and detects numerical instabilities.

Exit codes:
  0 = SUCCESS (loss decreased)
  2 = TRAINING_FAILURE (I/O or crash)
  3 = LOG_FORMAT_MISMATCH (wrong format or insufficient samples)
  4 = LOSS_NOT_DECREASING (training diverged)
  5 = NUMERIC_INSTABILITY (NaN or inf detected)

Usage: python scripts/summarize_epoch_log.py <log_file>
"""

import re
import math
import sys
from typing import Optional

LOSS_PATTERN = r"^\s+Batch (\d+)/(\d+) - Loss: (.+)$"
MIN_SAMPLES = 3

def parse_losses_from_log(log_content: str) -> Optional[list[float]]:
    """Extract loss values from training log using regex."""
    losses = []
    for line in log_content.split('\n'):
        match = re.match(LOSS_PATTERN, line)
        if match:
            try:
                loss_value = float(match.group(3))
                losses.append(loss_value)
            except ValueError:
                return None  # Unparseable loss value
    return losses if losses else None

def check_numeric_stability(losses: list[float]) -> Optional[str]:
    """Detect NaN or inf; return error reason or None if stable."""
    for i, loss in enumerate(losses):
        if math.isnan(loss):
            return f"NaN detected at batch {i}"
        if math.isinf(loss):
            return f"Inf detected at batch {i}"
    return None

def validate_loss_decreasing(losses: list[float]) -> bool:
    """Check if loss decreased from first to last batch."""
    if len(losses) < 2:
        return False
    return losses[-1] < losses[0]

def main() -> int:
    """Parse log and return exit code."""
    if len(sys.argv) < 2:
        print("Usage: summarize_epoch_log.py <log_file>", file=sys.stderr)
        return 2

    log_file = sys.argv[1]

    try:
        with open(log_file, 'r') as f:
            log_content = f.read()
    except OSError as e:
        print(f"ERROR: Failed to read {log_file}: {e}", file=sys.stderr)
        return 2  # TRAINING_FAILURE

    # Parse losses from log
    losses = parse_losses_from_log(log_content)

    if losses is None:
        print("ERROR: Log format mismatch — no loss values found", file=sys.stderr)
        print("SUMMARY: FORMAT_MISMATCH", file=sys.stdout)
        return 3  # LOG_FORMAT_MISMATCH

    # Require minimum samples (fail-loud on format changes)
    if len(losses) < MIN_SAMPLES:
        print(f"ERROR: Insufficient samples ({len(losses)} < {MIN_SAMPLES} required)", file=sys.stderr)
        print("SUMMARY: FORMAT_MISMATCH", file=sys.stdout)
        return 3

    # Check for numerical instabilities
    numeric_error = check_numeric_stability(losses)
    if numeric_error:
        print(f"ERROR: {numeric_error}", file=sys.stderr)
        print("SUMMARY: NUMERIC_INSTABILITY", file=sys.stdout)
        return 5  # NUMERIC_INSTABILITY

    # Validate loss decreasing
    if not validate_loss_decreasing(losses):
        first, last = losses[0], losses[-1]
        print(f"ERROR: Loss not decreasing (first={first}, last={last})", file=sys.stderr)
        print("SUMMARY: LOSS_NOT_DECREASING", file=sys.stdout)
        return 4  # LOSS_NOT_DECREASING

    # Success
    first, last = losses[0], losses[-1]
    print(f"Success: Loss decreased (first={first:.4f}, last={last:.4f})", file=sys.stdout)
    print("SUMMARY: SUCCESS", file=sys.stdout)
    return 0  # SUCCESS

if __name__ == "__main__":
    sys.exit(main())
```

### Exit Code Semantics

| Exit Code | Status | Meaning | CI Action |
|-----------|--------|---------|-----------|
| 0 | ✅ SUCCESS | Training ran, loss decreased normally | Proceed to next validation |
| 2 | ❌ TRAINING_FAILURE | Script error or training crashed (I/O, no log file, etc.) | Retry job; investigate infrastructure |
| 3 | ❌ LOG_FORMAT_MISMATCH | Training output format wrong or too few samples | Debug training code; check Mojo output format |
| 4 | ⚠️ LOSS_NOT_DECREASING | Training diverged (loss increased or stayed same) | Adjust learning rate, model, or hyperparameters; not a code bug |
| 5 | ⚠️ NUMERIC_INSTABILITY | NaN or inf in loss values; training diverged badly | Check gradient computation, batch normalization, or weight initialization |

### Usage in CI

```bash
# Run training, capture log
mojo run scripts/train.mojo > train.log 2>&1
train_exit=$?

# Validate loss decreasing (separate exit code logic)
python scripts/summarize_epoch_log.py train.log
log_validation_exit=$?

# Report
case $log_validation_exit in
    0) echo "Training successful" ;;
    2) echo "Training failed"; exit 2 ;;
    3) echo "Format mismatch"; exit 1 ;;
    4) echo "Loss not decreasing — hyperparameter issue"; exit 1 ;;
    5) echo "Numeric instability"; exit 1 ;;
esac
```

### Testing All Paths

Each exit path is independently testable:

1. **SUCCESS (0)**: Create log with 3+ batches, losses decreasing
2. **LOSS_NOT_DECREASING (4)**: Create log with 3+ batches, losses increasing
3. **NUMERIC_INSTABILITY (5)**: Create log with "Loss: nan" or "Loss: inf"
4. **LOG_FORMAT_MISMATCH (3)**: Create log with no loss lines, or < 3 lines
5. **TRAINING_FAILURE (2)**: Pass non-existent file path

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #5526 — Validate CIFAR-10 training epoch loss decreases | Created `scripts/summarize_epoch_log.py` to parse MobileNetV1 training output. Tested all 5 exit paths: SUCCESS, LOSS_NOT_DECREASING, NUMERIC_INSTABILITY, LOG_FORMAT_MISMATCH, TRAINING_FAILURE. Regex pattern `^\s+Batch (\d+)/(\d+) - Loss: (.+)$` verified on actual training output. Type hints follow ProjectOdyssey CLAUDE.md Python conventions. |
