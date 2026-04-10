#!/usr/bin/env python3
"""
Tests for Quick Reference section handling in fix_remaining_warnings.py.

Verifies that:
- Top-level ## Quick Reference alongside ## Verified Workflow is merged as subsection
- Quick Reference ONLY (no Verified Workflow) still triggers the wrapper path
- Idempotency: running fix twice produces the same result
- No change when file has no Quick Reference or already has it as subsection
"""

from pathlib import Path

from conftest import (
    SAMPLE_FAILED_ATTEMPTS as FAILED_ATTEMPTS,
)
from conftest import (
    SAMPLE_FRONTMATTER as FRONTMATTER,
)
from conftest import (
    SAMPLE_OVERVIEW as OVERVIEW,
)
from conftest import (
    SAMPLE_QUICK_REFERENCE as QUICK_REFERENCE_CONTENT,
)
from conftest import (
    SAMPLE_RESULTS as RESULTS,
)
from conftest import (
    SAMPLE_VERIFIED_WORKFLOW as VERIFIED_WORKFLOW_CONTENT,
)
from fix_remaining_warnings import (
    add_verified_workflow_wrapper,
    has_orphan_quick_reference,
    has_verified_workflow_section,
    merge_quick_reference_into_verified_workflow,
)
from validate_plugins import validate_skill_md


def make_skill(
    has_quick_reference: bool = True,
    has_verified_workflow: bool = True,
    qr_before_vw: bool = True,
    qr_as_subsection: bool = False,
) -> str:
    """Build a SKILL.md string with configurable section layout."""
    parts = [FRONTMATTER, OVERVIEW]

    if qr_as_subsection:
        # Quick Reference already nested under Verified Workflow
        vw = VERIFIED_WORKFLOW_CONTENT.rstrip("\n") + "\n\n### Quick Reference\n\n```bash\ngit status\n```\n\n"
        parts.append(vw)
    elif has_quick_reference and has_verified_workflow:
        if qr_before_vw:
            parts.append(QUICK_REFERENCE_CONTENT)
            parts.append(VERIFIED_WORKFLOW_CONTENT)
        else:
            parts.append(VERIFIED_WORKFLOW_CONTENT)
            parts.append(QUICK_REFERENCE_CONTENT)
    elif has_quick_reference:
        parts.append(QUICK_REFERENCE_CONTENT)
    elif has_verified_workflow:
        parts.append(VERIFIED_WORKFLOW_CONTENT)

    parts.append(FAILED_ATTEMPTS)
    parts.append(RESULTS)
    return "".join(parts)


# ---------------------------------------------------------------------------
# Tests for has_orphan_quick_reference()
# ---------------------------------------------------------------------------


class TestHasOrphanQuickReference:
    def test_returns_true_when_top_level_quick_reference_present(self) -> None:
        content = make_skill(has_quick_reference=True, has_verified_workflow=True)
        assert has_orphan_quick_reference(content) is True

    def test_returns_false_when_quick_reference_is_subsection(self) -> None:
        content = make_skill(qr_as_subsection=True)
        assert has_orphan_quick_reference(content) is False

    def test_returns_false_when_no_quick_reference(self) -> None:
        content = make_skill(has_quick_reference=False)
        assert has_orphan_quick_reference(content) is False

    def test_returns_false_when_quick_reference_only_as_subsection_marker(self) -> None:
        # Content where ### Quick Reference appears but not ## Quick Reference
        content = (
            FRONTMATTER
            + OVERVIEW
            + "## Verified Workflow\n\n### Quick Reference\n\n```bash\ngit x\n```\n\n"
            + FAILED_ATTEMPTS
        )
        assert has_orphan_quick_reference(content) is False


# ---------------------------------------------------------------------------
# Tests for merge_quick_reference_into_verified_workflow()
# ---------------------------------------------------------------------------


class TestMergeQuickReferenceIntoVerifiedWorkflow:
    def test_qr_before_vw_is_moved_under_vw(self) -> None:
        content = make_skill(has_quick_reference=True, has_verified_workflow=True, qr_before_vw=True)
        result = merge_quick_reference_into_verified_workflow(content)

        # Top-level ## Quick Reference must be gone
        import re

        assert not re.search(r"^## Quick Reference", result, re.MULTILINE)
        # Subsection ### Quick Reference must exist
        assert re.search(r"^### Quick Reference", result, re.MULTILINE)
        # ## Verified Workflow must still be there
        assert "## Verified Workflow" in result
        # ### Quick Reference must appear after ## Verified Workflow
        vw_pos = result.index("## Verified Workflow")
        qr_pos = result.index("### Quick Reference")
        assert qr_pos > vw_pos

    def test_qr_after_vw_is_moved_under_vw(self) -> None:
        content = make_skill(has_quick_reference=True, has_verified_workflow=True, qr_before_vw=False)
        result = merge_quick_reference_into_verified_workflow(content)

        import re

        assert not re.search(r"^## Quick Reference", result, re.MULTILINE)
        assert re.search(r"^### Quick Reference", result, re.MULTILINE)
        vw_pos = result.index("## Verified Workflow")
        qr_pos = result.index("### Quick Reference")
        assert qr_pos > vw_pos

    def test_no_change_when_already_subsection(self) -> None:
        content = make_skill(qr_as_subsection=True)
        result = merge_quick_reference_into_verified_workflow(content)
        assert result == content

    def test_content_of_quick_reference_preserved(self) -> None:
        content = make_skill(has_quick_reference=True, has_verified_workflow=True)
        result = merge_quick_reference_into_verified_workflow(content)
        # The bash commands inside Quick Reference must still be present
        assert "git status" in result
        assert "git log" in result

    def test_idempotent(self) -> None:
        content = make_skill(has_quick_reference=True, has_verified_workflow=True)
        first_pass = merge_quick_reference_into_verified_workflow(content)
        second_pass = merge_quick_reference_into_verified_workflow(first_pass)
        assert first_pass == second_pass


