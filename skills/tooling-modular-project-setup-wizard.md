---
name: tooling-modular-project-setup-wizard
description: "Set up a new Modular/Mojo/MAX project with correct structure. Use when: (1) creating a new Mojo or MAX project from scratch, (2) initializing pixi or uv environment for Mojo/MAX, (3) choosing between nightly and stable channels."
category: tooling
date: 2026-04-09
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [mojo, max, project-setup, pixi, uv, scaffolding, modular-upstream]
---

# Modular Project Setup Wizard

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-09 |
| **Objective** | Interactive wizard for creating new Mojo/MAX projects with correct toolchain setup |
| **Outcome** | Authoritative setup guide from Modular covering pixi, uv, pip, and conda |
| **Source** | [modular/skills](https://github.com/modular/skills) (Apache 2.0) |

## When to Use

- Creating a new Mojo or MAX project from scratch
- Choosing between environment managers (pixi recommended, uv, pip, conda)
- Setting up nightly vs stable channels
- Ensuring version alignment between MAX and Mojo

## Verified Workflow

### Quick Reference

Infer options from user's request, then prompt only for unspecified options:

1. **Project name**
2. **Type** — Mojo or MAX
3. **Environment manager** — Pixi (recommended), uv, pip, or conda
4. **If uv**: full project (`uv init`) or quick environment (`uv venv`)
5. **Channel** — nightly (latest) or stable (production)

**Note**: `magic` is no longer supported — Pixi has fully replaced it.

### System Prerequisites

| OS | Command |
| --------------- | ---------------------------------------------------------- |
| Ubuntu/Debian | `sudo apt install gcc` |
| Fedora/RHEL | `sudo dnf install gcc` |
| macOS | `xcode-select --install` |
| Windows | WSL2 required (`wsl --install`), then gcc in WSL |

### Pixi (Recommended)

```bash
# Nightly
pixi init <project-name> \
  -c https://conda.modular.com/max-nightly/ -c conda-forge \
  && cd <project-name>
pixi add [max / mojo]
pixi shell

# Stable (v26.1.0.0.0)
pixi init <project-name> \
  -c https://conda.modular.com/max/ -c conda-forge \
  && cd <project-name>
pixi add "[max / mojo]==0.26.1.0.0.0"
pixi shell

# Python-using projects
pixi add python
pixi add requests           # conda-forge packages
pixi add --pypi some-pkg    # PyPI-only packages
```

### uv

```bash
# Nightly (project)
uv init <project-name> && cd <project-name>
uv add [max / mojo] \
  --index https://whl.modular.com/nightly/simple/ \
  --prerelease allow

# Stable (project)
uv init <project-name> && cd <project-name>
uv add [max / mojo] \
  --extra-index-url https://modular.gateway.scarf.sh/simple/

# Nightly (quick environment)
mkdir <project-name> && cd <project-name>
uv venv
uv pip install [max / mojo] \
  --index https://whl.modular.com/nightly/simple/ \
  --prerelease allow
```

### pip

```bash
# Nightly
python3 -m venv .venv && source .venv/bin/activate
pip install --pre [max / mojo] \
  --index https://whl.modular.com/nightly/simple/

# Stable
python3 -m venv .venv && source .venv/bin/activate
pip install [max / mojo] \
  --extra-index-url https://modular.gateway.scarf.sh/simple/
```

### conda

```bash
# Nightly
conda install -c conda-forge \
  -c https://conda.modular.com/max-nightly/ [max / mojo]

# Stable
conda install -c conda-forge \
  -c https://conda.modular.com/max/ "[max / mojo]==0.26.1.0.0.0"
```

### Version Alignment

MAX and Mojo versions must match when using custom Mojo kernels:

```bash
uv pip show mojo | grep Version   # e.g., 0.26.2
pixi run mojo --version           # Must match major.minor
```

Mismatched versions cause kernel compilation failures. Use the same channel for both.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Using `magic` for project setup | `magic init` / `magic add` | `magic` is deprecated; Pixi replaced it | Always use `pixi` — do not look for or use `magic` |
| (sourced from upstream) | Modular's official skills repo | N/A — authoritative reference | Version strings differ: mojo uses `0.` prefix (0.26.1.0.0.0), max does not (26.1.0.0.0) |

## Results & Parameters

### Channel URLs

| Channel | Conda URL | PyPI Index |
| --------- | ----------- | ------------ |
| Nightly | `https://conda.modular.com/max-nightly/` | `https://whl.modular.com/nightly/simple/` |
| Stable | `https://conda.modular.com/max/` | `https://modular.gateway.scarf.sh/simple/` |

### References

- [Mojo Installation Guide](https://docs.modular.com/mojo/manual/install)
- [Mojo Stable Docs](https://docs.modular.com/stable/mojo/)
- [Mojo Nightly Docs](https://docs.modular.com/mojo/)

## Related Skills

- [mojo-build-package](./mojo-build-package.md) — Building Mojo packages
- [mojo-026-breaking-changes](./mojo-026-breaking-changes.md) — Current Mojo syntax reference

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| (upstream) | Modular official skills repo | Authoritative project setup reference |

---
*Adapted from [modular/skills](https://github.com/modular/skills) under Apache License 2.0.
Copyright (c) Modular Inc.*
