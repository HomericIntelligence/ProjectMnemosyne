#!/usr/bin/env python3
"""
Tests for scripts/migrate_ecosystem_skills.py.

Covers:
- parse_frontmatter: valid content, missing delimiters, empty body, no frontmatter
- frontmatter_to_yaml: key ordering, quoting, list handling
- _format_yaml_value: none, list, special chars, booleans
- map_category: scylla override, source mapping, defaults
- generalize_paths: pixi, project-specific absolute paths, catch-all home paths
- rename_workflow_section: bare "## Workflow" -> "## Verified Workflow"
- has_section: present / absent patterns
- add_missing_sections: all missing, some present, stub insertion order
- remove_repo_specific_fields: removes reserved keys, preserves others
- build_target_frontmatter: defaults, category mapping, field cleanup
- transform_skill: end-to-end transformation
- discover_odyssey_skills / discover_scylla_skills / discover_keystone_skills
- build_skill_registry: deduplication / priority / source filter / skill filter
- migrate_skill: skip existing, dry-run, write, force overwrite, read error
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Path setup (matches conftest.py pattern)
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from migrate_ecosystem_skills import (
    FIELDS_TO_REMOVE,
    TODAY,
    _format_yaml_value,
    _insert_before_failed_attempts,
    _insert_before_results,
    _insert_before_verified_workflow,
    add_missing_sections,
    build_skill_registry,
    build_target_frontmatter,
    discover_keystone_skills,
    discover_odyssey_skills,
    discover_scylla_skills,
    frontmatter_to_yaml,
    generalize_paths,
    has_section,
    map_category,
    migrate_skill,
    parse_frontmatter,
    remove_repo_specific_fields,
    rename_workflow_section,
    transform_skill,
)

# ---------------------------------------------------------------------------
# Sample content helpers
# ---------------------------------------------------------------------------

MINIMAL_FRONTMATTER = """\
---
name: my-skill
description: "A skill."
category: tooling
date: 2026-01-01
version: "1.0.0"
user-invocable: false
---
"""

FULL_SKILL_MD = """\
---
name: my-skill
description: "A skill."
category: tooling
date: 2026-01-01
version: "1.0.0"
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-01 |
| **Objective** | Do something |
| **Outcome** | Success |

## When to Use

- Some condition

## Verified Workflow

### Quick Reference

```bash
echo hello
```

More steps here.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Tried X | It failed | Use Y instead |

## Results & Parameters

