---
name: generate-changelog
description: "Generate changelog from git commits with safe delimiter handling. Use when: (1) writing git log format strings that parse fields, (2) parsing conventional commit messages, (3) extracting scope from commit prefixes."
category: tooling
date: '2026-03-25'
version: "2.0.0"
user-invocable: false
verification: verified-local
history: generate-changelog.history
tags:
  - git
  - changelog
  - parsing
  - conventional-commits
---

# Generate Changelog

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Generate formatted changelogs from git commit history using safe delimiter parsing |
| **Outcome** | Operational — delimiter bug fixed, edge-case tests added |
| **Verification** | verified-local |
| **History** | [changelog](./generate-changelog.history) |

## When to Use

- Writing `git log --pretty=format` strings that split output into fields
- Parsing conventional commit messages (`type(scope): message`)
- Extracting scope from commit prefixes that may contain nested parentheses
- Generating changelogs or release notes from commit history
- Testing commit parsers for edge cases (pipes, colons, nested parens)

## Verified Workflow

### Quick Reference

```bash
# CORRECT: Use %x09 (tab) as field delimiter — tabs never appear in commit subjects
git log v1.0.0..HEAD --pretty=format:"%h%x09%s%x09%an" --no-merges

# WRONG: Pipe delimiter breaks if subject contains | characters
# git log --pretty=format:"%h|%s|%an"  # DO NOT USE

# Parse in Python:
# parts = line.split("\t", 2)  # NOT split("|", 2)
```

### Detailed Steps

1. **Use tab delimiter in git log format**: Replace `%h|%s|%an` with `%h%x09%s%x09%an`. The `%x09` is git's hex escape for tab. Tabs cannot appear in git commit subjects, making the split reliable.

2. **Split on tab in parser**: `commit_line.split("\t", 2)` instead of `split("|", 2)`. The `maxsplit=2` ensures the author field captures any remaining content.

3. **Parse conventional commit prefix**: Split subject on first colon only (`subject.split(":", 1)`) to preserve colons in the message body (e.g., `fix: url: handle https://`).

4. **Extract scope with index/rindex for nested parens**: Instead of `prefix.split("(")[1].split(")")[0]`, use:
   ```python
   open_paren = prefix.index("(")
   close_paren = prefix.rindex(")")
   scope = prefix[open_paren + 1 : close_paren].strip()
   ```
   This correctly handles `feat(core(sub)): msg` → scope = `core(sub)`.

5. **Test edge cases**: Always test parsers with:
   - Pipe characters in subject: `"abc\tfeat: add A|B toggle\tAuthor"`
   - Multiple colons: `"abc\tfix: url: handle https://example.com\tAuthor"`
   - Nested parentheses in scope: `"abc\tfeat(core(sub)): msg\tAuthor"`
   - Empty input: `""`
   - Incomplete fields (missing author): `"abc\tsubject"`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Pipe delimiter | `--pretty=format:%h\|%s\|%an` with `split("\|", 2)` | Commit subjects containing pipe characters produce garbled fields — the split finds 4+ parts instead of 3 | Use a character that cannot appear in commit subjects. Tab (`%x09`) is ideal since git strips tabs from subjects |
| Chained split for scope | `prefix.split("(")[1].split(")")[0]` | Breaks on nested parentheses like `feat(core(sub))` — `split("(")[1]` returns `core` and `split(")")[0]` returns `core`, losing the inner parens entirely | Use `index("(")`/`rindex(")")` to grab everything between the outermost parentheses |
| Split on all colons | `subject.split(":")` without maxsplit | Loses everything after the second colon in messages like `fix: url: handle https://` | Always use `split(":", 1)` to split only on the first colon |

## Results & Parameters

```python
# Correct parse_commit implementation pattern:
def parse_commit(commit_line: str) -> tuple[str, str, str, str]:
    parts = commit_line.split("\t", 2)
    if len(parts) != 3:
        return ("", "other", "", commit_line)

    commit_hash, subject, _author = parts
    commit_type = "other"
    scope = ""
    message = subject

    if ":" in subject:
        prefix, rest = subject.split(":", 1)
        message = rest.strip()

        if "(" in prefix and ")" in prefix:
            commit_type = prefix.split("(")[0].strip().lower()
            open_paren = prefix.index("(")
            close_paren = prefix.rindex(")")
            scope = prefix[open_paren + 1 : close_paren].strip()
        else:
            commit_type = prefix.strip().lower()

    return (commit_hash, commit_type, scope, message)
```

```python
# Edge-case test patterns (pytest):
@pytest.mark.parametrize("commit_line,expected", [
    ("abc\tfeat: add A|B toggle\tAuthor", ("abc", "feat", "", "add A|B toggle")),
    ("abc\tfix: url: handle https://x.com\tA", ("abc", "fix", "", "url: handle https://x.com")),
    ("abc\tfeat(core(sub)): msg\tA", ("abc", "feat", "core(sub)", "msg")),
    ("", ("", "other", "", "")),
    ("abc\tsubject", ("", "other", "", "abc\tsubject")),
])
def test_parse_commit_edge_cases(commit_line, expected):
    assert parse_commit(commit_line) == expected
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #33 — pipe delimiter bug fix | 38 changelog tests pass, 401 total unit tests pass (82.14% coverage) |

## References

- See `doc-update-blog` skill for blog post updates
- See git documentation for commit message conventions
- See <https://keepachangelog.com/> for changelog format standards
- ProjectHephaestus PR #71: https://github.com/HomericIntelligence/ProjectHephaestus/pull/71
