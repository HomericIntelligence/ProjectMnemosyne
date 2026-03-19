#!/usr/bin/env python3
"""
Generate marketplace.json index from flat-format skill files.

Scans skills/*.md and generates a searchable index file.

Usage:
    python3 scripts/generate_marketplace.py [output_file]

    Defaults:
        output_file: .claude-plugin/marketplace.json
"""

import json
import sys
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional


def load_skill_metadata(skill_file: Path) -> Optional[Dict[str, Any]]:
    """Load metadata from a flat skill file's YAML frontmatter."""
    try:
        with open(skill_file, "r") as f:
            content = f.read()
    except IOError:
        return None

    # Extract YAML frontmatter
    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        frontmatter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None

    # Add path relative to repo root
    frontmatter["path"] = str(skill_file.relative_to(Path(".")))
    return frontmatter


def find_skills() -> List[Path]:
    """Find all flat skill files (skills/*.md, exclude *.notes.md)."""
    skills_dir = Path("skills")

    if not skills_dir.exists():
        return []

    files = sorted([
        f for f in skills_dir.glob("*.md")
        if not f.name.endswith(".notes.md") and f.is_file()
    ])
    return files


def generate_marketplace() -> Dict[str, Any]:
    """Generate marketplace index from flat skill files."""
    skills = find_skills()
    plugin_entries = []
    seen_names: set = set()

    for skill_file in skills:
        metadata = load_skill_metadata(skill_file)
        if not metadata:
            continue

        name = metadata.get("name", skill_file.stem)

        # Avoid duplicates
        if name in seen_names:
            continue
        seen_names.add(name)

        # Create marketplace entry
        entry = {
            "name": name,
            "description": metadata.get("description", ""),
            "version": metadata.get("version", "1.0.0"),
            "source": "./skills/" + skill_file.name,
            "category": metadata.get("category", "uncategorized"),
            "tags": metadata.get("tags", []),
        }

        plugin_entries.append(entry)

    # Sort by category then name
    plugin_entries.sort(key=lambda x: (x["category"], x["name"]))

    # Official marketplace format
    marketplace = {
        "name": "ProjectMnemosyne",
        "owner": {
            "name": "HomericIntelligence",
            "url": "https://github.com/HomericIntelligence"
        },
        "description": "Skills marketplace for the HomericIntelligence agentic ecosystem",
        "version": "1.0.0",
        "plugins": plugin_entries,
    }

    return marketplace


def main() -> int:
    """Main entry point.

    Usage: generate_marketplace.py [output_file]
    Defaults: output_file=.claude-plugin/marketplace.json
    """
    output_file_arg = sys.argv[1] if len(sys.argv) > 1 else ".claude-plugin/marketplace.json"
    output_file = Path(output_file_arg)

    marketplace = generate_marketplace()

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write output
    with open(output_file, "w") as f:
        json.dump(marketplace, f, indent=2)

    print(f"Generated {output_file}")
    print(f"  Skills indexed: {len(marketplace['plugins'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
