#!/usr/bin/env python3
"""
Tests for JSON Schema validation of marketplace.json and skill frontmatter.

Uses the ``jsonschema`` library when available; falls back to manual
structural checks so the test suite still passes without the extra
dependency.
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = ROOT / "schemas"
MARKETPLACE_PATH = ROOT / ".claude-plugin" / "marketplace.json"

VALID_CATEGORIES = {
    "architecture", "ci-cd", "debugging", "documentation",
    "evaluation", "optimization", "testing", "tooling", "training",
}

try:
    from jsonschema import validate, ValidationError  # type: ignore[import-untyped]
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Marketplace schema tests
# ---------------------------------------------------------------------------

class TestMarketplaceSchema:
    """Validate marketplace.json against its JSON Schema."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.marketplace = _load_json(MARKETPLACE_PATH)
        self.schema = _load_json(SCHEMAS_DIR / "marketplace.schema.json")

    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_marketplace_validates_against_schema(self):
        """Full JSON Schema validation using the jsonschema library."""
        validate(instance=self.marketplace, schema=self.schema)

    # -- Manual structural checks (always run) --

    def test_top_level_required_fields(self):
        for field in ("name", "owner", "description", "version",
                      "total_plugins", "categories", "last_updated", "plugins"):
            assert field in self.marketplace, f"Missing top-level field: {field}"

    def test_owner_structure(self):
        owner = self.marketplace["owner"]
        assert isinstance(owner, dict)
        assert "name" in owner and isinstance(owner["name"], str)
        assert "url" in owner and isinstance(owner["url"], str)

    def test_total_plugins_is_integer(self):
        assert isinstance(self.marketplace["total_plugins"], int)

    def test_categories_are_valid(self):
        for cat in self.marketplace["categories"]:
            assert cat in VALID_CATEGORIES, f"Unknown category: {cat}"

    def test_plugins_is_list(self):
        assert isinstance(self.marketplace["plugins"], list)
        assert len(self.marketplace["plugins"]) > 0

    def test_plugin_entry_structure(self):
        """Spot-check the first plugin entry for required fields."""
        plugin = self.marketplace["plugins"][0]
        for field in ("name", "description", "version", "source", "category", "tags"):
            assert field in plugin, f"Plugin missing field: {field}"
        assert plugin["category"] in VALID_CATEGORIES
        assert isinstance(plugin["tags"], list)

    def test_all_plugin_categories_valid(self):
        for plugin in self.marketplace["plugins"]:
            assert plugin["category"] in VALID_CATEGORIES, (
                f"Plugin '{plugin.get('name')}' has invalid category: {plugin['category']}"
            )


# ---------------------------------------------------------------------------
# Skill frontmatter schema tests
# ---------------------------------------------------------------------------

class TestSkillFrontmatterSchema:
    """Validate the skill-frontmatter schema against sample data."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.schema = _load_json(SCHEMAS_DIR / "skill-frontmatter.schema.json")

    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_valid_frontmatter_passes(self):
        sample = {
            "name": "my-test-skill",
            "description": "A test skill.",
            "category": "tooling",
            "date": "2026-01-15",
            "version": "1.0.0",
        }
        validate(instance=sample, schema=self.schema)

    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_invalid_category_fails(self):
        sample = {
            "name": "bad-cat",
            "description": "Bad category.",
            "category": "invalid-category",
            "date": "2026-01-15",
            "version": "1.0.0",
        }
        with pytest.raises(ValidationError):
            validate(instance=sample, schema=self.schema)

    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_missing_required_field_fails(self):
        sample = {
            "name": "no-version",
            "description": "Missing version.",
            "category": "tooling",
            "date": "2026-01-15",
        }
        with pytest.raises(ValidationError):
            validate(instance=sample, schema=self.schema)

    def test_schema_has_required_fields(self):
        """Structural check: schema defines the expected required fields."""
        assert set(self.schema["required"]) == {
            "name", "description", "category", "date", "version"
        }

    def test_schema_category_enum(self):
        """Structural check: category enum matches project categories."""
        assert set(self.schema["properties"]["category"]["enum"]) == VALID_CATEGORIES