- param: value
"""


def _make_skill_md_file(directory: Path, content: str) -> Path:
    """Write SKILL.md into *directory* and return the path."""
    path = directory / "SKILL.md"
    path.write_text(content, encoding="utf-8")
    return path


# ===========================================================================
# parse_frontmatter
# ===========================================================================


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = "---\nname: my-skill\ncategory: tooling\n---\nBody here."
        fm, body = parse_frontmatter(content)
        assert fm["name"] == "my-skill"
        assert fm["category"] == "tooling"
        assert body == "Body here."

    def test_no_frontmatter(self):
        content = "Just some body text."
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_missing_closing_delimiter(self):
        content = "---\nname: my-skill\n"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_quoted_string_values_stripped(self):
        content = '---\nname: "double-quoted"\nother: \'single-quoted\'\n---\nBody.'
        fm, body = parse_frontmatter(content)
        assert fm["name"] == "double-quoted"
        assert fm["other"] == "single-quoted"

    def test_empty_value_becomes_none(self):
        content = "---\nname:\n---\nBody."
        fm, body = parse_frontmatter(content)
        assert fm["name"] is None

    def test_comment_lines_ignored(self):
        content = "---\n# a comment\nname: skill\n---\nBody."
        fm, body = parse_frontmatter(content)
        assert "name" in fm
        assert fm.get("# a comment") is None

    def test_body_whitespace_stripped(self):
        content = "---\nname: skill\n---\n\n\nActual body."
        fm, body = parse_frontmatter(content)
        assert body == "Actual body."


# ===========================================================================
# frontmatter_to_yaml / _format_yaml_value
# ===========================================================================


class TestFrontmatterToYaml:
    def test_canonical_key_order(self):
        fm = {
            "version": "1.0.0",
            "name": "my-skill",
            "category": "tooling",
            "description": "desc",
            "date": "2026-01-01",
            "user-invocable": "false",
        }
        yaml_text = frontmatter_to_yaml(fm)
        keys_in_order = [line.split(":")[0].strip() for line in yaml_text.splitlines() if ":" in line]
        canonical = ["name", "description", "category", "date", "version", "user-invocable"]
        for i in range(len(canonical) - 1):
            assert keys_in_order.index(canonical[i]) < keys_in_order.index(canonical[i + 1])

    def test_none_value_serialized_correctly(self):
        result = _format_yaml_value("key", None)
        assert result == "key:"

    def test_list_value_serialized_as_empty_list(self):
        result = _format_yaml_value("tags", ["a", "b"])
        assert result == "tags: []"

    def test_value_with_colon_is_quoted(self):
        result = _format_yaml_value("description", "Use when: something")
        assert result.startswith('description: "')
        assert "Use when: something" in result

    def test_boolean_like_value_is_quoted(self):
        result = _format_yaml_value("user-invocable", "false")
        assert result.startswith('user-invocable: "')

    def test_plain_value_unquoted(self):
        result = _format_yaml_value("category", "tooling")
        assert result == "category: tooling"

    def test_extra_keys_emitted_after_canonical(self):
        fm = {"name": "s", "extra-key": "extra-val"}
        yaml_text = frontmatter_to_yaml(fm)
        assert "extra-key: extra-val" in yaml_text


# ===========================================================================
# map_category
# ===========================================================================


class TestMapCategory:
    def test_scylla_category_overrides_source(self):
        # scylla_category drives the mapping
        assert map_category("training", "ci") == "ci-cd"
        assert map_category(None, "github") == "tooling"

    def test_known_source_category_mapped(self):
        assert map_category("ci", None) == "ci-cd"
        assert map_category("mojo", None) == "architecture"
        assert map_category("training", None) == "training"

    def test_unknown_category_defaults_to_tooling(self):
        assert map_category("unknown-category", None) == "tooling"
        assert map_category(None, None) == "tooling"

    def test_category_mapping_case_insensitive(self):
        assert map_category("CI", None) == "ci-cd"
        assert map_category("TRAINING", None) == "training"


# ===========================================================================
# generalize_paths
# ===========================================================================


class TestGeneralizePaths:
    def test_pixi_run_mojo_replaced(self):
        text = "Run it with pixi run mojo script.mojo"
        result = generalize_paths(text)
        assert "<package-manager> run mojo" in result
        assert "pixi" not in result

    def test_pixi_run_replaced(self):
        text = "Use pixi run test to run tests"
        result = generalize_paths(text)
        assert "<package-manager> run test" in result
        assert "pixi" not in result

    def test_odyssey_path_replaced(self):
        text = "See /home/user/repos/ProjectOdyssey/src/main.py"
        result = generalize_paths(text)
        assert "<project-root>/src/main.py" in result
        assert "/home/user" not in result

    def test_scylla_path_replaced(self):
        # Pattern requires at least one path segment before ProjectScylla
        text = "Config at /home/runner/repos/ProjectScylla/config.yaml"
        result = generalize_paths(text)
        assert "<project-root>/config.yaml" in result
        assert "/home/runner" not in result

    def test_keystone_path_replaced(self):
        text = "From /home/dev/work/ProjectKeystone/lib/tool.py"
        result = generalize_paths(text)
        assert "<project-root>/lib/tool.py" in result

    def test_catch_all_home_path_replaced(self):
        text = "Found at /home/alice/some/other/path/file.txt"
        result = generalize_paths(text)
        assert "<home>/some/other/path/file.txt" in result
        assert "/home/alice" not in result

    def test_no_paths_unchanged(self):
        text = "No absolute paths here, just words."
        result = generalize_paths(text)
        assert result == text


# ===========================================================================
# rename_workflow_section
# ===========================================================================


class TestRenameWorkflowSection:
    def test_bare_workflow_renamed(self):
        body = "## Workflow\n\nSome steps."
        result = rename_workflow_section(body)
        assert "## Verified Workflow" in result
        assert "## Workflow\n" not in result

    def test_verified_workflow_unchanged(self):
        body = "## Verified Workflow\n\nSome steps."
        result = rename_workflow_section(body)
        assert result == body

    def test_workflow_in_heading_text_unchanged(self):
        # "## My Workflow Notes" should NOT be renamed
        body = "## My Workflow Notes\n\nstuff"
        result = rename_workflow_section(body)
        assert "## My Workflow Notes" in result

    def test_multiline_body(self):
        body = "## Overview\n\n## Workflow\n\nsteps\n"
        result = rename_workflow_section(body)
        assert "## Verified Workflow" in result
        assert "## Overview" in result


# ===========================================================================
# has_section
# ===========================================================================


class TestHasSection:
    def test_section_present(self):
        body = "## Overview\n\nsome text\n## When to Use\n\nstuff"
        assert has_section(body, r"## When to Use") is True

    def test_section_absent(self):
        body = "## Overview\n\nsome text"
        assert has_section(body, r"## When to Use") is False

    def test_pattern_anchored_to_line_start(self):
        body = "Prefix ## Overview inline text"
        # The section heading is not at line start
        assert has_section(body, r"^## Overview") is False


# ===========================================================================
# add_missing_sections
# ===========================================================================


class TestAddMissingSections:
    def test_all_sections_already_present_unchanged(self):
        result = add_missing_sections(FULL_SKILL_MD.split("---\n", 2)[2], "my-skill")
        assert "## Overview" in result
        assert "## When to Use" in result
        assert "## Verified Workflow" in result
        assert "## Failed Attempts" in result
        assert "## Results & Parameters" in result

    def test_overview_stub_added_when_missing(self):
        body = "## When to Use\n\n- something\n"
        result = add_missing_sections(body, "my-skill")
        assert "## Overview" in result
        assert TODAY in result

    def test_when_to_use_stub_added_when_missing(self):
        body = "## Overview\n\n| x | y |\n\n## Verified Workflow\n\n### Quick Reference\n```bash\n```\n\n## Failed Attempts\n\n| A | B | C | D |\n\n## Results & Parameters\n\n- x\n"
        result = add_missing_sections(body, "my-skill")
        assert "## When to Use" in result

    def test_failed_attempts_stub_added_when_missing(self):
        body = "## Overview\n\n## When to Use\n\n## Verified Workflow\n\n### Quick Reference\n```bash\n```\n\n## Results & Parameters\n\n"
        result = add_missing_sections(body, "my-skill")
        assert "## Failed Attempts" in result
        assert "Attempt" in result

    def test_results_stub_added_when_missing(self):
        body = "## Overview\n\n## When to Use\n\n## Verified Workflow\n\n### Quick Reference\n```bash\n```\n\n## Failed Attempts\n\n| A | B | C | D |\n"
        result = add_missing_sections(body, "my-skill")
        assert "## Results & Parameters" in result

    def test_quick_reference_added_to_existing_verified_workflow(self):
        body = "## Verified Workflow\n\nsome steps\n\n## Failed Attempts\n\n| x | y | z | w |\n\n## Results & Parameters\n\n- x\n"
        result = add_missing_sections(body, "my-skill")
        assert "### Quick Reference" in result


# ===========================================================================
# remove_repo_specific_fields
# ===========================================================================


class TestRemoveRepoSpecificFields:
    def test_removes_all_reserved_fields(self):
        fm = {k: "value" for k in FIELDS_TO_REMOVE}
        fm["name"] = "keep-this"
        result = remove_repo_specific_fields(fm)
        for field in FIELDS_TO_REMOVE:
            assert field not in result
        assert result["name"] == "keep-this"

    def test_non_reserved_fields_preserved(self):
        fm = {"name": "my-skill", "category": "tooling", "custom-field": "custom"}
        result = remove_repo_specific_fields(fm)
        assert result == fm


# ===========================================================================
# build_target_frontmatter
# ===========================================================================


class TestBuildTargetFrontmatter:
    def test_defaults_added_for_missing_fields(self):
        fm = {"name": "my-skill", "description": "desc"}
        result = build_target_frontmatter(fm, "my-skill", None)
        assert result["version"] == "1.0.0"
        assert result["user-invocable"] == "false"
        assert result["verification"] == "unverified"
        assert result["date"] == TODAY
        assert result["tags"] == []

    def test_existing_fields_not_overwritten(self):
        fm = {"name": "my-skill", "description": "desc", "version": "2.0.0", "date": "2025-01-01"}
        result = build_target_frontmatter(fm, "my-skill", None)
        assert result["version"] == "2.0.0"
        assert result["date"] == "2025-01-01"

    def test_category_mapped_correctly(self):
        fm = {"name": "my-skill", "description": "desc", "category": "ci"}
        result = build_target_frontmatter(fm, "my-skill", None)
        assert result["category"] == "ci-cd"

    def test_scylla_category_overrides_fm_category(self):
        fm = {"name": "my-skill", "description": "desc", "category": "training"}
        result = build_target_frontmatter(fm, "my-skill", "github")
        assert result["category"] == "tooling"

    def test_reserved_fields_removed(self):
        fm = {"name": "my-skill", "description": "desc", "source": "odyssey", "phase": "2"}
        result = build_target_frontmatter(fm, "my-skill", None)
        assert "source" not in result
        assert "phase" not in result

    def test_name_defaults_to_skill_name_arg(self):
        fm = {}
        result = build_target_frontmatter(fm, "derived-name", None)
        assert result["name"] == "derived-name"


# ===========================================================================
# transform_skill (end-to-end)
# ===========================================================================


class TestTransformSkill:
    def test_valid_skill_transforms_without_error(self):
        result = transform_skill(FULL_SKILL_MD, "my-skill", None)
        assert result.startswith("---\n")
        assert result.endswith("\n")

    def test_reserved_fields_stripped_from_output(self):
        content = "---\nname: my-skill\ndescription: desc\nsource: odyssey\nmcp_fallback: true\n---\nBody.\n"
        result = transform_skill(content, "my-skill", None)
        assert "source:" not in result
        assert "mcp_fallback:" not in result

    def test_workflow_section_renamed(self):
        content = "---\nname: my-skill\ndescription: desc\n---\n## Workflow\n\nSteps.\n"
        result = transform_skill(content, "my-skill", None)
        assert "## Verified Workflow" in result
        assert "## Workflow\n" not in result

    def test_paths_generalized(self):
        # Pattern requires at least one path segment before the project dir
        content = "---\nname: my-skill\ndescription: desc\n---\nSee /home/user/repos/ProjectOdyssey/docs.\n"
        result = transform_skill(content, "my-skill", None)
        assert "<project-root>" in result
        assert "/home/user" not in result

    def test_missing_sections_injected(self):
        content = "---\nname: my-skill\ndescription: desc\n---\nJust some text.\n"
        result = transform_skill(content, "my-skill", None)
        for section in ["## Overview", "## When to Use", "## Verified Workflow", "## Failed Attempts", "## Results & Parameters"]:
            assert section in result, f"Missing section: {section}"

    def test_no_frontmatter_still_produces_valid_output(self):
        content = "Just plain text without any frontmatter.\n"
        result = transform_skill(content, "plain-skill", None)
        assert result.startswith("---\n")
        assert "name: plain-skill" in result


# ===========================================================================
# discover_odyssey_skills
# ===========================================================================


class TestDiscoverOdysseySkills:
    def test_discovers_skills(self, tmp_path, monkeypatch):
        monkeypatch.setitem(__import__("migrate_ecosystem_skills").SOURCES, "odyssey", tmp_path)
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        _make_skill_md_file(skill_dir, "content")

        skills = discover_odyssey_skills()
        assert len(skills) == 1
        assert skills[0][0] == "my-skill"
        assert skills[0][2] is None  # no scylla_category

    def test_skips_non_directories(self, tmp_path, monkeypatch):
        monkeypatch.setitem(__import__("migrate_ecosystem_skills").SOURCES, "odyssey", tmp_path)
        (tmp_path / "file.md").write_text("just a file")
        skills = discover_odyssey_skills()
        assert skills == []

    def test_skips_hidden_directories(self, tmp_path, monkeypatch):
        monkeypatch.setitem(__import__("migrate_ecosystem_skills").SOURCES, "odyssey", tmp_path)
        hidden = tmp_path / ".hidden-skill"
        hidden.mkdir()
        _make_skill_md_file(hidden, "content")
        skills = discover_odyssey_skills()
        assert skills == []

    def test_missing_source_returns_empty(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "does-not-exist"
        monkeypatch.setitem(__import__("migrate_ecosystem_skills").SOURCES, "odyssey", nonexistent)
        skills = discover_odyssey_skills()
        assert skills == []


# ===========================================================================
# discover_scylla_skills
# ===========================================================================


class TestDiscoverScyllaSkills:
    def test_discovers_skills_with_category(self, tmp_path, monkeypatch):
        monkeypatch.setitem(__import__("migrate_ecosystem_skills").SOURCES, "scylla", tmp_path)
        cat_dir = tmp_path / "ci"
        skill_dir = cat_dir / "my-ci-skill"
        skill_dir.mkdir(parents=True)
        _make_skill_md_file(skill_dir, "content")

        skills = discover_scylla_skills()
        assert len(skills) == 1
        assert skills[0][0] == "my-ci-skill"
        assert skills[0][2] == "ci"

    def test_discovers_nested_tier_skills(self, tmp_path, monkeypatch):
        monkeypatch.setitem(__import__("migrate_ecosystem_skills").SOURCES, "scylla", tmp_path)
        tier_dir = tmp_path / "other" / "tier-1" / "nested-skill"
        tier_dir.mkdir(parents=True)
        _make_skill_md_file(tier_dir, "content")

        skills = discover_scylla_skills()
        assert any(s[0] == "nested-skill" for s in skills)

    def test_missing_source_returns_empty(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "does-not-exist"
        monkeypatch.setitem(__import__("migrate_ecosystem_skills").SOURCES, "scylla", nonexistent)
        skills = discover_scylla_skills()
        assert skills == []


# ===========================================================================
# discover_keystone_skills
# ===========================================================================


class TestDiscoverKeystoneSkills:
    def test_discovers_skills(self, tmp_path, monkeypatch):
        monkeypatch.setitem(__import__("migrate_ecosystem_skills").SOURCES, "keystone", tmp_path)
        skill_dir = tmp_path / "ks-skill"
        skill_dir.mkdir()
        _make_skill_md_file(skill_dir, "content")

        skills = discover_keystone_skills()
        assert len(skills) == 1
        assert skills[0][0] == "ks-skill"
        assert skills[0][2] is None

    def test_discovers_nested_skills(self, tmp_path, monkeypatch):
        monkeypatch.setitem(__import__("migrate_ecosystem_skills").SOURCES, "keystone", tmp_path)
        sub_dir = tmp_path / "tier-1" / "nested-ks"
        sub_dir.mkdir(parents=True)
        _make_skill_md_file(sub_dir, "content")

        skills = discover_keystone_skills()
        assert any(s[0] == "nested-ks" for s in skills)

    def test_missing_source_returns_empty(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "does-not-exist"
        monkeypatch.setitem(__import__("migrate_ecosystem_skills").SOURCES, "keystone", nonexistent)
        skills = discover_keystone_skills()
        assert skills == []


# ===========================================================================
# build_skill_registry
# ===========================================================================


class TestBuildSkillRegistry:
    def _setup_sources(self, tmp_path, monkeypatch):
        import migrate_ecosystem_skills as mod

        odyssey = tmp_path / "odyssey"
        scylla = tmp_path / "scylla"
        keystone = tmp_path / "keystone"
        odyssey.mkdir()
        scylla.mkdir()
        keystone.mkdir()
        monkeypatch.setitem(mod.SOURCES, "odyssey", odyssey)
        monkeypatch.setitem(mod.SOURCES, "scylla", scylla)
        monkeypatch.setitem(mod.SOURCES, "keystone", keystone)
        return odyssey, scylla, keystone

    def test_single_source(self, tmp_path, monkeypatch):
        odyssey, _, _ = self._setup_sources(tmp_path, monkeypatch)
        skill_dir = odyssey / "alpha-skill"
        skill_dir.mkdir()
        _make_skill_md_file(skill_dir, "content")

        registry = build_skill_registry()
        assert "alpha-skill" in registry

    def test_scylla_wins_deduplication(self, tmp_path, monkeypatch):
        odyssey, scylla, keystone = self._setup_sources(tmp_path, monkeypatch)
        # Same skill in odyssey and scylla
        for base in [odyssey, scylla / "ci"]:
            base.mkdir(exist_ok=True)
            skill_dir = base / "shared-skill"
            skill_dir.mkdir(exist_ok=True)
            _make_skill_md_file(skill_dir, "content")

        registry = build_skill_registry()
        source, _, _ = registry["shared-skill"]
        assert source == "scylla"

    def test_source_filter_limits_scan(self, tmp_path, monkeypatch):
        odyssey, scylla, keystone = self._setup_sources(tmp_path, monkeypatch)
        ody_dir = odyssey / "ody-only"
        ody_dir.mkdir()
        _make_skill_md_file(ody_dir, "content")
        scylla_cat = scylla / "testing"
        scylla_cat.mkdir()
        scylla_dir = scylla_cat / "scylla-only"
        scylla_dir.mkdir()
        _make_skill_md_file(scylla_dir, "content")

        registry = build_skill_registry(source_filter="odyssey")
        assert "ody-only" in registry
        assert "scylla-only" not in registry

    def test_skill_filter_limits_results(self, tmp_path, monkeypatch):
        odyssey, _, _ = self._setup_sources(tmp_path, monkeypatch)
        for name in ["alpha-skill", "beta-skill", "gamma-skill"]:
            d = odyssey / name
            d.mkdir()
            _make_skill_md_file(d, "content")

        registry = build_skill_registry(skill_filter="beta-skill")
        assert list(registry.keys()) == ["beta-skill"]

    def test_empty_sources_returns_empty_registry(self, tmp_path, monkeypatch):
        self._setup_sources(tmp_path, monkeypatch)
        registry = build_skill_registry()
        assert registry == {}


# ===========================================================================
# migrate_skill
# ===========================================================================


class TestMigrateSkill:
    def _make_source_skill(self, tmp_path: Path, name: str, content: str = FULL_SKILL_MD) -> Path:
        skill_dir = tmp_path / "source" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        path = skill_dir / "SKILL.md"
        path.write_text(content, encoding="utf-8")
        return path

    def test_migrates_skill_to_target(self, tmp_path, monkeypatch):
        import migrate_ecosystem_skills as mod

        target_skills_dir = tmp_path / "skills"
        monkeypatch.setattr(mod, "SKILLS_DIR", target_skills_dir)

        source_path = self._make_source_skill(tmp_path, "new-skill")
        result = migrate_skill("new-skill", "odyssey", source_path, None, dry_run=False, force=False)

        assert result == "migrated"
        assert (target_skills_dir / "new-skill.md").exists()

    def test_skips_existing_without_force(self, tmp_path, monkeypatch):
        import migrate_ecosystem_skills as mod

        target_skills_dir = tmp_path / "skills"
        target_skills_dir.mkdir()
        monkeypatch.setattr(mod, "SKILLS_DIR", target_skills_dir)
        existing = target_skills_dir / "existing-skill.md"
        existing.write_text("already here")

        source_path = self._make_source_skill(tmp_path, "existing-skill")
        result = migrate_skill("existing-skill", "odyssey", source_path, None, dry_run=False, force=False)

        assert result == "skipped"
        assert existing.read_text() == "already here"

    def test_force_overwrites_existing(self, tmp_path, monkeypatch):
        import migrate_ecosystem_skills as mod

        target_skills_dir = tmp_path / "skills"
        target_skills_dir.mkdir()
        monkeypatch.setattr(mod, "SKILLS_DIR", target_skills_dir)
        existing = target_skills_dir / "existing-skill.md"
        existing.write_text("old content")

        source_path = self._make_source_skill(tmp_path, "existing-skill")
        result = migrate_skill("existing-skill", "odyssey", source_path, None, dry_run=False, force=True)

        assert result == "migrated"
        assert existing.read_text() != "old content"

    def test_dry_run_does_not_write_file(self, tmp_path, monkeypatch):
        import migrate_ecosystem_skills as mod

        target_skills_dir = tmp_path / "skills"
        monkeypatch.setattr(mod, "SKILLS_DIR", target_skills_dir)

        source_path = self._make_source_skill(tmp_path, "dry-run-skill")
        result = migrate_skill("dry-run-skill", "odyssey", source_path, None, dry_run=True, force=False)

        assert result == "migrated"
        assert not (target_skills_dir / "dry-run-skill.md").exists()

    def test_missing_source_file_returns_failed(self, tmp_path, monkeypatch):
        import migrate_ecosystem_skills as mod

        target_skills_dir = tmp_path / "skills"
        monkeypatch.setattr(mod, "SKILLS_DIR", target_skills_dir)

        nonexistent = tmp_path / "nonexistent" / "SKILL.md"
        result = migrate_skill("ghost-skill", "odyssey", nonexistent, None, dry_run=False, force=False)

        assert result == "failed"

    def test_scylla_category_included_in_output_label(self, tmp_path, monkeypatch, capsys):
        import migrate_ecosystem_skills as mod

        target_skills_dir = tmp_path / "skills"
        monkeypatch.setattr(mod, "SKILLS_DIR", target_skills_dir)

        source_path = self._make_source_skill(tmp_path, "ci-skill")
        migrate_skill("ci-skill", "scylla", source_path, "ci", dry_run=False, force=False)

        captured = capsys.readouterr()
        assert "ci/ci-skill" in captured.out
