---
name: yaml-frontmatter-colon-fix
description: "Fix silent data-loss when parsing YAML frontmatter containing colons in values by replacing line.partition(':') with yaml.safe_load(). Use when: a frontmatter parser truncates values at the first colon."
category: tooling
date: 2026-03-07
user-invocable: false
---

# YAML Frontmatter Colon Fix

## Overview

| Item | Details |
|------|---------|
| Name | yaml-frontmatter-colon-fix |
| Category | tooling |
| Language | Python |
| Root cause | `str.partition(':')` splits on first colon, silently truncating values that contain colons |
| Fix | Replace manual loop with `yaml.safe_load()` on the frontmatter block |

## When to Use

- A Python script parses `---` YAML frontmatter using `line.partition(':')` or `line.split(':', 1)`
- Values like `description: "Create PR linked to issue: #123"` are silently truncated to `"Create PR linked to issue"`
- Migration or transformation scripts copy frontmatter fields and downstream consumers see incomplete data
- You need to add a regression test for colons inside quoted YAML values

## Verified Workflow

### 1. Identify the faulty parser

Look for patterns like:

```python
for line in frontmatter_lines:
    if ":" in line:
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
```

### 2. Add the import

```python
import yaml
```

### 3. Replace the loop with yaml.safe_load()

```python
frontmatter_text = "\n".join(frontmatter_lines)
try:
    parsed = yaml.safe_load(frontmatter_text)
    frontmatter = parsed if isinstance(parsed, dict) else {}
except yaml.YAMLError:
    frontmatter = {}
```

`yaml` is part of PyYAML which is a standard dependency in most Python projects. No new package needed.

### 4. Add regression tests

```python
def test_colon_in_quoted_value(self) -> None:
    """Regression: description with colon inside quoted value must not be truncated."""
    content = '---\nname: gh-create-pr-linked\ndescription: "Create PR linked to issue: #123"\n---\n# Body'
    fm, _ = parse_frontmatter(content)
    assert fm["description"] == "Create PR linked to issue: #123"

def test_invalid_yaml_returns_empty_dict(self) -> None:
    """Malformed YAML in frontmatter returns {} without raising."""
    content = "---\n: invalid: yaml: [\n---\n# Body"
    fm, _ = parse_frontmatter(content)
    assert fm == {}
```

### 5. Run tests

```bash
pixi run python -m pytest tests/scripts/test_migrate_odyssey_skills.py -v
```

All tests should pass, including the new regression cases.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Keep `partition(':')` but strip quotes | Strip `"` and `'` after splitting on first colon | Still wrong: `"Create PR linked to issue: #123"` → `"Create PR linked to issue` (truncated before strip) | The colon is inside the value, not separating key from value — stripping quotes does not help |
| Use `split(':', 1)` | Split at most once, take `[1]` as value | Same root cause: still splits at the first colon even when it is inside a quoted string | Only a real YAML parser understands quoting rules |
| Regex to detect quoted values | Match `key: "value with: colons"` | Fragile; does not handle multi-line values, escape sequences, or other YAML syntax | Use the YAML spec instead of reimplementing it |

## Results & Parameters

### Key parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| PyYAML function | `yaml.safe_load()` | Use `safe_load`, never `load()` — avoids arbitrary code execution |
| Fallback on parse error | `{}` | Catch `yaml.YAMLError`, return empty dict to avoid crashing |
| Type check after parse | `isinstance(parsed, dict)` | `yaml.safe_load` on empty string returns `None`; guard against it |

### Validated fix (from Odyssey2 PR #3928)

```python
import yaml

def parse_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content
    lines = content.split("\n")
    end_idx = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break
    if end_idx == -1:
        return {}, content
    frontmatter_lines = lines[1:end_idx]
    remaining = "\n".join(lines[end_idx + 1 :])
    frontmatter_text = "\n".join(frontmatter_lines)
    try:
        parsed = yaml.safe_load(frontmatter_text)
        frontmatter = parsed if isinstance(parsed, dict) else {}
    except yaml.YAMLError:
        frontmatter = {}
    return frontmatter, remaining
```
