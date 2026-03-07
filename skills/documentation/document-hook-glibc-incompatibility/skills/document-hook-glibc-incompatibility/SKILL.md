---
name: document-hook-glibc-incompatibility
description: "Document pre-commit hook OS/runtime incompatibilities in CONTRIBUTING.md. Use when: a hook auto-skips due to host OS constraints but lacks a discoverable explanation for contributors."
category: documentation
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | document-hook-glibc-incompatibility |
| **Category** | documentation |
| **Complexity** | Low |
| **Files Changed** | `CONTRIBUTING.md` |
| **Risk** | Minimal — documentation only |

Documents the `mojo-format` pre-commit hook GLIBC incompatibility on Debian 10 / glibc < 2.32
hosts. By the time this was raised as issue #3253, a wrapper script (`scripts/mojo-format-compat.sh`)
and a full compatibility doc (`docs/dev/mojo-glibc-compatibility.md`) already existed from #3170.
The only gap was that `CONTRIBUTING.md` had no mention — contributors hitting the warning had no
self-service path to understanding it.

## When to Use

- A pre-commit hook fails (or auto-skips) on some host OSes due to system library version
  constraints, not code errors
- A wrapper/compat script already handles the incompatibility gracefully but there is no
  discoverable explanation in `CONTRIBUTING.md`
- Contributors report confusion about hook warning messages they cannot trace to their code
- An issue is filed specifically requesting CONTRIBUTING.md or CLAUDE.md documentation of
  a known hook limitation

## Verified Workflow

1. **Read the issue** — `gh issue view <number> --comments` to understand scope and check
   whether a plan already exists.

2. **Audit existing state** — before adding docs, check:
   - `.pre-commit-config.yaml` for inline comments already explaining the issue
   - `docs/dev/` for an existing compatibility doc
   - `CONTRIBUTING.md` for any existing mentions (use `grep -n "GLIBC\|glibc\|SKIP="`)
   - The wrapper/compat script if referenced in `.pre-commit-config.yaml`

3. **Determine the actual gap** — in this case the `.pre-commit-config.yaml` already had a
   5-line comment block and `docs/dev/mojo-glibc-compatibility.md` was comprehensive. Only
   `CONTRIBUTING.md` was missing a mention.

4. **Add a named subsection** to `CONTRIBUTING.md` under the "Hook Failure Policy" section:
   - Use a `####` heading so it is scannable but does not inflate the TOC
   - Include: affected OS/glibc range, the exact warning text contributors will see,
     what the hook does automatically, CI enforcement guarantee, Docker workaround,
     and a link to the full compatibility doc

5. **Validate markdown linting**:
   ```bash
   SKIP=mojo-format pixi run pre-commit run markdownlint-cli2 --all-files
   ```
   Ensure all code blocks have language specifiers, blank lines around fenced blocks and
   lists, and no lines > 120 characters.

6. **Commit with `SKIP=mojo-format`** (required on incompatible hosts):
   ```bash
   SKIP=mojo-format git commit -m "docs(contributing): document mojo-format GLIBC incompatibility"
   ```

7. **Push, create PR, enable auto-merge**:
   ```bash
   git push -u origin <branch>
   gh pr create --title "..." --body "Closes #<number>"
   gh pr merge --auto --rebase
   ```

## Key Findings

### Check existing state before writing anything

The issue plan called for changes to both `.pre-commit-config.yaml` and `CONTRIBUTING.md`.
Reading both files first revealed `.pre-commit-config.yaml` already had a complete comment
block (added in #3170). Only `CONTRIBUTING.md` needed updating — reducing scope significantly.

### Exact warning text is critical for discoverability

Contributors hitting this will search for the warning message they see. Reproducing the
exact warning text in `CONTRIBUTING.md` (copied from `docs/dev/mojo-glibc-compatibility.md`)
makes the section findable by grepping or searching the web.

### `SKIP=mojo-format` required on the host that triggered this issue

The issue was filed because the host runs Debian Buster (glibc 2.28). All commits on that
host require `SKIP=mojo-format`. The wrapper script auto-skips but pre-commit still records
a "Skipped" status that can confuse contributors.

### markdownlint: `npx` not available, use `pixi run pre-commit`

`pixi run npx markdownlint-cli2` fails with `npx: command not found` on this host.
The correct command is:
```bash
SKIP=mojo-format pixi run pre-commit run markdownlint-cli2 --all-files
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run markdownlint via `pixi run npx markdownlint-cli2` | Called `pixi run npx markdownlint-cli2 CONTRIBUTING.md` | `npx` not in PATH on this host | Use `pixi run pre-commit run markdownlint-cli2 --all-files` instead |
| Changing `.pre-commit-config.yaml` | Plan originally included adding GLIBC comment to config | File already had a full comment block from #3170 | Always read files before editing; audit existing state first |

## Results & Parameters

### Exact CONTRIBUTING.md addition (copy-paste template)

Insert after the "If a hook itself is broken" bullet list, before the next `##` section:

```markdown
#### Known Hook Incompatibility: mojo-format on Debian Buster / glibc < 2.32

The `mojo-format` hook requires **glibc 2.32+** (Debian 12 / Ubuntu 22.04 or newer).
On Debian 10 (Buster) or other hosts with glibc < 2.32, the hook automatically detects
the incompatibility and **skips with a warning** instead of failing your commit.

You will see output like:

```text
WARNING: mojo-format skipped: host glibc is incompatible with Mojo binary.
         Mojo requires GLIBC_2.32+. Your system has an older glibc.
         Files were NOT reformatted. Run inside Docker for full formatting.
         See docs/dev/mojo-glibc-compatibility.md for details.
```

CI always runs on Ubuntu 24.04 (glibc 2.39) and enforces formatting before merge, so your
code will still be format-checked. To format locally on an incompatible host, use Docker:

```bash
just shell
# Inside container:
pixi run mojo format path/to/file.mojo
```

See [docs/dev/mojo-glibc-compatibility.md](docs/dev/mojo-glibc-compatibility.md) for full details.
```

### Commit message format

```text
docs(contributing): document mojo-format GLIBC incompatibility

Add a named subsection under "Pre-commit Hooks > Hook Failure Policy"
in CONTRIBUTING.md explaining the mojo-format GLIBC < 2.32 limitation
on Debian 10/Buster hosts.

Closes #<issue-number>
```
