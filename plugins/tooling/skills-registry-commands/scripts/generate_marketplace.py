#!/usr/bin/env python3
"""
Generate marketplace.json from all plugins in the plugins directory.

Scans for plugin.json files and creates a searchable index.

Usage:
    python scripts/generate_marketplace.py
"""

import json
from pathlib import Path
from datetime import datetime, timezone


def generate_marketplace():
    plugins_dir = Path("plugins")
    plugins = []

    for plugin_json in sorted(plugins_dir.rglob("plugin.json")):
        with open(plugin_json) as f:
            plugin = json.load(f)

        # Extract category from path
        rel_path = plugin_json.relative_to(plugins_dir)
        category = rel_path.parts[0]

        plugins.append({
            "name": plugin["name"],
            "category": category,
            "description": plugin["description"],
            "tags": plugin.get("tags", []),
            "path": str(plugin_json.parent.parent),
            "date": plugin.get("date", ""),
            "version": plugin.get("version", "1.0.0")
        })

    marketplace = {
        "version": "1.0.0",
        "updated": datetime.now(timezone.utc).isoformat(),
        "plugin_count": len(plugins),
        "plugins": plugins
    }

    with open("marketplace.json", "w") as f:
        json.dump(marketplace, f, indent=2)

    print(f"Generated marketplace.json with {len(plugins)} plugins")


if __name__ == "__main__":
    generate_marketplace()
