---
name: claude-md-doc-consolidation
description: "Trim duplicate documentation sections in CLAUDE.md by replacing verbose content with a summary + link to canonical docs. Use when: CLAUDE.md has sections duplicating docs/ content, file is too large, or consolidating multiple doc locations."
category: documentation
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | claude-md-doc-consolidation |
| **Category** | documentation |
| **Complexity** | S (Small) |
| **PR Pattern** | Edit CLAUDE.md → pre-commit (SKIP mojo-format if needed) → commit → PR |

## When to Use

- CLAUDE.md has a section that nearly duplicates content in `docs/dev/` or similar canonical docs
- CLAUDE.md is growing large (1,500+ lines) and consuming excess tokens on every context load
- Issue asks to consolidate N doc locations to 2 (CLAUDE.md summary + canonical doc)
- The canonical doc already exists and is complete

## Verified Workflow

1. **Read the target section** in CLAUDE.md (use `Grep` to find line numbers, then `Read` with offset/limit)
2. **Verify canonical doc** at `docs/dev/<topic>.md` is complete and covers everything in the CLAUDE.md section
3. **Replace with Edit tool** — swap the verbose section for the 3-5 line summary format:
   ```markdown
   ## <Section Title>

   See [docs/dev/<topic>.md](docs/dev/<topic>.md) for the complete
   <brief description of what the canonical doc covers>.
   ```
4. **Run pre-commit** — `pixi run pre-commit run --all-files`
   - If `mojo-format` fails due to GLIBC incompatibility on older Linux hosts, use `SKIP=mojo-format git commit ...`
   - All other hooks (markdownlint, trailing-whitespace, check-yaml, etc.) must pass
5. **Commit with `SKIP=mojo-format`** if no `.mojo` files were changed:
   ```bash
   SKIP=mojo-format git commit -m "docs(claude): trim <section> section to summary + link"
   ```
6. **Push and create PR** with `Closes #<issue>` in body, enable auto-merge

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `just pre-commit-all` | Used `just` command runner | `just` not in PATH on this host | Use `pixi run pre-commit run --all-files` directly |
| Full pre-commit without SKIP | Ran all hooks including mojo-format | mojo binary requires GLIBC 2.32-2.34, host has older version | Use `SKIP=mojo-format` when no `.mojo` files were changed |

## Results & Parameters

**Target section size**: ~85-115 lines → 3-5 lines (95%+ reduction)

**Canonical summary template**:
```markdown
## <Section Title>

See [docs/dev/<topic>.md](docs/dev/<topic>.md) for the complete
<tier1 description>, <tier2 description>, and
<tier3 description>.
```

**Commit command** (when no `.mojo` files changed):
```bash
SKIP=mojo-format git commit -m "$(cat <<'EOF'
docs(claude): trim <section> section to summary + link

Replaces ~N-line duplicate section in CLAUDE.md with a 3-line summary
pointing to the canonical docs/dev/<topic>.md.

Reduces CLAUDE.md token consumption on every context load.

Closes #<issue>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

**Success criteria**:
- CLAUDE.md section is ≤10 lines
- Canonical doc is complete and accurate
- All pre-commit hooks pass (except mojo-format on GLIBC-incompatible hosts)
- PR linked to issue with auto-merge enabled
