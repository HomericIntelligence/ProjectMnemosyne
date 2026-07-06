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
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

# Use the canonical skill helpers instead of duplicating logic here.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mnemosyne_skill_utils import find_skill_files, parse_frontmatter  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_project_version() -> str:
    """Read the marketplace version from pyproject.toml.

    Falls back to "0.0.0" if pyproject.toml is missing or unreadable so
    the generator never hard-fails on environments without the file.
    """
    pyproject = REPO_ROOT / "pyproject.toml"
    try:
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        return str(data.get("project", {}).get("version", "0.0.0"))
    except (OSError, KeyError, ValueError):
        return "0.0.0"


def load_skill_metadata(skill_file: Path) -> Optional[Dict[str, Any]]:
    """Load metadata from a flat skill file's YAML frontmatter.

    Thin wrapper around mnemosyne_skill_utils.parse_frontmatter to keep call-sites
    in this module unchanged while reusing the canonical implementation.
    """
    try:
        with open(skill_file, "r") as f:
            content = f.read()
    except IOError:
        return None

    frontmatter, _body, errors = parse_frontmatter(content)
    if errors:
        return None

    # Add path relative to repo root
    frontmatter["path"] = str(skill_file.relative_to(Path(".")))
    return frontmatter


def generate_marketplace() -> Dict[str, Any]:
    """Generate marketplace index from flat skill files."""
    skills = find_skill_files()
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

    # Compute category statistics
    category_counts = dict(sorted(Counter(entry["category"] for entry in plugin_entries).items()))

    # Official marketplace format. Version is sourced from pyproject.toml
    # so the marketplace tracks the project's semver instead of a literal.
    marketplace = {
        "name": "ProjectMnemosyne",
        "owner": {"name": "HomericIntelligence", "url": "https://github.com/HomericIntelligence"},
        "description": "Skills marketplace for the HomericIntelligence agentic ecosystem",
        "version": _load_project_version(),
        "total_plugins": len(plugin_entries),
        "categories": category_counts,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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

    # Write output atomically: write to temp file in same directory, then os.replace().
    # Prevents leaving marketplace.json corrupt or truncated if the process is killed
    # mid-write (see #1458).
    import os
    import tempfile

    fd, tmp_path = tempfile.mkstemp(
        prefix=output_file.name + ".",
        suffix=".tmp",
        dir=str(output_file.parent),
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(marketplace, f, indent=2)
        os.replace(tmp_path, output_file)
    except Exception:
        # Best-effort cleanup of the temp file on failure.
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise

    print(f"Generated {output_file}")
    print(f"  Total skills: {marketplace['total_plugins']}")
    print(f"  Last updated: {marketplace['last_updated']}")
    print("  Categories:")
    for category, count in marketplace["categories"].items():
        print(f"    {category}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
