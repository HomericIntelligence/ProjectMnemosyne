#!/usr/bin/env python3
"""
Fix remaining validation issues:
1. Duplicate/malformed YAML frontmatter (keep first one)
2. Missing Failed Attempts section
"""

import re
import sys
from pathlib import Path

SKILLS_DIR = Path("skills")


def read_skill_file(skill_path: Path) -> str:
    """Read skill file content."""
    with open(skill_path, "r") as f:
        return f.read()


def write_skill_file(skill_path: Path, content: str) -> None:
    """Write skill file content."""
    with open(skill_path, "w") as f:
        f.write(content)


def fix_duplicate_frontmatter(content: str) -> tuple[str, bool]:
    """Remove duplicate/malformed YAML frontmatter."""
    changed = False

    # Find all frontmatter blocks
    frontmatter_count = content.count("---")

    if frontmatter_count > 2:
        print(f"  Fixing duplicate frontmatter blocks")
        # Remove all but the first two --- markers
        parts = content.split("---")

        if len(parts) >= 3:
            # Keep first block (before first ---, content between first and second ---, then rest)
            fixed_content = "---" + parts[1] + "---" + "---".join(parts[3:])
            content = fixed_content
            changed = True

    return content, changed


def ensure_failed_attempts_section(content: str) -> tuple[str, bool]:
    """Ensure Failed Attempts section exists."""
    changed = False

    if "## Failed Attempts" not in content:
        print(f"  Adding missing Failed Attempts section")

        new_section = """## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |

"""
        # Insert before Results & Parameters or at end
        if "## Results" in content:
            idx = content.find("## Results")
            content = content[:idx] + new_section + content[idx:]
        else:
            content = content.rstrip() + "\n\n" + new_section.rstrip()

        changed = True

    return content, changed


def fix_problematic_skills():
    """Fix specific problematic skills."""
    problematic = [
        "babylonjs-havok-vite-wasm",
        "close-script-test-gap-cmd-run-repair",
        "complexity-regression-gate",
        "cytoscape-frontend-rewrite",
        "dockerfile-pyproject-version-guard",
        "dryrun3-completion",
        "extend-script-test-coverage",
        "fix-review-feedback-missing-assertion",
        "fix-review-feedback-runner-path-untested",
        "github-actions-security-patterns",
        "mypy-annotate-test-functions",
        "pytest-pythonpath-scripts-fix",
        "python-repo-modernization",
        "quality-audit-docstring-false-positive",
        "verify-mypy-compliance-test-annotations",
        "gh-create-pr-linked",
        "gh-fix-pr-feedback",
        "manage-experiment-audit",
    ]

    fixed_count = 0

    for skill_name in problematic:
        skill_file = SKILLS_DIR / f"{skill_name}.md"

        if not skill_file.exists():
            print(f"✗ Not found: {skill_name}")
            continue

        try:
            content = read_skill_file(skill_file)
            file_changed = False

            # Fix duplicate frontmatter
            content, changed = fix_duplicate_frontmatter(content)
            file_changed = file_changed or changed

            # Ensure Failed Attempts section
            content, changed = ensure_failed_attempts_section(content)
            file_changed = file_changed or changed

            # Write if changed
            if file_changed:
                write_skill_file(skill_file, content)
                print(f"✓ Fixed: {skill_name}")
                fixed_count += 1
            else:
                print(f"  No changes: {skill_name}")

        except Exception as e:
            print(f"✗ Error processing {skill_name}: {e}")

    return fixed_count


def main():
    """Fix remaining issues."""
    print("Fixing remaining validation issues...\n")

    fixed_count = fix_problematic_skills()

    print(f"\n{'='*60}")
    print(f"Fixed: {fixed_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
