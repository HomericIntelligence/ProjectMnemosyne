#!/usr/bin/env python3
"""
Migrate legacy skills from flat/category-based format to plugin format under skills/<category>/<name>/.

Legacy skills live in:
  - skills/<name>/SKILL.md  (flat format, most common)
  - skills/<category>/<name>/SKILL.md  (already partially categorized)

Target format (plugin structure):
  skills/<category>/<name>/
  ├── .claude-plugin/
  │   └── plugin.json
  ├── skills/<name>/
  │   └── SKILL.md
  └── references/
      └── notes.md  (if it existed)

Usage:
    python3 scripts/migrate_to_skills.py [--dry-run]
"""

import json
import re
import shutil
import sys
from pathlib import Path


# Category mapping for non-standard values
CATEGORY_MAP = {
    "workflow": "tooling",
    "refactoring": "architecture",
    "automation": "tooling",
    "docs": "documentation",
}

VALID_CATEGORIES = {
    "training",
    "evaluation",
    "optimization",
    "debugging",
    "architecture",
    "tooling",
    "ci-cd",
    "testing",
    "documentation",
}

# These are category directories inside skills/ (not skill names)
CATEGORY_DIRS = {"testing", "tooling", "architecture", "ci-cd"}


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter fields from SKILL.md content."""
    if not content.startswith("---"):
        return {}

    end = content.find("---", 3)
    if end == -1:
        return {}

    frontmatter_text = content[3:end].strip()
    result = {}

    for line in frontmatter_text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip().strip('"').strip("'")

    return result


def infer_category_from_skill_md(skill_md_path: Path) -> str | None:
    """Try to infer category from SKILL.md frontmatter."""
    if not skill_md_path.exists():
        return None

    content = skill_md_path.read_text(encoding="utf-8")
    fm = extract_frontmatter(content)

    cat = fm.get("category")
    if cat:
        cat = CATEGORY_MAP.get(cat, cat)
        if cat in VALID_CATEGORIES:
            return cat

    return None


def infer_category_from_name(name: str) -> str:
    """Infer category from skill name keywords."""
    name_lower = name.lower()

    if any(k in name_lower for k in ("train", "grpo", "finetune", "lora")):
        return "training"
    if any(k in name_lower for k in ("eval", "judge", "metric", "benchmark", "score")):
        return "evaluation"
    if any(k in name_lower for k in ("optim", "speed", "perf", "cache", "simd")):
        return "optimization"
    if any(k in name_lower for k in ("debug", "fix", "bug", "error", "fail", "crash", "corrupt")):
        return "debugging"
    if any(k in name_lower for k in ("architect", "design", "refactor", "consolidat", "unify", "pattern", "struct")):
        return "architecture"
    if any(k in name_lower for k in ("ci", "cd", "workflow", "pipeline", "action", "deploy", "docker", "precommit", "pre-commit", "github-action")):
        return "ci-cd"
    if any(k in name_lower for k in ("test", "coverage", "lint", "ruff", "mypy", "type")):
        return "testing"
    if any(k in name_lower for k in ("doc", "paper", "readme", "latex", "academic")):
        return "documentation"

    return "tooling"


def get_category(legacy_dir: Path) -> str:
    """Determine category for a legacy skill."""
    # 1. Try plugin.json
    plugin_json = legacy_dir / "plugin.json"
    if plugin_json.exists():
        try:
            data = json.loads(plugin_json.read_text())
            cat = data.get("category", "")
            cat = CATEGORY_MAP.get(cat, cat)
            if cat in VALID_CATEGORIES:
                return cat
        except (json.JSONDecodeError, KeyError):
            pass

    # 2. Try SKILL.md frontmatter
    skill_md = legacy_dir / "SKILL.md"
    cat = infer_category_from_skill_md(skill_md)
    if cat:
        return cat

    # 3. Infer from name
    return infer_category_from_name(legacy_dir.name)


def build_plugin_json(legacy_dir: Path, name: str, category: str) -> dict:
    """Build plugin.json from existing data or defaults."""
    # Try existing plugin.json
    existing = legacy_dir / "plugin.json"
    if existing.exists():
        try:
            data = json.loads(existing.read_text())
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    # Try SKILL.md for description/date
    skill_md = legacy_dir / "SKILL.md"
    fm = {}
    if skill_md.exists():
        fm = extract_frontmatter(skill_md.read_text(encoding="utf-8"))

    description = (
        data.get("description")
        or fm.get("description")
        or f"Skill: {name}. Use when working with {name.replace('-', ' ')}."
    )

    # Ensure description meets minimum length
    if len(description) < 20:
        description = f"Skill: {name}. {description}"

    tags = data.get("tags", [])
    if not tags:
        # Build basic tags from name
        tags = [t for t in name.split("-") if len(t) > 2]

    date = data.get("date") or data.get("created") or fm.get("date") or "2026-01-01"

    return {
        "name": name,
        "version": data.get("version", "1.0.0"),
        "description": description,
        "category": category,
        "date": date,
        "tags": tags,
    }


def migrate_flat_skill(legacy_dir: Path, skills_root: Path, dry_run: bool = False) -> bool:
    """Migrate a flat legacy skill (skills/<name>/) to plugin format.

    Returns True if migration was performed (or would be in dry_run).
    """
    name = legacy_dir.name
    category = get_category(legacy_dir)
    target_dir = skills_root / category / name

    # Check if target already exists (plugin format wins)
    if (target_dir / ".claude-plugin" / "plugin.json").exists():
        print(f"  SKIP {name}: already exists in plugin format at {category}/{name}")
        return False

    in_place = target_dir.resolve() == legacy_dir.resolve()
    print(f"  MIGRATE {name} → {category}/{name}/" + (" (in-place)" if in_place else ""))

    if dry_run:
        return True

    # Create target structure
    target_dir.mkdir(parents=True, exist_ok=True)

    if in_place:
        # Skill is already in the right category dir — just add the plugin structure
        # 1. Create skills/<name>/SKILL.md if SKILL.md exists at top level
        skill_src = legacy_dir / "SKILL.md"
        skill_dest_dir = target_dir / "skills" / name
        if skill_src.exists() and not (skill_dest_dir / "SKILL.md").exists():
            skill_dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(skill_src, skill_dest_dir / "SKILL.md")

        # 2. Create .claude-plugin/plugin.json
        plugin_json_data = build_plugin_json(legacy_dir, name, category)
        plugin_dir = target_dir / ".claude-plugin"
        plugin_dir.mkdir(exist_ok=True)
        (plugin_dir / "plugin.json").write_text(
            json.dumps(plugin_json_data, indent=2) + "\n",
            encoding="utf-8",
        )
        # references/ already in place, no need to copy
    else:
        # Different location — copy contents to target
        # 1. Copy SKILL.md → skills/<name>/SKILL.md
        skill_src = legacy_dir / "SKILL.md"
        if skill_src.exists():
            skill_dest_dir = target_dir / "skills" / name
            skill_dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(skill_src, skill_dest_dir / "SKILL.md")
        else:
            print(f"    WARNING: No SKILL.md found in {legacy_dir}")

        # 2. Create .claude-plugin/plugin.json
        plugin_json_data = build_plugin_json(legacy_dir, name, category)
        plugin_dir = target_dir / ".claude-plugin"
        plugin_dir.mkdir(exist_ok=True)
        (plugin_dir / "plugin.json").write_text(
            json.dumps(plugin_json_data, indent=2) + "\n",
            encoding="utf-8",
        )

        # 3. Copy references/ if it exists
        refs_src = legacy_dir / "references"
        if refs_src.exists() and refs_src.is_dir():
            refs_dest = target_dir / "references"
            if refs_dest.exists():
                shutil.rmtree(refs_dest)
            shutil.copytree(refs_src, refs_dest)

    return True


def find_legacy_skills(skills_root: Path) -> list[Path]:
    """Find all legacy skill directories (flat and category-based)."""
    legacy_skills = []

    for item in skills_root.iterdir():
        if not item.is_dir():
            continue
        if item.name.startswith("."):
            continue

        if item.name in CATEGORY_DIRS:
            # Category dir — recurse one level
            for sub in item.iterdir():
                if not sub.is_dir() or sub.name.startswith("."):
                    continue
                # Check if it's already plugin format
                if (sub / ".claude-plugin" / "plugin.json").exists():
                    continue
                # It's a legacy skill inside a category dir
                legacy_skills.append(sub)
        else:
            # Flat skill dir at top level
            if (item / ".claude-plugin" / "plugin.json").exists():
                # Already plugin format (shouldn't happen but skip)
                continue
            if (item / "SKILL.md").exists():
                legacy_skills.append(item)

    return sorted(legacy_skills)


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    root = Path(__file__).parent.parent
    skills_root = root / "skills"

    if not skills_root.exists():
        print(f"Skills directory not found: {skills_root}")
        return 1

    if dry_run:
        print("DRY RUN MODE — no files will be modified\n")

    legacy_skills = find_legacy_skills(skills_root)
    print(f"Found {len(legacy_skills)} legacy skills to migrate\n")

    migrated = 0
    skipped = 0

    for legacy_dir in legacy_skills:
        result = migrate_flat_skill(legacy_dir, skills_root, dry_run=dry_run)
        if result:
            migrated += 1
        else:
            skipped += 1

    print(f"\n{'='*60}")
    if dry_run:
        print(f"Would migrate: {migrated} skills")
        print(f"Would skip:    {skipped} skills (already in plugin format)")
    else:
        print(f"Migrated: {migrated} skills")
        print(f"Skipped:  {skipped} skills (already in plugin format)")
        print("\nNow cleaning up old flat/category legacy dirs...")

        # Remove old flat skill dirs and category subdirs
        for legacy_dir in legacy_skills:
            parent = legacy_dir.parent
            if parent.name in CATEGORY_DIRS:
                # legacy_dir is skills/<category>/<name>/ - remove it
                if legacy_dir.exists():
                    shutil.rmtree(legacy_dir)
                    print(f"  Removed {legacy_dir.relative_to(skills_root)}")
                # If category dir is now empty (no non-.claude-plugin children), skip removal
                # (it has the migrated plugin dirs now)
            else:
                # Flat skill - remove
                if legacy_dir.exists():
                    shutil.rmtree(legacy_dir)
                    print(f"  Removed {legacy_dir.relative_to(skills_root)}")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
