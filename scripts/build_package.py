#!/usr/bin/env python3
"""Build the canonical `package` artifact: the marketplace bundle tarball.

Mnemosyne distributes a skills/plugins marketplace, not a Python
library. The canonical CI `package` check builds and verifies this bundle.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tarfile
from pathlib import Path

BUNDLE_DIRS = (".claude-plugin", "skills", "plugins", "schemas", "templates")
EXCLUDE_PARTS = {"__pycache__"}
VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def get_version(pyproject: Path) -> str:
    """Extract the project version string from a pyproject.toml file."""
    text = pyproject.read_text(encoding="utf-8")
    if re.search(r"^\[project\]\s*$", text, re.MULTILINE) is None:
        raise ValueError(f"No [project] table found in {pyproject}")
    match = VERSION_RE.search(text)
    if match is None:
        raise ValueError(f"No version field found in {pyproject}")
    return match.group(1)


def _include(path: Path) -> bool:
    return not (EXCLUDE_PARTS & set(path.parts)) and path.suffix != ".pyc"


def build_package(repo_root: Path, output_dir: Path) -> Path:
    """Build the versioned marketplace bundle tarball and return its path."""
    version = get_version(repo_root / "pyproject.toml")
    output_dir.mkdir(parents=True, exist_ok=True)
    tarball = output_dir / f"project-mnemosyne-{version}.tar.gz"
    with tarfile.open(tarball, "w:gz") as tar:
        for dirname in BUNDLE_DIRS:
            base = repo_root / dirname
            if not base.is_dir():
                raise FileNotFoundError(f"Required bundle directory missing: {base}")
            for path in sorted(p for p in base.rglob("*") if p.is_file()):
                if _include(path.relative_to(repo_root)):
                    tar.add(path, arcname=str(path.relative_to(repo_root)))
    return tarball


def verify_package(tarball: Path) -> list[str]:
    """Read-only checks on the built artifact. Returns a list of problems."""
    problems: list[str] = []
    with tarfile.open(tarball, "r:gz") as tar:
        names = tar.getnames()
        for required in (".claude-plugin/marketplace.json", ".claude-plugin/plugin.json"):
            if required not in names:
                problems.append(f"missing {required}")
        if ".claude-plugin/marketplace.json" in names:
            member = tar.extractfile(".claude-plugin/marketplace.json")
            if member is None:
                problems.append(".claude-plugin/marketplace.json is not a regular file")
            else:
                try:
                    json.load(io.TextIOWrapper(member, encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    problems.append(f"marketplace.json is not valid JSON: {exc}")
        if not any(n.startswith("skills/") and n.endswith(".md") for n in names):
            problems.append("no skill .md files in bundle")
    return problems


def main(argv: list[str] | None = None) -> int:
    """Build and verify the marketplace bundle; return a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to <repo-root>/dist",
    )
    args = parser.parse_args(argv)
    output_dir = args.output_dir if args.output_dir is not None else args.repo_root / "dist"
    tarball = build_package(args.repo_root, output_dir)
    problems = verify_package(tarball)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1
    print(f"Built and verified {tarball}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
