---
name: markdownlint-md012-trailing-blank-eof
description: "Diagnose markdownlint MD012/no-multiple-blanks errors that are actually caused by a trailing double newline at end-of-file, not by visible double blanks at the reported line. Use when: (1) markdownlint CI reports MD012 at a line number close to the file's last content line, (2) the same MD012 error appears across multiple PRs touching different markdown files, (3) you almost stripped blank lines inside a fenced code block trying to fix MD012 (MD012 ignores blanks inside code fences by default), (4) you want a one-line POSIX fix that strips trailing whitespace and re-adds a single newline terminator."
category: tooling
date: 2026-05-29
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - markdownlint
  - MD012
  - no-multiple-blanks
  - eof-newline
  - end-of-file-fixer
  - ci-unblocking
  - pre-commit
  - diagnostics
---

# Markdownlint MD012 Caused by Trailing-Blank at EOF

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-29 |
| **Objective** | Correctly diagnose MD012/no-multiple-blanks failures whose true root cause is a `\n\n` sequence at end-of-file, not visible double blank lines at the reported line number |
| **Outcome** | Applied as one-line fix across 4 separate ProjectMnemosyne PRs (#2001, #2002, #2003, #2004); all PRs pushed with auto-merge armed; CI MD012 violations resolved |
| **Verification** | verified-ci — fix landed across 4 PRs with passing markdownlint check |

## When to Use

- Markdownlint CI reports an error of the form `<file>.md:<N> MD012/no-multiple-blanks Multiple consecutive blank lines [Expected: 1; Actual: 2]` where `<N>` is close to the file's last content line
- The same MD012 error appears across multiple PRs touching different markdown files (e.g., a 4-of-9 hit rate suggests a systemic missing `end-of-file-fixer` pre-commit hook, not a content authoring problem)
- You are tempted to edit the literal "line N" the linter reported, but the visible content there looks fine
- You see `\n\n` runs inside fenced code blocks and are wondering whether to strip them (you should not — MD012 ignores blanks inside code fences by default)
- You want a portable POSIX one-liner that fixes the EOF case without touching any other blank lines

## Verified Workflow

### Quick Reference

```bash
# 1. Detect the EOF-trailing-blank cause (last byte is \n AND second-to-last byte is \n):
[ -z "$(tail -c 2 <file> | head -c 1 | tr -d '\n')" ] && \
  printf "TRAILING_BLANK_AT_EOF: yes -- strip and re-add single newline\n"

# 2. Fix (strips ALL trailing blank lines, re-adds exactly one final newline):
printf '%s\n' "$(cat <file>)" > <file>.tmp && mv <file>.tmp <file>

# 3. Verify locally (same lint version CI uses):
npx --yes markdownlint-cli2 <file>

# 4. (Prophylactic) install end-of-file-fixer in pre-commit:
#    https://github.com/pre-commit/pre-commit-hooks
#    - repo: https://github.com/pre-commit/pre-commit-hooks
#      hooks:
#        - id: end-of-file-fixer
```

### Detailed Steps

1. **Read the CI error literally** — e.g. `skills/foo.md:149 MD012/no-multiple-blanks ... [Expected: 1; Actual: 2]`.

2. **Check the file length**. If the file is ~149-150 lines long and the error is at line 149, the "Actual: 2" run almost certainly ends at EOF. The line number in the MD012 error points to where the consecutive-blank run *begins*, which at EOF is the last newline-after-content.

3. **Confirm via the detection one-liner** (see Quick Reference). If the last two bytes are both `\n`, you have the EOF case.

4. **Apply the fix**. `printf '%s\n' "$(cat file.md)" > file.md.tmp && mv file.md.tmp file.md` is POSIX-correct: command substitution strips *all* trailing newlines, then `printf '%s\n'` re-adds exactly one. Equivalent `sed` form: `sed -i -e :a -e '/^$/{$d;N;ba' -e '}' file.md`.

5. **Verify with the same tool CI uses**. ProjectMnemosyne CI runs markdownlint v0.40.0 via markdownlint-cli2 v0.22.1. `npx --yes markdownlint-cli2 <file>` reproduces the CI error exactly.

6. **Prophylaxis** — if the same pattern shows up in 2+ PRs, install the `end-of-file-fixer` pre-commit hook from `pre-commit/pre-commit-hooks`. Every future fix becomes a one-line auto-commit, and the class of bug disappears.

7. **MD012 + fenced code blocks** — confirmed: markdownlint MD012 default config has `code_blocks: false` semantics (blank lines inside fenced code blocks are exempt). Do *not* strip `\n\n` runs inside `` ``` `` fences when chasing this error; you will damage the example output and the MD012 violation will still be there because the real one is at EOF.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Edit literal "line N" the lint reported | Opened the file at the exact line in the MD012 error and looked for visible double blank lines | There were none at the reported line — the line was real content; the run actually started at EOF, several lines later | The MD012 line number marks where the consecutive-blank run *begins*, not where the issue is "felt". Always check EOF first when the line number ≈ file length |
| Search file for any `\n\n\n` (triple newline) sequence | `grep -P` / `rg -U` for `\n{3,}` to find double-blanks anywhere | Misses the EOF case: at end-of-file the sequence is `\n\n<EOF>` (two newlines) not `\n\n\n` (three) | EOF is special — the "second blank line" is implicit. Use a tail-2-bytes check, not a body-scan regex |
| Strip blank lines inside fenced code blocks | Saw `\n\n` runs inside `` ``` `` Python example blocks and thought MD012 was firing on those | MD012's `code_blocks: false` default exempts fenced code; the violation was at EOF the whole time. Would have damaged example output for zero lint benefit | MD012 ignores fenced code blocks by default. Filter your visual scan to *outside* code fences before suspecting in-fence blanks |
| Use `sed -i '${/^$/d}' file.md` (single-line trailing-blank delete) | Tried the canonical short sed idiom to delete one trailing blank | Only deletes a single trailing blank line — leaves `\n\n` runs of length 3+ untouched; also macOS sed needs `-i ''` | Use `printf '%s\n' "$(cat file)" > file` for portability; it strips *all* trailing blank lines in one pass and works identically on GNU and BSD systems |

## Results & Parameters

**Tooling versions verified against:**

| Tool | Version | Source |
|------|---------|--------|
| markdownlint | 0.40.0 | invoked by markdownlint-cli2 in ProjectMnemosyne CI |
| markdownlint-cli2 | 0.22.1 | `npx --yes markdownlint-cli2 <file>` |

**MD012 rule behavior (defaults):**

| Setting | Default | Effect |
|---------|---------|--------|
| `maximum` | 1 | At most 1 consecutive blank line allowed |
| `code_blocks` | false | Fenced code blocks are exempt from the rule |

**One-line fixes (copy-paste ready):**

```bash
# Portable POSIX fix (works on GNU + BSD/macOS):
printf '%s\n' "$(cat path/to/file.md)" > /tmp/_fix && mv /tmp/_fix path/to/file.md

# GNU sed equivalent (strips ALL trailing blanks):
sed -i -e :a -e '/^$/{$d;N;ba' -e '}' path/to/file.md

# Detect before fixing (returns "yes" iff last two bytes are both newlines):
[ -z "$(tail -c 2 path/to/file.md | head -c 1 | tr -d '\n')" ] && echo yes
```

**Pre-commit prophylaxis (`.pre-commit-config.yaml`):**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: end-of-file-fixer
        files: \.md$
```

**Observed hit rate during ProjectMnemosyne PR batch (2026-05-29):**

| Metric | Value |
|--------|-------|
| Total markdownlint failures triaged | 9 |
| Failures rooted in EOF trailing-blank | 4 (PRs #2001, #2002, #2003, #2004) |
| Hit rate | 44% (4/9) |
| PRs fixed with the one-liner | 4 (commits 6600e6a, 6ff96f5, 9e3fb70, 5611cdc) |
| Average fix size | 1 line (trailing newline) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | Batch fix of 10 failing PRs on 2026-05-29; 4 of 9 markdownlint failures shared this exact root cause | PRs #2001, #2002, #2003, #2004 — all pushed with auto-merge armed; commits 6600e6a / 6ff96f5 / 9e3fb70 / 5611cdc |
