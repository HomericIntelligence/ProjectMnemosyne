#!/usr/bin/env python3
"""Fix residual SKILL.md warning patterns.

Supports:
- Wrapping top-level ``## Quick Reference`` under ``## Verified Workflow``
- Merging orphaned top-level ``## Quick Reference`` blocks into an existing
  ``## Verified Workflow`` section as ``### Quick Reference``
- Converting plain-text ``## Failed Attempts`` content into the required table

This module is intentionally small and importable from tests.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Sequence


WRAPPABLE_SECTIONS = ("Quick Reference", "Analysis Workflow", "Usage")


def has_verified_workflow_section(content: str) -> bool:
    """Return True when a top-level Verified Workflow section exists."""
    return bool(re.search(r"^## Verified Workflow\b", content, re.MULTILINE))


def has_orphan_quick_reference(content: str) -> bool:
    """Return True when a top-level Quick Reference heading exists."""
    return bool(re.search(r"^## Quick Reference\b", content, re.MULTILINE))


def merge_quick_reference_into_verified_workflow(content: str) -> str:
    """Move a top-level Quick Reference block under Verified Workflow.

    If the file does not have both a top-level ``## Quick Reference`` block and a
    top-level ``## Verified Workflow`` block, the content is returned unchanged.
    """
    if not has_orphan_quick_reference(content) or not has_verified_workflow_section(content):
        return content

    quick_ref_match = re.search(
        r"^## Quick Reference[^\n]*\n.*?(?=^## |\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if quick_ref_match is None:
        return content

    quick_ref_block = quick_ref_match.group(0)
    quick_ref_subsection = re.sub(
        r"^## Quick Reference\b",
        "### Quick Reference",
        quick_ref_block,
        count=1,
        flags=re.MULTILINE,
    ).strip("\n")

    content_without_qr = content[: quick_ref_match.start()] + content[quick_ref_match.end() :]
    workflow_match = re.search(
        r"^## Verified Workflow[^\n]*\n",
        content_without_qr,
        re.MULTILINE,
    )
    if workflow_match is None:
        return content

    insert_at = workflow_match.end()
    merged = (
        content_without_qr[:insert_at]
        + "\n"
        + quick_ref_subsection
        + "\n\n"
        + content_without_qr[insert_at:].lstrip("\n")
    )
    return merged


def add_verified_workflow_wrapper(content: str) -> str:
    """Wrap top-level workflow-like sections in ``## Verified Workflow``.

    This is primarily used when a file only has ``## Quick Reference`` and no
    verified workflow wrapper at all.
    """
    if has_verified_workflow_section(content):
        return content

    for section_name in WRAPPABLE_SECTIONS:
        pattern = rf"^## {re.escape(section_name)}\b"
        if re.search(pattern, content, re.MULTILINE):
            return re.sub(
                pattern,
                f"## Verified Workflow\n\n### {section_name}",
                content,
                count=1,
                flags=re.MULTILINE,
            )

    return content


def _failed_attempts_needs_table(content: str) -> bool:
    """Return True when Failed Attempts content is plain text rather than a table."""
    match = re.search(
        r"^## Failed Attempts\s*\n(.*?)(?=^## |\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        return False

    section_content = match.group(1).strip()
    if not section_content:
        return True
    return "|" not in section_content


def _normalize_failed_attempts_table(content: str) -> str:
    """Convert plain-text Failed Attempts content into the required table format."""
    match = re.search(
        r"(^## Failed Attempts\s*\n)(.*?)(?=^## |\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        return content

    raw_content = match.group(2).strip()
    if "|" in raw_content:
        return content

    summary = raw_content or "No failed attempts recorded."
    table = (
        "| Attempt | What Was Tried | Why It Failed | Lesson Learned |\n"
        "|---------|----------------|---------------|----------------|\n"
        f"| 1 | {summary} | Not specified | Replace this placeholder with a concrete failed attempt when one exists. |\n\n"
    )
    return content[: match.start(2)] + table + content[match.end(2) :]


def fix_skill_file(skill_path: Path, dry_run: bool = False) -> tuple[bool, list[str]]:
    """Fix one SKILL.md file in place unless ``dry_run`` is enabled."""
    original = skill_path.read_text()
    updated = original
    fixes: list[str] = []

    if has_orphan_quick_reference(updated):
        if has_verified_workflow_section(updated):
            merged = merge_quick_reference_into_verified_workflow(updated)
            if merged != updated:
                updated = merged
                fixes.append("Moved Quick Reference under Verified Workflow")
        else:
            wrapped = add_verified_workflow_wrapper(updated)
            if wrapped != updated:
                updated = wrapped
                fixes.append("Wrapped Quick Reference in Verified Workflow")

    if _failed_attempts_needs_table(updated):
        normalized = _normalize_failed_attempts_table(updated)
        if normalized != updated:
            updated = normalized
            fixes.append("Normalized Failed Attempts into required table format")

    modified = updated != original
    if modified and not dry_run:
        skill_path.write_text(updated)

    return modified, fixes


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Fix residual SKILL.md warning patterns")
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=Path("skills"),
        help="Root directory to scan recursively for SKILL.md files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    skill_files = sorted(args.skills_dir.rglob("SKILL.md"))
    if not skill_files:
        print(f"No SKILL.md files found under {args.skills_dir}")
        return

    if args.dry_run:
        print("DRY RUN: previewing fixes only")

    for skill_file in skill_files:
        modified, fixes = fix_skill_file(skill_file, dry_run=args.dry_run)
        if not modified:
            continue

        action = "Would fix" if args.dry_run else "Fixed"
        print(f"{action}: {skill_file}")
        for fix in fixes:
            print(f"  - {fix}")


if __name__ == "__main__":
    main()
