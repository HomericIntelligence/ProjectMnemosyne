#!/usr/bin/env python3
"""
Validate flat-format skill files (skills/*.md).

Checks:
- Required YAML frontmatter fields (name, description, category, date, version)
- Section presence (Overview, When to Use, Verified Workflow, Failed Attempts, Results & Parameters)
- Failed Attempts table structure
- Category validity
- Date format (YYYY-MM-DD)
- Quick Reference demotion check (should be ### not ##)
"""

import re
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Tuple

SKILLS_DIR = Path("skills")
VALID_CATEGORIES = {
    "training", "evaluation", "optimization", "debugging",
    "architecture", "tooling", "ci-cd", "testing", "documentation"
}

# Color codes for terminal output
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"


def find_plugins() -> List[Path]:
    """Find all flat skill files (skills/*.md, exclude *.notes*.md and *.history)."""
    if not SKILLS_DIR.exists():
        return []

    files = sorted([
        f for f in SKILLS_DIR.glob("*.md")
        if not re.match(r".*\.notes(-\w+)?\.md$", f.name) and f.is_file()
    ])
    return files


def parse_frontmatter(content: str) -> Tuple[Dict, str, List[str]]:
    """
    Parse YAML frontmatter from markdown.
    Returns (frontmatter_dict, body, errors).
    """
    errors = []

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


def validate_frontmatter(frontmatter: Dict, filename: str) -> List[str]:
    """Validate required frontmatter fields."""
    errors = []

    # Required fields
    required = ["name", "description", "category", "date", "version"]
    for field in required:
        if field not in frontmatter:
            errors.append(f"Missing required field: {field}")
        elif not frontmatter[field]:
            errors.append(f"Empty required field: {field}")

    # Category validation
    if "category" in frontmatter:
        cat = frontmatter["category"]
        if cat not in VALID_CATEGORIES:
            errors.append(f"Invalid category: {cat}. Valid: {', '.join(sorted(VALID_CATEGORIES))}")

    # Date format validation (YYYY-MM-DD)
    if "date" in frontmatter:
        date_str = frontmatter["date"]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date_str)):
            errors.append(f"Invalid date format: {date_str} (expected YYYY-MM-DD)")

    # Name format validation (kebab-case: lowercase alphanumeric + hyphens only)
    if "name" in frontmatter:
        name = str(frontmatter["name"])
        if not re.match(r"^[a-z0-9-]+$", name):
            errors.append(f"Invalid name format: '{name}' must be kebab-case (lowercase, hyphens, no spaces)")

    return errors


def validate_sections(body: str) -> List[str]:
    """Validate required markdown sections."""
    errors = []

    required_sections = [
        "## Overview",
        "## When to Use",
        "## Verified Workflow",
        "## Failed Attempts",
        "## Results & Parameters",
    ]

    for section in required_sections:
        if section not in body:
            errors.append(f"Missing required section: {section}")

    return errors


def validate_failed_attempts_table(body: str) -> List[str]:
    """Validate Failed Attempts table structure."""
    errors: List[str] = []

    # Find Failed Attempts section
    if "## Failed Attempts" not in body:
        return errors  # Already checked in validate_sections

    # Extract Failed Attempts content
    match = re.search(
        r"## Failed Attempts\s*\n(.*?)(?:\n## |\Z)",
        body,
        re.DOTALL
    )

    if not match:
        return errors

    section_content = match.group(1).strip()

    # Check if it's a table or plain text
    if "|" not in section_content:
        # Allow plain text failed attempts
        if not section_content or section_content.lower() == "none.":
            errors.append("Failed Attempts section is empty or only contains 'None.'")
        return errors

    # Validate table structure
    lines = section_content.split("\n")
    if len(lines) < 3:
        errors.append("Failed Attempts table is incomplete (needs header, separator, at least one row)")
        return errors

    # Check header row
    header = lines[0].strip()
    if not all(col in header for col in ["Attempt", "What Was Tried", "Why It Failed", "Lesson Learned"]):
        errors.append("Failed Attempts table missing required columns")

    return errors


def validate_quick_reference_heading(body: str) -> List[str]:
    """
    Validate that Quick Reference uses ### not ##.
    This was a common issue in old format.
    """
    errors = []

    # Look for ## Quick Reference (should be ### Quick Reference)
    if re.search(r"^## Quick Reference", body, re.MULTILINE):
        errors.append("Quick Reference should use ### (h3) not ## (h2)")

    return errors


def validate_skill_md(plugin_dir: Path, _plugin_json: Dict) -> Tuple[List[str], List[str]]:
    """Validate a legacy plugin-style skill directory.

    Returns ``(errors, warnings)`` where orphaned top-level Quick Reference
    headings are emitted as warnings, matching the historical test contract.
    """
    errors: List[str] = []
    warnings: List[str] = []

    skill_files = sorted(plugin_dir.rglob("SKILL.md"))
    if not skill_files:
        return ["Missing SKILL.md"], warnings

    content = skill_files[0].read_text()
    frontmatter, body, parse_errors = parse_frontmatter(content)
    errors.extend(parse_errors)

    if not frontmatter:
        return errors, warnings

    errors.extend(validate_frontmatter(frontmatter, skill_files[0].name))
    errors.extend(validate_sections(body))
    errors.extend(validate_failed_attempts_table(body))

    if re.search(r"^## Quick Reference", body, re.MULTILINE):
        warnings.append("Quick Reference should be a subsection (###) under Verified Workflow")

    return errors, warnings


def validate_plugin(filename: str) -> List[str]:
    """Validate a single skill file. Returns list of errors."""
    errors = []

    file_path = SKILLS_DIR / filename

    try:
        with open(file_path, "r") as f:
            content = f.read()
    except IOError as e:
        return [f"Cannot read file: {e}"]

    # Parse frontmatter
    frontmatter, body, parse_errors = parse_frontmatter(content)
    errors.extend(parse_errors)

    if not frontmatter:
        return errors  # Fatal error, can't continue

    # Validate frontmatter fields
    errors.extend(validate_frontmatter(frontmatter, filename))

    # Validate sections
    errors.extend(validate_sections(body))

    # Validate Failed Attempts table
    errors.extend(validate_failed_attempts_table(body))

    # Validate Quick Reference heading
    errors.extend(validate_quick_reference_heading(body))

    return errors


def main():
    """Main validation entry point."""
    plugins = find_plugins()

    if not plugins:
        print(f"{RED}No skill files found in {SKILLS_DIR}{RESET}")
        sys.exit(1)

    print(f"Validating {len(plugins)} skill files...\n")

    total_errors = 0
    valid_files = 0

    for plugin_file in plugins:
        filename = plugin_file.name
        errors = validate_plugin(filename)

        if errors:
            total_errors += len(errors)
            print(f"{RED}✗{RESET} {filename}")
            for error in errors:
                print(f"    {RED}•{RESET} {error}")
        else:
            valid_files += 1
            print(f"{GREEN}✓{RESET} {filename}")

    # Summary
    print(f"\n{'='*60}")
    print(f"Validation Summary:")
    print(f"  {GREEN}Valid{RESET}: {valid_files}/{len(plugins)}")
    if total_errors > 0:
        print(f"  {RED}Errors{RESET}: {total_errors}")
    print(f"{'='*60}")

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
