---
name: installation-md-ide-setup
description: 'Extend an installation.md with IDE setup section and tighten prerequisites
  version constraints. Use when: an installation doc lacks editor/IDE guidance, VS
  Code Mojo extension steps are missing, or prerequisites need explicit version numbers.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | installation-md-ide-setup |
| **Category** | documentation |
| **Trigger** | Installation docs missing IDE/editor guidance or version constraints in prerequisites |
| **Output** | Expanded installation.md with `## IDE Setup` section and tightened prerequisites |
| **Validated On** | ML Odyssey `docs/getting-started/installation.md` (issue #3918) |

## When to Use

- An `installation.md` exists with real content but no IDE or editor setup section
- A getting-started guide is missing VS Code extension installation steps
- Prerequisites list tools without version numbers (e.g. "Git" with no version)
- A quickstart or README links to installation.md expecting IDE coverage
- Issue asks to "add IDE setup" or "cover editor configuration"

## Verified Workflow

### Step 1: Read the existing installation.md and related shared docs

Read the target file alongside any shared install reference (e.g. `shared/INSTALL.md`,
`tools/INSTALL.md`) to understand what's already covered and what's missing:

```bash
# Read in parallel
Read docs/getting-started/installation.md
Read shared/INSTALL.md
Read tools/INSTALL.md
```

Also read the issue with `gh issue view <n> --comments` to confirm scope.

### Step 2: Identify gaps in prerequisites

Scan the `## Prerequisites` section for tools listed without version constraints.
For each, add the minimum version. Common additions:

- `Pixi` → `Pixi >= 0.24`
- `Git` → `Git >= 2.x (any modern 2.x release is sufficient)`

Keep the note short — one clause per bullet is enough.

### Step 3: Write the IDE Setup section

Insert `## IDE Setup` **before** `## Troubleshooting`. Standard subsections:

#### VS Code

```markdown
### VS Code

Install the **Mojo** extension from the VS Code marketplace:

1. Open VS Code
2. Press `Ctrl+Shift+X` to open Extensions
3. Search for **Mojo** (publisher: Modular)
4. Click **Install**

The extension provides syntax highlighting, code completion, and inline diagnostics for `.mojo`
and `.🔥` files.

**Configure the formatter** to use Pixi's Mojo by adding the following to
`.vscode/settings.json` in the repository root:

```json
{
    "mojo.mojoPath": "${workspaceFolder}/.pixi/envs/default/bin/mojo"
}
```

Verify the extension is using the correct Mojo version by checking
**View → Output → Mojo Language Server**.
```

#### Other Editors

```markdown
### Other Editors

For editors with LSP support, point the Mojo LSP server to:

```text
.pixi/envs/default/bin/mojo-lsp-server
```

Set the formatter to:

```bash
pixi run mojo format <file>
```
```

### Step 4: Run markdownlint

```bash
pixi run npx markdownlint-cli2 docs/getting-started/installation.md
```

This is the reliable path in ML Odyssey (npx is available via the pixi env). If it reports
`0 error(s)`, proceed. If `npx: command not found`, fall back to pre-commit:

```bash
pixi run pre-commit run markdownlint-cli2 --files docs/getting-started/installation.md
```

### Step 5: Commit and PR

Stage only the target file:

```bash
git add docs/getting-started/installation.md
git commit -m "docs(installation): add IDE setup section and tighten prerequisites

Add VS Code Mojo extension setup instructions and LSP configuration
for other editors. Tighten Prerequisites to include Pixi >= 0.24
version requirement and clarify Git 2.x note.

Closes #<n>"
git push -u origin <branch>
gh pr create --title "docs(installation): add IDE setup section and tighten prerequisites" \
  --body "$(cat <<'EOF'
## Summary

- Add \`## IDE Setup\` section with VS Code Mojo extension install steps
- Add LSP configuration for other editors
- Tighten prerequisites with version constraints

Closes #<n>
EOF
)"
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `Skill` tool for commit+push+PR | Invoked `commit-commands:commit-push-pr` skill | Skill tool denied in `don't ask` permission mode | Fall back to direct `git add` + `git commit` + `git push` + `gh pr create` commands |
| Checking `shared/INSTALL.md` for content to copy | Read shared INSTALL.md hoping for IDE section to lift | Shared INSTALL.md focuses on Docker/pixi install, not IDE config | Write IDE Setup from scratch using standard VS Code + LSP patterns |

## Results & Parameters

### Minimal prerequisites bullets

```markdown
- **Git** >= 2.x (any modern Git 2.x release is sufficient)
- **Pixi** >= 0.24 package manager (installation steps below)
```

### VS Code settings.json path for Pixi-managed Mojo

```json
{
    "mojo.mojoPath": "${workspaceFolder}/.pixi/envs/default/bin/mojo"
}
```

### LSP server path (generic, Pixi layout)

```text
.pixi/envs/default/bin/mojo-lsp-server
```

### markdownlint command (ML Odyssey — npx available)

```bash
pixi run npx markdownlint-cli2 <file>
```

### Section insertion point

Insert `## IDE Setup` immediately before `## Troubleshooting` so the reading order
follows: install → verify → optional alternatives → IDE → troubleshoot.