# ---------------------------------------------------------------------------
# Tests for add_verified_workflow_wrapper() regression
# (existing path: ## Quick Reference ONLY, no ## Verified Workflow)
# ---------------------------------------------------------------------------


class TestAddVerifiedWorkflowWrapperRegression:
    def test_quick_reference_only_gets_wrapped(self) -> None:
        content = make_skill(has_quick_reference=True, has_verified_workflow=False)
        assert not has_verified_workflow_section(content)
        result = add_verified_workflow_wrapper(content)
        assert has_verified_workflow_section(result)

    def test_no_change_when_already_has_verified_workflow(self) -> None:
        content = make_skill(has_quick_reference=False, has_verified_workflow=True)
        result = add_verified_workflow_wrapper(content)
        # The wrapper function should leave the content unchanged (no Quick Reference to wrap)
        assert result == content


# ---------------------------------------------------------------------------
# Integration: fix_skill_file() behaviour
# ---------------------------------------------------------------------------


class TestFixSkillFileIntegration:
    def test_fix_skill_file_handles_orphan_qr(self, tmp_path: Path) -> None:
        import re

        from fix_remaining_warnings import fix_skill_file

        content = make_skill(has_quick_reference=True, has_verified_workflow=True)
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(content)

        modified, fixes = fix_skill_file(skill_file)

        assert modified is True
        assert any("Quick Reference" in fix for fix in fixes)
        result = skill_file.read_text()
        assert not re.search(r"^## Quick Reference", result, re.MULTILINE)
        assert re.search(r"^### Quick Reference", result, re.MULTILINE)

    def test_fix_skill_file_is_idempotent(self, tmp_path: Path) -> None:
        from fix_remaining_warnings import fix_skill_file

        content = make_skill(has_quick_reference=True, has_verified_workflow=True)
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(content)

        fix_skill_file(skill_file)
        content_after_first = skill_file.read_text()

        modified, fixes = fix_skill_file(skill_file)

        assert modified is False
        assert skill_file.read_text() == content_after_first

    def test_fix_skill_file_no_change_when_clean(self, tmp_path: Path) -> None:
        from fix_remaining_warnings import fix_skill_file

        content = make_skill(has_quick_reference=False, has_verified_workflow=True)
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(content)

        modified, fixes = fix_skill_file(skill_file)

        assert modified is False
        assert fixes == []


# ---------------------------------------------------------------------------
# Tests for validate_plugins.py warning
# ---------------------------------------------------------------------------


class TestValidatePluginsQuickReferenceWarning:
    def _make_plugin_dir(self, tmp_path: Path, skill_content: str) -> Path:
        """Set up a minimal plugin directory structure."""
        plugin_dir = tmp_path / "test-plugin"
        skill_subdir = plugin_dir / "skills" / "test-plugin"
        skill_subdir.mkdir(parents=True)
        (skill_subdir / "SKILL.md").write_text(skill_content)

        plugin_json_dir = plugin_dir / ".claude-plugin"
        plugin_json_dir.mkdir()
        import json

        (plugin_json_dir / "plugin.json").write_text(
            json.dumps(
                {
                    "name": "test-plugin",
                    "version": "1.0.0",
                    "description": "A test plugin for unit testing purposes.",
                    "category": "tooling",
                    "date": "2026-01-01",
                }
            )
        )
        return plugin_dir

    def test_warns_on_orphaned_top_level_quick_reference(self, tmp_path: Path) -> None:
        content = make_skill(has_quick_reference=True, has_verified_workflow=True)
        plugin_dir = self._make_plugin_dir(tmp_path, content)

        errors, warnings = validate_skill_md(plugin_dir, {})

        warning_texts = " ".join(warnings)
        assert "Quick Reference" in warning_texts
        assert "subsection" in warning_texts.lower() or "###" in warning_texts

    def test_no_warning_when_quick_reference_is_subsection(self, tmp_path: Path) -> None:
        content = make_skill(qr_as_subsection=True)
        plugin_dir = self._make_plugin_dir(tmp_path, content)

        errors, warnings = validate_skill_md(plugin_dir, {})

        qr_warnings = [w for w in warnings if "Quick Reference" in w and "subsection" in w.lower()]
        assert qr_warnings == []

    def test_no_warning_when_no_quick_reference(self, tmp_path: Path) -> None:
        content = make_skill(has_quick_reference=False, has_verified_workflow=True)
        plugin_dir = self._make_plugin_dir(tmp_path, content)

        errors, warnings = validate_skill_md(plugin_dir, {})

        qr_warnings = [w for w in warnings if "Quick Reference" in w]
        assert qr_warnings == []
