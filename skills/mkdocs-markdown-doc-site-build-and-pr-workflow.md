---
name: mkdocs-markdown-doc-site-build-and-pr-workflow
description: "Use when: (1) MkDocs build failures from nav or cross-references pointing at deleted files — run a pre-deletion audit, fix mkdocs.yml nav, repair --strict out-of-tree links; (2) markdownlint CI reports MD056/table-column-count errors from pipes inside backtick spans, or mkdocs --strict fails with relative links escaping docs/, or a systemic main-branch markdownlint regression is blocking a PR queue; (3) adding a CI pre-commit script to detect drift between documented metric values (CLAUDE.md, README.md) and pyproject.toml config sources (coverage threshold, test counts); (4) starting any documentation-only PR task — detect already-done work, handle a review fix plan that concludes no changes are needed, merge overlapping markdown docs, document pre-commit hook incompatibilities in CONTRIBUTING.md."
category: documentation
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: mkdocs-markdown-doc-site-build-and-pr-workflow.history
tags:
  - mkdocs
  - markdownlint
  - strict-mode
  - nav-cleanup
  - MD056
  - pipe-escape
  - doc-config-drift
  - documentation-workflow
  - pre-commit
  - ci-unblocking
---

## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | mkdocs-markdown-doc-site-build-and-pr-workflow |
| **Category** | documentation |
| **Objective** | Build and ship a documentation site (MkDocs + markdownlint) cleanly, and run documentation-only PR workflows without churn |
| **Trigger** | mkdocs/markdownlint CI red; doc deletions; doc/config metric drift; any docs-only PR |
| **Outcome** | Passing `mkdocs build --strict`, green markdownlint, drift gate wired, no-op-aware doc PR flow |
| **Verification** | verified-ci |

## When to Use

- **mkdocs nav/build cleanup** — a PR is about to (or did) delete `.md` files referenced
  by `mkdocs.yml` nav or by surviving docs; CI "Deploy Documentation" fails with
  "Documentation file 'X.md' specified in nav is not found".
- **mkdocs `--strict` out-of-tree links** — a relative link like `../../docs/dev/foo.md`
  or `../../scripts/foo.sh` resolves outside the `docs/` root and `--strict` aborts.
- **markdownlint CI failures** — MD056/table-column-count from `|` inside backtick code
  spans; MD060 compact table separators; MD033/MD018/MD059 false-positives in prose.
- **Systemic queue block** — every open PR fails the same required markdownlint check on
  the same `file:line` because the bad row lives in `main`.
- **Doc/config metric drift** — numeric thresholds or config paths documented in
  CLAUDE.md / README.md must stay in sync with authoritative `pyproject.toml` values
  (coverage `fail_under`, `--cov` path, test counts).
- **Documentation-only PR workflows** — detect already-done work, confirm a no-op review,
  triage a docs-only security review, make a small targeted edit, merge overlapping docs,
  or document a pre-commit hook incompatibility in CONTRIBUTING.md.

## Verified Workflow

### Quick Reference

```bash
# --- Pre-deletion audit (run BEFORE pushing any doc-deletion PR) ---
FILES_TO_DELETE=$(git diff --name-only --diff-filter=D origin/main...HEAD -- '*.md')
PATTERN=$(echo "$FILES_TO_DELETE" | xargs -n1 basename | sed 's/\.md$//' | paste -sd'|')
grep -rn -E "$PATTERN" docs/ mkdocs.yml --exclude-dir=.git   # any hit MUST be fixed

# --- mkdocs strict local test ---
pixi run mkdocs build --strict     # must finish with NO WARNING lines

# --- MD056 pipe escape: every | inside backticks in a table cell -> \| ---
# Before: | `pip list | grep x` |     After: | `pip list \| grep x` |
grep -nE '\|.*`[^`]*\|[^`]*`' <file>   # detect backtick spans with internal pipes

# --- Validate markdownlint (file or all) ---
npx --yes markdownlint-cli2 "skills/<name>.md"        # "Summary: 0 error(s)"
SKIP=mojo-format pixi run pre-commit run markdownlint-cli2 --all-files

# --- Doc/config drift gate ---
pixi run python scripts/check_doc_config_consistency.py --verbose

# --- Documentation-only PR orientation (run first) ---
git log --oneline -5; git status; gh pr list --head "$(git branch --show-current)"

# --- Commit on GLIBC-incompatible host ---
SKIP=mojo-format git commit -m "docs(<scope>): <summary>"
```

