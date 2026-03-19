---
name: docstring-fragment-validator
description: Pattern for adding a pre-commit hook that validates Python docstrings
  as complete semantic units (not line-by-line), preventing false-positive fragment
  detection during audits of correctly-wrapped multi-line docstrings
category: ci-cd
date: 2026-03-03
version: 1.0.0
user-invocable: false
---
# Docstring Fragment Validator Pre-commit Hook

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-03 |
| **Objective** | Add a pre-commit gate that detects genuine docstring sentence fragments in Python files without false-positiving on correctly-wrapped multi-line docstrings |
| **Outcome** | ✅ Hook implemented, 35 unit tests added, full suite passes (4034/4034), PR #1384 merged |
| **PR** | HomericIntelligence/ProjectScylla#1384 |
| **Fixes** | Issue #1363 (follow-up from March 2026 quality audit #1346) |

## Overview

Quality auditors checking Python docstrings line-by-line can flag the continuation line of a
correctly-wrapped sentence as a "sentence fragment". For example:

```python
"""Test runner orchestration for agent evaluations.

This module provides the EvalRunner class that orchestrates test execution
across multiple tiers, models, and runs in Docker containers, with support for
parallel execution and file I/O operations.
"""
```

A line-by-line auditor sees `"across multiple tiers, models..."` in isolation and flags it as a
fragment — but it is the valid continuation of the preceding sentence.

This skill adds a Python-based pre-commit hook that uses `ast.parse()` to extract docstrings as
**complete strings** and then checks only the **first non-empty line** of each docstring against a
curated set of lowercase continuation words. This ensures:

- Genuine fragments (e.g. `"""across multiple tiers."""` as a standalone docstring) are caught
- Wrapped sentences are never flagged — the full docstring is analysed, not individual lines

## When to Use This Skill

Invoke when:

- A quality audit falsely flags wrapped docstring sentences as fragments
- You want to automate docstring quality checking at commit time without false positives
- You need to enforce that docstrings are semantically complete (not lint them line-by-line)

## Verified Workflow

### Step 1 — Write the Checker Script

Create `scripts/check_docstring_fragments.py`. Key design decisions:

**Use `ast.parse()` — never split lines manually:**

```python
import ast

def _docstring_nodes(tree: ast.Module) -> list[tuple[ast.AST, str, int]]:
    """Yield (node, docstring_text, line_number) for all docstring-bearing nodes."""
    results: list[tuple[ast.AST, str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", [])
        if not body:
            continue
        first_stmt = body[0]
        if not isinstance(first_stmt, ast.Expr):
            continue
        value = first_stmt.value
        # Python 3.8+: use .value (not .s which is deprecated)
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        results.append((node, value.value, first_stmt.lineno))
    return results
```

**CRITICAL**: Use `ast.Constant.value` (not `.s`) — `.s` is deprecated since Python 3.8 and
removed in 3.14.

**Detect genuine fragments by checking the first non-empty line's first word:**

```python
_CONTINUATION_STARTERS = frozenset({
    "across", "after", "against", "along", "also", "although", "among",
    "and", "around", "as", "at", "because", "before", "beneath", "beside",
    "between", "beyond", "but", "by", "despite", "during", "except",
    "for", "from", "hence", "however", "if", "in", "including", "instead",
    "into", "nor", "of", "on", "or", "over", "plus", "since", "so",
    "than", "that", "the", "then", "thereby", "therefore", "though",
    "through", "throughout", "thus", "to", "toward", "under", "unless",
    "until", "upon", "via", "when", "where", "whereas", "whether",
    "which", "while", "with", "within", "without", "yet",
})

def _is_genuine_fragment(docstring: str) -> bool:
    lines = docstring.splitlines()
    first_line = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            first_line = stripped
            break
    if not first_line:
        return False
    first_word = first_line.split()[0].rstrip(".,;:!?")
    if first_word and first_word == first_word.lower() and first_word.isalpha():
        return first_word in _CONTINUATION_STARTERS
    return False
```

**Key design choices**:
- Checks only the **first non-empty line** — continuation lines are not checked
- `first_word.isalpha()` — technical tokens with digits/underscores are not flagged
- `first_word == first_word.lower()` — capitalised words (normal sentence starts) are always OK
- Leading blank lines are skipped (triple-quoted docstrings often start with a blank line)

**Full script structure** mirrors existing hooks like `audit_doc_examples.py`:

```python
@dataclass
class FragmentFinding:
    file: str
    line: int
    docstring_first_line: str
    context: str

def scan_file(file_path: Path, repo_root: Path) -> list[FragmentFinding]: ...
def scan_repository(repo_root: Path) -> list[FragmentFinding]: ...
def format_report(findings: list[FragmentFinding]) -> str: ...
def main() -> int: ...
```

### Step 2 — Write Unit Tests

Create `tests/unit/scripts/test_check_docstring_fragments.py`. Essential test cases:

