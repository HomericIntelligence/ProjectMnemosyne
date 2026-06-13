---
name: ci-matrix-yaml-multiformat-regex-fallback
description: "Regex fallback pattern for parsing CI matrix Python version lists that appear in either inline bracket format (python-version: [\"3.10\", \"3.11\"]) or multiline YAML sequence format. Use when: (1) extending a function that parses CI workflow YAML for Python version lists, (2) a regex-based parser only handles one of the two common GHA matrix formats, (3) reviewing a plan to add multiline sequence support alongside existing inline bracket support."
category: ci-cd
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [yaml, regex, python-version, ci-matrix, github-actions, multiformat]
---

# CI Matrix YAML Multiformat Regex Fallback

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Extend `extract_ci_matrix_python_versions` to handle both inline bracket and multiline YAML sequence formats |
| **Outcome** | Plan produced; not yet implemented or tested |
| **Verification** | unverified |

GitHub Actions CI matrix workflows express `python-version` lists in two common formats:

**Inline bracket** (most common):
```yaml
python-version: ["3.10", "3.11", "3.12"]
```

**Multiline YAML sequence**:
```yaml
python-version:
  - "3.10"
  - "3.11"
  - "3.12"
```

A regex-based parser that only handles the inline bracket format silently returns no versions when encountering the sequence format, causing coverage checks to pass vacuously. The fix is a two-regex fallback: try the bracket pattern first; if it yields no results, try the sequence pattern.

## When to Use

- Extending a function that parses CI YAML workflow files for Python version lists
- A `check_python_version_consistency` script reports no CI matrix versions but the workflow file exists
- Reviewing an implementation plan for adding multiline sequence support to `extract_ci_matrix_python_versions`
- Writing tests for a parser that must handle both YAML matrix formats

## Verified Workflow

> **Warning:** This workflow has **not** been validated end-to-end. The implementation is a proposed plan derived from code inspection only — no tests were run. Treat as a hypothesis until CI confirms.

### Quick Reference

```python
import re
from typing import List

# Inline bracket format: python-version: ["3.10", "3.11"]
_CI_MATRIX_BRACKET_RE = re.compile(
    r'python-version:\s*\[([^\]]+)\]'
)

# Multiline sequence format:
#   python-version:
#     - "3.10"
#     - "3.11"
_CI_MATRIX_SEQUENCE_RE = re.compile(
    r'python-version:\s*\n((?:\s+-\s+["\']?\d+\.\d+["\']?\s*\n)+)',
    re.MULTILINE,
)

# Individual version extractor (shared)
_CI_VERSION_RE = re.compile(r'["\']?(\d+\.\d+)["\']?')


def extract_ci_matrix_python_versions(content: str) -> List[str]:
    """Extract Python versions from a CI matrix, supporting bracket and sequence formats."""
    # Try inline bracket format first
    bracket_match = _CI_MATRIX_BRACKET_RE.search(content)
    if bracket_match:
        return _CI_VERSION_RE.findall(bracket_match.group(1))

    # Fall back to multiline sequence format
    seq_match = _CI_MATRIX_SEQUENCE_RE.search(content)
    if seq_match:
        return _CI_VERSION_RE.findall(seq_match.group(1))

    return []
```

### Detailed Steps

1. **Locate the existing function** in `hephaestus/scripts_lib/check_python_version_consistency.py`. Confirm the current regex is inlined inside the function body (not a module-level constant named `_CI_MATRIX_PYTHON_RE` — that constant may not exist).

2. **Extract module-level constants** for both patterns and the version extractor RE, replacing any inlined pattern.

3. **Implement two-pass fallback**: `re.search` for bracket format first; only attempt sequence RE if bracket returns no match.

4. **Add tests** covering:
   - Inline bracket format (existing behavior preserved)
   - Multiline sequence format (new)
   - Mixed file where both formats appear (bracket wins by precedence — see caveats)
   - Empty / no version key (returns `[]`)
   - File with no trailing newline (see caveat on `re.MULTILINE`)

