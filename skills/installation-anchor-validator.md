---
name: installation-anchor-validator
description: 'Validate anchor fragments in markdown deep-links to an installation
  guide. Use when: README or other docs link to specific sections of installation.md
  and you need CI to catch broken anchors when headings are renamed or removed.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Skill** | installation-anchor-validator |
| **Category** | documentation |
| **Complexity** | Low |
| **Typical Duration** | 30–60 min |
| **Key Tools** | Write, Edit, Bash (pytest, gh) |

## When to Use

- A repository has one or more markdown files linking to specific sections of an installation
  guide (e.g., `installation.md#prerequisites`) and you want CI to catch regressions
- Headings in an installation guide are being reorganised or renamed and you want to be
  sure all deep-links remain valid
- You are adding a lightweight anchor validation script alongside an existing `validate_links.py`
  that intentionally strips anchors for file-existence checks
- You need hermetic pytest tests that do NOT touch real repo files (TemporaryDirectory pattern)

## Verified Workflow

### Quick Reference

| Step | Command |
|------|---------|
| Run script | `python3 scripts/validate_installation_anchors.py README.md docs/getting-started/installation.md` |
| Run tests | `python3 -m pytest tests/test_validate_installation_anchors.py -v` |
| Check CI step | see `.github/workflows/link-check.yml` |

### 1. Audit the current state

Check what links to `installation.md` already exist and whether they have anchors:

```bash
grep -rn "installation\.md" README.md docs/ --include="*.md"
```

Most projects start with a plain link (no anchor). The validator will pass cleanly until
a deep-link is added, at which point it catches regressions.

### 2. Understand the existing validate_links.py

Before creating a new script, read the existing link-validation script. It likely strips
anchors intentionally (to check file existence only):

```python
# scripts/validate_links.py line ~77 — intentionally ignores anchors
link_path = link.split("#")[0]
```

Do **not** modify this script — it serves a different purpose. Create a focused, additive
script instead.

### 3. Implement heading_to_anchor (GitHub slug algorithm)

GitHub's anchor slug rules (implement in pure Python, no extra deps):

```python
import re

def heading_to_anchor(heading: str) -> str:
    slug = heading.lower()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug
```

Key edge cases to test:
- Backtick-wrapped text: `` `pixi install` fails `` → `pixi-install-fails`
- Parenthesised suffixes: `Run Tests (without shell)` → `run-tests-without-shell`
- Numbers preserved: `Step 1 Setup` → `step-1-setup`

### 4. Implement extract_headings and extract_installation_links

```python
def extract_headings(content: str) -> List[str]:
    headings = []
    for line in content.splitlines():
        match = re.match(r"^#{1,6}\s+(.*)", line)
        if match:
            headings.append(match.group(1).strip())
    return headings

def extract_installation_links(
    content: str, source_path: str
) -> List[Tuple[str, str, Optional[str]]]:
    results = []
    link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
    for line in content.splitlines():
        for match in link_pattern.finditer(line):
            target = match.group(2).strip()
            base, _, fragment = target.partition("#")
            if not base.endswith("installation.md"):
                continue
            anchor = fragment if fragment else None
            results.append((source_path, target, anchor))
    return results
```

### 5. Write the validate() function and CLI main()

```python
def validate(source_paths: List[Path], installation_path: Path) -> List[str]:
    errors: List[str] = []
    if not installation_path.exists():
        return [f"installation.md not found: {installation_path}"]
    installation_content = installation_path.read_text(encoding="utf-8")
    headings = extract_headings(installation_content)
    valid_anchors = {heading_to_anchor(h) for h in headings}
    for source_path in source_paths:
        if not source_path.exists():
            errors.append(f"Source file not found: {source_path}")
            continue
        content = source_path.read_text(encoding="utf-8")
        for src, target, anchor in extract_installation_links(content, str(source_path)):
            if anchor is None:
                continue  # plain link without anchor — always valid
            if anchor not in valid_anchors:
                errors.append(
                    f"{src}: broken anchor '#{anchor}' in '{target}' "
                    f"(valid: {sorted(valid_anchors)})"
                )
    return errors

def main(argv: List[str]) -> int:
    # If 2+ positional args: last = installation.md, rest = sources
    # If 1 positional arg: treat as installation.md, scan whole repo
    # If 0 args: use default paths
    ...
    errors = validate(source_paths, installation_path)
    if errors:
        for e in errors: logger.error(e)
        return 1
    logger.info("All installation.md anchor links are valid.")
    return 0
```