### Detailed Steps

#### 1 — MkDocs nav cleanup (pre-deletion audit, preferred)

`mkdocs --strict` only catches broken links at build time and stops on the first batch,
so a deletion PR with cross-references in N surviving docs takes N red CI runs to fix
incrementally. Audit up front instead:

1. **Enumerate the deletion set** — every `.md` the PR removes:
   `git diff --name-only --diff-filter=D origin/main...HEAD -- '*.md'`.
2. **Build a basename grep pattern** — basenames catch relative links, absolute links,
   nav entries, AND bare prose mentions (e.g. inventory enumerations):
   `echo "$FILES_TO_DELETE" | xargs -n1 basename | sed 's/\.md$//' | paste -sd'|'`.
3. **Grep surviving docs + mkdocs.yml**: `grep -rn -E "$PATTERN" docs/ mkdocs.yml`.
4. **Fix every hit in the same commit**: surviving doc link → remove/repoint;
   `mkdocs.yml` nav entry → remove (and parent section if empty); inventory enumeration
   (`ADR-001 through ADR-XYZ`) → update the range; unavoidable reference → repoint to an
   archive URL/footnote, never leave a bare broken link.
5. **Re-run the grep — must return empty** before committing. Optionally double-check with
   `mkdocs build --strict` if available locally.

**Post-hoc fallback** (CI already red): identify deleted files from the PR diff, run the
same basename audit in ONE pass (do not push partial fixes), remove nav entries + repoint
cross-links, re-grep to empty, `pre-commit run --files ...`, commit and push.

#### 2 — MkDocs `--strict` out-of-tree links

`--strict` rejects ANY relative link whose resolved target leaves `docs/`, regardless of
`../` depth.

```markdown
<!-- WRONG: from docs/adr/ADR-014.md this escapes docs/ -->
[link](../../docs/dev/mojo-jit-crash-workaround.md)
<!-- CORRECT: ../ from docs/adr/ stays inside docs/ -->
[link](../dev/mojo-jit-crash-workaround.md)

<!-- For targets OUTSIDE docs/ (repo root, scripts/, .github/) use an absolute URL -->
See [wrapper](https://github.com/<org>/<repo>/blob/main/scripts/mojo-under-gdb.sh).
```

Decision rule for links from `docs/`: target inside `docs/` → relative link (count `../`
carefully); target outside `docs/` → absolute GitHub blob URL; external site → absolute
`https://`. Re-verify with `pixi run mkdocs build --strict` (only WARNING-level entries
abort; INFO is tolerated).

#### 3 — markdownlint build fixes

**MD056 (pipe escape).** `Actual - Expected` equals the count of literal `|` inside
backticks on that row. The reported `line:col` points at the surplus pipe. If it sits
inside backticks, escape each `|` as `\|` (CommonMark renders `\|` back to `|`); if not,
the table itself is structurally wrong — restructure, do not escape. Same fix for any
content: shell pipelines, jq filters (`[.comments[]\|select(.body\|test(...))]`), GHA
expressions (`${{ a && '1' \|\| '0' }}`), CLI syntax (`{dry-run\|smoke\|full}`), regex
alternations. Apply to BOTH the `.md` and any `.history` snapshot — `.history` is linted
by CI and inherits unescaped pipes from absorbed Failed Attempts tables. Do NOT use
`&#124;` inside backticks (renders verbatim) and do NOT change table arity.

**MD060 (table separator style).** Compact `|---|` → spaced `| --- |`.

**False-positive escape catalog** (escape the character, never reword):

- MD033 on `<placeholder>` in prose → backtick-wrap: `` `<version>` `` (not `&lt;...&gt;`).
- MD018 on line-start `#NNN` → reflow so `#NNN` is mid-sentence, or escape `\#NNN`.
- MD059 on `[link]`/`[here]`/`[click]` → use the real subject: `[PR #5453](url)`.

