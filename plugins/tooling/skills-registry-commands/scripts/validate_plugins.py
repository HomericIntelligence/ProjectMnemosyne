#!/usr/bin/env python3
"""
Validate plugin.json files in the plugins directory.

Checks:
- Required fields present (name, version, description)
- Description has minimum length
- Description includes trigger conditions ("Use when:")

Usage:
    python scripts/validate_plugins.py
"""

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = ["name", "version", "description"]
MIN_DESCRIPTION_LENGTH = 20


def validate_plugin(plugin_path: Path) -> list[str]:
    """Validate a plugin.json file."""
    errors = []

    try:
        with open(plugin_path) as f:
            plugin = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in plugin:
            errors.append(f"Missing required field: {field}")

    # Check description quality
    desc = plugin.get("description", "")
    if len(desc) < MIN_DESCRIPTION_LENGTH:
        errors.append(f"Description too short ({len(desc)} chars, min {MIN_DESCRIPTION_LENGTH})")

    if "Use when:" not in desc:
        errors.append("Description should include 'Use when:' trigger conditions")

    return errors


def main():
    plugins_dir = Path("plugins")
    all_errors = {}

    for plugin_json in plugins_dir.rglob("plugin.json"):
        errors = validate_plugin(plugin_json)
        if errors:
            all_errors[str(plugin_json)] = errors

    if all_errors:
        print("Validation errors found:")
        for path, errors in all_errors.items():
            print(f"\n{path}:")
            for error in errors:
                print(f"  - {error}")
        sys.exit(1)

    print("All plugins valid!")


if __name__ == "__main__":
    main()
