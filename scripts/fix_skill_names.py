#!/usr/bin/env python3
"""
Fix skill names to be kebab-case (lowercase, hyphens, no spaces).
Reads frontmatter, converts name field to kebab-case, and updates file.
"""

import re
import yaml
from pathlib import Path
from typing import Tuple

SKILLS_DIR = Path("skills")


def kebab_case(text: str) -> str:
    """Convert text to kebab-case."""
    # Convert to lowercase
    text = text.lower()
    # Replace spaces, underscores, slashes with hyphens
    text = re.sub(r'[\s_/]+', '-', text)
    # Remove special characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Collapse multiple hyphens
    while '--' in text:
        text = text.replace('--', '-')
    # Strip leading/trailing hyphens
    text = text.strip('-')
    return text


def read_skill_file(skill_path: Path) -> Tuple[str, str, str]:
    """Read skill file and extract frontmatter, body."""
    with open(skill_path, 'r') as f:
        content = f.read()

    # Find frontmatter boundaries
    if not content.startswith('---'):
        return '', '', content

    parts = content.split('---', 2)
    if len(parts) < 3:
        return '', '', content

    frontmatter_text = parts[1]
    body = parts[2]

    return frontmatter_text, body, content


def write_skill_file(skill_path: Path, frontmatter_text: str, body: str) -> None:
    """Write skill file with updated frontmatter."""
    content = f"---\n{frontmatter_text}---{body}"
    with open(skill_path, 'w') as f:
        f.write(content)


def fix_skill_names():
    """Fix all skill names to kebab-case."""
    skill_files = sorted([
        f for f in SKILLS_DIR.glob("*.md")
        if not f.name.endswith(".notes.md") and f.is_file()
    ])

    fixed_count = 0
    error_count = 0

    for skill_file in skill_files:
        try:
            frontmatter_text, body, original_content = read_skill_file(skill_file)

            if not frontmatter_text:
                continue

            # Parse YAML frontmatter
            frontmatter = yaml.safe_load(frontmatter_text)
            if not frontmatter:
                continue

            # Check if name needs fixing
            old_name = frontmatter.get('name', '')
            if not old_name:
                continue

            new_name = kebab_case(old_name)

            if old_name != new_name:
                print(f"  Fixing: '{old_name}' → '{new_name}'")
                frontmatter['name'] = new_name

                # Reconstruct frontmatter YAML preserving order
                field_order = ["name", "description", "category", "date", "version", "user-invocable", "tags"]

                ordered_lines = []
                for field in field_order:
                    if field in frontmatter:
                        value = frontmatter[field]
                        # Format value appropriately
                        if isinstance(value, str):
                            # Quote strings that contain special chars
                            if any(c in value for c in [':', '#', '\n', '"']):
                                value = repr(value)
                            ordered_lines.append(f"{field}: {value}")
                        elif isinstance(value, bool):
                            ordered_lines.append(f"{field}: {str(value).lower()}")
                        elif value is None:
                            ordered_lines.append(f"{field}: null")
                        else:
                            ordered_lines.append(f"{field}: {value}")

                # Add remaining fields
                for key, value in frontmatter.items():
                    if key not in field_order:
                        if isinstance(value, str):
                            if any(c in value for c in [':', '#', '\n', '"']):
                                value = repr(value)
                            ordered_lines.append(f"{key}: {value}")
                        elif isinstance(value, bool):
                            ordered_lines.append(f"{key}: {str(value).lower()}")
                        elif isinstance(value, list):
                            ordered_lines.append(f"{key}: {value}")
                        else:
                            ordered_lines.append(f"{key}: {value}")

                new_frontmatter_text = '\n'.join(ordered_lines) + '\n'
                write_skill_file(skill_file, new_frontmatter_text, body)
                fixed_count += 1

        except Exception as e:
            print(f"✗ Error processing {skill_file.name}: {e}")
            error_count += 1

    print(f"\n{'='*60}")
    print(f"Fixed: {fixed_count}")
    print(f"Errors: {error_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    print("Fixing skill names to kebab-case...\n")
    fix_skill_names()