**Systemic queue block.** When the same `file:line` fails across unrelated PRs, the bug
is in `main`. Verify uniform failure mode per PR via `statusCheckRollup` before any bulk
action, then run a two-track recovery: Track A lands the escape fix (admin-merge it — its
merge-base still has the bad file, so it will also fail, expected); Track B drains the
stuck queue by admin-merging each verified-uniform PR **sequentially** (parallel
admin-merges race on the base branch).

#### 4 — Doc/config drift detection script

Add a pre-commit gate that reads authoritative values from `pyproject.toml` and asserts
docs match. Place `scripts/check_doc_config_consistency.py` (full source in `.history`)
with checks: coverage `fail_under` vs. `CLAUDE.md` `(\d+)%\+?\s+test coverage`; `--cov=`
path vs. `README.md`; and README test-count claims within a 10% tolerance of
`pytest --collect-only -q`. `main()` returns `int` (the `__main__` block does
`sys.exit(main())`), making unit tests call `main()` directly and assert the return value.
Patch `subprocess.run` in the script's own namespace
(`scripts.check_doc_config_consistency.subprocess.run`), not the stdlib location. Wire it:

```yaml
- id: check-doc-config-consistency
  name: Check Doc/Config Metric Consistency
  entry: pixi run python scripts/check_doc_config_consistency.py
  language: system
  files: ^(CLAUDE\.md|README\.md|pyproject\.toml)$
  pass_filenames: false
```

#### 5 — Documentation-only PR workflow

**Always run orientation first** — `git log --oneline -5`, `git status`,
`gh pr list --head <branch>` — before touching any file.

- **Already-committed detection:** clean status + log commit matching the issue title →
  read target files to confirm content (do not trust the commit message), confirm the
  open PR has auto-merge + `Closes #<N>`, then stop. Do not create a duplicate
  commit/PR. Judge completeness against Success Criteria, not plan notes.
- **No-op review confirmation:** if `.claude-review-fix-*.md` says "no fixes required",
  verify the CI failures pre-exist on `main`, confirm a clean tree, and report — do not
  create an empty commit or redundant push.
- **Docs-only security triage:** classify every changed file; if all are `.md` / static
  `.json` / `.txt` / `.rst` there is no attack surface — issue the clean no-findings
  report. YAML/Actions examples inside `.md` code blocks are documentation, not workflows.
- **Small doc edit:** read the issue + target file, anchor the Edit's `old_string` to the
  lines before AND after the insert point, `pre-commit run --all-files`, commit only the
  modified file with `Closes #<N>`, push, `gh pr merge --auto --rebase`.
- **Merge overlapping docs:** read both in parallel, grep all cross-references
  (`grep -rn "old-filename\.md" --include="*.md" .`), append unique content into the
  canonical, `git rm` the duplicate, repoint every reference (including self-referential
  "See Also" links in the canonical), then fix MD013/MD032 and close fenced blocks with a
  plain ```` ``` ```` (never ```` ```text ```` as a closing tag).
- **Hook incompatibility doc:** audit `.pre-commit-config.yaml`, `docs/dev/`, and
  `CONTRIBUTING.md` first (often only CONTRIBUTING.md is missing); add a `####` subsection
  with OS/library range, exact warning text, what the hook does automatically, the CI
  guarantee, and a link to the full compat doc.

