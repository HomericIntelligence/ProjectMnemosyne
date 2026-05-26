---
name: ci-markdownlint-md060-table-separator-spaces
description: "Use when: (1) CI markdownlint job fails with MD060/table-column-style 'Table pipe is missing space to the right/left for style compact', (2) local pre-commit Markdown Lint hook passes but CI's separate markdownlint job fails on the same .md file, (3) adding or modifying any markdown table in docs/ and you want to pre-empt the CI gate."
category: ci-cd
date: 2026-05-26
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - markdownlint
  - markdownlint-cli2
  - MD060
  - tables
  - table-column-style
  - ci-cd
  - pre-commit-divergence
  - docs
---

# CI markdownlint MD060: use spaced table separators

## Overview

| Field | Value |
| ----- | ----- |
| **Date** | 2026-05-26 |
| **Objective** | Stop CI's markdownlint job from failing MD060 on table separators after local pre-commit Markdown Lint already passed |
| **Outcome** | Verified — converting `\|---\|---\|---\|` to `\| --- \| --- \| --- \|` and re-running `pixi run npx markdownlint-cli2` locally produces 0 errors and unblocks CI |
| **Verification** | verified-ci (CI passed on PR #5457 after fix applied to `docs/dev/autograd-phase2-design.md`) |

## When to Use

- CI's `markdownlint` job reports `MD060/table-column-style ... Table pipe is missing space to the right for style 'compact'` (or "to the left")
- Local `pixi run pre-commit run --from-ref origin/main --to-ref HEAD` reports the **Markdown Lint** hook as `Passed`, but CI's separate `markdownlint` job fails on the same file
- You are about to push a PR that adds or modifies any markdown table in `docs/` or any other markdown file scanned by CI
- You see MD060 errors specifically on **table separator rows** (the `|---|` row, not data rows)

## Verified Workflow

### Quick Reference

```bash
# 1. Convert compact separators to spaced separators in the target file
python3 - <<'PY'
import re
from pathlib import Path
p = Path("docs/dev/<file>.md")
text = p.read_text()
def fix_sep(m):
    cells = m.group(0).strip().strip('|').split('|')
    return '| ' + ' | '.join(c.strip() for c in cells) + ' |'
new = re.sub(r'^\|[\s:|-]+\|\s*$', fix_sep, text, flags=re.MULTILINE)
p.write_text(new)
PY

# 2. Verify with the SAME tool CI runs (NOT pre-commit)
pixi run npx markdownlint-cli2 docs/dev/<file>.md
# Must print "Summary: 0 error(s)" before pushing
```

### Detailed Steps

1. **Confirm the failure class.** Inspect the CI log:

   ```bash
   gh run view <RUN_ID> --log-failed | grep -E "MD060|table-column-style"
   ```

   Look for `Table pipe is missing space to the right for style 'compact'` (or `left`).
   The reported line numbers will point at separator rows like `|---|---|---|`.

2. **Apply the fix.** Replace every compact separator row with a spaced separator:

   ```markdown
   <!-- BEFORE (fails MD060 in CI) -->
   | Col A | Col B | Col C |
   |---|---|---|
   | a | b | c |

   <!-- AFTER (passes MD060) -->
   | Col A | Col B | Col C |
   | --- | --- | --- |
   | a | b | c |
   ```

   The Quick Reference Python snippet above does this safely with a regex anchored
   to lines that match `^\|[\s:|-]+\|\s*$` (separator rows only — never touches data rows).
   The snippet also preserves alignment markers (`:---`, `:---:`, `---:`).

3. **Verify with CI's actual tool, not pre-commit.**

   ```bash
   pixi run npx markdownlint-cli2 docs/dev/<file>.md
   ```

   Pre-commit's `Markdown Lint` hook and CI's `markdownlint` job use **different
   config files / different rule enablement**. Local pre-commit may say `Passed`
   while CI fails on MD060. The only authoritative pre-push check is running
   `markdownlint-cli2` directly the way CI does.

4. **Commit, push, watch CI.** The dedicated `markdownlint` job should now report success.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Trusted local pre-commit Markdown Lint hook | Ran `pixi run pre-commit run --from-ref origin/main --to-ref HEAD`; the `Markdown Lint` hook printed `Passed` and the PR was pushed | CI's `markdownlint` job is a **separate gate** with a different markdownlint-cli2 invocation/config that enables MD060 strictly. Local pre-commit's hook config did not flag MD060 on compact separators | Local pre-commit passing does NOT imply CI markdownlint will pass. Always run `pixi run npx markdownlint-cli2 <file>.md` directly before pushing any .md change |
| `markdownlint-cli2 --fix` to auto-fix MD060 | Ran `pixi run npx markdownlint-cli2 --fix docs/dev/<file>.md` expecting auto-repair like other MD0xx rules | `--fix` covers many markdownlint rules but **not** MD060/table-column-style. The tool reported 0 modifications and the error persisted | MD060 has no autofix. Apply the regex/Python snippet (or hand-edit) — do not waste a cycle on `--fix` |
| Adding more dashes to compact separators | Tried `\|------\|------\|------\|` thinking MD060 wanted longer dashes | MD060 is about **space padding around pipes**, not dash count. Compact-style separators fail regardless of how many `-` chars sit between the pipes | Spaces around pipes are the fix; dash count is irrelevant |

## Results & Parameters

### Reproducer

```markdown
| A | B | C |
|---|---|---|
| 1 | 2 | 3 |
```

`pixi run npx markdownlint-cli2 file.md` →

```text
file.md:2 MD060/table-column-style Table column style
  [Table pipe is missing space to the right for style 'compact']
```

### Fixed form (passes)

```markdown
| A | B | C |
| --- | --- | --- |
| 1 | 2 | 3 |
```

### Pre-push verification command (only authoritative local check)

```bash
pixi run npx markdownlint-cli2 path/to/file.md
# Required: "Summary: 0 error(s)" — anything else means CI will fail
```

### Why pre-commit and CI diverge

| Gate | Tool invocation | MD060 enforced? |
| ---- | --------------- | --------------- |
| Local pre-commit `Markdown Lint` hook | Uses the hook's bundled config (may disable MD060 or use looser table-column-style) | Often no |
| CI `markdownlint` job | Direct `markdownlint-cli2` with repo `.markdownlint*` config | Yes |

The remediation is mechanical (regex/sed) and idempotent.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectOdyssey | PR #5457 — `docs/dev/autograd-phase2-design.md` | 26 MD060 errors at table separator rows; fixed with the regex snippet; CI markdownlint job then passed |
