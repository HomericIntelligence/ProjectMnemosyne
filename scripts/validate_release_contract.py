#!/usr/bin/env python3
"""Validate the Mnemosyne release contract (issue #2913).

Contract (single source of truth: pyproject.toml [project].version):
  1. pyproject version is strict semver (X.Y.Z).
  2. .claude-plugin/plugin.json .version matches it.
  3. .claude-plugin/marketplace.json .version matches it.
  4. CHANGELOG.md's topmost versioned heading '## [X.Y.Z]' matches it
     (an '## [Unreleased]' section may precede it).
  5. With --tag vX.Y.Z (used by the tag-publish workflow): tag == 'v' + version.

Exit codes: 0 = contract holds, 1 = violation (argparse usage errors exit 2).
Strictly read-only: never creates or mutates any file it checks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Optional

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback
    import tomli as tomllib  # type: ignore[no-redef]

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
CHANGELOG_HEADING_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)

PLUGIN_JSON = Path(".claude-plugin") / "plugin.json"
MARKETPLACE_JSON = Path(".claude-plugin") / "marketplace.json"
CHANGELOG_MD = Path("CHANGELOG.md")


def load_project_version(repo_root: Path) -> Optional[str]:
    """Read [project].version from pyproject.toml; None if missing/unreadable."""
    pyproject = repo_root / "pyproject.toml"
    try:
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
    except (OSError, ValueError):
        return None
    version = data.get("project", {}).get("version")
    return str(version) if version is not None else None


def check_semver(version: str) -> List[str]:
    """Require the version to be strict semver (X.Y.Z)."""
    if not SEMVER_RE.match(version):
        return [f"pyproject.toml version {version!r} is not strict semver (X.Y.Z)"]
    return []


def _check_json_version_sync(path: Path, version: str) -> List[str]:
    """Require the JSON file at path to have .version equal to version."""
    if not path.is_file():
        return [f"missing file: {path}"]
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot parse {path}: {exc}"]
    found = data.get("version")
    if found != version:
        return [f"{path} version {found!r} != pyproject.toml version {version!r}"]
    return []


def check_plugin_json_sync(repo_root: Path, version: str) -> List[str]:
    """Require .claude-plugin/plugin.json .version to match the pyproject version."""
    return _check_json_version_sync(repo_root / PLUGIN_JSON, version)


def check_marketplace_sync(repo_root: Path, version: str) -> List[str]:
    """Require .claude-plugin/marketplace.json .version to match the pyproject version."""
    return _check_json_version_sync(repo_root / MARKETPLACE_JSON, version)


def check_changelog(repo_root: Path, version: str) -> List[str]:
    """Require CHANGELOG.md's topmost '## [X.Y.Z]' heading to match version.

    An '## [Unreleased]' section may precede the versioned heading; it does
    not match the versioned-heading pattern and is skipped. Absence of
    CHANGELOG.md is reported as a violation — never fabricated.
    """
    changelog = repo_root / CHANGELOG_MD
    if not changelog.is_file():
        return [f"missing file: {changelog}"]
    try:
        text = changelog.read_text()
    except OSError as exc:
        return [f"cannot read {changelog}: {exc}"]
    match = CHANGELOG_HEADING_RE.search(text)
    if match is None:
        return [f"{changelog} has no versioned '## [X.Y.Z]' heading"]
    if match.group(1) != version:
        return [
            f"{changelog} topmost versioned heading is {match.group(1)!r}, "
            f"expected {version!r} (pyproject.toml version)"
        ]
    return []


def check_tag(tag: str, version: str) -> List[str]:
    """Require the release tag to be exactly 'v' + the pyproject version."""
    expected = f"v{version}"
    if tag != expected:
        return [f"release tag {tag!r} != expected {expected!r} ('v' + pyproject.toml version)"]
    return []


def find_violations(repo_root: Path, tag: Optional[str] = None) -> List[str]:
    """Aggregate all contract checks; returns human-readable violations."""
    version = load_project_version(repo_root)
    if version is None:
        return [f"cannot read [project].version from {repo_root / 'pyproject.toml'}"]

    violations: List[str] = []
    violations.extend(check_semver(version))
    violations.extend(check_plugin_json_sync(repo_root, version))
    violations.extend(check_marketplace_sync(repo_root, version))
    violations.extend(check_changelog(repo_root, version))
    if tag is not None:
        violations.extend(check_tag(tag, version))
    return violations


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Exit 0 if the contract holds, 1 on any violation."""
    parser = argparse.ArgumentParser(
        prog="validate_release_contract.py",
        description="Validate the Mnemosyne release contract (version sync + changelog anchor).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to validate (default: this script's repo)",
    )
    parser.add_argument(
        "--tag",
        default=None,
        help="Release tag to cross-check against the version (vX.Y.Z)",
    )
    args = parser.parse_args(argv)

    violations = find_violations(args.repo_root, args.tag)
    if violations:
        for violation in violations:
            print(f"RELEASE-CONTRACT VIOLATION: {violation}", file=sys.stderr)
        return 1
    print("OK: release contract holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
