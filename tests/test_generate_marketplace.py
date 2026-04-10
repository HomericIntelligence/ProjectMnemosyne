#!/usr/bin/env python3
"""
Tests for marketplace statistics and integrity in generate_marketplace.py.

Verifies that:
- total_plugins count matches the number of plugin entries
- categories dict has correct per-category counts
- last_updated is a valid ISO 8601 timestamp
- stdout summary is printed during generation
- Schema validation (required top-level and plugin fields)
- No duplicate plugin names or source paths
- Source paths resolve to existing files and match expected pattern
- Category validation against allowed set
- Date format is valid ISO 8601
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

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
        f'description: "Test skill {name}"\n'
        f"category: {category}\n"
        f"date: 2026-01-01\n"
        f'version: "1.0.0"\n'
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


ALLOWED_CATEGORIES = {
    "training",
    "evaluation",
    "optimization",
    "debugging",
    "architecture",
    "tooling",
    "ci-cd",
    "testing",
    "documentation",
}

REQUIRED_TOP_LEVEL_FIELDS = {
    "name",
    "owner",
    "description",
    "version",
    "total_plugins",
    "categories",
    "last_updated",
    "plugins",
}

REQUIRED_PLUGIN_FIELDS = {"name", "description", "version", "source", "category"}


class TestSchemaValidation:
    """Tests that marketplace output conforms to the expected schema."""

    def test_required_top_level_fields_present(self, tmp_path, monkeypatch):
        """Marketplace JSON must contain all required top-level fields."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")

        result = generate_marketplace()

        missing = REQUIRED_TOP_LEVEL_FIELDS - set(result.keys())
        assert not missing, f"Missing top-level fields: {missing}"

    def test_each_plugin_has_required_fields(self, tmp_path, monkeypatch):
        """Every plugin entry must contain all required fields."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")
        _make_skill_file(tmp_path, "skill-b", "debugging")

        result = generate_marketplace()

        for plugin in result["plugins"]:
            missing = REQUIRED_PLUGIN_FIELDS - set(plugin.keys())
            assert not missing, f"Plugin '{plugin.get('name', '?')}' missing fields: {missing}"

    def test_total_plugins_matches_plugins_length(self, tmp_path, monkeypatch):
        """total_plugins must equal len(plugins)."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")
        _make_skill_file(tmp_path, "skill-b", "debugging")
        _make_skill_file(tmp_path, "skill-c", "tooling")

        result = generate_marketplace()

        assert result["total_plugins"] == len(result["plugins"])

    def test_empty_marketplace_has_required_fields(self, tmp_path, monkeypatch):
        """Even an empty marketplace must have all required top-level fields."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "skills").mkdir()

        result = generate_marketplace()

        missing = REQUIRED_TOP_LEVEL_FIELDS - set(result.keys())
        assert not missing, f"Missing top-level fields: {missing}"
        assert result["total_plugins"] == 0
        assert result["plugins"] == []


class TestDeduplication:
    """Tests that no duplicate plugin names or source paths exist."""

    def test_no_duplicate_plugin_names(self, tmp_path, monkeypatch):
        """Plugin names must be unique."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")
        _make_skill_file(tmp_path, "skill-b", "debugging")
        _make_skill_file(tmp_path, "skill-c", "tooling")

        result = generate_marketplace()

        names = [p["name"] for p in result["plugins"]]
        assert len(names) == len(set(names)), (
            f"Duplicate plugin names found: {[n for n in names if names.count(n) > 1]}"
        )

    def test_no_duplicate_source_paths(self, tmp_path, monkeypatch):
        """Source paths must be unique."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")
        _make_skill_file(tmp_path, "skill-b", "debugging")

        result = generate_marketplace()

        sources = [p["source"] for p in result["plugins"]]
        assert len(sources) == len(set(sources)), (
            f"Duplicate source paths found: {[s for s in sources if sources.count(s) > 1]}"
        )

    def test_duplicate_name_in_frontmatter_is_deduplicated(self, tmp_path, monkeypatch):
        """If two files declare the same name, only one should appear."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(exist_ok=True)

        # Two files with the same frontmatter name
        (skills_dir / "file-one.md").write_text(
            "---\nname: duplicate-name\ndescription: first\n"
            "category: training\ndate: 2026-01-01\nversion: '1.0.0'\n---\n"
        )
        (skills_dir / "file-two.md").write_text(
            "---\nname: duplicate-name\ndescription: second\n"
            "category: debugging\ndate: 2026-01-01\nversion: '1.0.0'\n---\n"
        )

        result = generate_marketplace()

        names = [p["name"] for p in result["plugins"]]
        assert names.count("duplicate-name") == 1


