#!/usr/bin/env python3
"""
Migrate skills from ProjectOdyssey, ProjectScylla, and ProjectKeystone
into ProjectMnemosyne's flat skills/<name>.md format.

Usage:
    python3 scripts/migrate_ecosystem_skills.py [options]

Options:
    --dry-run       Show what would be done without creating files
    --source        Migrate from a specific source only (odyssey, scylla, keystone)
    --skill         Migrate a specific skill by name
    --force         Overwrite skills that already exist
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

TODAY = "2026-03-25"

# Source definitions: name -> (base_path, skill_glob_pattern)
# Scylla uses <category>/<skill-name>/SKILL.md; others use <skill-name>/SKILL.md
SOURCES = {
    "odyssey": Path("/home/mvillmow/Agents/Aindrea/ProjectOdyssey/.claude/skills"),
    "scylla": Path("/home/mvillmow/ProjectScylla/tests/claude-code/shared/skills"),
    "keystone": Path("/home/mvillmow/ProjectKeystone/.claude/skills"),
}

# Fields to remove from frontmatter during migration
FIELDS_TO_REMOVE = {"mcp_fallback", "agent", "tier", "source", "phase"}

# Category mapping table: source-category -> target-category
CATEGORY_MAP = {
    "github": "tooling",
    "worktree": "tooling",
    "agent": "tooling",
    "plan": "tooling",
    "generation": "tooling",
    "workflow": "tooling",
    "other": "tooling",
    "ci": "ci-cd",
    "phase": "ci-cd",
    "cicd": "ci-cd",
    "mojo": "architecture",
    "doc": "documentation",
    "documentation": "documentation",
    "quality": "evaluation",
    "review": "evaluation",
    "testing": "testing",
    "training": "training",
    "analysis": "optimization",
    "ml": "optimization",
    "example": "tooling",
}

# Deduplication priority: primary source first
PRIORITY_ORDER = ["scylla", "keystone", "odyssey"]

# Required section titles and their stub generators
# Each value is (check_pattern, stub_markdown_generator)
REQUIRED_SECTIONS = {
    "overview": r"## Overview",
    "when_to_use": r"## When to Use",
    "verified_workflow": r"## Verified Workflow",
    "failed_attempts": r"## Failed Attempts",
    "results_parameters": r"## Results & Parameters",
}

# Path generalization patterns: (pattern, replacement)
# Order matters: longer patterns first
PATH_GENERALIZATIONS = [
    # pixi run mojo -> must come before pixi run
    (r"pixi run mojo", "<package-manager> run mojo"),
    (r"pixi run", "<package-manager> run"),
    # ProjectOdyssey paths
    (r"/home/mvillmow/[^\s\"'`]*/ProjectOdyssey/", "<project-root>/"),
    (r"/home/mvillmow/Agents/Aindrea/ProjectOdyssey/", "<project-root>/"),
    # ProjectScylla paths
    (r"/home/mvillmow/[^\s\"'`]*/ProjectScylla/", "<project-root>/"),
    (r"/home/mvillmow/ProjectScylla/", "<project-root>/"),
    # ProjectKeystone paths
    (r"/home/mvillmow/[^\s\"'`]*/ProjectKeystone/", "<project-root>/"),
    (r"/home/mvillmow/ProjectKeystone/", "<project-root>/"),
]


# ---------------------------------------------------------------------------
# Frontmatter parsing (manual, no yaml dependency)
# ---------------------------------------------------------------------------

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter from markdown content.

    Returns (frontmatter_dict, body_text).
    If no frontmatter is found, returns ({}, content).
    """
    if not content.startswith("---"):
        return {}, content

    # Find closing ---
    rest = content[3:]
    end_idx = rest.find("\n---")
    if end_idx == -1:
        return {}, content

    fm_text = rest[:end_idx].strip()
    body = rest[end_idx + 4:].lstrip("\n")

    frontmatter = {}
    for line in fm_text.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            # Handle quoted strings
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            # Handle empty values
            if val == "":
                val = None
            frontmatter[key] = val

    return frontmatter, body


