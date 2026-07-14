#!/usr/bin/env python3
"""
Tests for scripts/validate_release_contract.py.

Covers:
- find_violations: compliant fixture, one dedicated test per violation branch
  (non-semver version, missing/misanchored CHANGELOG.md)
- check_tag: matching tag, wrong version, missing 'v' prefix
- main: orchestrator altitude (exit codes + stderr/stdout via capsys),
  argparse default --repo-root branch
- Live-tree alignment: the real repo satisfies the contract

Mnemosyne is a skills/memory store (Athena is the plugin distribution), so the
contract no longer tracks any .claude-plugin/ marketplace or plugin.json version.
"""

from pathlib import Path
from typing import Optional

from validate_release_contract import check_tag, find_violations, main

REPO_ROOT = Path(__file__).resolve().parent.parent

COMPLIANT_CHANGELOG = """\
# Changelog

## [Unreleased]

## [2.1.0] - 2026-07-03

- Baseline entry.
"""


def make_repo(
    tmp_path: Path,
    version: str = "2.1.0",
    changelog: Optional[str] = COMPLIANT_CHANGELOG,
) -> Path:
    """Write a minimal repo fixture; defaults produce a compliant contract."""
    (tmp_path / "pyproject.toml").write_text(f'[project]\nname = "x"\nversion = "{version}"\n')
    if changelog is not None:
        (tmp_path / "CHANGELOG.md").write_text(changelog)
    return tmp_path


class TestFindViolations:
    def test_compliant_repo_passes(self, tmp_path):
        assert find_violations(make_repo(tmp_path)) == []

    def test_non_semver_version(self, tmp_path):
        repo = make_repo(
            tmp_path,
            version="2.1",
            changelog="# Changelog\n\n## [2.1.0] - 2026-07-03\n\n- x\n",
        )
        violations = find_violations(repo)
        assert any("not strict semver" in v for v in violations)

    def test_missing_changelog(self, tmp_path):
        repo = make_repo(tmp_path, changelog=None)
        violations = find_violations(repo)
        assert len(violations) == 1
        assert "missing file" in violations[0]
        assert "CHANGELOG.md" in violations[0]
        # Read-only guard: the validator must never fabricate the changelog.
        assert not (repo / "CHANGELOG.md").exists()

    def test_changelog_no_versioned_heading(self, tmp_path):
        repo = make_repo(tmp_path, changelog="# Changelog\n\n## [Unreleased]\n\n- x\n")
        violations = find_violations(repo)
        assert len(violations) == 1
        assert "no versioned" in violations[0]

    def test_changelog_top_heading_mismatch(self, tmp_path):
        repo = make_repo(tmp_path, changelog="# Changelog\n\n## [2.0.0] - 2026-01-01\n\n- x\n")
        violations = find_violations(repo)
        assert len(violations) == 1
        assert "'2.0.0'" in violations[0] and "'2.1.0'" in violations[0]

    def test_unreleased_section_above_versioned_heading_passes(self, tmp_path):
        repo = make_repo(
            tmp_path,
            changelog="# Changelog\n\n## [Unreleased]\n\n- pending\n\n## [2.1.0] - 2026-07-03\n\n- x\n",
        )
        assert find_violations(repo) == []

    def test_missing_pyproject(self, tmp_path):
        violations = find_violations(tmp_path)
        assert len(violations) == 1
        assert "pyproject.toml" in violations[0]

    def test_tag_checked_when_provided(self, tmp_path):
        repo = make_repo(tmp_path)
        assert find_violations(repo, tag="v2.1.0") == []
        violations = find_violations(repo, tag="v9.9.9")
        assert len(violations) == 1
        assert "release tag" in violations[0]


class TestCheckTag:
    def test_matching_tag_passes(self):
        assert check_tag("v2.1.0", "2.1.0") == []

    def test_wrong_version_fails(self):
        violations = check_tag("v2.2.0", "2.1.0")
        assert len(violations) == 1
        assert "'v2.2.0'" in violations[0] and "'v2.1.0'" in violations[0]

    def test_missing_v_prefix_fails(self):
        assert len(check_tag("2.1.0", "2.1.0")) == 1


class TestMain:
    def test_main_broken_fixture_returns_1(self, tmp_path, capsys):
        repo = make_repo(
            tmp_path,
            version="2.1",
            changelog="# Changelog\n\n## [2.1.0] - 2026-07-03\n\n- x\n",
        )
        assert main(["--repo-root", str(repo)]) == 1
        captured = capsys.readouterr()
        assert "RELEASE-CONTRACT VIOLATION" in captured.err
        assert "not strict semver" in captured.err

    def test_main_compliant_fixture_returns_0(self, tmp_path, capsys):
        repo = make_repo(tmp_path)
        assert main(["--repo-root", str(repo)]) == 0
        captured = capsys.readouterr()
        assert "OK: release contract holds" in captured.out

    def test_main_tag_mismatch_returns_1(self, tmp_path, capsys):
        repo = make_repo(tmp_path)
        assert main(["--repo-root", str(repo), "--tag", "v9.9.9"]) == 1
        assert "release tag" in capsys.readouterr().err

    def test_main_repo_root_default(self, capsys):
        # Flag absent: exercises the argparse default branch, which resolves
        # to parents[1] of the script — the real repo, which must comply.
        assert main([]) == 0
        assert "OK: release contract holds" in capsys.readouterr().out


def test_real_repo_contract_holds():
    """Live-tree alignment: the gate ships green on the real repository."""
    assert find_violations(REPO_ROOT) == []
