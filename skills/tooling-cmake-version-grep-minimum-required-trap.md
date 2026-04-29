---
name: tooling-cmake-version-grep-minimum-required-trap
description: "Fix empty VERSION string when extracting project version from CMakeLists.txt using grep -m1 'VERSION'. Use when: (1) CI job fails with 'ERROR: Could not parse VERSION from CMakeLists.txt' despite version being present, (2) grep -m1 'VERSION' returns cmake_minimum_required line instead of project() block, (3) three-part semver regex finds no match on a two-component string like '3.20'."
category: tooling
date: 2026-04-28
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - cmake
  - grep
  - version-extraction
  - ci-cd
  - semver
  - cmake-minimum-required
  - regex
---

# CMake Version grep Hits cmake_minimum_required Trap

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-28 |
| **Objective** | Extract the project version from `CMakeLists.txt` reliably in CI |
| **Outcome** | Successful — scoping grep to the `project()` block returns correct version |
| **Verification** | verified-ci (fix confirmed in HomericIntelligence/ProjectCharybdis PR #50) |

## When to Use

- CI job fails with `ERROR: Could not parse VERSION from CMakeLists.txt` even though `VERSION 0.1.0` is clearly present in the file
- `grep -m1 'VERSION' CMakeLists.txt` returns `cmake_minimum_required(VERSION 3.20)` instead of the project version
- A three-part semver regex (`\d+\.\d+\.\d+`) finds no match because the extracted string has only two components (e.g., `3.20`)
- The `deps/version-sync` job or any CI step that parses the CMake project version produces an empty `VERSION` variable

## Verified Workflow

### Quick Reference

```bash
# BROKEN — grep -m1 matches cmake_minimum_required line first:
VERSION=$(grep -m1 'VERSION' CMakeLists.txt | grep -oP '\d+\.\d+\.\d+' | head -1)
# Result: "3.20" has no three-part match → VERSION="" → CI failure

# FIXED — scope grep to the project() block:
VERSION=$(grep -A5 'project(' CMakeLists.txt | grep -oP '\d+\.\d+\.\d+' | head -1)
# Result: "0.1.0" ✓

# ALTERNATIVE FIX — use sed to extract from project() block:
VERSION=$(sed -n '/^project(/,/^)/p' CMakeLists.txt | grep -oP 'VERSION\s+\K[\d.]+')
# Result: "0.1.0" ✓
```

### Detailed Steps

1. **Understand the trap**: `grep -m1 'VERSION'` scans top-to-bottom and stops at the first match. In a typical `CMakeLists.txt`, `cmake_minimum_required(VERSION 3.20)` appears on line 1, which is matched before the `project()` block version on a later line.

   ```cmake
   cmake_minimum_required(VERSION 3.20)    # ← line 1: grep -m1 'VERSION' matches HERE
   project(ProjectCharybdis
     VERSION 0.1.0                         # ← line 5: intended match
     LANGUAGES CXX
   )
   ```

2. **Diagnose**: Run the broken command manually and inspect what it returns:

   ```bash
   grep -m1 'VERSION' CMakeLists.txt
   # Output: cmake_minimum_required(VERSION 3.20)
   ```

3. **Apply the fix** — scope to the `project()` block using either approach:

   **Option A — grep with context lines:**
   ```bash
   VERSION=$(grep -A5 'project(' CMakeLists.txt | grep -oP '\d+\.\d+\.\d+' | head -1)
   ```
   Extracts up to 5 lines after `project(`, then matches the first three-part semver.
   Adjust `-A5` if the `VERSION` field is further down inside the block.

   **Option B — sed range extraction:**
   ```bash
   VERSION=$(sed -n '/^project(/,/^)/p' CMakeLists.txt | grep -oP 'VERSION\s+\K[\d.]+')
   ```
   Prints only the lines between `project(` and the closing `)`, then extracts the version value after `VERSION `.

4. **Validate before using:**
   ```bash
   if [[ -z "$VERSION" ]]; then
     echo "ERROR: Could not parse VERSION from CMakeLists.txt"
     exit 1
   fi
   echo "Parsed version: $VERSION"
   ```

5. **Update CI YAML** — replace the broken one-liner with the fixed version in the affected workflow file (e.g., `_required.yml`, step `deps/version-sync`).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `grep -m1 'VERSION' CMakeLists.txt` | First match in file for the word VERSION | `cmake_minimum_required(VERSION 3.20)` appears on line 1 before `project()` block — match returns `3.20`, a two-component string | `grep -m1` is naive; it does not understand CMake block structure |
| Three-part semver regex on `3.20` | `grep -oP '\d+\.\d+\.\d+'` applied to `3.20` | `3.20` has only two numeric components — the regex requires three separated by dots, so it produces no match | CMake minimum version strings are intentionally short (major.minor); always scope the search to the `project()` block |
| Visual inspection of CMakeLists.txt | Checked the file manually and confirmed `VERSION 0.1.0` was present | Did not notice that the first line also contains `VERSION` in `cmake_minimum_required` | Tools see bytes top-to-bottom; visual inspection naturally jumps to the intended line |

## Results & Parameters

```yaml
# Symptom
ci_error: "ERROR: Could not parse VERSION from CMakeLists.txt"
ci_job: deps/version-sync
ci_file: _required.yml
version_variable: ""  # empty after broken grep

# Root cause
broken_command: "grep -m1 'VERSION' CMakeLists.txt | grep -oP '\\d+\\.\\d+\\.\\d+' | head -1"
first_match_line: "cmake_minimum_required(VERSION 3.20)"
regex_input: "3.20"
regex_components: 2   # three-part regex requires 3 → no match → empty string

# Fix
fixed_command_a: "grep -A5 'project(' CMakeLists.txt | grep -oP '\\d+\\.\\d+\\.\\d+' | head -1"
fixed_command_b: "sed -n '/^project(/,/^)/p' CMakeLists.txt | grep -oP 'VERSION\\s+\\K[\\d.]+'"
result: "0.1.0"

# Verification
pr: "HomericIntelligence/ProjectCharybdis#50"
ci_outcome: passing
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectCharybdis | `_required.yml` `deps/version-sync` job | Broken grep matched cmake_minimum_required line; fixed with `grep -A5 'project('` |