def frontmatter_to_yaml(frontmatter: dict) -> str:
    """Serialize frontmatter dict back to YAML block."""
    lines = []
    # Emit in a defined order for readability
    ordered_keys = [
        "name", "description", "category", "date", "version",
        "user-invocable", "verification", "tags",
    ]
    emitted = set()
    for key in ordered_keys:
        if key in frontmatter:
            val = frontmatter[key]
            lines.append(_format_yaml_value(key, val))
            emitted.add(key)
    # Emit any remaining keys not in the canonical order
    for key, val in frontmatter.items():
        if key not in emitted:
            lines.append(_format_yaml_value(key, val))
    return "\n".join(lines)


def _format_yaml_value(key: str, val) -> str:
    """Format a single YAML key-value pair."""
    if val is None:
        return f"{key}:"
    if isinstance(val, list):
        return f"{key}: []"
    val_str = str(val)
    # Quote strings that contain special chars or look like they need quoting
    needs_quote = (
        ":" in val_str
        or "#" in val_str
        or val_str.startswith("{")
        or val_str.startswith("[")
        or val_str.lower() in ("true", "false", "null", "yes", "no")
        or not val_str
    )
    if needs_quote and not (val_str.startswith('"') and val_str.endswith('"')):
        escaped = val_str.replace('"', '\\"')
        return f'{key}: "{escaped}"'
    return f"{key}: {val_str}"


# ---------------------------------------------------------------------------
# Category mapping
# ---------------------------------------------------------------------------

def map_category(source_category: Optional[str], scylla_category: Optional[str]) -> str:
    """Map a source category to a Mnemosyne category."""
    # If this came from Scylla, the directory IS the category
    if scylla_category is not None:
        mapped = CATEGORY_MAP.get(scylla_category.lower(), "tooling")
        return mapped

    if source_category is None:
        return "tooling"

    cat_lower = source_category.lower()
    return CATEGORY_MAP.get(cat_lower, "tooling")


# ---------------------------------------------------------------------------
# Content transformations
# ---------------------------------------------------------------------------

def generalize_paths(content: str) -> str:
    """Replace hardcoded project paths with generic placeholders."""
    for pattern, replacement in PATH_GENERALIZATIONS:
        content = re.sub(pattern, replacement, content)
    return content


def rename_workflow_section(body: str) -> str:
    """Rename '## Workflow' to '## Verified Workflow' if needed."""
    # Only rename bare "## Workflow" lines (not "## Workflow\n### ..." etc.)
    # Also handles "## Workflow\n" at end of string
    body = re.sub(r"^## Workflow\b", "## Verified Workflow", body, flags=re.MULTILINE)
    return body


def has_section(body: str, pattern: str) -> bool:
    """Check if a section heading exists in the body."""
    return bool(re.search(pattern, body, re.MULTILINE))


