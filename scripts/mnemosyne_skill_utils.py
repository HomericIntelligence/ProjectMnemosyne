#!/usr/bin/env python3
"""
Shared utilities for skill file discovery and frontmatter parsing.

Centralises logic that was previously duplicated across
validate_plugins.py and generate_marketplace.py (see #914, #928, #1110).
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

SKILLS_DIR = Path("skills")


def parse_frontmatter(content: str) -> Tuple[Dict, str, List[str]]:
    """
    Parse YAML frontmatter from markdown content.

    Returns (frontmatter_dict, body, errors).
    """
    errors: List[str] = []

    if not content.startswith("---"):
        errors.append("File does not start with YAML frontmatter delimiter (---)")
        return {}, content, errors

    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append("Invalid frontmatter: missing closing ---")
        return {}, content, errors

    try:
        frontmatter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML frontmatter: {e}")
        return {}, content, errors

    body = parts[2].lstrip("\n")
    return frontmatter, body, errors


def find_skill_files(skills_dir: Path = SKILLS_DIR) -> List[Path]:
    """Find all flat skill files (skills/*.md).

    Excludes auxiliary files:
    - ``*.notes*.md``  (session notes)
    - ``*.history*``   (history files)
    """
    if not skills_dir.exists():
        return []

    files = sorted(
        [
            f
            for f in skills_dir.glob("*.md")
            if not re.match(r".*\.notes(-\w+)?\.md$", f.name) and not re.match(r".*\.history", f.name) and f.is_file()
        ]
    )
    return files
