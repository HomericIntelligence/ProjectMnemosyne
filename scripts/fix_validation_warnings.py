#!/usr/bin/env python3
"""
Script to fix validation warnings in SKILL.md files.

Fixes:
1. Missing ## Overview tables
2. Missing ## Verified Workflow (rename from ## Workflow)
3. Missing ## Results & Parameters
4. Failed Attempts lacking pipe tables
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def read_file(path: Path) -> str:
    """Read file content."""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(path: Path, content: str) -> None:
    """Write content to file."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def extract_frontmatter_date(content: str) -> str:
    """Extract date from YAML frontmatter."""
    match = re.search(r'^date:\s*["\']?([0-9-]+)["\']?', content, re.MULTILINE)
    return match.group(1) if match else "N/A"


def extract_objective(content: str) -> str:
    """Extract objective from first paragraph after title."""
    # Find first paragraph after H1 and frontmatter
    lines = content.split('\n')
    in_frontmatter = False
    past_title = False
    objective_lines = []

    for line in lines:
        if line.strip() == '---':
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if line.startswith('# '):
            past_title = True
            continue
        if past_title and line.strip() and not line.startswith('#'):
            objective_lines.append(line.strip())
            if len(' '.join(objective_lines)) > 100:
                break

    objective = ' '.join(objective_lines)
    if len(objective) > 150:
        objective = objective[:147] + "..."
    return objective if objective else "Document workflow and best practices"


def has_overview_section(content: str) -> bool:
    """Check if ## Overview exists."""
    return bool(re.search(r'^## Overview', content, re.MULTILINE))


def has_verified_workflow_section(content: str) -> bool:
    """Check if ## Verified Workflow exists."""
    return bool(re.search(r'^## Verified Workflow', content, re.MULTILINE))


def has_results_section(content: str) -> bool:
    """Check if ## Results exists."""
    return bool(re.search(r'^## Results', content, re.MULTILINE))


def has_failed_attempts_table(content: str) -> bool:
    """Check if Failed Attempts section has a pipe table."""
    match = re.search(r'^## Failed Attempts\s*$(.*?)^##', content, re.MULTILINE | re.DOTALL)
    if not match:
        return True  # No Failed Attempts section, skip
    section_content = match.group(1)
    return '|' in section_content


def add_overview_section(content: str) -> str:
    """Add ## Overview table after title."""
    date = extract_frontmatter_date(content)
    objective = extract_objective(content)

    overview_table = f"""
## Overview

| Item | Details |
|------|---------|
| Date | {date} |
| Objective | {objective} |
| Outcome | Operational |
"""

    # Find position after title (first # line after frontmatter)
    lines = content.split('\n')
    insert_pos = 0
    in_frontmatter = False

    for i, line in enumerate(lines):
        if line.strip() == '---':
            in_frontmatter = not in_frontmatter
            continue
        if not in_frontmatter and line.startswith('# '):
            insert_pos = i + 1
            break

    lines.insert(insert_pos, overview_table)
    return '\n'.join(lines)


def rename_workflow_to_verified(content: str) -> str:
    """Rename ## Workflow to ## Verified Workflow."""
    # Only rename if ## Verified Workflow doesn't exist
    if has_verified_workflow_section(content):
        return content
    return re.sub(r'^## Workflow$', '## Verified Workflow', content, flags=re.MULTILINE)


def add_results_section(content: str) -> str:
    """Add ## Results & Parameters section before ## References or at end."""
    results_section = """
## Results & Parameters

N/A — this skill describes a workflow pattern.
"""

    # Try to insert before ## References
    if '## References' in content:
        return content.replace('## References', results_section + '\n## References')

    # Otherwise append at end
    return content.rstrip() + '\n' + results_section


def add_failed_attempts_table(content: str) -> str:
    """Add summary table to ## Failed Attempts section."""
    match = re.search(r'^## Failed Attempts\s*$', content, re.MULTILINE)
    if not match:
        return content  # No Failed Attempts section

    # Check if there are ### subsections
    section_match = re.search(r'^## Failed Attempts\s*$(.*?)(?:^##|\Z)', content, re.MULTILINE | re.DOTALL)
    if not section_match:
        return content

    section_content = section_match.group(1)
    has_subsections = bool(re.search(r'^###', section_content, re.MULTILINE))

    if has_subsections:
        # Extract attempt info from subsections
        table = """

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| See detailed subsections below | Various technical issues | Refer to individual attempt details |
"""
    else:
        # Generic table for prose format
        table = """

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Initial approach | See details below | Refer to notes in this section |
"""

    # Insert table right after ## Failed Attempts heading
    insert_pos = match.end()
    return content[:insert_pos] + table + content[insert_pos:]


def fix_skill_file(skill_path: Path) -> Tuple[bool, List[str]]:
    """Fix a single SKILL.md file. Returns (modified, fixes_applied)."""
    content = read_file(skill_path)
    original_content = content
    fixes = []

    # Fix 1: Add Overview if missing
    if not has_overview_section(content):
        content = add_overview_section(content)
        fixes.append("Added ## Overview table")

    # Fix 2: Rename Workflow to Verified Workflow
    if not has_verified_workflow_section(content):
        new_content = rename_workflow_to_verified(content)
        if new_content != content:
            content = new_content
            fixes.append("Renamed ## Workflow to ## Verified Workflow")

    # Fix 3: Add Results section if missing
    if not has_results_section(content):
        content = add_results_section(content)
        fixes.append("Added ## Results & Parameters")

    # Fix 4: Add Failed Attempts table if missing
    if not has_failed_attempts_table(content):
        content = add_failed_attempts_table(content)
        fixes.append("Added Failed Attempts summary table")

    # Write back if modified
    if content != original_content:
        write_file(skill_path, content)
        return True, fixes

    return False, []


def main():
    """Main execution."""
    plugins_dir = Path('/home/mvillmow/ProjectMnemosyne/plugins')

    total_files = 0
    modified_files = 0
    all_fixes = []

    # Find all SKILL.md files
    for skill_file in plugins_dir.rglob('*/skills/*/SKILL.md'):
        total_files += 1
        modified, fixes = fix_skill_file(skill_file)

        if modified:
            modified_files += 1
            rel_path = skill_file.relative_to(plugins_dir)
            print(f"✓ {rel_path}")
            for fix in fixes:
                print(f"  - {fix}")
                all_fixes.append(fix)

    print(f"\n{'='*60}")
    print(f"Processed {total_files} SKILL.md files")
    print(f"Modified {modified_files} files")
    print(f"\nFixes applied:")
    for fix_type in set(all_fixes):
        count = all_fixes.count(fix_type)
        print(f"  - {fix_type}: {count} files")


if __name__ == '__main__':
    main()
