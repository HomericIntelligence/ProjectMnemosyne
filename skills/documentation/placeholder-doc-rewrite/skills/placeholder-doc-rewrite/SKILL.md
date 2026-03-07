---
name: placeholder-doc-rewrite
description: "Replace placeholder documentation with accurate, verified content grounded in the actual codebase. Use when: a doc file contains stub text, a getting-started guide needs real commands, or a quickstart links to non-existent paths."
category: documentation
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | placeholder-doc-rewrite |
| **Category** | documentation |
| **Trigger** | Placeholder docs with stub text; quickstart/installation guides needing real content |
| **Output** | Verified, linting-compliant markdown replacing the placeholder |
| **Validated On** | ML Odyssey `docs/getting-started/quickstart.md` (issue #3305) |

## When to Use

- A markdown file contains stub text like "More examples.", "Step 1/2/3", `import ml_odyssey`
- A README or navigation page links to a doc that was never written
- An issue asks to "write a real quickstart" or "replace placeholder"
- Installation or getting-started guides reference commands/paths that may not exist

## Verified Workflow

### Step 1: Read the placeholder and related docs in parallel

Read the target placeholder alongside any adjacent docs it references (e.g. `installation.md`,
`first_model.md`) and the issue body with `gh issue view <n> --comments`.

```bash
gh issue view 3305 --comments
```

Use `Read` on all related files in a single parallel call, not sequentially.

### Step 2: Verify all paths and imports before writing

Before writing any command or import path, confirm it exists:

- Use `Glob` to verify file paths mentioned in the doc
- Use `Read` on `__init__.mojo` / package index files to confirm actual exports
- Use `Bash ls` on directories referenced in code examples

This prevents documenting paths or APIs that don't exist.

### Step 3: Write the replacement doc

Structure the content around what the issue specifies. For quickstarts, the standard
sections are: Prerequisites, Clone/Install, Verify Environment, Run First Test,
Minimal Usage Example, What's Next.

Keep code examples minimal and executable — one file, real imports, real output.

### Step 4: Validate markdown before committing

`pixi run npx markdownlint-cli2` is unreliable (npx often not in pixi env).
Use pre-commit instead:

```bash
pixi run pre-commit run markdownlint-cli2 --files docs/path/to/file.md
```

### Step 5: Commit and PR

Stage only the target file (not backup files, not the prompt file):

```bash
git add docs/getting-started/quickstart.md
git commit -m "docs(getting-started): write real quickstart.md

<body>

Closes #<n>"
git push -u origin <branch>
gh pr create --title "..." --body "..." --label "documentation"
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `pixi run npx markdownlint-cli2 <file>` | Run markdownlint via npx inside pixi env | `npx: command not found` — npx not installed in the pixi conda env | Use `pixi run pre-commit run markdownlint-cli2 --files <file>` instead |
| Running pixi command as background task | Used `run_in_background=true` for markdownlint | Command took 3+ minutes just for pixi env init, causing repeated timeouts | Run markdownlint synchronously with a generous timeout (120s+), not in background |
| Documenting APIs from `shared/EXAMPLES.md` | Copied import examples from the EXAMPLES doc | EXAMPLES.md uses aspirational/planned APIs, not what's actually implemented | Always read `__init__.mojo` or package index to find real exports |

## Results & Parameters

### Minimal Usage Example Pattern

A quickstart usage example should:

1. Import from the actual package index (read `__init__.mojo` first)
2. Use 3–5 lines of real, runnable code
3. Show expected terminal output as a `text` code block

```mojo
from shared.core import ExTensor, zeros, ones

fn main() raises:
    var shape = List[Int]()
    shape.append(5)
    var t = zeros(shape, DType.float32)
    print("numel:", t.numel())
```

### Markdown Lint Command (Reliable)

```bash
pixi run pre-commit run markdownlint-cli2 --files <path/to/file.md>
```

### First-Test Selection Criteria

Pick a test that is:

- Self-contained (no external datasets, no network)
- Fast (< 30 seconds)
- Exercises a core primitive visible to new users

For ML Odyssey: `tests/shared/core/test_creation.mojo` satisfies all three.