### 6. Write hermetic tests (TemporaryDirectory pattern)

Mirror the pattern from `tests/test_audit_shared_links.py`:

```python
_INSTALLATION_CONTENT = """\
# Installation

## Prerequisites

Install required tools.

## Installing Pixi

Use the install script.
"""

class TestValidate:
    def test_no_anchor_links_passes(self) -> None:
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            installation = tmp / "installation.md"
            installation.write_text(_INSTALLATION_CONTENT)
            readme = tmp / "README.md"
            readme.write_text("[Guide](installation.md)\n")
            assert validate([readme], installation) == []

    def test_invalid_anchor_fails(self) -> None:
        with TemporaryDirectory() as tmpdir:
            ...
            readme.write_text("[Guide](installation.md#nonexistent)\n")
            errors = validate([readme], installation)
            assert len(errors) == 1
            assert "nonexistent" in errors[0]
```

### 7. Add step to CI workflow

Append after the lychee step in `.github/workflows/link-check.yml`:

```yaml
- name: Validate installation.md anchor links
  run: |
    python3 scripts/validate_installation_anchors.py \
      README.md \
      docs/getting-started/installation.md
```

No secrets or user-controlled input — the step is injection-safe.

### 8. Document in scripts/README.md

Add the script to the directory listing AND add a full documentation section
(with Features, Usage, Exit Codes) immediately before `validate_links.py`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Modifying validate_links.py to check anchors | Considered extending the existing script | It intentionally strips anchors for file-existence checking; changing it would break existing callers | Create a focused additive script instead of modifying an existing one |
| Using `--include-fragments` in lychee | Considered relying solely on lychee for anchor validation | lychee validates external URLs well but internal markdown anchor resolution is better handled with a Python script that implements GitHub's exact slug algorithm | Python gives full control over the slug algorithm and produces precise error messages |
| Importing `common.py` in the new script | Considered reusing `get_repo_root()` from common.py | The script needed to be self-contained with `Path(__file__).resolve().parent.parent` for repo root detection; common.py import added complexity for a function not needed in tests | Only import shared modules when the benefit clearly outweighs the coupling |

## Results & Parameters

**Script**: `scripts/validate_installation_anchors.py`
**Tests**: `tests/test_validate_installation_anchors.py` — 33 tests, all passing
**Workflow**: `.github/workflows/link-check.yml` — new step appended after lychee

### GitHub slug algorithm — key regex

```python
slug = heading.lower()
slug = slug.replace(" ", "-")
slug = re.sub(r"[^a-z0-9\-]", "", slug)  # strip non-alphanumeric except hyphen
slug = re.sub(r"-{2,}", "-", slug)         # collapse consecutive hyphens
slug = slug.strip("-")                     # remove leading/trailing hyphens
```

### Edge cases verified

| Heading | Expected anchor |
|---------|----------------|
| `Installation` | `installation` |
| `Installing Pixi` | `installing-pixi` |
| `` `pixi install` fails with channel errors `` | `pixi-install-fails-with-channel-errors` |
| `Run Tests Directly (without interactive shell)` | `run-tests-directly-without-interactive-shell` |
| `Step 1 Setup` | `step-1-setup` |

### Test pattern — TemporaryDirectory

Use `TemporaryDirectory` (not `tmp_path` alone) for compatibility with class-based
test classes that don't use pytest fixtures:

```python
class TestValidate:
    def test_foo(self) -> None:
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            ...
```
