---
name: security-pep508-parser-replaces-regex
description: "Replace custom regex validation of pip requirement strings with packaging.requirements.Requirement (PEP 508 parser). Use when: (1) validating pip/PyPI package names in install_package or similar functions, (2) custom regex allows unintended characters like whitespace or shell metacharacters in package names."
category: architecture
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
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
| **Issue** | HomericIntelligence/ProjectHephaestus#31 |
| **PR** | HomericIntelligence/ProjectHephaestus#69 |

## When to Use

- A function validates pip/PyPI package names using a custom regex
- The regex allows unintended characters (whitespace, `!`, `<`, `>`, `;`, `|`, `&`) in package names
- You need to support the full PEP 508 requirement grammar (extras, version specifiers) without rolling your own parser
- Security review flags a package name validation regex as overly permissive

## Verified Workflow

### Quick Reference

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
| Original regex | `r"^[A-Za-z0-9_\-\.\[\],>=<!\s]+$"` | Allowed whitespace, standalone `!`, `<`, `>` — more permissive than intended | Custom regex for complex grammars (PEP 508) is inherently incomplete; use the canonical parser |
| Tightening the regex | Considered removing `\s` and `!` from the character class | Would still miss edge cases in PEP 508 (markers, extras with dots, etc.) | When a well-maintained parser exists for the grammar, always prefer it over regex |

## Results & Parameters

**Dependency**: `packaging>=21.0` (available since Python packaging ecosystem standardization)

**Key behaviors verified**:
```
"requests"                          → accepted (simple name)
"pkg[extra1,extra2]"                → accepted (extras syntax)
"pkg>=1.0,<2"                       → accepted (version specifiers)
"pkg!=1.3"                          → accepted (exclusion specifier)
"pkg1 pkg2"                         → rejected (whitespace/multi-package)
"pkg; rm -rf /"                     → rejected (shell injection)
"pkg && echo pwned"                 → rejected (shell metacharacters)
"pkg @ https://evil.com/mal.tar.gz" → rejected (URL-based requirement)
""                                  → rejected (empty string)
```

**Error message pattern**: `ValueError: Invalid package requirement: <name!r>` (or `URL-based requirements are not supported` for URL inputs)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #31 — install_package shell-metachar injection | 54 unit tests pass, ruff/mypy clean, helpers.py at 94.83% coverage |
