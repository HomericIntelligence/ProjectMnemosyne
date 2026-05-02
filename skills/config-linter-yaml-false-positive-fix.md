---
name: config-linter-yaml-false-positive-fix
description: "Fix line-level YAML linter false positives by replacing a narrow key regex with an allowlist of valid YAML constructs and block scalar state tracking. Use when: (1) a regex-based YAML linter flags valid colons as malformed keys, (2) block scalar contents trigger line-level warnings."
category: tooling
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - yaml
  - linter
  - false-positive
  - regex
  - config-validation
---

# Fix YAML Linter False-Positive Malformed Key Detection

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Eliminate false-positive "Possible malformed key" warnings from a line-level YAML syntax checker that flagged valid constructs containing colons |
| **Outcome** | Success — all false-positive cases resolved, genuine malformed keys still detected, 30 tests pass |
| **Verification** | verified-local |
| **Project** | ProjectHephaestus `hephaestus/validation/config_lint.py` |

## When to Use

- A line-level YAML linter uses `re.match(r"^\s*[\w\-]+:", line)` to identify valid keys and warns on everything else containing a colon
- Valid YAML constructs trigger false positives: quoted keys, flow mappings, list items, timestamps, block scalars, colons in values
- You need to add block scalar state tracking (`|`/`>`) to skip multi-line string contents in a line-by-line linter
- Ruff C901 complexity limits require extracting validation logic into helper methods

## Verified Workflow

### Quick Reference

```python
# Allowlist pattern — replaces narrow ^\s*[\w\-]+: regex
@staticmethod
def _is_valid_yaml_key_line(line: str) -> bool:
    s = line.strip()
    return bool(
        not s
        or "://" in line                                    # URL
        or re.match(r"^\s*[\w\-]+:", line)                  # simple key
        or re.match(r'^\s*["\'][^"\']+["\']:', line)        # quoted key
        or re.match(r"^\s*\{", line)                        # flow mapping
        or re.match(r"^\s*-\s", line)                       # list item
        or re.match(r"^\s*---", line)                       # document separator
        or re.match(r"^\s*\.\.\.", line)                    # document end
    )

# Block scalar tracking — skip lines inside | and >
if re.match(r"^\s*[\w\"\'\-][^:]*:\s*[|>]", stripped):
    in_block_scalar = True
    block_scalar_indent = len(line) - len(line.lstrip())
    continue

# Continuation check
if in_block_scalar:
    if stripped == "" or len(line) - len(line.lstrip()) > block_scalar_indent:
        continue  # still inside block scalar
    in_block_scalar = False  # indentation decreased, block ended
```

### Detailed Steps

1. **Replace the narrow regex** (`^\s*[\w\-]+:`) with an allowlist of valid YAML constructs. The key insight is that a single regex cannot cover all valid YAML key patterns — an allowlist of specific patterns is more maintainable and correct.

2. **Add block scalar state tracking** using `in_block_scalar` and `block_scalar_indent` variables. Lines inside `|` or `>` block scalars are continuation text, not key-value pairs, and must be skipped entirely.

3. **Extract helpers to satisfy C901 complexity**. The block scalar check and the allowlist validation each become static methods, reducing the main loop's cyclomatic complexity below the ruff threshold (10).

4. **Test both directions**: parametrized tests for all false-positive cases (16 valid YAML constructs that must NOT warn) plus a regression test confirming genuinely malformed keys (e.g., `@weird:stuff`) still produce warnings.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Expanding the single regex | Try to make `^\s*[\w\-]+:` handle quoted keys and flow mappings in one pattern | Regex becomes unmaintainable and still misses edge cases like list items and document separators | An allowlist of specific patterns is clearer than one universal regex |
| Nested `if` statements | `if ":" in line: if not valid:` | Ruff SIM102 flags nested `if` that can be combined with `and` | Use `if ":" in x and not valid(x):` instead |
| Inline block scalar check | Keeping the block scalar continuation logic inside `_check_yaml_syntax` | Ruff C901 complexity exceeded 10 (was 12) | Extract state-checking logic into static helper methods |

## Results & Parameters

**False-positive cases now handled (all verified with parametrized tests):**

```yaml
# Colon in quoted value
description: "Time: 3:00pm"

# Quoted keys
"my key": value
'my key': value

# Flow mappings
mapping: {key: value}
{key: value, other: 2}

# List items
items:
  - "key: value"
  - name: foo

# Timestamps
created: 2024-01-15T10:30:00

# Block scalars (| and >)
desc: |
  Line with: colon
  Another: line

# Document markers
---
...

# Comments
# comment with: colon

# URLs (pre-existing, preserved)
url: https://example.com
```

**Still detected as malformed:**
```yaml
@weird:stuff    # No valid YAML pattern match → warning emitted
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #64 / PR #130 | 30 unit tests pass, ruff lint+format clean |