5. **Verify public API export** — check `validation/__init__.py` around line 105 (exact line unverified) to confirm `extract_ci_matrix_python_versions` is re-exported before touching exports.

6. **Run the test suite**: `pixi run pytest tests/unit/scripts_lib/ -v`

### Bracket-Format Precedence

Precedence between formats is determined by `re.search` position in the string: `_CI_MATRIX_BRACKET_RE` is tried first unconditionally. If it matches anywhere in the file, the sequence RE is never tried. This means:

- A file with both formats returns the bracket version list
- A file with only the sequence format is handled correctly by the fallback
- A file with the sequence format appearing textually before the bracket line still returns the bracket result — because the bracket RE is attempted first, not because it appears earlier in the string

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single regex covering both formats | `r'python-version:\s*(?:\[([^\]]+)\]\|((?:\n\s+-\s+.+)+))'` | Alternation with backreference groups makes extraction ambiguous; harder to read and test | Two separate named patterns with explicit fallback logic are clearer and independently testable |
| PyYAML `yaml.safe_load` for full parsing | Parse the entire workflow YAML with PyYAML | PyYAML is likely dev-only (unverified); adding a runtime dependency for one field extraction is disproportionate; GHA workflow YAML may have non-standard anchors | Regex is the right tool here; PyYAML approach not pursued |

## Results & Parameters

### Unverified Assumptions

The following assumptions in the plan were inferred from grep/code inspection and were **not directly verified**:

| Assumption | Basis | Risk if Wrong |
|------------|-------|---------------|
| `validation/__init__.py:105` exports `extract_ci_matrix_python_versions` as public API | Inferred from grep pattern; line not read | Wrong export path means adding the export is unnecessary or goes to the wrong file |
| `_CI_MATRIX_PYTHON_RE` is a module-level constant | Referenced in planning notes | The constant may not exist; the current implementation may inline the regex in the function body |
| PyYAML is dev-only (not in base install surface) | Observed `yaml.safe_load` usage in `hephaestus/validation/`; `pixi.toml` not checked | If PyYAML is already a runtime dep, the "regex-not-yaml" rationale weakens |

### Reviewer Risk Flags

1. **`re.MULTILINE` flag on `_CI_MATRIX_SEQUENCE_RE`**: The pattern uses explicit `\n` characters rather than `^`/`$` anchors. `re.MULTILINE` changes `^`/`$` behavior but has no effect on explicit `\n`. The flag may be unnecessary and could be confusing — consider removing it and testing that behavior is unchanged.

2. **`_CI_VERSION_RE` permissiveness**: `r'["\']?(\d+\.\d+)["\']?'` matches any `N.N` string. It could match version-like strings in YAML comments (e.g., `# requires >= 3.10`) if those appear inside the bracket or sequence capture group. Tighten the pattern or add comment-stripping if false positives are observed.

3. **Trailing newline assumption**: `_CI_MATRIX_SEQUENCE_RE` expects each sequence item to end with `\n` (the `(?:\s+-\s+["\']?\d+\.\d+["\']?\s*\n)+` quantifier). A YAML file ending without a trailing newline will miss the last entry. Use `(?:\n|$)` on the terminal newline, or strip-and-re-add a trailing newline before matching.

4. **`check_ci_matrix_coverage` hardcodes `test.yml`**: The coverage check reads only one specific workflow filename. If a repo uses `ci.yml`, `build.yml`, or another name, the extended parser won't help. This is intentionally out of scope for issue #1284 but worth noting in the PR description.

### Reference

- Source file: `hephaestus/scripts_lib/check_python_version_consistency.py`
- Candidate public API file: `hephaestus/validation/__init__.py` (~line 105, unverified)
- Issue: HomericIntelligence/ProjectHephaestus #1284
