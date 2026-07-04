#!/usr/bin/env python3
"""Regression checks for intentional skill-memory consolidations."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from skill_utils import parse_frontmatter

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
MARKETPLACE_PATH = ROOT / ".claude-plugin" / "marketplace.json"


CONSOLIDATIONS = [
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


def _frontmatter_for(skill_name: str) -> dict:
    content = (SKILLS_DIR / f"{skill_name}.md").read_text()
    frontmatter, _, errors = parse_frontmatter(content)
    assert errors == []
    return frontmatter


def test_consolidated_canonicals_have_major_versions_and_history():
    for consolidation in CONSOLIDATIONS:
        canonical = consolidation["canonical"]
        frontmatter = _frontmatter_for(canonical)
        assert frontmatter["version"] == consolidation["version"]
        assert frontmatter["history"] == f"{canonical}.history"
        assert (SKILLS_DIR / frontmatter["history"]).is_file()


def test_absorbed_skill_snapshots_remain_in_history():
    for consolidation in CONSOLIDATIONS:
        canonical = consolidation["canonical"]
        history = (SKILLS_DIR / f"{canonical}.history").read_text()
        assert "MAJOR bump" in history

        for absorbed in consolidation["absorbed"]:
            assert not (SKILLS_DIR / f"{absorbed}.md").exists()
            assert f"Superseded from `{absorbed}`" in history
            assert f"name: {absorbed}\n" in history


def test_marketplace_only_lists_canonical_consolidation_targets():
    marketplace = json.loads(MARKETPLACE_PATH.read_text())
    plugins = {plugin["name"]: plugin for plugin in marketplace["plugins"]}

    for consolidation in CONSOLIDATIONS:
        canonical = consolidation["canonical"]
        assert plugins[canonical]["version"] == consolidation["version"]

        for absorbed in consolidation["absorbed"]:
            assert absorbed not in plugins
