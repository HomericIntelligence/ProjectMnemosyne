#!/usr/bin/env python3
"""
Script to add summary tables to Failed Attempts sections.

Adds a summary table while preserving existing detailed content.
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


def has_failed_attempts_table(content: str) -> bool:
    """Check if Failed Attempts section has a pipe table."""
    match = re.search(r'^## Failed Attempts.*?$(.*?)(?:^##|\Z)', content, re.MULTILINE | re.DOTALL)
    if not match:
        return True  # No Failed Attempts section
    section_content = match.group(1)
    return '|' in section_content


def extract_attempts_from_subsections(section_content: str) -> List[dict]:
    """Extract attempt information from ### subsections."""
    attempts = []

    # Find all ### headings that look like attempts
    attempt_patterns = [
        r'###\s*❌\s*Attempt\s+\d+:\s*(.+?)$',
        r'###\s*Attempt\s+\d+:\s*(.+?)$',
        r'###\s*(.+?)$',
    ]

    for pattern in attempt_patterns:
        matches = list(re.finditer(pattern, section_content, re.MULTILINE))
        if matches:
            for match in matches[:3]:  # Max 3 attempts for table
                title = match.group(1).strip()
                attempts.append({
                    'title': title,
                    'position': match.start()
                })
            break

    return attempts


def generate_summary_table(section_content: str) -> str:
    """Generate a summary table based on section content."""

    attempts = extract_attempts_from_subsections(section_content)

    if attempts:
        # Create table with extracted attempts
        table = "\n| Attempt | Issue | Resolution |\n|---------|-------|------------|\n"
        for i, attempt in enumerate(attempts, 1):
            title = attempt['title']
            if len(title) > 50:
                title = title[:47] + "..."
            table += f"| {i}. {title} | See details below | Documented in subsections |\n"
    else:
        # Generic table for other formats
        table = """
| Attempt | Issue | Resolution |
|---------|-------|------------|
| See detailed notes below | Various approaches tried | Refer to documentation in this section |
"""

    return table


def add_failed_attempts_table(content: str) -> str:
    """Add summary table to Failed Attempts section."""

    # Match ## Failed Attempts with any suffix (& Lessons Learned, etc.)
    match = re.search(r'^## Failed Attempts.*?$', content, re.MULTILINE)
    if not match:
        return content

    # Get the section content
    section_match = re.search(r'^## Failed Attempts.*?$(.*?)(?:^##|\Z)', content, re.MULTILINE | re.DOTALL)
    if not section_match:
        return content

    section_content = section_match.group(1)

    # Generate appropriate table
    table = generate_summary_table(section_content)

    # Insert table right after ## Failed Attempts heading
    insert_pos = match.end()
    return content[:insert_pos] + table + content[insert_pos:]


def fix_skill_file(skill_path: Path) -> Tuple[bool, str]:
    """Fix a single SKILL.md file. Returns (modified, description)."""
    content = read_file(skill_path)

    if has_failed_attempts_table(content):
        return False, "Already has table"

    original_content = content
    content = add_failed_attempts_table(content)

    if content != original_content:
        write_file(skill_path, content)
        return True, "Added summary table"

    return False, "No changes needed"


def main():
    """Main execution."""
    plugins_dir = Path('/home/mvillmow/ProjectMnemosyne/plugins')

    # Plugins that still need Failed Attempts tables
    plugins_with_table_warning = [
        'evaluation/add-analysis-metric',
        'evaluation/dryrun-validation',
        'evaluation/e2e-checkpoint-resume',
        'evaluation/publication-pipeline-enhancement',
        'evaluation/processpool-rate-limit-recovery',
        'evaluation/granular-scoring-systems',
        'evaluation/parallel-metrics-integration',
        'evaluation/containerize-e2e-experiments',
        'debugging/retry-transient-errors',
        'tooling/experiment-recovery-tools',
        'tooling/review-task-orchestration',
        'architecture/refactor-for-extensibility',
        'documentation/arxiv-paper-polish',
        'documentation/paper-final-review',
        'documentation/academic-paper-qa',
        'documentation/latex-architecture-section',
        'documentation/paper-revision-workflow',
        'documentation/paper-validation-workflow',
        'documentation/paper-consolidation',
        'documentation/publication-readiness-check',
        'ci-cd/fix-ruff-linting-errors',
        'ci-cd/ci-test-failure-diagnosis',
        'ci-cd/rescue-broken-prs',
    ]

    total_files = 0
    modified_files = 0

    for plugin_path in plugins_with_table_warning:
        skill_file = plugins_dir / plugin_path / 'skills' / Path(plugin_path).name / 'SKILL.md'

        if not skill_file.exists():
            print(f"⚠ Skipping {plugin_path} - SKILL.md not found")
            continue

        total_files += 1
        modified, description = fix_skill_file(skill_file)

        if modified:
            modified_files += 1
            print(f"✓ {plugin_path} - {description}")
        else:
            print(f"  {plugin_path} - {description}")

    print(f"\n{'='*60}")
    print(f"Processed {total_files} SKILL.md files")
    print(f"Modified {modified_files} files")


if __name__ == '__main__':
    main()
