#!/usr/bin/env python3
"""
Fix common skill validation issues - Version 2:
1. Fix duplicate category replacements (ci-cd-cd-cd, etc.)
2. Replace invalid categories with valid ones
3. Fix Failed Attempts tables
4. Ensure all required sections exist
"""

import re
import sys
from pathlib import Path

SKILLS_DIR = Path("skills")

# Map invalid categories to valid ones
CATEGORY_MAPPING = {
    "agent": "architecture",
    "analysis": "evaluation",
    "automation": "tooling",
    "ci": "ci-cd",
    "mojo": "optimization",
    "refactoring": "architecture",
    "uncategorized": "tooling",
}

VALID_CATEGORIES = {
    "training", "evaluation", "optimization", "debugging",
    "architecture", "tooling", "ci-cd", "testing", "documentation"
}


def read_skill_file(skill_path: Path) -> str:
    """Read skill file content."""
    with open(skill_path, "r") as f:
        return f.read()


def write_skill_file(skill_path: Path, content: str) -> None:
    """Write skill file content."""
    with open(skill_path, "w") as f:
        f.write(content)


def fix_category(content: str) -> tuple[str, bool]:
    """Replace invalid categories, including deduped ones."""
    changed = False

    # Extract category from frontmatter (match first occurrence)
    match = re.search(r"^category:\s*(.+?)$", content, re.MULTILINE)
    if not match:
        return content, changed

    old_category = match.group(1).strip()

    # Check for malformed categories (ci-cd-cd-cd, etc.)
    if old_category.startswith("ci-cd"):
        # Fix: change ci-cd-cd-cd to ci-cd
        new_category = "ci-cd"
        print(f"  Fixing malformed category: {old_category} → {new_category}")
        content = re.sub(
            r"^category:\s*.+?$",
            f"category: {new_category}",
            content,
            count=1,
            flags=re.MULTILINE
        )
        changed = True
    elif old_category in CATEGORY_MAPPING:
        new_category = CATEGORY_MAPPING[old_category]
        print(f"  Fixing category: {old_category} → {new_category}")
        content = re.sub(
            r"^category:\s*.+?$",
            f"category: {new_category}",
            content,
            count=1,
            flags=re.MULTILINE
        )
        changed = True
    elif old_category not in VALID_CATEGORIES:
        # Unknown invalid category - map to tooling
        print(f"  Fixing unknown category: {old_category} → tooling")
        content = re.sub(
            r"^category:\s*.+?$",
            "category: tooling",
            content,
            count=1,
            flags=re.MULTILINE
        )
        changed = True

    return content, changed


def fix_failed_attempts_table(content: str) -> tuple[str, bool]:
    """Fix Failed Attempts section - ensure it has proper table structure."""
    changed = False

    # Find Failed Attempts section
    match = re.search(
        r"## Failed Attempts\s*\n(.*?)(?:\n## |\Z)",
        content,
        re.DOTALL
    )

    if not match:
        return content, changed

    section_content = match.group(1).strip()

    # If it's already a table, check columns
    if "|" in section_content:
        lines = section_content.split("\n")
        if len(lines) >= 2:
            header = lines[0]
            # Check if it has all required columns
            required_cols = ["Attempt", "What Was Tried", "Why It Failed", "Lesson Learned"]
            has_all_cols = all(col in header for col in required_cols)

            if has_all_cols:
                return content, changed

            # Missing columns - rebuild table
            print(f"  Fixing Failed Attempts table structure")
            new_section = """## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
"""
            # Replace the section
            content = re.sub(
                r"## Failed Attempts\s*\n.*?(?=\n## |\Z)",
                new_section.rstrip(),
                content,
                flags=re.DOTALL
            )
            changed = True
    else:
        # Not a table - convert to table
        print(f"  Converting Failed Attempts to table format")
        new_section = """## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
"""
        # Replace the section
        content = re.sub(
            r"## Failed Attempts\s*\n.*?(?=\n## |\Z)",
            new_section.rstrip(),
            content,
            flags=re.DOTALL
        )
        changed = True

    return content, changed


def ensure_required_sections(content: str) -> tuple[str, bool]:
    """Ensure all required sections exist."""
    changed = False

    required_sections = [
        ("## Overview", """## Overview

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Objective** | Skill objective |
| **Outcome** | Success/Operational |
"""),
        ("## When to Use", """## When to Use

- Use condition 1
- Use condition 2
"""),
        ("## Verified Workflow", """## Verified Workflow

Steps that worked:
1. Step 1
2. Step 2
"""),
        ("## Results & Parameters", """## Results & Parameters

Copy-paste ready configurations and expected outputs.
"""),
    ]

    for section_marker, section_template in required_sections:
        if section_marker not in content:
            print(f"  Adding missing section: {section_marker}")
            # Find where to insert (before ## Failed Attempts or at end)
            if "## Failed Attempts" in content:
                idx = content.find("## Failed Attempts")
                content = content[:idx] + section_template + "\n" + content[idx:]
            else:
                content = content.rstrip() + "\n\n" + section_template
            changed = True

    return content, changed


def main():
    """Fix all skill files."""
    skill_files = sorted([
        f for f in SKILLS_DIR.glob("*.md")
        if not f.name.endswith(".notes.md")
    ])

    print(f"Processing {len(skill_files)} skill files...\n")

    fixed_count = 0
    error_count = 0

    for skill_file in skill_files:
        try:
            skill_name = skill_file.stem
            content = read_skill_file(skill_file)
            file_changed = False

            # Fix categories (including malformed ones)
            content, changed = fix_category(content)
            file_changed = file_changed or changed

            # Fix Failed Attempts table
            content, changed = fix_failed_attempts_table(content)
            file_changed = file_changed or changed

            # Ensure required sections
            content, changed = ensure_required_sections(content)
            file_changed = file_changed or changed

            # Write if changed
            if file_changed:
                write_skill_file(skill_file, content)
                print(f"✓ Fixed: {skill_name}")
                fixed_count += 1

        except Exception as e:
            print(f"✗ Error processing {skill_name}: {e}")
            error_count += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Fix Summary:")
    print(f"  Fixed: {fixed_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total: {fixed_count + error_count}/{len(skill_files)}")
    print(f"{'='*60}")

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
