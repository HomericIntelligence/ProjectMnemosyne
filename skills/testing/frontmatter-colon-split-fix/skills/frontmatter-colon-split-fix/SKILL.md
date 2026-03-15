---
name: frontmatter-colon-split-fix
description: "Fix YAML frontmatter parsers that use manual line.split(':', 1) instead of yaml.safe_load(), which silently truncates values containing colons. Use when: auditing frontmatter parsers for colon-split bugs, adding regression tests for URL/ratio values in YAML fields, or fixing description fields that lose data after the first colon."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Property | Value |
|----------|-------|
| **Problem** | Manual `line.split(":", 1)` parsing of YAML frontmatter silently truncates values that contain colons (URLs like `https://...`, ratios like `3:1`, quoted strings with mid-sentence colons) |
| **Root Cause** | `split(":", 1)` splits on the *first* colon in the line, so `description: See https://example.com` becomes key=`description`, value=`See https` |
| **Fix** | Replace manual parsing with `yaml.safe_load()` which correctly handles all YAML value types |
| **Test Pattern** | Regression tests for each colon variant: URL, numeric ratio, quoted colon, multi-colon (URL with port) |
| **Language** | Python + PyYAML |
| **Context** | Found in agent config validation scripts (`validate_configs.py`, `check_frontmatter.py`, `validate_agents.py`) |

## When to Use

- A frontmatter parser reads YAML values using `line.split(":", 1)` or `partition(":")`
- Description fields are being silently truncated when they contain URLs or colons
- Adding audit tests to scripts that parse agent markdown files
- Writing regression tests to prevent the truncation bug from returning
- The parsed `description` value is suspiciously short or ends at a URL's `://`

## Verified Workflow

### Quick Reference

```python
# WRONG - silently truncates "See https://example.com for details"
# into just "See https"
key, value = line.split(":", 1)

# RIGHT - preserves full value including colons
import yaml
parsed = yaml.safe_load(frontmatter_text)
```

### Step 1: Identify the Bug

Search for manual colon splitting in frontmatter parsers:

```bash
grep -n "split.*:" scripts/agents/*.py
grep -n "partition.*:" scripts/agents/*.py
```

Look for patterns like:

```python
for line in frontmatter_text.split("\n"):
    if ":" not in line:
        continue
    key, value = line.split(":", 1)   # ← Bug here
    frontmatter[key] = value
```

### Step 2: Fix the Parser

Replace the manual loop with `yaml.safe_load()`:

```python
# Before (buggy)
import re
frontmatter = {}
frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
frontmatter_text = frontmatter_match.group(1)
for line in frontmatter_text.split("\n"):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    if ":" not in line:
        errors.append(f"Invalid frontmatter line (no colon): {line}")
        continue
    key, value = line.split(":", 1)
    key = key.strip()
    value = value.strip()
    frontmatter[key] = value

# After (correct)
import re
import yaml
from typing import Any, Dict

frontmatter: Dict[str, Any] = {}
frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
frontmatter_text = frontmatter_match.group(1)
try:
    parsed = yaml.safe_load(frontmatter_text)
except yaml.YAMLError as e:
    errors.append(f"Invalid YAML frontmatter: {e}")
    return errors, warnings, frontmatter
if not isinstance(parsed, dict):
    errors.append("Frontmatter must be a YAML mapping")
    return errors, warnings, frontmatter
frontmatter = parsed
```

Update type annotations to use `Dict[str, Any]` instead of `Dict[str, str]`:

```python
# Before
def _validate_frontmatter(self, content: str) -> Tuple[List[str], List[str], Dict[str, str]]:

# After
def _validate_frontmatter(self, content: str) -> Tuple[List[str], List[str], Dict[str, Any]]:
```

### Step 3: Write Regression Tests

Create a `TestFrontmatterColonValues` class (or equivalent) in the test file:

```python
class TestFrontmatterColonValues:
    """Regression tests for colon-containing values in frontmatter.

    These tests verify that the parser correctly handles YAML values that
    contain colons without truncation.
    """

    def test_url_in_description_preserved(self):
        """Description with a URL should not be truncated at the colon."""
        content = """---
name: test-agent
description: See https://docs.example.com/api for details
tools: Read,Write
model: sonnet
---
# Content"""
        result = parse_frontmatter(content)
        assert result["description"] == "See https://docs.example.com/api for details"

    def test_quoted_colon_preserved(self):
        """Colon inside a quoted YAML string should be preserved whole."""
        content = """---
name: test-agent
description: "Use when you need to: parse, validate, or check files"
tools: Read,Write
model: sonnet
---
# Content"""
        result = parse_frontmatter(content)
        assert result["description"] == "Use when you need to: parse, validate, or check files"

    def test_numeric_ratio_colon_preserved(self):
        """Numeric ratio notation (3:1) should be preserved."""
        content = """---
name: test-agent
description: Handles ratio 3:1 splits for training and validation
tools: Read,Write
model: sonnet
---
# Content"""
        result = parse_frontmatter(content)
        assert result["description"] == "Handles ratio 3:1 splits for training and validation"

    def test_url_with_port_preserved(self):
        """URL with port number (multiple colons) should be preserved."""
        content = """---
name: test-agent
description: Connect to http://localhost:8080/api for testing
tools: Read,Write
model: sonnet
---
# Content"""
        result = parse_frontmatter(content)
        assert result["description"] == "Connect to http://localhost:8080/api for testing"
```

### Step 4: Important YAML Nuance

**Bare colons mid-sentence are invalid YAML** unless quoted. This is correct YAML behavior:

```yaml
# VALID: URL (colon followed by //)
description: See https://example.com for details

# VALID: numeric ratio (colon between numbers)
description: Handles 3:1 splits

# VALID: colon in quoted string
description: "Use when you need to: do something"

# INVALID YAML: bare colon followed by space (looks like a mapping key)
description: Use when you need to: do something
# ↑ PyYAML raises ScannerError here - this is correct behavior!
```

When writing regression tests, use **valid** YAML forms. Don't test for values that are genuinely invalid YAML — the parser correctly rejects them.

### Step 5: Run the Tests

```bash
pixi run python -m pytest tests/agents/test_<script>.py::TestFrontmatterColonValues -v
```

All colon-variant tests should pass. If any fail, check if the test itself uses invalid YAML (bare colon followed by space) — that's a test bug, not a parser bug.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Test with bare `to: parse` colon | Wrote test: `description: Use when you need to: parse, validate, or check files` | PyYAML raises `ScannerError` — this is genuinely invalid YAML (colon+space = mapping key) | Only test valid YAML forms; bare `key: value` mid-sentence is invalid YAML, not a parser bug |
| Keep `Dict[str, str]` type annotation | Left return type as `Dict[str, str]` after switching to `yaml.safe_load()` | `yaml.safe_load()` returns `Any` values (int, bool, list), not just strings | Update type annotations to `Dict[str, Any]` when switching from manual parsing to PyYAML |

## Results & Parameters

**Files Fixed in ProjectOdyssey:**

```text
tests/agents/validate_configs.py      # Main fix: yaml.safe_load() + Dict[str, Any]
tests/agents/test_agent_utils.py      # Added TestFrontmatterColonValues regression class
tests/agents/test_check_frontmatter.py  # New: tests for check_frontmatter.py
tests/agents/test_validate_agents.py    # New: tests for validate_agents.py
```

**Test count:** 86 tests, all passing

**Grep pattern to find the bug:**

```bash
grep -rn "split.*\":\"\|split.*':'\\|partition.*\":\"\|partition.*':'" scripts/ tests/
```

**Validation that yaml.safe_load handles URLs:**

```python
import yaml
# All of these parse correctly:
yaml.safe_load("description: See https://example.com for details")
# → {'description': 'See https://example.com for details'}  ✓

yaml.safe_load('description: "Use when you need to: parse files"')
# → {'description': 'Use when you need to: parse files'}  ✓

yaml.safe_load("description: Handles 3:1 ratio")
# → {'description': 'Handles 3:1 ratio'}  ✓
```
