## 2026-04-06: pixi-tectonic-latex-build v1.0.0 — ProjectScylla Haiku Paper Build

Session: Add LaTeX build capability to ProjectScylla pixi environment for docs/arxiv/haiku/paper.tex

### Problem statement
Need pdflatex or equivalent to build the research paper locally and in CI. System pdflatex is available but not portable; want a pixi-managed solution.

### Attempts in order

#### Attempt 1: texlive-core from conda-forge
```toml
[feature.docs.dependencies]
texlive-core = ">=2025,<2026"
```
**Result:** Solve fails. Only version 20230313 exists on conda-forge.

#### Attempt 2: texlive-core without version constraint
```toml
[feature.docs.dependencies]
texlive-core = "*"
```
**Result:** Solve fails on win-64 (package does not exist for Windows).

#### Attempt 3: texlive-core with platform targets
```toml
[feature.docs.target.linux-64.dependencies]
texlive-core = "*"
```
**Result:** pdflatex binary installed but running it fails:
```
kpathsea: Running mktexfmt pdflatex.fmt
/home/mvillmow/.pixi/envs/docs/bin/fmtutil: line 67: mktexlsr.pl: No such file or directory
```
The .fmt format files are missing and cannot be generated because mktexlsr.pl Perl module is not shipped.

#### Attempt 4: texlive-core + perl
```toml
[feature.docs.target.linux-64.dependencies]
texlive-core = "*"
perl = "*"
```
**Result:** perl binary installed but TeX Live's internal Perl modules (tlpkg/) are not included in the conda texlive-core package. fmtutil still fails.

#### Attempt 5: tectonic as global dependency
```toml
[dependencies]
tectonic = ">=0.15,<1"
```
**Result:** Fails because tectonic is not available on win-64 and pixi.toml lists win-64 in platforms.

#### Attempt 6: tectonic with platform-specific deps (WORKING)
```toml
[feature.docs.target.linux-64.dependencies]
tectonic = ">=0.15,<1"

[feature.docs.target.osx-arm64.dependencies]
tectonic = ">=0.15,<1"

[feature.docs.target.osx-64.dependencies]
tectonic = ">=0.15,<1"

[feature.docs.tasks]
paper-build = { cmd = "tectonic docs/arxiv/haiku/paper.tex" }

[environments]
docs = { features = ["docs"], solve-group = "default" }
```
**Result:** `pixi install` succeeds. `pixi run --environment docs paper-build` runs tectonic.

#### Attempt 7: Fix LaTeX preamble for tectonic
First tectonic build failed with:
```
error: something failed during xetex's execution
! Undefined control sequence.
l.7 \pdfoutput=1
```
Tectonic uses XeTeX backend, which does not support `\pdfoutput`. Also `\usepackage[T1]{fontenc}` and `\usepackage[utf8]{inputenc}` are pdfTeX-specific.

**Fix:** Added `iftex` package and `\ifpdftex` guards:
```latex
\usepackage{iftex}
\ifpdftex
  \pdfoutput=1
  \usepackage[T1]{fontenc}
  \usepackage[utf8]{inputenc}
\fi
```

**Final result:** tectonic builds paper successfully to 50-page 978KB PDF.

### Key decisions
1. Separate `docs` environment instead of adding tectonic to default — keeps the main environment clean
2. `solve-group = "default"` — shares dependency resolution with main env to avoid solve conflicts
3. `iftex` over removing pdfTeX commands — maintains compatibility with system pdflatex for users who prefer it
4. No win-64 support — tectonic and texlive-core both unavailable on Windows via conda-forge

### Platform availability summary (conda-forge, 2026-04)
| Package | linux-64 | osx-arm64 | osx-64 | win-64 |
| --------- | ---------- | ----------- | -------- | -------- |
| tectonic | >=0.15 | >=0.15 | >=0.15 | N/A |
| texlive-core | 20230313 (broken) | 20230313 (broken) | 20230313 (broken) | N/A |
