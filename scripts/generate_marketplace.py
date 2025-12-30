#!/usr/bin/env python3
"""
Generate marketplace.json index from all plugins.

This script scans the plugins/ directory and generates a searchable
index file at .claude-plugin/marketplace.json.

Usage:
    python3 scripts/generate_marketplace.py [plugins_dir] [output_file]

    Defaults:
        plugins_dir: plugins/
        output_file: .claude-plugin/marketplace.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any


def load_plugin_metadata(plugin_dir: Path) -> Dict[str, Any] | None:
    """Load metadata from a plugin's plugin.json."""
    plugin_json_path = plugin_dir / ".claude-plugin" / "plugin.json"

    if not plugin_json_path.exists():
        return None

    try:
        with open(plugin_json_path) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return None

    # Get category from parent directory if not in plugin.json
    if "category" not in data:
        data["category"] = plugin_dir.parent.name

    # Add path to plugin
    data["path"] = str(plugin_dir)

    return data


def find_plugins(plugins_dir: Path) -> List[Path]:
    """Find all plugin directories."""
    plugins = []

    for category_dir in plugins_dir.iterdir():
        if not category_dir.is_dir():
            continue
        if category_dir.name.startswith("."):
            continue

        for plugin_dir in category_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            if plugin_dir.name.startswith("."):
                continue

            # Check if it has plugin structure
            if (plugin_dir / ".claude-plugin" / "plugin.json").exists():
                plugins.append(plugin_dir)

    return plugins


def generate_marketplace(plugins_dir: Path) -> Dict[str, Any]:
    """Generate marketplace index."""
    plugins = find_plugins(plugins_dir)

    plugin_entries = []
    for plugin_path in plugins:
        metadata = load_plugin_metadata(plugin_path)
        if metadata:
            # Create clean entry for index (official format uses 'source')
            entry = {
                "name": metadata.get("name", plugin_path.name),
                "description": metadata.get("description", ""),
                "version": metadata.get("version", "1.0.0"),
                "source": "./" + str(plugin_path.relative_to(plugins_dir.parent)),
                "category": metadata.get("category", "unknown"),
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
    """Main entry point."""
    plugins_dir_arg = sys.argv[1] if len(sys.argv) > 1 else "plugins"
    output_file_arg = sys.argv[2] if len(sys.argv) > 2 else ".claude-plugin/marketplace.json"

    plugins_dir = Path(plugins_dir_arg)
    output_file = Path(output_file_arg)

    if not plugins_dir.exists():
        print(f"Plugins directory not found: {plugins_dir}")
        return 1

    marketplace = generate_marketplace(plugins_dir)

    # Write output
    with open(output_file, "w") as f:
        json.dump(marketplace, f, indent=2)

    print(f"Generated {output_file}")
    print(f"  Plugins indexed: {len(marketplace['plugins'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
