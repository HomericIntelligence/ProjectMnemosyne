---
name: pixi-tectonic-latex-build
description: Configure tectonic as a LaTeX build engine in pixi environments with platform-specific dependencies and engine-agnostic preambles
category: tooling
date: 2026-04-06
version: 1.0.0
user-invocable: false
tags: [pixi, tectonic, latex, pdflatex, texlive, conda-forge, iftex, cross-platform]
---
# Skill: pixi-tectonic-latex-build

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-04-06 |
| Category | tooling |
| Objective | Add LaTeX compilation capability to a pixi-managed Python project using tectonic from conda-forge |
| Outcome | Successfully configured tectonic in a separate pixi `docs` environment with platform-specific dependencies and engine-agnostic LaTeX preamble; builds a 50-page 978KB PDF |

## When to Use

Use this skill when:

- You need pdflatex or a LaTeX engine in a pixi-managed project
- texlive-core from conda-forge fails with missing format files or Perl module errors
- You need cross-platform LaTeX builds (Linux + macOS) but not Windows
- A LaTeX paper uses pdfTeX-specific commands that break under XeTeX/tectonic
- You want reproducible LaTeX builds without system-level TeX Live installation

## Verified Workflow

### Step 1: Use tectonic, not texlive-core

**Do NOT use texlive-core from conda-forge.** It is broken:

- `pdflatex` binary exists but `.fmt` format files are missing
- `fmtutil` cannot generate formats because `mktexlsr.pl` Perl module is not included in the conda package
- Adding `perl` as a dependency does not fix it because TeX Live's internal Perl modules (`tlpkg/`) are not shipped
- Only version `20230313` exists on conda-forge (version constraints like `>=2025,<2026` fail to solve)
- Package does not exist on `win-64` at all

**Use tectonic instead:**
- Self-contained TeX engine that downloads packages on demand
- Available on conda-forge for `linux-64`, `osx-arm64`, `osx-64`
- NOT available on `win-64`

### Step 2: Create a separate pixi environment for docs

Add to `pixi.toml`:

```toml
[feature.docs.dependencies]
# Platform-independent dependencies go here (if any)

[feature.docs.target.linux-64.dependencies]
tectonic = ">=0.15,<1"

[feature.docs.target.osx-arm64.dependencies]
tectonic = ">=0.15,<1"

[feature.docs.target.osx-64.dependencies]
tectonic = ">=0.15,<1"

# NOTE: No win-64 entry — tectonic is not available on Windows

[feature.docs.tasks]
paper-build = { cmd = "tectonic docs/arxiv/haiku/paper.tex", description = "Build the research paper PDF" }

[environments]
docs = { features = ["docs"], solve-group = "default" }
```

**Key points:**
- Use platform-specific dependency blocks (`[feature.docs.target.<platform>.dependencies]`)
- Do NOT list tectonic as a global dependency or it will fail on win-64
- The `platforms` key is NOT valid inside `[environments.<name>]` — only `features`, `solve-group`, and `no-default-feature` are valid
- Use `solve-group = "default"` to share the dependency solution with the main environment

### Step 3: Make LaTeX preamble engine-agnostic with iftex

pdfTeX-specific commands cause errors under tectonic (which uses XeTeX backend):

```
! Undefined control sequence.
\pdfoutput=1
```

**Fix: Use the `iftex` package to guard pdfTeX-specific commands:**

```latex
\usepackage{iftex}

% pdfTeX-specific settings (ignored by XeTeX/LuaTeX)
\ifpdftex
  \pdfoutput=1
  \usepackage[T1]{fontenc}
  \usepackage[utf8]{inputenc}
\fi

% Engine-agnostic packages (work everywhere)
\usepackage{hyperref}
\usepackage{graphicx}
\usepackage{booktabs}
```

**Commands that MUST be guarded with `\ifpdftex`:**
- `\pdfoutput=1` — causes XeTeX to load `hpdftex.def` which has undefined control sequences
- `\usepackage[T1]{fontenc}` — XeTeX/LuaTeX use different font handling (fontspec)
- `\usepackage[utf8]{inputenc}` — XeTeX/LuaTeX handle UTF-8 natively

### Step 4: Build and verify

```bash
# Install the docs environment
pixi install --environment docs

# Build the paper
pixi run --environment docs paper-build

# Verify output
ls -lh docs/arxiv/haiku/paper.pdf

# Tectonic automatically handles:
# - Package downloads (first run is slower)
# - Multiple compilation passes (resolves cross-references)
# - BibTeX/biber processing
```

### Step 5: Lock file maintenance

After modifying `pixi.toml`:

```bash
pixi install  # Regenerates pixi.lock
git add pixi.lock pixi.toml
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| texlive-core from conda-forge | Added `texlive-core` as a pixi dependency | pdflatex binary exists but format files (.fmt) are missing; fmtutil fails because mktexlsr.pl Perl module is not shipped in the conda package | texlive-core on conda-forge is fundamentally broken for direct pdflatex use; use tectonic instead |
| texlive-core version constraint | Used `texlive-core = ">=2025,<2026"` | Only version 20230313 exists on conda-forge; solve fails | Check available versions with `pixi search texlive-core` before constraining |
| texlive-core + perl dependency | Added both `texlive-core` and `perl` as dependencies | Perl binary installed but TeX Live's internal Perl modules (tlpkg/) are not included in the conda package | TeX Live's internal Perl dependencies are not satisfiable through conda's perl package |
| texlive-core on win-64 | Listed texlive-core as a global dependency | Package does not exist on win-64; pixi solve fails | Always check platform availability; use platform-specific dependency blocks |
| tectonic as global dependency | Added tectonic to default dependencies | Fails on win-64 where tectonic is not available | Use feature-specific, platform-targeted dependencies for tools not available everywhere |
| `platforms` key in environment | Used `[environments] docs = { features = [...], platforms = [...] }` | `platforms` is not a valid key for pixi environment definitions | Only `features`, `solve-group`, `no-default-feature` are valid environment keys; use target-specific feature dependencies instead |
| tectonic with `\pdfoutput=1` | Built paper with tectonic without guarding pdfTeX commands | XeTeX backend loads `hpdftex.def` which contains undefined control sequences | Guard all pdfTeX-specific commands with `\ifpdftex` from the `iftex` package |

## Results & Parameters

### Configuration
- tectonic version: `>=0.15,<1` (conda-forge)
- pixi environment: `docs` (separate from default)
- Platforms: `linux-64`, `osx-arm64`, `osx-64` (NOT `win-64`)
- LaTeX engine compatibility: `iftex` package with `\ifpdftex` guards
- Build command: `pixi run --environment docs paper-build`

### Output
- Paper: 50 pages, 978KB PDF
- Build time: ~30s first run (package downloads), ~10s subsequent
- Verification level: verified-local (not tested in CI)

### Key files modified
- `pixi.toml` — added `[feature.docs.*]` sections and `docs` environment
- `paper.tex` — added `iftex` package and `\ifpdftex` guards in preamble

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Haiku analysis paper LaTeX build (2026-04-06) | tectonic builds 50-page PDF from docs/arxiv/haiku/paper.tex |
