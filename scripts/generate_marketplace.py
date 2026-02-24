#!/usr/bin/env python3
"""
Generate marketplace.json index from all plugins/skills.

This script scans one or more directories and generates a searchable
index file at .claude-plugin/marketplace.json.

Usage:
    python3 scripts/generate_marketplace.py [output_file] [scan_dir ...]

    Defaults:
        output_file: .claude-plugin/marketplace.json
        scan_dirs: skills/ plugins/
"""

import json
import sys
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


def generate_marketplace(scan_dirs: List[Path], repo_root: Path) -> Dict[str, Any]:
    """Generate marketplace index from multiple scan directories."""
    plugin_entries = []
    seen_names: set = set()

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        plugins = find_plugins(scan_dir)
        for plugin_path in plugins:
            metadata = load_plugin_metadata(plugin_path)
            if metadata:
                name = metadata.get("name", plugin_path.name)
                # Avoid duplicates (skills/ wins over plugins/ if same name)
                if name in seen_names:
                    continue
                seen_names.add(name)
                # Create clean entry for index (official format uses 'source')
                entry = {
                    "name": name,
                    "description": metadata.get("description", ""),
                    "version": metadata.get("version", "1.0.0"),
                    "source": "./" + str(plugin_path.relative_to(repo_root)),
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
    """Main entry point.

    Usage: generate_marketplace.py [output_file] [scan_dir ...]
    Defaults: output=.claude-plugin/marketplace.json, scan_dirs=skills/ plugins/
    """
    args = sys.argv[1:]

    # First arg is output file if it ends with .json, else it's a scan dir
    if args and (args[0].endswith(".json") or args[0].startswith(".claude-plugin")):
        output_file_arg = args[0]
        scan_dir_args = args[1:] if len(args) > 1 else ["skills", "plugins"]
    else:
        output_file_arg = ".claude-plugin/marketplace.json"
        scan_dir_args = args if args else ["skills", "plugins"]

    output_file = Path(output_file_arg)
    repo_root = Path(".")
    scan_dirs = [Path(d) for d in scan_dir_args]

    existing = [d for d in scan_dirs if d.exists()]
    if not existing:
        print(f"No scan directories found: {scan_dir_args}")
        return 1

    marketplace = generate_marketplace(scan_dirs, repo_root)

    # Write output
    with open(output_file, "w") as f:
        json.dump(marketplace, f, indent=2)

    print(f"Generated {output_file}")
    print(f"  Plugins indexed: {len(marketplace['plugins'])}")
    print(f"  Scanned dirs: {[str(d) for d in existing]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