def add_missing_sections(body: str, skill_name: str) -> str:
    """Add stub sections for any required sections that are missing."""

    # Overview table stub
    if not has_section(body, r"^## Overview"):
        overview_stub = (
            "\n## Overview\n\n"
            "| Attribute | Value |\n"
            "|-----------|-------|\n"
            f"| **Date** | {TODAY} |\n"
            "| **Objective** | (fill in objective) |\n"
            "| **Outcome** | (fill in outcome) |\n"
        )
        # Insert before first section heading or at top of body
        first_heading = re.search(r"^#", body, re.MULTILINE)
        if first_heading:
            pos = first_heading.start()
            body = body[:pos] + overview_stub + "\n" + body[pos:]
        else:
            body = overview_stub + "\n" + body

    # When to Use stub
    if not has_section(body, r"^## When to Use"):
        when_stub = (
            "\n## When to Use\n\n"
            "- (fill in trigger conditions)\n"
        )
        body = _insert_before_verified_workflow(body, when_stub)

    # Verified Workflow with Quick Reference sub-section
    if not has_section(body, r"^## Verified Workflow"):
        workflow_stub = (
            "\n## Verified Workflow\n\n"
            "### Quick Reference\n\n"
            "```bash\n"
            "# (fill in quick reference commands)\n"
            "```\n"
        )
        body = _insert_before_failed_attempts(body, workflow_stub)
    else:
        # Verified Workflow exists; ensure Quick Reference subsection exists inside it
        if not has_section(body, r"^### Quick Reference"):
            # Insert Quick Reference right after ## Verified Workflow heading
            body = re.sub(
                r"(^## Verified Workflow\b.*?\n)",
                (
                    r"\1\n"
                    "### Quick Reference\n\n"
                    "```bash\n"
                    "# (fill in quick reference commands)\n"
                    "```\n\n"
                ),
                body,
                count=1,
                flags=re.MULTILINE,
            )

    # Failed Attempts stub
    if not has_section(body, r"^## Failed Attempts"):
        failed_stub = (
            "\n## Failed Attempts\n\n"
            "| Attempt | What Was Tried | Why It Failed | Lesson Learned |\n"
            "|---------|----------------|---------------|----------------|\n"
            "| N/A | Direct approach worked | N/A | Solution was straightforward |\n"
        )
        body = _insert_before_results(body, failed_stub)

    # Results & Parameters stub
    if not has_section(body, r"^## Results & Parameters"):
        results_stub = (
            "\n## Results & Parameters\n\n"
            "- (fill in key parameters and outcomes)\n"
        )
        body = body.rstrip() + "\n" + results_stub + "\n"

    return body


def _insert_before_verified_workflow(body: str, stub: str) -> str:
    """Insert stub before ## Verified Workflow, or before ## Failed Attempts, or at end."""
    for pattern in [r"^## Verified Workflow", r"^## Failed Attempts", r"^## Results"]:
        m = re.search(pattern, body, re.MULTILINE)
        if m:
            return body[:m.start()] + stub + "\n" + body[m.start():]
    return body.rstrip() + "\n" + stub + "\n"


def _insert_before_failed_attempts(body: str, stub: str) -> str:
    """Insert stub before ## Failed Attempts or ## Results, or at end."""
    for pattern in [r"^## Failed Attempts", r"^## Results"]:
        m = re.search(pattern, body, re.MULTILINE)
        if m:
            return body[:m.start()] + stub + "\n" + body[m.start():]
    return body.rstrip() + "\n" + stub + "\n"


def _insert_before_results(body: str, stub: str) -> str:
    """Insert stub before ## Results & Parameters, or at end."""
    m = re.search(r"^## Results", body, re.MULTILINE)
    if m:
        return body[:m.start()] + stub + "\n" + body[m.start():]
    return body.rstrip() + "\n" + stub + "\n"


def remove_repo_specific_fields(frontmatter: dict) -> dict:
    """Remove repo-specific fields from frontmatter."""
    return {k: v for k, v in frontmatter.items() if k not in FIELDS_TO_REMOVE}


def build_target_frontmatter(
    frontmatter: dict,
    skill_name: str,
    scylla_category: Optional[str],
) -> dict:
    """Build the final frontmatter dict for the target file."""
    cleaned = remove_repo_specific_fields(frontmatter)

    # Ensure required fields
    cleaned.setdefault("name", skill_name)
    cleaned.setdefault("description", f"Skill: {skill_name}")

    # Map category
    source_category = cleaned.get("category")
    cleaned["category"] = map_category(source_category, scylla_category)

    # Add missing standard fields
    cleaned.setdefault("date", TODAY)
    cleaned.setdefault("version", "1.0.0")
    cleaned.setdefault("user-invocable", "false")
    cleaned.setdefault("verification", "unverified")
    cleaned.setdefault("tags", [])

    return cleaned


def transform_skill(
    content: str,
    skill_name: str,
    scylla_category: Optional[str],
) -> str:
    """
    Apply all transformations to a SKILL.md content and return the
    resulting flat markdown with updated frontmatter.
    """
    frontmatter, body = parse_frontmatter(content)

    # Build target frontmatter
    target_fm = build_target_frontmatter(frontmatter, skill_name, scylla_category)

    # Transform body
    body = rename_workflow_section(body)
    body = generalize_paths(body)
    body = add_missing_sections(body, skill_name)

    # Assemble final content
    fm_yaml = frontmatter_to_yaml(target_fm)
    result = f"---\n{fm_yaml}\n---\n{body}"
    if not result.endswith("\n"):
        result += "\n"
    return result


