---
name: security-pep508-parser-replaces-regex
description: "Replace custom regex validation of pip requirement strings with packaging.requirements.Requirement (PEP 508 parser). Use when: (1) validating pip/PyPI package names in install_package or similar functions, (2) custom regex allows unintended characters like whitespace or shell metacharacters in package names."
category: architecture
date: 2026-03-25
version: "2.0.0"
user-invocable: false
verification: verified-local
history: security-pep508-parser-replaces-regex.history
tags:
  - security
  - input-validation
  - pip
  - packaging
  - pep508
---

# Replace Regex Package Validation with PEP 508 Parser

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Eliminate shell-metachar injection risk in `install_package()` by replacing a permissive custom regex with the canonical PEP 508 parser |
| **Outcome** | Successful — all valid pip requirement syntax accepted, all dangerous inputs rejected |
| **Verification** | verified-local |
| **Issue (broad)** | HomericIntelligence/ProjectHephaestus#31 |
| **Issue (regex-specific)** | HomericIntelligence/ProjectHephaestus#62 |
| **PR (PEP 508 parser)** | HomericIntelligence/ProjectHephaestus#69 |
| **PR (regex tightening)** | HomericIntelligence/ProjectHephaestus#126 |
| **History** | [changelog](./security-pep508-parser-replaces-regex.history) |

## When to Use

- A function validates pip/PyPI package names using a custom regex
- The regex allows unintended characters (whitespace, `!`, `<`, `>`, `;`, `|`, `&`) in package names
- You need to support the full PEP 508 requirement grammar (extras, version specifiers) without rolling your own parser
- Security review flags a package name validation regex as overly permissive
- As an interim fix: tighten the regex by replacing `\s` with literal space and removing `!`

## Verified Workflow

### Quick Reference

**Preferred approach (PEP 508 parser):**

```python
from packaging.requirements import InvalidRequirement, Requirement

def validate_requirement(package_name: str) -> None:
    """Validate a single PEP 508 requirement string."""
    if not package_name or not package_name.strip():
        raise ValueError(f"Invalid package requirement: {package_name!r}")

    try:
        req = Requirement(package_name)
    except InvalidRequirement as e:
        raise ValueError(f"Invalid package requirement: {package_name!r}") from e

    # Reject URL-based requirements for security
    if req.url is not None:
        raise ValueError(f"URL-based requirements are not supported: {package_name!r}")
```

**Interim approach (tightened regex):**

```python
import re

# Use re.fullmatch (not re.match) with literal space (not \s) and no !
if not re.fullmatch(r"[A-Za-z0-9_\-.\[\],>=< ]+", package_name):
    raise ValueError(f"Invalid package name: {package_name!r}")
```

### Detailed Steps

1. **Add `packaging` as a dependency** in `pyproject.toml`:
   ```toml
   dependencies = [
       "packaging>=21.0",
   ]
   ```
   Note: `packaging` is already available transitively via pip/setuptools, but declare it explicitly since library code imports it.

2. **Replace the regex block** with `Requirement()` parse + URL check:
   - `Requirement(name)` handles the full PEP 508 grammar: extras `[extra1,extra2]`, version specifiers `>=1.0,<2`, environment markers
   - Raises `InvalidRequirement` for anything invalid (whitespace-separated names, shell metacharacters, etc.)
   - Check `req.url is not None` to reject `pkg @ https://...` URL-based requirements

3. **Add empty/whitespace guard** before the parser call — `Requirement("")` may not raise on all `packaging` versions.

4. **Write parametrized tests** covering:
   - Valid: `"requests"`, `"my-package"`, `"pkg[extra1,extra2]"`, `"pkg>=1.0,<2"`, `"pkg==1.2.3"`, `"pkg!=1.3"`
   - Invalid: `"pkg1 pkg2"`, `"pkg; rm -rf /"`, `""`, `"   "`, `"pkg && echo pwned"`, `"pkg | cat /etc/passwd"`, `"pkg\nnewline"`
   - URL-based: `"pkg @ https://evil.com/malware.tar.gz"`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Original regex | `r"^[A-Za-z0-9_\-\.\[\],>=<!\s]+$"` with `re.match` | Allowed newlines (via `\s`), `!` (shell history expansion), and other unintended whitespace | Custom regex for complex grammars (PEP 508) is inherently incomplete; use the canonical parser |
| Tightened regex (PR #126) | `re.fullmatch(r"[A-Za-z0-9_\-.\[\],>=< ]+", ...)` — removed `\s` and `!`, used `fullmatch` | Blocks newlines/tabs/`!` but still can't handle full PEP 508 grammar (markers, extras with dots, etc.) | Useful as interim hardening but not a complete solution; a proper parser is still needed |

## Results & Parameters

**Dependency**: `packaging>=21.0` (available since Python packaging ecosystem standardization)

**Key behaviors verified (PEP 508 parser approach)**:
```
"requests"                          -> accepted (simple name)
"pkg[extra1,extra2]"                -> accepted (extras syntax)
"pkg>=1.0,<2"                       -> accepted (version specifiers)
"pkg!=1.3"                          -> accepted (exclusion specifier)
"pkg1 pkg2"                         -> rejected (whitespace/multi-package)
"pkg; rm -rf /"                     -> rejected (shell injection)
"pkg && echo pwned"                 -> rejected (shell metacharacters)
"pkg @ https://evil.com/mal.tar.gz" -> rejected (URL-based requirement)
""                                  -> rejected (empty string)
```

**Key behaviors verified (tightened regex approach, PR #126)**:
```
"some-package"                      -> accepted (simple name)
"torch>=2.0,<3"                     -> accepted (version constraints)
"pkg[extra]"                        -> accepted (extras)
"pkg\nmalicious"                    -> rejected (newline blocked)
"pkg!exploit"                       -> rejected (! blocked)
"pkg\texploit"                      -> rejected (tab blocked)
```

**Error message pattern**: `ValueError: Invalid package name: <name!r>` (regex) or `ValueError: Invalid package requirement: <name!r>` (PEP 508)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #31 — PEP 508 parser replacement | 54 unit tests pass, ruff/mypy clean, helpers.py at 94.83% coverage |
| ProjectHephaestus | Issue #62 — regex tightening (interim fix) | 41 unit tests pass, `re.fullmatch` with literal space, `!` removed |
