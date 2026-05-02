---
name: audit-shared-links
description: 'Audit shared documentation files for missing link-backs in a root markdown
  file. Use when: adding shared files that should appear in a Quick Links section,
  wiring a pre-commit hook to prevent drift, or implementing documentation audits
  with typed Python and pytest.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
| ----------- | ------- |
| **Skill** | audit-shared-links |
| **Category** | documentation |
| **Complexity** | Low |
| **Typical Duration** | 15–30 min |
| **Key Tools** | Edit, Write, Bash (pytest, pre-commit) |

## When to Use

- A shared documentation directory (e.g. `.claude/shared/`) has files that should be discoverable from a root file's Quick Links section
- A new file was added to the shared directory but not linked from the index/root file
- You want a pre-commit hook that prevents future link drift
- You need typed Python with pytest for a lightweight documentation validation script

## Verified Workflow

### 1. Identify missing links

Read the root file's Quick Links section and list the shared directory:

```bash
grep -n "shared/" CLAUDE.md | head -30
ls .claude/shared/
```

Compare to find files present on disk but absent from Quick Links.

### 2. Add missing entries to the root file

Edit the Quick Links / Core Guidelines list directly:

```markdown
- [Git Commit Policy](/.claude/shared/git-commit-policy.md)
- [Output Style Guidelines](/.claude/shared/output-style-guidelines.md)
- [Tool Use Optimization](/.claude/shared/tool-use-optimization.md)
```

### 3. Write the audit script (`scripts/audit_shared_links.py`)

Key functions with typed signatures:

```python
def list_shared_files(shared_dir: Path) -> List[str]:
    return sorted(
        f".claude/shared/{p.name}"
        for p in shared_dir.iterdir()
        if p.is_file() and p.suffix == ".md"
    )

def extract_quick_links_section(claude_md_content: str) -> str:
    match = re.search(
        r"^## Quick Links\b(.*?)(?=^## |\Z)",
        claude_md_content,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(0) if match else ""

def extract_linked_shared_paths(section: str) -> Set[str]:
    # Handle both absolute (/.claude/shared/foo.md) and relative links,
    # and strip optional #anchor fragments
    link_pattern = re.compile(r"\(/?\.claude/shared/([^)#\s]+)(?:#[^)]*)?\)")
    return {f".claude/shared/{m.group(1)}" for m in link_pattern.finditer(section)}
```

### 4. Write hermetic pytest tests (`tests/test_audit_shared_links.py`)

Use `TemporaryDirectory` for all file I/O — no dependency on real repo layout:

```python
def _make_shared_dir(tmp: Path, filenames: List[str]) -> Path:
    shared = tmp / ".claude" / "shared"
    shared.mkdir(parents=True)
    for name in filenames:
        (shared / name).write_text(f"# {name}")
    return shared
```

Cover: `list_shared_files`, `extract_quick_links_section`,
`extract_linked_shared_paths`, `audit`, and `main()` with 20 tests total.

### 5. Wire pre-commit hook (`.pre-commit-config.yaml`)

```yaml
- repo: local
  hooks:
    - id: audit-shared-links
      name: Audit shared/ links in CLAUDE.md
      description: Ensure every .claude/shared/*.md file is listed in CLAUDE.md Quick Links
      entry: python scripts/audit_shared_links.py
      language: system
      files: ^(CLAUDE\.md|\.claude/shared/.*)$
      pass_filenames: false
```

### 6. Verify and commit

```bash
pixi run python -m pytest tests/test_audit_shared_links.py -v   # 20 passed
python scripts/audit_shared_links.py                            # AUDIT PASSED
pixi run pre-commit run --files CLAUDE.md scripts/audit_shared_links.py
git add CLAUDE.md .pre-commit-config.yaml scripts/audit_shared_links.py tests/test_audit_shared_links.py
git commit -m "feat(docs): audit .claude/shared/ links and add missing Quick Links entries"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Regex `[^)#\s]+` as full pattern | Pattern `\(/?\.claude/shared/([^)#\s]+)\)` — stops capture at `#` but then requires `)` immediately | Links with anchors like `foo.md#section` never match because `)` comes after `#section`, not right after the filename | Use `([^)#\s]+)(?:#[^]*)?` to capture filename separately, then allow optional anchor before closing paren |

## Results & Parameters

**Audit script exit codes:**

- `0` — all `.claude/shared/*.md` files linked in Quick Links
- `1` — one or more files missing, or CLAUDE.md/shared-dir not found

**Pre-commit trigger pattern:**

```text
^(CLAUDE\.md|\.claude/shared/.*)$
```

**Regex for link extraction (handles absolute, relative, anchors):**

```python
re.compile(r"\(/?\.claude/shared/([^)#\s]+)(?:#[^)]*)?\)")
```

**Test count**: 20 unit tests, all hermetic (no real filesystem dependency).