class TestPathResolution:
    """Tests that source paths are valid and follow the expected pattern."""

    def test_source_paths_point_to_existing_files(self, tmp_path, monkeypatch):
        """Every source path must resolve to an existing file."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")
        _make_skill_file(tmp_path, "skill-b", "debugging")

        result = generate_marketplace()

        for plugin in result["plugins"]:
            source = plugin["source"]
            resolved = tmp_path / source.lstrip("./")
            assert resolved.exists(), (
                f"Source path '{source}' does not resolve to an existing file (checked {resolved})"
            )

    def test_source_paths_match_skills_pattern(self, tmp_path, monkeypatch):
        """Source paths must match ./skills/<name>.md pattern."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")
        _make_skill_file(tmp_path, "skill-b", "debugging")

        result = generate_marketplace()

        pattern = re.compile(r"^\./skills/[a-z0-9][a-z0-9\-]*\.md$")
        for plugin in result["plugins"]:
            source = plugin["source"]
            assert pattern.match(source), f"Source path '{source}' does not match expected pattern ./skills/<name>.md"


class TestCategoryValidation:
    """Tests that categories are valid and counts are accurate."""

    def test_all_categories_in_allowed_set(self, tmp_path, monkeypatch):
        """Every plugin category must be in the allowed categories set."""
        monkeypatch.chdir(tmp_path)
        for cat in ["training", "debugging", "tooling", "evaluation"]:
            _make_skill_file(tmp_path, f"skill-{cat}", cat)

        result = generate_marketplace()

        for plugin in result["plugins"]:
            assert plugin["category"] in ALLOWED_CATEGORIES, (
                f"Plugin '{plugin['name']}' has invalid category '{plugin['category']}'"
            )

    def test_category_counts_match_actual_plugin_counts(self, tmp_path, monkeypatch):
        """Category counts dict must match actual per-category plugin counts."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")
        _make_skill_file(tmp_path, "skill-b", "training")
        _make_skill_file(tmp_path, "skill-c", "debugging")
        _make_skill_file(tmp_path, "skill-d", "tooling")

        result = generate_marketplace()

        # Count categories from plugin entries
        actual_counts: dict[str, int] = {}
        for plugin in result["plugins"]:
            cat = plugin["category"]
            actual_counts[cat] = actual_counts.get(cat, 0) + 1

        assert result["categories"] == actual_counts

    def test_categories_dict_has_no_extra_keys(self, tmp_path, monkeypatch):
        """categories dict must not contain categories absent from plugins."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")

        result = generate_marketplace()

        plugin_categories = {p["category"] for p in result["plugins"]}
        extra = set(result["categories"].keys()) - plugin_categories
        assert not extra, f"Extra categories in counts dict: {extra}"


class TestDateFormat:
    """Tests that date fields are valid ISO 8601."""

    def test_last_updated_is_valid_iso8601(self, tmp_path, monkeypatch):
        """last_updated must be a valid ISO 8601 UTC timestamp ending in Z."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")

        result = generate_marketplace()

        ts = result["last_updated"]
        assert ts.endswith("Z"), f"Timestamp '{ts}' does not end with Z"
        # Must parse without error
        parsed = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        assert parsed.year >= 2026

    def test_last_updated_matches_iso8601_regex(self, tmp_path, monkeypatch):
        """last_updated must match the YYYY-MM-DDTHH:MM:SSZ pattern."""
        monkeypatch.chdir(tmp_path)
        _make_skill_file(tmp_path, "skill-a", "training")

        result = generate_marketplace()

        pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        assert pattern.match(result["last_updated"]), (
            f"Timestamp '{result['last_updated']}' does not match ISO 8601 pattern"
        )


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