**GLIBC caveat:** if `mojo-format` fails with `GLIBC_2.3x not found` and no `.mojo` files
changed, `SKIP=mojo-format git commit ...`. All other hooks must pass. Prefer
`pixi run pre-commit run --all-files` over `just pre-commit-all` (the latter fails with
unrelated "Text file busy" errors).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Push deletion PR with no upfront cross-reference audit | Scorched-earth deletion PR; mkdocs `--strict` failed on surviving docs linking to a deleted page | mkdocs reports broken links only at build time and stops on the first batch; partial fixes guarantee another red iteration per missed referrer | Run the basename pre-deletion audit grep in the same commit as the deletion; after ANY deletion-caused CI failure, re-audit the full deletion set before re-pushing — never patch only the file CI named |
| Rely on mkdocs to catch stale inventory enumerations | A surviving `docs/README.md` enumerated `ADR-001 through ADR-008` including deleted ADRs | `--strict` validates only parsable link targets, not bare filename/ID mentions in prose | Use a basename grep (not just link-target grep) so prose mentions, footnotes, and inventory lists are caught too |
| Treating link-check failures as in-scope | Planned to fix root-relative path errors in unrelated files in a deletion PR | They were pre-existing on `main`, not caused by the PR | Verify with `gh run list --branch main --workflow "..."` before scoping fixes |
| Adding more `../` hops / HTML anchor / symlink for out-of-tree links | Bumped `../../` to `../../../`, used `<a href=...>`, symlinked `docs/scripts -> ../scripts` | `--strict` rejects ANY relative link resolving outside `docs/`, parses HTML anchors the same way, and renders symlinked non-doc files as broken pages | Link to non-doc files via absolute GitHub blob URLs |
| Wrapped pipe content in HTML code tags / used `&#124;` inside backticks | Tried `<code>...</code>` or HTML entity to protect pipes in a table cell | markdownlint counts unescaped `\|` before any code-span/HTML semantics; backticks render `&#124;` verbatim | Backslash-escape each internal pipe as `\|`; use `&#124;` only outside backticks |
| Ran `markdownlint-cli2 --fix` for MD056 | Hoped autofix would handle the table-column error | MD056 has no autofix — 0 modifications, error persists | Manual `\|` escape; triage by `line:col` (column lands on the surplus pipe) |
| Adding columns to the header / removing the pipe to absorb MD056 | Bumped header arity or rewrote the command without the pipe | Destroyed table semantics or lost the documented behavior | Never change table arity; escape the pipe and preserve the example verbatim |
| HTML-entity / bracket-removal for MD033, reword to `[here]` for MD059, leading space for MD018 | Tried `&lt;version&gt;`, dropped angle brackets, `[here]`, indented `#NNN` | Entities render literally; brackets carry substitution-slot meaning; `here`/`click`/`this` are also non-descriptive; the ATX parser strips leading whitespace | Backtick-wrap placeholders, use the real subject as link text, reflow or `\#NNN` |
| Parallel admin-merge of a stuck markdownlint queue | Ran `gh pr merge --admin` against 17 PRs concurrently | 13 hit "base branch was modified" races | Admin-merge stuck queues sequentially, one at a time, after a per-PR `statusCheckRollup` audit |
| Trusted `.history` snapshots to be lint-safe | Snapshotted skill files into `.history` without pre-flight lint | Absorbed Failed Attempts tables carry unescaped pipes; `.history` IS linted by CI | Pre-flight markdownlint on BOTH the `.md` AND `.history` before pushing |
| Patched `subprocess.run` globally in drift-check tests | `patch("subprocess.run", ...)` for `collect_actual_test_count` | The script already imported `subprocess`; patching the stdlib location has no effect on the bound reference | Patch in the module's own namespace: `scripts.check_doc_config_consistency.subprocess.run` |
| Used `pytest.raises(SystemExit)` for drift-check `main()` tests | Expected `main()` to call `sys.exit()` | `main()` returns `int`; only the `__main__` block exits | Call `main()` directly and assert the return value |
| Creating an empty commit / duplicate PR on a no-op or already-done branch | Committed review files or re-edited targets "to have something"; ran `gh pr create` without checking | Adds history noise / opens a second PR causing CI confusion | Only commit real changes; always check `gh pr list --head <branch>` and read target files first |
| Performing full multi-phase security review on a docs-only PR | Ran Phase 1-3 review on a PR of only `.md` + `plugin.json` | All findings excluded by the hard docs exclusion rule; YAML inside `.md` code blocks is documentation, not a workflow | Classify file types first; if all docs/metadata, issue the no-findings report immediately |
| Closing fenced blocks with ```` ```text ```` after a doc merge / pasting long lines | Used a language-tagged closing fence; pasted 150-241 char source lines | markdownlint treats ```` ```text ```` as opening a new block; lines failed MD013 | Close fences with a plain ```` ``` ````; run markdownlint after every merge to catch line length and MD032 |
| Running `just pre-commit-all` / `pixi run npx markdownlint-cli2` for validation | Used `just` or `npx` as the validation entrypoint | `just`/`npx` not on PATH on this host; `just` also throws unrelated "Text file busy" | Use `pixi run pre-commit run --all-files` (or `markdownlint-cli2 --all-files`) directly |
| Editing the main repo instead of the active worktree | Made CLAUDE.md edits in the main repo path | The worktree tracks a different commit on the feature branch | Edit the worktree directly or `cp` changes into the worktree path |

## Results & Parameters

### MD056 reproducer

```markdown
| A | B | C | D |
| - | - | - | - |
| x | y | `cmd \|\| other` | z |
```

`markdownlint-cli2 --config .markdownlint.yaml file.md` → exit 0. Without the backslashes:
`MD056 Expected: 4; Actual: 6`.

### Pre-deletion audit (copy-paste)

```bash
FILES_TO_DELETE=$(git diff --name-only --diff-filter=D origin/main...HEAD -- '*.md')
if [ -z "$FILES_TO_DELETE" ]; then
  echo "No .md deletions detected."
