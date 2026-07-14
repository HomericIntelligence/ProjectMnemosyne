#!/usr/bin/env python3
"""Regression checks for intentional skill-memory consolidations."""

import sys
from pathlib import Path
from typing import TypedDict, cast

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from mnemosyne_skill_utils import parse_frontmatter

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"


class Consolidation(TypedDict):
    canonical: str
    version: str
    absorbed: list[str]


CONSOLIDATIONS: list[Consolidation] = [
    {
        "canonical": "planning-verify-issue-premise-before-implementing",
        "version": "3.0.0",
        "absorbed": [
            "planning-verify-assumptions-before-enforcement-gate",
            "planning-verify-full-population-not-just-named-entities",
            "planning-verify-impl-return-shapes-before-asserting",
            "planning-verify-integration-point-exists-before-guarding",
            "planning-verify-issue-claims-and-required-check-gating",
            "planning-verify-issue-premises-against-main",
            "planning-verify-live-state-before-assuming-work-remains",
        ],
    },
    {
        "canonical": "cli-validator-cross-section-blind-spot",
        "version": "3.0.0",
        "absorbed": [
            "cli-tier-docs-duplicate-section-detection",
            "validation-cli-tier-docs-duplicate-section-detection",
        ],
    },
    {
        "canonical": "console-scripts-exit-code-discipline",
        "version": "2.0.0",
        "absorbed": ["console-scripts-instance-state-error-tracking"],
    },
    {
        "canonical": "testing-env-leak-local-fail-ci-pass",
        "version": "2.0.0",
        "absorbed": [
            "local-test-failures-env-pollution-not-ci",
            "pytest-local-false-failure-inherited-heph-env-vars",
            "testing-os-environ-pollution-local-vs-ci-false-failure",
        ],
    },
]


def _frontmatter_for(skill_name: str) -> dict[str, object]:
    content = (SKILLS_DIR / f"{skill_name}.md").read_text()
    frontmatter, _, errors = parse_frontmatter(content)
    assert errors == []
    return cast("dict[str, object]", frontmatter)


def test_consolidated_canonicals_have_major_versions_and_history():
    for consolidation in CONSOLIDATIONS:
        canonical = consolidation["canonical"]
        frontmatter = _frontmatter_for(canonical)
        assert frontmatter["version"] == consolidation["version"]
        history = frontmatter["history"]
        assert isinstance(history, str)
        assert history == f"{canonical}.history"
        assert (SKILLS_DIR / history).is_file()


def test_absorbed_skill_snapshots_remain_in_history():
    for consolidation in CONSOLIDATIONS:
        canonical = consolidation["canonical"]
        history = (SKILLS_DIR / f"{canonical}.history").read_text()
        assert "MAJOR bump" in history

        for absorbed in consolidation["absorbed"]:
            assert not (SKILLS_DIR / f"{absorbed}.md").exists()
            assert f"Superseded from `{absorbed}`" in history
            assert f"name: {absorbed}\n" in history


def test_skill_files_only_keep_canonical_consolidation_targets():
    """The canonical skill file exists at the expected version and every
    absorbed skill file has been removed. Checks the skills/ corpus directly
    (Mnemosyne no longer ships a plugin marketplace to mirror)."""
    for consolidation in CONSOLIDATIONS:
        canonical = consolidation["canonical"]
        canonical_path = SKILLS_DIR / f"{canonical}.md"
        assert canonical_path.is_file(), f"missing canonical skill: {canonical}"
        fm, _body, errs = parse_frontmatter(canonical_path.read_text())
        assert not errs, (canonical, errs)
        assert fm.get("version") == consolidation["version"]

        for absorbed in consolidation["absorbed"]:
            assert not (SKILLS_DIR / f"{absorbed}.md").exists(), f"absorbed skill still present: {absorbed}"