# ---------------------------------------------------------------------------
# Skill discovery
# ---------------------------------------------------------------------------

def discover_odyssey_skills() -> list[tuple[str, Path, None]]:
    """
    Discover skills from ProjectOdyssey.
    Format: <skill-name>/SKILL.md
    Returns list of (skill_name, skill_md_path, scylla_category=None)
    """
    base = SOURCES["odyssey"]
    if not base.exists():
        return []

    skills = []
    for item in sorted(base.iterdir()):
        if not item.is_dir():
            continue
        if item.name.startswith("."):
            continue
        skill_md = item / "SKILL.md"
        if skill_md.exists():
            skills.append((item.name, skill_md, None))
    return skills


def discover_scylla_skills() -> list[tuple[str, Path, str]]:
    """
    Discover skills from ProjectScylla.
    Format: <category>/<skill-name>/SKILL.md
    Returns list of (skill_name, skill_md_path, scylla_category)
    """
    base = SOURCES["scylla"]
    if not base.exists():
        return []

    skills = []
    for category_dir in sorted(base.iterdir()):
        if not category_dir.is_dir():
            continue
        if category_dir.name.startswith("."):
            continue
        category = category_dir.name

        # Handle nested tiers (e.g., other/tier-1/, other/tier-2/)
        for item in sorted(category_dir.iterdir()):
            if not item.is_dir():
                continue
            if item.name.startswith("."):
                continue

            # Check for nested tier directories
            skill_md = item / "SKILL.md"
            if skill_md.exists():
                skills.append((item.name, skill_md, category))
            else:
                # Look one level deeper (tier-1/skill-name/SKILL.md)
                for subitem in sorted(item.iterdir()):
                    if not subitem.is_dir():
                        continue
                    sub_skill_md = subitem / "SKILL.md"
                    if sub_skill_md.exists():
                        skills.append((subitem.name, sub_skill_md, category))

    return skills


def discover_keystone_skills() -> list[tuple[str, Path, None]]:
    """
    Discover skills from ProjectKeystone.
    Format: <skill-name>/SKILL.md (or <skill-name>/<sub>/SKILL.md for nested)
    Returns list of (skill_name, skill_md_path, scylla_category=None)
    """
    base = SOURCES["keystone"]
    if not base.exists():
        return []

    skills = []
    for item in sorted(base.iterdir()):
        if not item.is_dir():
            continue
        if item.name.startswith("."):
            continue

        skill_md = item / "SKILL.md"
        if skill_md.exists():
            skills.append((item.name, skill_md, None))
        else:
            # Look for nested skills (e.g., tier-1/analyze-code-structure/SKILL.md)
            for subitem in sorted(item.iterdir()):
                if not subitem.is_dir():
                    continue
                sub_skill_md = subitem / "SKILL.md"
                if sub_skill_md.exists():
                    skills.append((subitem.name, sub_skill_md, None))

    return skills


