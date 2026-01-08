#!/usr/bin/env python3
"""Add user-invocable: false to skill frontmatter."""

import re
from pathlib import Path

# Sub-skills that should be marked as user-invocable: false
SUB_SKILLS = [
    # gh-pr-review-workflow
    "plugins/tooling/gh-pr-review-workflow/skills/fix-feedback/SKILL.md",
    "plugins/tooling/gh-pr-review-workflow/skills/get-comments/SKILL.md",
    "plugins/tooling/gh-pr-review-workflow/skills/reply-comment/SKILL.md",
    # git-worktree-workflow
    "plugins/tooling/git-worktree-workflow/skills/cleanup/SKILL.md",
    "plugins/tooling/git-worktree-workflow/skills/create/SKILL.md",
    "plugins/tooling/git-worktree-workflow/skills/switch/SKILL.md",
    "plugins/tooling/git-worktree-workflow/skills/sync/SKILL.md",
    # skills-registry-commands
    "plugins/tooling/skills-registry-commands/skills/advise/SKILL.md",
    "plugins/tooling/skills-registry-commands/skills/documentation-patterns/SKILL.md",
    "plugins/tooling/skills-registry-commands/skills/retrospective/SKILL.md",
    "plugins/tooling/skills-registry-commands/skills/validation-workflow/SKILL.md",
    # ci-failure-workflow
    "plugins/ci-cd/ci-failure-workflow/skills/analyze/SKILL.md",
    "plugins/ci-cd/ci-failure-workflow/skills/fix/SKILL.md",
]

def add_user_invocable(file_path: Path) -> bool:
    """Add user-invocable: false to frontmatter if not present."""
    content = file_path.read_text()

    # Check if already has user-invocable
    if "user-invocable:" in content:
        print(f"  ✓ {file_path.name} already has user-invocable field")
        return False

    # Match YAML frontmatter
    pattern = r'^(---\n)(.*?)(---\n)'
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        print(f"  ✗ {file_path.name} has no frontmatter")
        return False

    frontmatter = match.group(2)
    # Add user-invocable: false after the last field
    new_frontmatter = frontmatter.rstrip() + "\nuser-invocable: false\n"
    new_content = f"---\n{new_frontmatter}---\n" + content[match.end():]

    file_path.write_text(new_content)
    print(f"  ✓ Added user-invocable: false to {file_path.name}")
    return True

def main():
    root = Path(__file__).parent.parent
    updated = 0

    for skill_path in SUB_SKILLS:
        full_path = root / skill_path
        if not full_path.exists():
            print(f"  ✗ Not found: {skill_path}")
            continue

        if add_user_invocable(full_path):
            updated += 1

    print(f"\n✓ Updated {updated} skills with user-invocable: false")

if __name__ == "__main__":
    main()
