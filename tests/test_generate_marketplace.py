#!/usr/bin/env python3
"""
Tests for marketplace statistics in generate_marketplace.py.

Verifies that:
- total_plugins count matches the number of plugin entries
- categories dict has correct per-category counts
- last_updated is a valid ISO 8601 timestamp
- stdout summary is printed during generation
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_marketplace import generate_marketplace, main


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_skill_file(tmp_path: Path, name: str, category: str) -> Path:
    """Create a minimal skill .md file with YAML frontmatter."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(exist_ok=True)
    skill_file = skills_dir / f"{name}.md"
    skill_file.write_text(
        f"---\n"
        f"name: {name}\n"
        f"description: \"Test skill {name}\"\n"
        f"category: {category}\n"
        f"date: 2026-01-01\n"
        f"version: \"1.0.0\"\n"
        f"user-invocable: false\n"
        f"---\n"
        f"# {name}\n"
    )
    return skill_file


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMarketplaceStatistics:
    """Tests for total_plugins, categories, and last_updated fields."""

    def test_total_plugins_matches_entries(self, tmp_path, monkeypatch):
        """total_plugins should equal len(plugins)."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")
        _make_skill_file(tmp_path, "skill-b", "debugging")
        _make_skill_file(tmp_path, "skill-c", "training")

        result = generate_marketplace()

        assert result["total_plugins"] == 3
        assert result["total_plugins"] == len(result["plugins"])

    def test_category_counts_correct(self, tmp_path, monkeypatch):
        """categories dict should have correct per-category counts."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")
        _make_skill_file(tmp_path, "skill-b", "debugging")
        _make_skill_file(tmp_path, "skill-c", "training")
        _make_skill_file(tmp_path, "skill-d", "tooling")

        result = generate_marketplace()

        assert result["categories"] == {
            "debugging": 1,
            "tooling": 1,
            "training": 2,
        }

    def test_categories_sorted_alphabetically(self, tmp_path, monkeypatch):
        """categories keys should be sorted alphabetically."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-z", "tooling")
        _make_skill_file(tmp_path, "skill-a", "architecture")
        _make_skill_file(tmp_path, "skill-m", "debugging")

        result = generate_marketplace()
        keys = list(result["categories"].keys())

        assert keys == sorted(keys)

    def test_last_updated_is_valid_iso8601(self, tmp_path, monkeypatch):
        """last_updated should be a valid ISO 8601 UTC timestamp."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")

        result = generate_marketplace()

        ts = result["last_updated"]
        assert ts.endswith("Z")
        # Should parse without error
        parsed = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        assert parsed.year >= 2026

    def test_empty_skills_directory(self, tmp_path, monkeypatch):
        """Empty skills dir should produce zero counts."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "skills").mkdir()

        result = generate_marketplace()

        assert result["total_plugins"] == 0
        assert result["categories"] == {}
        assert "last_updated" in result

    def test_no_skills_directory(self, tmp_path, monkeypatch):
        """Missing skills dir should produce zero counts."""
        monkeypatch.chdir(tmp_path)

        result = generate_marketplace()

        assert result["total_plugins"] == 0
        assert result["categories"] == {}

    def test_notes_files_excluded(self, tmp_path, monkeypatch):
        """*.notes.md files should not be counted."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")
        # Create a notes file that should be excluded
        notes = tmp_path / "skills" / "skill-a.notes.md"
        notes.write_text("---\nname: skill-a-notes\ncategory: training\n---\n# Notes\n")

        result = generate_marketplace()

        assert result["total_plugins"] == 1


class TestMainSummaryOutput:
    """Tests for stdout summary printed by main()."""

    def test_main_prints_summary(self, tmp_path, monkeypatch, capsys):
        """main() should print total, timestamp, and category breakdown."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")
        _make_skill_file(tmp_path, "skill-b", "debugging")

        output_file = str(tmp_path / "marketplace.json")
        monkeypatch.setattr("sys.argv", ["generate_marketplace.py", output_file])

        ret = main()
        captured = capsys.readouterr()

        assert ret == 0
        assert "Total skills: 2" in captured.out
        assert "Last updated:" in captured.out
        assert "training: 1" in captured.out
        assert "debugging: 1" in captured.out

    def test_main_writes_statistics_to_json(self, tmp_path, monkeypatch):
        """main() should write total_plugins and categories to the JSON file."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "tooling")
        _make_skill_file(tmp_path, "skill-b", "tooling")

        output_file = tmp_path / "marketplace.json"
        monkeypatch.setattr("sys.argv", ["generate_marketplace.py", str(output_file)])

        main()

        data = json.loads(output_file.read_text())
        assert data["total_plugins"] == 2
        assert data["categories"] == {"tooling": 2}
        assert "last_updated" in data