def get_content_size(path: Path) -> int:
    """Return content size of a SKILL.md file (for prefer-most-content logic)."""
    try:
        return path.stat().st_size
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def build_skill_registry(
    source_filter: Optional[str] = None,
    skill_filter: Optional[str] = None,
) -> dict[str, tuple[str, Path, Optional[str]]]:
    """
    Build a deduplicated registry of skills to migrate.
    Keys are skill names; values are (source, skill_md_path, scylla_category).

    Deduplication strategy:
    - Primary: scylla
    - Fill gaps: keystone
    - Fill remaining: odyssey
    - If same skill in multiple repos, prefer the one with most content
    """
    all_skills: dict[str, list[tuple[str, Path, Optional[str]]]] = {}

    sources_to_scan = PRIORITY_ORDER
    if source_filter:
        sources_to_scan = [source_filter]

    for source in sources_to_scan:
        if source == "scylla":
            candidates = discover_scylla_skills()
        elif source == "keystone":
            candidates = discover_keystone_skills()
        elif source == "odyssey":
            candidates = discover_odyssey_skills()
        else:
            continue

        for skill_name, skill_path, scylla_cat in candidates:
            if skill_filter and skill_name != skill_filter:
                continue
            if skill_name not in all_skills:
                all_skills[skill_name] = []
            all_skills[skill_name].append((source, skill_path, scylla_cat))

    # Resolve duplicates: prefer priority order; if tie on source, prefer larger content
    registry: dict[str, tuple[str, Path, Optional[str]]] = {}
    for skill_name, candidates in all_skills.items():
        # Sort by: priority order first, then size descending
        def sort_key(c: tuple[str, Path, Optional[str]]) -> tuple[int, int]:
            source_idx = PRIORITY_ORDER.index(c[0]) if c[0] in PRIORITY_ORDER else 99
            size = -get_content_size(c[1])  # negative for descending
            return (source_idx, size)

        candidates.sort(key=sort_key)
        registry[skill_name] = candidates[0]

    return registry


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

def migrate_skill(
    skill_name: str,
    source: str,
    skill_path: Path,
    scylla_category: Optional[str],
    dry_run: bool = False,
    force: bool = False,
) -> str:
    """
    Migrate a single skill.

    Returns:
        "skipped"  - skill already exists in target and force=False
        "migrated" - skill was successfully written
        "failed"   - an error occurred
    """
    target_path = SKILLS_DIR / f"{skill_name}.md"

    if target_path.exists() and not force:
        return "skipped"

    try:
        content = skill_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"  ERROR reading {skill_path}: {e}", file=sys.stderr)
        return "failed"

    try:
        transformed = transform_skill(content, skill_name, scylla_category)
    except Exception as e:
        print(f"  ERROR transforming {skill_name}: {e}", file=sys.stderr)
        return "failed"

    action = "would write" if dry_run else "writing"
    src_label = f"{source}:{scylla_category}/{skill_name}" if scylla_category else f"{source}:{skill_name}"
    print(f"  {action}: {src_label} -> skills/{skill_name}.md")

    if not dry_run:
        try:
            SKILLS_DIR.mkdir(parents=True, exist_ok=True)
            target_path.write_text(transformed, encoding="utf-8")
        except OSError as e:
            print(f"  ERROR writing {target_path}: {e}", file=sys.stderr)
            return "failed"

    return "migrated"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate skills from ProjectOdyssey, ProjectScylla, and ProjectKeystone "
            "into ProjectMnemosyne's flat skills/<name>.md format."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without creating files",
    )
    parser.add_argument(
        "--source",
        choices=["odyssey", "scylla", "keystone"],
        default=None,
        help="Migrate from a specific source only",
    )
    parser.add_argument(
        "--skill",
        default=None,
        metavar="SKILL_NAME",
        help="Migrate a specific skill by name",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite skills that already exist in target",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.dry_run:
        print("DRY RUN — no files will be written\n")

    # Build the deduped registry
    registry = build_skill_registry(
        source_filter=args.source,
        skill_filter=args.skill,
    )

    if not registry:
        print("No skills found matching the given filters.")
        return 0

    print(f"Found {len(registry)} skill(s) to process.\n")

    counts = {"migrated": 0, "skipped": 0, "failed": 0}

    for skill_name in sorted(registry):
        source, skill_path, scylla_cat = registry[skill_name]
        result = migrate_skill(
            skill_name=skill_name,
            source=source,
            skill_path=skill_path,
            scylla_category=scylla_cat,
            dry_run=args.dry_run,
            force=args.force,
        )
        counts[result] += 1

    print(f"\n{'--- DRY RUN SUMMARY ---' if args.dry_run else '--- SUMMARY ---'}")
    print(f"  Succeeded : {counts['migrated']}")
    print(f"  Skipped   : {counts['skipped']}")
    print(f"  Failed    : {counts['failed']}")

    return 1 if counts["failed"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
