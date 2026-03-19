#!/usr/bin/env python3
"""
Migrate skills from nested format to flat format.

Converts:
  skills/<category>/<name>/
    ├── .claude-plugin/plugin.json
    ├── skills/<name>/SKILL.md
    └── references/notes.md

To:
  skills/<name>.md (with merged frontmatter)
  skills/<name>.notes.md (optional, if notes.md has content)
"""

import json
import os
import shutil
import sys
import yaml
from pathlib import Path
from typing import Dict, Optional, Set

SKILLS_DIR = Path("skills")
DRY_RUN = False


def find_skill_directories() -> list[Path]:
    """Find all skill directories (both nested and semi-flat formats)."""
    skill_dirs = []

    # Look for .claude-plugin/plugin.json to identify skill dirs
    for plugin_json in SKILLS_DIR.rglob(".claude-plugin/plugin.json"):
        skill_dir = plugin_json.parent.parent
        skill_dirs.append(skill_dir)

    return sorted(skill_dirs)


def read_plugin_json(skill_dir: Path) -> Optional[Dict]:
    """Read plugin.json from a skill directory."""
    plugin_path = skill_dir / ".claude-plugin" / "plugin.json"
    if not plugin_path.exists():
        return None

    with open(plugin_path, "r") as f:
        return json.load(f)


def read_skill_md(skill_dir: Path) -> Optional[tuple[str, Dict]]:
    """
    Read SKILL.md and extract frontmatter + content.
    Returns (content, frontmatter_dict) or (None, None) if not found.
    """
    # Try nested structure first
    skill_md_path = skill_dir / "skills" / skill_dir.name / "SKILL.md"
    if not skill_md_path.exists():
        # Try direct structure
        skill_md_path = skill_dir / "SKILL.md"

    if not skill_md_path.exists():
        return None, None

    with open(skill_md_path, "r") as f:
        content = f.read()

    # Extract YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].lstrip("\n")
                return body, frontmatter
            except yaml.YAMLError:
                pass

    return content, {}


def read_notes(skill_dir: Path) -> Optional[str]:
    """Read references/notes.md if it exists."""
    notes_path = skill_dir / "references" / "notes.md"
    if notes_path.exists():
        with open(notes_path, "r") as f:
            content = f.read().strip()
            if content:
                return content
    return None


def merge_metadata(plugin_json: Dict, skill_frontmatter: Dict) -> Dict:
    """Merge plugin.json and SKILL.md frontmatter into unified frontmatter."""
    # Start with skill frontmatter (has more fields)
    merged = skill_frontmatter.copy()

    # Layer in plugin.json fields, prioritizing skill_frontmatter
    if "name" not in merged and "name" in plugin_json:
        merged["name"] = plugin_json["name"]
    if "description" not in merged and "description" in plugin_json:
        merged["description"] = plugin_json["description"]
    if "category" not in merged and "category" in plugin_json:
        merged["category"] = plugin_json["category"]
    if "date" not in merged and "created" in plugin_json:
        merged["date"] = plugin_json["created"]
    if "version" not in merged and "version" in plugin_json:
        merged["version"] = plugin_json["version"]

    # Ensure required fields
    if "name" not in merged:
        merged["name"] = "unknown"
    if "description" not in merged:
        merged["description"] = ""
    if "category" not in merged:
        merged["category"] = "uncategorized"
    if "date" not in merged:
        merged["date"] = "2026-03-19"
    if "version" not in merged:
        merged["version"] = "1.0.0"

    # Add optional fields if present
    for key in ["tags", "user-invocable", "requires"]:
        if key in skill_frontmatter:
            merged[key] = skill_frontmatter[key]

    # Store metadata for reference (copy to comments)
    if "project" in plugin_json or "issue" in plugin_json or "pr" in plugin_json:
        merged["source_metadata"] = {k: v for k, v in plugin_json.items()
                                      if k in ["project", "issue", "pr", "outcome"]}

    return merged


def generate_flat_filename(skill_dir: Path, metadata: Dict, taken_names: Set[str]) -> str:
    """Generate filename for flat structure, handling collisions."""
    name = metadata.get("name", skill_dir.name)
    # Sanitize: lowercase, replace spaces and underscores with hyphens, remove special chars
    name = name.lower()
    name = name.replace(" ", "-").replace("_", "-")
    # Remove special characters except hyphens
    name = "".join(c if c.isalnum() or c == "-" else "" for c in name)
    # Collapse multiple hyphens
    while "--" in name:
        name = name.replace("--", "-")
    name = name.strip("-")

    # If collision, append category prefix
    base_filename = f"{name}.md"
    if base_filename in taken_names:
        category = metadata.get("category", "uncategorized")
        # Try category-prefixed version
        collision_filename = f"{category}-{name}.md"
        if collision_filename not in taken_names:
            return collision_filename
        # Last resort: add directory name
        collision_filename = f"{category}-{skill_dir.name}.md"
        return collision_filename

    return base_filename


