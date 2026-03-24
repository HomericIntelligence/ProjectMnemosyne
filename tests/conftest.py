#!/usr/bin/env python3
"""
Shared pytest fixtures and configuration for the test suite.

Centralises:
- sys.path setup so every test file can ``import fix_remaining_warnings``
  (and other scripts) without its own ``sys.path.insert`` hack.
- Reusable sample content constants (frontmatter, skill markdown, etc.)
- Common helper functions used across multiple test modules.
"""

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup (replaces per-file sys.path.insert hacks)
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

SAMPLE_FRONTMATTER = """\
---
name: test-skill
description: "A test skill for unit testing purposes."
category: tooling
date: 2026-01-01
user-invocable: false
---
"""

SAMPLE_OVERVIEW = """\
# Test Skill

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-01-01 |
| Objective | Test |
| Outcome | Test |

## When to Use

- Condition A
- Condition B

"""

SAMPLE_QUICK_REFERENCE = """\
## Quick Reference

```bash
# Key commands
git status
git log
```

"""

SAMPLE_VERIFIED_WORKFLOW = """\
## Verified Workflow

### Step 1

Do the thing.

### Step 2

Do another thing.

"""

SAMPLE_FAILED_ATTEMPTS = """\
## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| N/A | No failures yet | Document failures as they occur |

"""

SAMPLE_RESULTS = """\
## Results & Parameters

N/A - workflow pattern skill.
"""

CLEAN_SKILL_MD = """\
---
name: test-skill
description: "A test skill."
category: tooling
date: 2026-01-01
user-invocable: false
---

# Test Skill

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-01-01 |
| Objective | Test |
| Outcome | Pass |

## When to Use

- When testing

## Verified Workflow

### Step 1

Do the thing.

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| N/A | No failures | Document as they occur |

## Results & Parameters

N/A
"""

SAMPLE_PLUGIN_JSON = {
    "name": "test-plugin",
    "version": "1.0.0",
    "description": "A test plugin for unit testing purposes.",
    "category": "tooling",
    "date": "2026-01-01",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_skill_md() -> str:
    """Return a complete, valid SKILL.md string (no warnings)."""
    return CLEAN_SKILL_MD


@pytest.fixture()
def sample_frontmatter() -> str:
    """Return sample YAML frontmatter block."""
    return SAMPLE_FRONTMATTER


@pytest.fixture()
def sample_plugin_json() -> dict:
    """Return a minimal valid plugin.json dict."""
    return dict(SAMPLE_PLUGIN_JSON)


@pytest.fixture()
def skill_dir(tmp_path: Path, sample_skill_md: str) -> Path:
    """Create a temporary directory containing a valid SKILL.md file.

    Returns the directory ``Path`` — the skill file is at ``skill_dir / "SKILL.md"``.
    """
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(sample_skill_md)
    return tmp_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_skill_file(directory: Path, content: str) -> Path:
    """Write a SKILL.md into *directory* and return its path."""
    skill_file = directory / "SKILL.md"
    skill_file.write_text(content)
    return skill_file