else
  PATTERN=$(echo "$FILES_TO_DELETE" | xargs -n1 basename | sed 's/\.md$//' | paste -sd'|')
  grep -rn -E "$PATTERN" docs/ mkdocs.yml --exclude-dir=.git || echo "Clean — safe to push."
fi
```

### Tooling versions verified

| Tool | Version | Result |
| ---- | ------- | ------ |
| markdownlint-cli2 | 0.20.0 (local) / 0.22.1 (CI) | 0 errors after escape |
| markdownlint | 0.40.0 (CI underlying) | green |
| mkdocs | `--strict` | builds with no WARNING lines after link fixes |
| tomllib | Python 3.11+ stdlib | drift-check reads pyproject.toml directly |

### Queue-recovery telemetry

| Metric | Value |
| ------ | ----- |
| PRs blocked on the same MD056 line | 17 |
| Track-A admin-merge wall time | ~30 s |
| Track-B sequential admin-merge of remaining 16 | ~90 s |
| Total queue recovery | ~2 minutes |

### Doc/config drift-check parameters

| Parameter | Value |
| --------- | ----- |
| Script | `scripts/check_doc_config_consistency.py` |
| Hook ID | `check-doc-config-consistency` |
| Hook trigger | `^(CLAUDE\.md\|README\.md\|pyproject\.toml)$` |
| Exit codes | 0 = all pass, 1 = any violation |
| CLAUDE.md threshold pattern | `(\d+)%\+?\s+test coverage` |
| README cov-path pattern | `--cov=(\S+)` |
| README test-count pattern / tolerance | `(\d[\d,]*)\+?\s+tests?` / 10% |

### Documentation PR templates

```text
# Commit (docs-only)
docs(<scope>): <what was added>

Closes #<issue-number>

# Docs-only security review — clean no-findings report
No security vulnerabilities were identified in this PR.
The changes consist entirely of documentation files. Per the hard exclusion rules,
documentation findings are excluded, and these files contain no executable code,
user input handling, auth logic, cryptographic operations, or other attack surfaces.
```

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectOdyssey | PR \#3308 (issue \#3142) — deleted 17 placeholder docs, fixed `mkdocs.yml` nav + broken relative link | mkdocs nav cleanup |
| ProjectOdyssey | PR \#5381 (`63b9db7f9`) — mkdocs `--strict` out-of-tree links fixed in `docs/dev/mojo-jit-crash-capture-core.md` | Replaced `../../scripts/` / `../../.github/` links with absolute GitHub URLs |
| ProjectMnemosyne | PR \#1756 — same MD056 root cause across 17 PRs; two-track recovery in ~2 minutes | `gh run view --log-failed \| grep MD056` |
| ProjectMnemosyne | PRs \#1937/\#1959/\#1960/\#1965/\#1978 — MD033/MD059/MD018/MD056 false-positive catalog | 5-PR parallel swarm fix wave |
| ProjectMnemosyne | PRs \#2046/\#2049/\#2030 — MD056 fixes for shell + jq pipe filters in tables | 10-PR queue triage 2026-05-29 |
| ProjectScylla | Issue \#1151, PR \#1225 / Issue \#1226, PR \#1315 — doc/config drift script (coverage + cov path, then test count) | 53 tests; exits 0 against real repo |
| ProjectOdyssey | Issues \#3087/\#3089/\#3150/\#3253 — auto-impl, preflight, review-fix, hook-doc workflows | Documentation PR meta-patterns |
| ProjectMnemosyne | Docs-only security reviews + skill-cleanup issues | Documentation PR meta-patterns |
