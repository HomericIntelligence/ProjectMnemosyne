#!/usr/bin/env python3
"""
Tests for JSON Schema validation of skill frontmatter.

Uses the ``jsonschema`` library when available; falls back to manual
structural checks so the test suite still passes without the extra
dependency.
"""

import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = ROOT / "schemas"

VALID_CATEGORIES = {
    "architecture",
    "ci-cd",
    "debugging",
    "documentation",
    "evaluation",
    "optimization",
    "testing",
    "tooling",
    "training",
}

try:
    from jsonschema import ValidationError, validate  # type: ignore[import-untyped]

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())  # type: ignore[no-any-return]


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
        assert set(self.schema["required"]) == {"name", "description", "category", "date", "version"}

    def test_schema_category_enum(self):
        """Structural check: category enum matches project categories."""
        assert set(self.schema["properties"]["category"]["enum"]) == VALID_CATEGORIES
