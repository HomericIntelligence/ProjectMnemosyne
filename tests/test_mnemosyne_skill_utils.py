#!/usr/bin/env python3
"""
Tests for scripts/mnemosyne_skill_utils.py shared utility functions.

Covers:
- parse_frontmatter: valid content, missing opening delimiter, missing closing
  delimiter, invalid YAML, empty frontmatter, body whitespace stripping
- find_skill_files: normal discovery, exclusion of *.notes*.md and *.history*,
  empty directory, non-existent directory, files sorted deterministically
"""

from pathlib import Path

from mnemosyne_skill_utils import find_skill_files, parse_frontmatter

# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_valid_frontmatter_returns_dict_body_no_errors(self):
        content = "---\nname: my-skill\ncategory: tooling\n---\nBody text here."
        fm, body, errors = parse_frontmatter(content)

        assert errors == []
        assert fm["name"] == "my-skill"
        assert fm["category"] == "tooling"
        assert body == "Body text here."

    def test_missing_opening_delimiter_returns_error(self):
        content = "name: my-skill\n---\nBody."
        fm, body, errors = parse_frontmatter(content)

        assert len(errors) == 1
        assert "does not start with" in errors[0]
        assert fm == {}

    def test_missing_closing_delimiter_returns_error(self):
        content = "---\nname: my-skill\nBody without closing."
        fm, body, errors = parse_frontmatter(content)

        assert len(errors) == 1
        assert "missing closing" in errors[0]
        assert fm == {}

    def test_invalid_yaml_returns_error(self):
        content = "---\n: invalid: yaml: [broken\n---\nBody."
        fm, body, errors = parse_frontmatter(content)

        assert len(errors) == 1
        assert "Invalid YAML" in errors[0]
        assert fm == {}

    def test_empty_frontmatter_block_returns_empty_dict(self):
        content = "---\n\n---\nBody."
        fm, body, errors = parse_frontmatter(content)

        assert errors == []
        assert fm == {}
        assert body == "Body."

    def test_body_leading_newline_is_stripped(self):
        content = "---\nname: s\n---\n\nActual body."
        _, body, errors = parse_frontmatter(content)

        assert errors == []
        assert body == "Actual body."

    def test_multiple_fields_in_frontmatter(self):
        content = (
            "---\n"
            "name: multi-field\n"
            "description: A test\n"
            "category: debugging\n"
            "date: 2026-01-01\n"
            'version: "1.0.0"\n'
            "user-invocable: false\n"
            "---\n"
            "# Heading\n"
        )
        fm, body, errors = parse_frontmatter(content)

        assert errors == []
        assert fm["name"] == "multi-field"
        assert fm["version"] == "1.0.0"
        assert fm["user-invocable"] is False
        assert body.startswith("# Heading")

    def test_body_content_preserved_with_markdown(self):
        body_text = "## Section\n\nSome **bold** text.\n"
        content = f"---\nname: x\n---\n{body_text}"
        _, body, errors = parse_frontmatter(content)

        assert errors == []
        assert "## Section" in body
        assert "**bold**" in body

    def test_returns_original_content_as_body_on_no_delimiter(self):
        content = "plain text, no frontmatter at all"
        fm, body, errors = parse_frontmatter(content)

        assert len(errors) == 1
        assert fm == {}
        # body should be the original content
        assert body == content


# ---------------------------------------------------------------------------
# find_skill_files
# ---------------------------------------------------------------------------


class TestFindSkillFiles:
    def _write(self, directory: Path, name: str, text: str = "content") -> Path:
        """Helper: write a file into *directory* and return the path."""
        p = directory / name
        p.write_text(text)
        return p

    def test_returns_empty_list_when_dir_does_not_exist(self, tmp_path: Path):
        missing = tmp_path / "nonexistent"
        assert find_skill_files(missing) == []

    def test_returns_empty_list_for_empty_directory(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        assert find_skill_files(skills) == []

    def test_discovers_plain_skill_md_files(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        self._write(skills, "my-skill.md")
        self._write(skills, "another-skill.md")

        result = find_skill_files(skills)
        names = [f.name for f in result]

        assert "my-skill.md" in names
        assert "another-skill.md" in names
        assert len(result) == 2

    def test_excludes_notes_md_files(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        self._write(skills, "my-skill.md")
        self._write(skills, "my-skill.notes.md")
        self._write(skills, "other.notes-extra.md")

        result = find_skill_files(skills)
        names = [f.name for f in result]

        assert "my-skill.md" in names
        assert "my-skill.notes.md" not in names
        assert "other.notes-extra.md" not in names

    def test_excludes_history_files(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        self._write(skills, "my-skill.md")
        self._write(skills, "my-skill.history.md")
        self._write(skills, "my-skill.history")

        result = find_skill_files(skills)
        names = [f.name for f in result]

        assert "my-skill.md" in names
        assert "my-skill.history.md" not in names
        assert "my-skill.history" not in names

    def test_results_are_sorted(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        self._write(skills, "z-skill.md")
        self._write(skills, "a-skill.md")
        self._write(skills, "m-skill.md")

        result = find_skill_files(skills)
        names = [f.name for f in result]

        assert names == sorted(names)

    def test_returns_path_objects(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        self._write(skills, "skill.md")

        result = find_skill_files(skills)

        assert len(result) == 1
        assert isinstance(result[0], Path)

    def test_does_not_recurse_into_subdirectories(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        subdir = skills / "subdir"
        subdir.mkdir()
        self._write(skills, "top-skill.md")
        self._write(subdir, "nested-skill.md")

        result = find_skill_files(skills)
        names = [f.name for f in result]

        assert "top-skill.md" in names
        assert "nested-skill.md" not in names

    def test_excludes_non_md_files(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        self._write(skills, "skill.md")
        self._write(skills, "README.txt")
        self._write(skills, "config.yaml")

        result = find_skill_files(skills)
        names = [f.name for f in result]

        assert names == ["skill.md"]

    def test_notes_with_hyphen_suffix_excluded(self, tmp_path: Path):
        """Regression: *.notes-<word>.md should also be excluded."""
        skills = tmp_path / "skills"
        skills.mkdir()
        self._write(skills, "skill.md")
        self._write(skills, "skill.notes-session1.md")

        result = find_skill_files(skills)
        names = [f.name for f in result]

        assert "skill.md" in names
        assert "skill.notes-session1.md" not in names
