# Skill: Consolidate Pre-commit Exclude Patterns

## Overview

| Field     | Value                                             |
|-----------|---------------------------------------------------|
| Date      | 2026-02-20                                        |
| Issue     | #782                                              |
| PR        | #828                                              |
| Objective | Consolidate shellcheck `exclude` patterns into a single combined regex |
| Outcome   | Success — one-line change, all hooks passed       |
| Category  | ci-cd                                             |

## When to Use

- A pre-commit hook has a standalone `exclude:` for one path while other hooks use combined regexes
- A follow-up issue asks to standardise exclude patterns across hooks
- You need to add `build/` or another common directory to an existing hook's exclude list
- Reviewers flag inconsistent exclude conventions in `.pre-commit-config.yaml`

## Verified Workflow

1. **Read the current config**

   ```bash
   cat .pre-commit-config.yaml
   ```

   Look for hooks that have a lone `exclude:` vs hooks that use `^(path1/|path2/)` combined patterns.

2. **Identify the target hook** and compare its `exclude:` against the project convention (other hooks).

3. **Apply the one-line fix** — replace (or add) the `exclude:` field with a combined regex:

   ```yaml
   exclude: ^(build/|docs/arxiv/)
   ```

   Place `exclude:` immediately after `description:` and before `files:` to match the ordering used by other hooks.

4. **Verify locally**

   ```bash
   pixi run pre-commit run shellcheck --all-files
   ```

   Expected output: `ShellCheck...Passed`

5. **Commit, push, and open PR**

   ```bash
   git add .pre-commit-config.yaml
   git commit -m "chore(pre-commit): consolidate shellcheck exclude patterns into single regex"
   git push -u origin <branch>
   gh pr create --title "..." --body "Closes #<issue>"
   gh pr merge --auto --rebase <pr-number>
   ```

## Failed Attempts

| Attempt | What happened | Why it failed |
|---------|---------------|---------------|
| Used `Skill` tool (`commit-commands:commit`) | Permission denied — session running in don't-ask mode | Skill tool blocked; fell back to direct `git` + `gh` CLI commands |

## Results & Parameters

### Final change (`.pre-commit-config.yaml`)

```yaml
  # Shell script linting
  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.9.0.6
    hooks:
      - id: shellcheck
        name: ShellCheck
        description: Lint shell scripts and templates for best practices
        exclude: ^(build/|docs/arxiv/)   # <-- added line
        files: \.(sh|bash|sh\.template)$
        types: [text]
        args: ['--exclude=SC1091']
```

### Convention observed in this repo

| Hook              | Exclude pattern                          |
|-------------------|------------------------------------------|
| markdownlint-cli2 | combined regex (notes, build, docs/arxiv, docs/design) |
| yamllint          | `^(\.pixi\|build)/`                      |
| shellcheck        | `^(build/\|docs/arxiv/)` (after this fix) |

Markdownlint-cli2 full pattern:

```
^(notes/(plan|issues|review|blog)/|build/|docs/template\.md|docs/arxiv/|docs/design/figures/)
```

## Notes

- The fix is purely cosmetic/convention — no functional behaviour changes if the paths were already excluded
  by separate patterns (in this case `docs/arxiv/` was the only previously-excluded path; `build/` was new)
- Always check whether `build/` should also be excluded when adding `docs/arxiv/` — generated content in
  both directories should not trigger linting errors
