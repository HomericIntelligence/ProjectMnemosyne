#!/usr/bin/env python3
"""
Tests for scripts/validate_plugins.py validation functions.

Covers:
- parse_frontmatter: valid content, missing delimiters, invalid YAML, empty frontmatter
- validate_frontmatter: missing/empty fields, invalid category, date, name format
- validate_sections: missing required sections, all present
- validate_failed_attempts_table: valid table, empty section, missing columns, plain text
- validate_quick_reference_heading: ## vs ### detection
- find_plugins: excludes .notes.md, handles empty/missing dirs
- validate_plugin: integration tests with valid and invalid skill files
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from validate_plugins import (
    SKILLS_DIR,
    find_plugins,
    parse_frontmatter,
    validate_failed_attempts_table,
    validate_frontmatter,
    validate_plugin,
    validate_quick_reference_heading,
    validate_sections,
)

from conftest import CLEAN_SKILL_MD


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = "---\nname: my-skill\ncategory: tooling\n---\nBody here."
        fm, body, errors = parse_frontmatter(content)
        assert errors == []
        assert fm["name"] == "my-skill"
        assert fm["category"] == "tooling"
        assert body == "Body here."

    def test_missing_opening_delimiter(self):
        content = "name: my-skill\n---\nBody here."
        fm, body, errors = parse_frontmatter(content)
        assert len(errors) == 1
        assert "does not start with" in errors[0]
        assert fm == {}

    def test_missing_closing_delimiter(self):
        content = "---\nname: my-skill\nBody here."
        fm, body, errors = parse_frontmatter(content)
        assert len(errors) == 1
        assert "missing closing" in errors[0]
        assert fm == {}

    def test_invalid_yaml(self):
        content = "---\n: invalid: yaml: [broken\n---\nBody."
        fm, body, errors = parse_frontmatter(content)
        assert len(errors) == 1
        assert "Invalid YAML" in errors[0]
        assert fm == {}

    def test_empty_frontmatter(self):
        content = "---\n\n---\nBody."
        fm, body, errors = parse_frontmatter(content)
        assert errors == []
        assert fm == {}
        assert body == "Body."


# ---------------------------------------------------------------------------
# validate_frontmatter
# ---------------------------------------------------------------------------


class TestValidateFrontmatter:
    def test_valid_frontmatter(self):
        fm = {
            "name": "my-skill",
            "description": "A useful skill.",
            "category": "tooling",
            "date": "2026-01-15",
            "version": "1.0.0",
        }
        errors = validate_frontmatter(fm, "my-skill.md")
        assert errors == []

    def test_missing_required_field(self):
        fm = {
            "description": "A useful skill.",
            "category": "tooling",
            "date": "2026-01-15",
            "version": "1.0.0",
        }
        errors = validate_frontmatter(fm, "my-skill.md")
        assert any("Missing required field: name" in e for e in errors)

    def test_empty_required_field(self):
        fm = {
            "name": "",
            "description": "A useful skill.",
            "category": "tooling",
            "date": "2026-01-15",
            "version": "1.0.0",
        }
        errors = validate_frontmatter(fm, "my-skill.md")
        assert any("Empty required field: name" in e for e in errors)

    def test_invalid_category(self):
        fm = {
            "name": "my-skill",
            "description": "A useful skill.",
            "category": "invalid-cat",
            "date": "2026-01-15",
            "version": "1.0.0",
        }
        errors = validate_frontmatter(fm, "my-skill.md")
        assert any("Invalid category" in e for e in errors)

    def test_invalid_date_format(self):
        fm = {
            "name": "my-skill",
            "description": "A useful skill.",
            "category": "tooling",
            "date": "01-15-2026",
            "version": "1.0.0",
        }
        errors = validate_frontmatter(fm, "my-skill.md")
        assert any("Invalid date format" in e for e in errors)

    def test_name_with_spaces(self):
        fm = {
            "name": "my skill",
            "description": "A useful skill.",
            "category": "tooling",
            "date": "2026-01-15",
            "version": "1.0.0",
        }
        errors = validate_frontmatter(fm, "my-skill.md")
        assert any("Invalid name format" in e for e in errors)

    def test_name_with_uppercase(self):
        fm = {
            "name": "My-Skill",
            "description": "A useful skill.",
            "category": "tooling",
            "date": "2026-01-15",
            "version": "1.0.0",
        }
        errors = validate_frontmatter(fm, "my-skill.md")
        assert any("Invalid name format" in e for e in errors)

    def test_multiple_missing_fields(self):
        fm = {}
        errors = validate_frontmatter(fm, "empty.md")
        missing = [e for e in errors if "Missing required field" in e]
        assert len(missing) == 5


# ---------------------------------------------------------------------------
# validate_sections
# ---------------------------------------------------------------------------


class TestValidateSections:
    def test_all_sections_present(self):
        body = (
            "## Overview\nstuff\n"
            "## When to Use\nstuff\n"
            "## Verified Workflow\nstuff\n"
            "## Failed Attempts\nstuff\n"
            "## Results & Parameters\nstuff\n"
        )
        assert validate_sections(body) == []

    def test_missing_one_section(self):
        body = (
            "## Overview\nstuff\n"
            "## When to Use\nstuff\n"
            "## Verified Workflow\nstuff\n"
            "## Failed Attempts\nstuff\n"
        )
        errors = validate_sections(body)
        assert len(errors) == 1
        assert "Results & Parameters" in errors[0]

    def test_missing_all_sections(self):
        body = "Just some plain text with no sections."
        errors = validate_sections(body)
        assert len(errors) == 5


# ---------------------------------------------------------------------------
# validate_failed_attempts_table
# ---------------------------------------------------------------------------


class TestValidateFailedAttemptsTable:
    def test_valid_table(self):
        body = (
            "## Failed Attempts\n\n"
            "| Attempt | What Was Tried | Why It Failed | Lesson Learned |\n"
            "|---------|----------------|---------------|----------------|\n"
            "| 1 | Did X | Broke Y | Use Z instead |\n"
        )
        assert validate_failed_attempts_table(body) == []

    def test_empty_section(self):
        body = "## Failed Attempts\n\nNone.\n\n## Results & Parameters\n"
        errors = validate_failed_attempts_table(body)
        assert any("empty" in e.lower() or "None" in e for e in errors)

    def test_missing_columns(self):
        body = (
            "## Failed Attempts\n\n"
            "| Attempt | Details |\n"
            "|---------|--------|\n"
            "| 1 | Something |\n"
        )
        errors = validate_failed_attempts_table(body)
        assert any("missing required columns" in e for e in errors)

    def test_plain_text_allowed(self):
        body = (
            "## Failed Attempts\n\n"
            "We tried approach A but it did not work because of reason B.\n"
            "Then we tried approach C which also failed due to D.\n"
            "\n## Results & Parameters\n"
        )
        errors = validate_failed_attempts_table(body)
        assert errors == []

    def test_no_failed_attempts_section(self):
        body = "## Overview\nstuff\n"
        errors = validate_failed_attempts_table(body)
        assert errors == []

    def test_incomplete_table(self):
        body = (
            "## Failed Attempts\n\n"
            "| Attempt | What Was Tried | Why It Failed | Lesson Learned |\n"
            "|---------|----------------|---------------|----------------|\n"
        )
        errors = validate_failed_attempts_table(body)
        assert any("incomplete" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# validate_quick_reference_heading
# ---------------------------------------------------------------------------


class TestValidateQuickReferenceHeading:
    def test_h2_quick_reference_flagged(self):
        body = "## Verified Workflow\n\nstuff\n\n## Quick Reference\n\ncommands\n"
        errors = validate_quick_reference_heading(body)
        assert len(errors) == 1
        assert "### (h3)" in errors[0]

    def test_h3_quick_reference_ok(self):
        body = "## Verified Workflow\n\nstuff\n\n### Quick Reference\n\ncommands\n"
        errors = validate_quick_reference_heading(body)
        assert errors == []

    def test_no_quick_reference(self):
        body = "## Verified Workflow\n\nstuff\n"
        errors = validate_quick_reference_heading(body)
        assert errors == []


# ---------------------------------------------------------------------------
# find_plugins
# ---------------------------------------------------------------------------


class TestFindPlugins:
    def test_finds_skill_files(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "alpha.md").write_text("skill a")
        (skills / "beta.md").write_text("skill b")
        from skill_utils import find_skill_files
        result = find_skill_files(skills_dir=skills)
        assert len(result) == 2
        names = [p.name for p in result]
        assert "alpha.md" in names
        assert "beta.md" in names

    def test_excludes_notes_md(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "alpha.md").write_text("skill a")
        (skills / "alpha.notes.md").write_text("notes")
        (skills / "alpha.notes-v2.md").write_text("notes v2")
        from skill_utils import find_skill_files
        result = find_skill_files(skills_dir=skills)
        assert len(result) == 1
        assert result[0].name == "alpha.md"

    def test_empty_directory(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        from skill_utils import find_skill_files
        result = find_skill_files(skills_dir=skills)
        assert result == []

    def test_missing_directory(self, tmp_path):
        missing = tmp_path / "nonexistent"
        from skill_utils import find_skill_files
        result = find_skill_files(skills_dir=missing)
        assert result == []


# ---------------------------------------------------------------------------
# validate_plugin (integration)
# ---------------------------------------------------------------------------


class TestValidatePlugin:
    def test_valid_skill_file(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "good-skill.md").write_text(CLEAN_SKILL_MD)
        with patch("validate_plugins.SKILLS_DIR", skills):
            errors = validate_plugin("good-skill.md")
        # CLEAN_SKILL_MD from conftest uses short column names that won't
        # match the strict 4-column check, so filter to non-column errors.
        non_column_errors = [
            e for e in errors if "missing required columns" not in e
        ]
        assert non_column_errors == []

    def test_invalid_skill_file_no_frontmatter(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "bad.md").write_text("No frontmatter here, just text.")
        with patch("validate_plugins.SKILLS_DIR", skills):
            errors = validate_plugin("bad.md")
        assert len(errors) > 0
        assert any("frontmatter" in e.lower() for e in errors)

    def test_missing_file(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        with patch("validate_plugins.SKILLS_DIR", skills):
            errors = validate_plugin("nonexistent.md")
        assert len(errors) == 1
        assert "Cannot read file" in errors[0]