def write_flat_skill(filename: str, metadata: Dict, body: str,
                      notes: Optional[str] = None) -> None:
    """Write skill to flat file format."""
    # Build frontmatter
    frontmatter_dict = {}
    field_order = ["name", "description", "category", "date", "version", "user-invocable", "tags"]

    for field in field_order:
        if field in metadata:
            frontmatter_dict[field] = metadata[field]

    # Add remaining fields in metadata order
    for key, value in metadata.items():
        if key not in field_order and key != "source_metadata":
            frontmatter_dict[key] = value

    # Convert to YAML
    frontmatter_yaml = yaml.dump(frontmatter_dict, default_flow_style=False, sort_keys=False)

    # Build complete file
    content = f"---\n{frontmatter_yaml}---\n{body}"

    skill_path = SKILLS_DIR / filename
    if DRY_RUN:
        print(f"[DRY-RUN] Would write: {skill_path}")
    else:
        with open(skill_path, "w") as f:
            f.write(content)
        print(f"Wrote: {skill_path}")

    # Write notes file if content exists
    if notes:
        notes_filename = filename.replace(".md", ".notes.md")
        notes_path = SKILLS_DIR / notes_filename
        if DRY_RUN:
            print(f"[DRY-RUN] Would write: {notes_path}")
        else:
            with open(notes_path, "w") as f:
                f.write(notes)
            print(f"Wrote: {notes_path}")


def delete_skill_directory(skill_dir: Path) -> None:
    """Delete old nested skill directory."""
    if DRY_RUN:
        print(f"[DRY-RUN] Would delete: {skill_dir}")
    else:
        shutil.rmtree(skill_dir)
        print(f"Deleted: {skill_dir}")


def check_for_collisions(skill_names: Set[str]) -> bool:
    """Check for filename collisions."""
    if len(skill_names) < len(set(skill_names)):
        print("ERROR: Filename collisions detected!")
        from collections import Counter
        counts = Counter(skill_names)
        for name, count in counts.items():
            if count > 1:
                print(f"  - {name}: {count} collisions")
        return False
    return True


def cleanup_empty_directories() -> None:
    """Remove empty category directories."""
    if DRY_RUN:
        print("[DRY-RUN] Would remove empty category directories")
        return

    # Walk bottom-up to remove empty dirs
    for root, dirs, files in os.walk(SKILLS_DIR, topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            try:
                # Only remove if empty
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    print(f"Removed empty directory: {dir_path}")
            except OSError:
                pass


def main():
    global DRY_RUN

    if len(sys.argv) > 1:
        if sys.argv[1] == "--dry-run":
            DRY_RUN = True
            print("Running in DRY-RUN mode (no files will be modified)\n")
        else:
            print(f"Usage: {sys.argv[0]} [--dry-run]")
            sys.exit(1)

    if not SKILLS_DIR.exists():
        print(f"ERROR: {SKILLS_DIR} directory not found")
        sys.exit(1)

    # Find all skill directories
    skill_dirs = find_skill_directories()
    print(f"Found {len(skill_dirs)} skill directories to migrate\n")

    if not skill_dirs:
        print("No skills to migrate")
        return

    migrated_names = set()
    success_count = 0
    error_count = 0

    # Process each skill
    for skill_dir in skill_dirs:
        try:
            print(f"Processing: {skill_dir.relative_to(SKILLS_DIR)}")

            # Read source files
            plugin_json = read_plugin_json(skill_dir)
            if not plugin_json:
                print(f"  WARNING: No plugin.json found, skipping")
                error_count += 1
                continue

            body, skill_frontmatter = read_skill_md(skill_dir)
            if body is None:
                print(f"  WARNING: No SKILL.md found, skipping")
                error_count += 1
                continue

            notes = read_notes(skill_dir)

            # Merge metadata
            merged_metadata = merge_metadata(plugin_json, skill_frontmatter)

            # Generate filename (pass migrated_names to handle collisions)
            filename = generate_flat_filename(skill_dir, merged_metadata, migrated_names)

            migrated_names.add(filename)

            # Write flat files
            write_flat_skill(filename, merged_metadata, body, notes)

            # Delete old directory
            delete_skill_directory(skill_dir)

            success_count += 1
            print(f"  ✓ Migrated to {filename}\n")

        except Exception as e:
            print(f"  ERROR: {e}\n")
            error_count += 1

    # Cleanup empty directories
    cleanup_empty_directories()

    # Summary
    print("\n" + "="*60)
    print(f"Migration Summary:")
    print(f"  Successful: {success_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total: {success_count + error_count}/{len(skill_dirs)}")
    print("="*60)

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