| Class | Test | Assertion |
|-------|------|-----------|
| `TestIsGenuineFragment` | `test_wrapped_sentence_not_flagged` | Multi-line wrapped sentence with capital start → not a fragment |
| `TestIsGenuineFragment` | `test_continuation_word_across_flagged` | `"across multiple tiers."` → genuine fragment |
| `TestIsGenuineFragment` | `test_continuation_word_and_flagged` | `"and returns the result."` → genuine fragment |
| `TestIsGenuineFragment` | `test_empty_docstring_not_flagged` | Empty string → not flagged |
| `TestIsGenuineFragment` | `test_leading_blank_lines_skipped` | Blank lines before fragment → still detected |
| `TestIsGenuineFragment` | `test_technical_token_not_flagged` | `"path to config"` → not flagged (lowercase but not in set) |
| `TestScanFileDetectsFragments` | `test_detects_module_docstring_fragment` | Module-level fragment found |
| `TestScanFileDetectsFragments` | `test_detects_function_docstring_fragment` | Function-level fragment found |
| `TestScanFilePassesValidDocstrings` | `test_wrapped_sentence_not_flagged` | **The `runner.py` case: must pass** |
| `TestScanFilePassesValidDocstrings` | `test_syntax_error_file_returns_no_findings` | Broken files skipped gracefully |
| `TestScanRepositoryExclusions` | `test_excludes_path[.pixi]` | Excluded dirs are skipped |
| `TestFormatReport` | `test_no_findings_message` | Clean message when no violations |

### Step 3 — Register the Hook

In `.pre-commit-config.yaml`:

```yaml
- id: check-docstring-fragments
  name: Check Docstring Fragment False Positives
  description: Validates Python docstrings as complete semantic units to prevent false positive fragment detection during audits
  entry: pixi run python scripts/check_docstring_fragments.py
  language: system
  files: \.py$
  types: [python]
  pass_filenames: false
```

**Placement**: Register after `audit-doc-policy` and before `check-doc-config-consistency`.

**`pass_filenames: false`**: The script scans the full repository itself (not file arguments),
consistent with other structural validators.

### Step 4 — Verify Against the Repo

```bash
# Must exit 0 (no false positives on the existing codebase)
pixi run python scripts/check_docstring_fragments.py
echo $?  # 0

# Must pass all new tests
pixi run python -m pytest tests/unit/scripts/test_check_docstring_fragments.py -v
# 35 passed

# Full suite must pass
pixi run python -m pytest tests/unit/ --no-cov
# 4034 passed
```

### Step 5 — Commit and Push

```bash
git add scripts/check_docstring_fragments.py \
        tests/unit/scripts/test_check_docstring_fragments.py \
        .pre-commit-config.yaml
git commit -m "feat(pre-commit): add semantic docstring fragment validator"
git push -u origin <branch>
gh pr create --title "[feat] Add semantic docstring fragment validator pre-commit hook" \
  --body "Closes #1363"
gh pr merge --auto --rebase
```

## Failed Attempts

### ❌ Using `ast.Constant.s` in Python 3.14

**Symptom**: `AttributeError: 'Constant' object has no attribute 's'` at runtime and in tests.

**Root cause**: `ast.Constant.s` was deprecated in Python 3.8 and removed in Python 3.14. The
project runs Python 3.14.3.

**Fix**: Use `ast.Constant.value` instead:

```python
# WRONG (fails on Python 3.14):
if not isinstance(value, ast.Constant) or not isinstance(value.s, str):
    continue
results.append((node, value.s, first_stmt.lineno))

# CORRECT:
if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
    continue
results.append((node, value.value, first_stmt.lineno))
```

**Rule**: Always use `ast.Constant.value` for string constant nodes. `ast.Str`, `ast.Num`,
`ast.Bytes` and their `.s`/`.n` attributes are all removed in Python 3.14+.

### ❌ Line-by-line Regex Approach

**Considered but rejected**: A regex-based line-by-line scanner (similar to `audit_doc_examples.py`)
would reproduce the exact false-positive problem it's meant to fix — a continuation line read in
isolation still looks like a fragment.

**Fix**: Use `ast.parse()` to get the full docstring string, then check only the first non-empty
line's first word. This is the correct semantic unit boundary.

## Results & Parameters

**Tests**: 35 new tests, 4034 total passed, 72.11% coverage (threshold: 9% combined / 75% unit)

**Hook trigger**: `files: \.py$`, `types: [python]` — runs whenever Python files are staged

**False positive protection**: The `runner.py` case (`"This module provides... / across multiple
tiers..."`) passes cleanly — the fragment word `"across"` appears on line 4, not the first line.

**Script location**: `scripts/check_docstring_fragments.py`
**Test location**: `tests/unit/scripts/test_check_docstring_fragments.py`

## Related Skills

- `enforce-unit-test-structure-hook` — Same pattern for adding a structural pre-commit hook
- `pre-commit-maintenance` — General pre-commit hook management patterns
- `audit-doc-policy` — The existing markdown policy audit hook this complements
