---
name: odyssey-audit-migration-coverage
description: 'Add --audit flag to a migration script to cross-reference source skills
  against a target repo and report coverage gaps. Use when: CI needs to detect porting
  gaps, migration script lacks coverage observability.'
category: tooling
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# odyssey-audit-migration-coverage

## Overview

| Item | Details |
|------|---------|
| Name | odyssey-audit-migration-coverage |
| Category | tooling |
| Source file | `scripts/migrate_odyssey_skills.py` |
| New flags | `--audit`, `--audit-skip`, `--no-color`, `--source-dir`, `--target-dir` |
| Exit codes | 0 = all present, 1 = missing skills or dir error |
| Tests | 42 unit + integration tests in `tests/scripts/test_audit_migration_coverage.py` |

## When to Use

- A migration script has no way to report what was ported vs skipped without reading stdout manually
- CI needs to detect when new skills are added to the source repo but not yet ported to the target
- You want a tabular coverage report with percentage and CI-friendly non-zero exit on gaps
- A migration tool has hardcoded source/target paths that make it untestable in isolation

## Verified Workflow

### 1. Add configurable source/target dir args

The migration script had hardcoded module-level constants. Made `find_all_skills()` accept an
optional `source_dir` parameter, and added `--source-dir` / `--target-dir` CLI args. This
unlocks isolated testing with `tmp_path` fixtures without touching the filesystem globals.

```python
def find_all_skills(source_dir: Optional[Path] = None) -> list[tuple[str, Path, Optional[str]]]:
    skills_root = source_dir if source_dir is not None else ODYSSEY_SKILLS_DIR
    ...
```

### 2. Add audit dataclasses

```python
@dataclass
class SkillAuditEntry:
    name: str
    source_path: Path
    tier: Optional[str]
    mnemosyne_category: Optional[str]  # None if not found
    status: str  # "present", "missing", "skipped"

@dataclass
class AuditResult:
    skills: list[SkillAuditEntry] = field(default_factory=list)

    @property
    def coverage_pct(self) -> float:
        auditable = self.total - self.skipped
        if auditable == 0:
            return 100.0
        return self.present / auditable * 100
```

Key design: skipped skills are excluded from the coverage denominator so a skip list doesn't
inflate or deflate the reported percentage.

### 3. Implement core audit functions

```python
def find_skill_in_mnemosyne(skill_name: str, mnemosyne_skills_dir: Path) -> Optional[str]:
    """Return the Mnemosyne category containing this skill, or None if not found."""
    if not mnemosyne_skills_dir.exists():
        return None
    for category_dir in mnemosyne_skills_dir.iterdir():
        if not category_dir.is_dir():
            continue
        skill_path = category_dir / skill_name
        if skill_path.exists() and skill_path.is_dir():
            return category_dir.name
    return None

def load_skip_list(skip_file: Path) -> set[str]:
    """Load allowlist of skill names to skip (one per line, # comments supported)."""
    if not skip_file.exists():
        return set()
    names: set[str] = set()
    for line in skip_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(line)
    return names

def run_audit(source_skills, mnemosyne_skills_dir, skip_list) -> AuditResult:
    result = AuditResult()
    seen_names: set[str] = set()
    for skill_name, skill_md_path, tier in source_skills:
        if skill_name in seen_names:
            continue  # deduplicate tier-1/tier-2 overlaps
        seen_names.add(skill_name)
        ...
```

### 4. Wire into main() with early return

```python
if args.audit:
    skip_list = load_skip_list(Path(args.audit_skip))
    result = run_audit(all_skills, target_skills_dir, skip_list)
    print_audit_table(result, no_color=args.no_color)
    print_audit_summary(result, no_color=args.no_color)
    return 1 if result.missing > 0 else 0
```

Early return before the migration loop means `--audit` and migration are mutually exclusive,
keeping the audit path simple and testable independently.

### 5. Write integration tests using subprocess

The cleanest way to test `--source-dir`/`--target-dir` is subprocess integration tests that
build real tmp_path fixture trees:

```python
def test_exit_zero_when_all_skills_present(self, tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "skill-x").mkdir(parents=True)
    (source / "skill-x" / "SKILL.md").write_text("---\nname: skill-x\n---\n")

    target = tmp_path / "target"
    (target / "skills" / "tooling" / "skill-x").mkdir(parents=True)

    proc = subprocess.run([sys.executable, SCRIPT, "--audit", "--no-color",
                           "--source-dir", str(source), "--target-dir", str(target)],
                          capture_output=True, text=True)
    assert proc.returncode == 0
```

### 6. Handle deduplication

`find_all_skills()` can return the same skill name from both tier-1 and tier-2 directories.
The audit deduplicates by name (keeping first occurrence) to avoid double-counting.

### 7. Sample output

```text
Skill                                    Category             Status
------------------------------------------------------------------------
gh-create-pr-linked                      tooling              PRESENT
blog-writer                              -                    MISSING

========================================================================
Audit Summary:
  Total skills:   83
  Present:        81
  Missing:        2
  Skipped:        0
  Coverage:       97.6%
========================================================================

FAIL: 2 skill(s) are missing from Mnemosyne.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Hardcoded paths in tests | Called `main()` directly without `--source-dir`/`--target-dir` | `find_all_skills()` used the global `ODYSSEY_SKILLS_DIR` constant, not the test's tmp_path, so 80+ real skills were scanned instead of the fixture | Make path constants overridable via function args before writing tests; subprocess integration tests are the fallback |
| First commit attempt | Staged files and ran `git commit` | Pre-commit hook ran `ruff-format-python` which reformatted both files (no errors, just style) and reported "files were modified" causing the commit to abort | Always re-stage after ruff reformats; run a second `git commit` with the same message to succeed |

## Results & Parameters

### CLI flags added

| Flag | Default | Purpose |
|------|---------|---------|
| `--audit` | off | Enable audit mode |
| `--audit-skip FILE` | `.audit-skip` | Allowlist file (one skill name per line) |
| `--no-color` | off | Disable ANSI colors |
| `--source-dir DIR` | `ODYSSEY_SKILLS_DIR` constant | Override source skills directory |
| `--target-dir DIR` | `MNEMOSYNE_DIR` constant | Override target Mnemosyne directory |

### Test coverage

- 5 tests for `find_skill_in_mnemosyne()`
- 5 tests for `load_skip_list()`
- 8 tests for `run_audit()`
- 8 tests for `AuditResult` properties
- 5 tests for `print_audit_table()`
- 4 tests for `print_audit_summary()`
- 7 integration tests for `main()` exit codes via subprocess
- **Total: 42 tests, all passing**

### Key design decisions

- Skipped skills excluded from coverage denominator (100% if all auditable skills present)
- Deduplication by name handles tier-1/tier-2 skill overlaps in source
- `--audit` is mutually exclusive with migration (early return before migration loop)
- ANSI colors via string constants that collapse to `""` when `--no-color` is set
