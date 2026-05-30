---
name: markdown-linting-and-build-fixes
description: "Use when: (1) markdownlint CI reports MD056/table-column-count errors from
  pipes inside backtick code spans in table cells, (2) mkdocs --strict build fails with
  out-of-tree relative links pointing outside docs/, (3) CLAUDE.md exceeds a line/token
  budget and needs trimming without losing critical rules, (4) shared documentation files
  are missing link-backs in an index/root markdown file, (5) an entire PR queue is red on
  the same markdownlint check pointing to the same file:line — systemic main-branch
  regression needing fix + bulk queue recovery"
category: documentation
date: 2026-05-29
version: "1.2.0"
verification: verified-ci
user-invocable: false
history: markdown-linting-and-build-fixes.history
tags:
  - markdownlint
  - MD056
  - MD060
  - tables
  - pipe-escape
  - mkdocs
  - strict-mode
  - claude-md
  - token-budget
  - ci-unblocking
  - queue-unblock
  - admin-merge
  - MD033
  - MD018
  - MD059
  - false-positives
---

# Markdown Linting and Documentation Build Fixes

## Overview

| Field | Value |
| ----- | ----- |
| **Goal** | Fix documentation toolchain failures: markdownlint errors, mkdocs --strict build failures, CLAUDE.md token bloat, and shared-link drift |
| **Trigger** | CI red on markdownlint or mkdocs; CLAUDE.md over budget; shared docs missing from index |
| **Output** | Passing markdownlint + mkdocs build + trimmed CLAUDE.md + linked shared docs |
| **Risk** | Low — mechanical escapes, link rewrites, and structural edits only |

## When to Use

- **MD056 pipe escape**: markdownlint reports `Expected: N; Actual: N+K` on a table row
  containing `|` or `||` inside backtick code spans (GitHub Actions expressions, shell pipes)
- **Systemic queue block**: every open PR fails the same required markdownlint check on the
  same `file:line` — the bug lives in `main`, not in any PR
- **mkdocs --strict failure**: "Deploy Documentation" CI aborts with
  `Aborted with N warnings in strict mode` caused by relative links escaping the `docs/` tree
- **CLAUDE.md token budget**: file exceeds a line budget (e.g., >1,200 lines), sections
  duplicate content in `.claude/shared/`, or MD060 table-column-style errors need fixing
- **Shared-link drift**: `.claude/shared/` files exist on disk but are absent from a root
  file's Quick Links section; pre-commit hook needed to prevent future drift
- **MD033 false-positive on placeholders**: angle-bracket placeholders in prose like
  `` `<version>` ``, `` `<dep>` ``, `` `<thing>` `` trigger `MD033/no-inline-html` even
  though they are documentation prose, not HTML tags
- **MD018 false-positive on `#NNN` at column 1**: a line beginning with an issue
  reference like `\#5453.` triggers `MD018/no-missing-space-atx` (the `#` is misread as
  a malformed heading)
- **MD059 false-positive on link text**: link text like `[link](url)`, `[here](url)`,
  `[click](url)` triggers `MD059/descriptive-link-text`
- **MD056 in non-table cells**: pipe-containing syntax examples like
  `{dry-run\|smoke\|full}` or nested markdown-table examples inside a cell, not just
  GitHub Actions expressions

## Verified Workflow

### Quick Reference

```bash
# --- MD056 pipe escape ---
# Escape every | inside backticks in a table cell as \|
# Before: | `${{ a && '1' || '0' }}` |
# After:  | `${{ a && '1' \|\| '0' }}` |
# Before: | `pip list | grep hephaestus`           |
# After:  | `pip list \| grep hephaestus`          |
# Before: | `[.comments[]|select(.body|test(...))]` |
# After:  | `[.comments[]\|select(.body\|test(...))]` |

# --- Detect the pattern across a file ---
grep -nE '\|.*`[^`]*\|[^`]*`' <file>
# Finds backtick code spans containing internal pipes in table-line-ish content.

# --- Validate markdownlint ---
npx --yes markdownlint-cli2 "skills/<name>.md"
# MUST be "Summary: 0 error(s)" before commit/push

# --- mkdocs strict local test ---
pixi run mkdocs build --strict
# Must complete with no WARNING lines

# --- CLAUDE.md audit ---
grep -n "^##\|^###\|^####" CLAUDE.md
wc -l CLAUDE.md
pixi run npx markdownlint-cli2 CLAUDE.md   # baseline before editing

# --- Shared-link audit ---
grep -n "shared/" CLAUDE.md | head -30
ls .claude/shared/
python scripts/audit_shared_links.py
```

### Step 1 — Identify the failure type

Read the CI error output to classify:

| CI Error Pattern | Failure Type | Go to Step |
| ---------------- | ------------ | ---------- |
| `MD056 ... Too many cells` on a row with backtick `\|` | Pipe escape | Step 2 |
| Same `file:line` failing across all open PRs | Systemic queue block | Step 3 |
| `Aborted with N warnings in strict mode` in mkdocs job | mkdocs out-of-tree link | Step 4 |
| CLAUDE.md over line budget or MD060 errors | Token trim | Step 5 |
| `.claude/shared/` file missing from Quick Links | Shared-link audit | Step 6 |
| MD033 on `<version>`/`<placeholder>` in prose | Placeholder false-positive | Step 7 |
| MD018 on line starting with `#NNN` | Issue-ref false-positive | Step 7 |
| MD059 on `[link]`/`[here]`/`[click]` text | Non-descriptive link | Step 7 |
| MD056 on `{a\|b\|c}` syntax inside a cell | Non-GHA pipe in cell | Step 7 |

### Step 2 — Fix MD056: escape pipes inside backticks in table cells

**Diagnosis:** `M - N` in the MD056 error equals the count of literal `|` chars inside
backticks on that row (each `|` adds one phantom cell; `||` adds two).

```bash
gh run view <RUN_ID> --log-failed | grep MD056
```

**Column-number triage recipe.** When markdownlint reports
`Expected: N; Actual: N+K` at `line:col`:

1. Open the file at the cited `line:col`. The column number points at where the
   surplus `|` lives — not at the row's start.
2. Check whether that `|` sits inside backticks. If yes, this exact bug pattern —
   escape with `\|` inside the code span. The rendered output still shows `|`
   (CommonMark/GitHub renders `\|` as `|`).
3. If no, the table itself is structurally wrong (added/missing cells) — restructure
   the table, do NOT escape.

**Common offender content (NOT just GitHub Actions expressions):**

- Shell pipelines: `` `pip list | grep hephaestus` ``, `` `cat foo | head` ``
- jq filters with multiple `|` operators: `` `[.comments[]|select(.body|test(...))]` ``
- GitHub Actions expressions: `` `${{ a && '1' || '0' }}` ``
- CLI option syntax: `` `{dry-run|smoke|full}` ``
- Regex alternations: `` `(foo|bar|baz)` ``

The triage technique is identical regardless of content type — count literal `|`
chars inside backticks per cell.

**What does NOT fix it:**

- Adding columns to the table header — breaks the table's semantics.
- Removing the pipe from the code example — destroys the documented behavior.
- HTML entity `&#124;` inside backticks — renders as literal entity text in code spans.

**Fix:** inside any inline code span between backticks inside a table cell, replace every
`|` with `\|`. Leave structural pipe cell-separators alone.

```markdown
<!-- BEFORE (MD056 fires: 4-column table, row has 6 cells) -->
| Attempt | Tried | Why Failed | Lesson |
| ------- | ----- | ---------- | ------ |
| GHA expr | Used `${{ inputs.x && '1' || '0' }}` | n/a | n/a |

<!-- AFTER (passes MD056) -->
| Attempt | Tried | Why Failed | Lesson |
| ------- | ----- | ---------- | ------ |
| GHA expr | Used `${{ inputs.x && '1' \|\| '0' }}` | n/a | n/a |
```

Note: `&#124;` also works outside backticks but renders as the literal entity inside code
spans — use `\|` for table cells with inline code.

Apply this escape to BOTH the `.md` skill file AND any `.history` snapshot file — absorbed
content in `.history` frequently inherits unescaped pipes from original files' Failed
Attempts tables, and `.history` files ARE linted by CI.

Additional escape rules to apply in the same pass:

- Line-starting PR references like `#1234` at the start of a paragraph: escape as `\#1234`
  (prevents MD018)
- Avoid blank lines inside blockquotes (prevents MD028)

### Step 3 — Systemic queue block: one bad row in main blocks every PR

**Mechanism:** Required-check CI runs markdownlint over the merge-base snapshot (PR HEAD
merged into base). If the bad file lives in `main`, every open PR's merge-snapshot inherits
it and becomes un-mergeable — even PRs that never touched the file.

**Diagnostic giveaway:** failing `file:line` is identical across unrelated PRs.

**Safety gate — verify uniform failure mode before any bulk action:**

```bash
for pr in <list-of-pr-numbers>; do
  echo -n "PR #$pr: "
  gh pr view $pr --json statusCheckRollup \
    | python3 -c "import json,sys; d=json.load(sys.stdin); \
        print(','.join(c['name'] for c in d['statusCheckRollup'] \
              if c.get('conclusion') in ('FAILURE','CANCELLED','TIMED_OUT')))"
done
```

Expected: every line ends in just `markdownlint`. If any line lists additional failures,
investigate that PR individually — do not bulk admin-merge a queue with mixed failure modes.

**Two-track recovery (run both in parallel):**

- **Track A — land the fix:** branch from `main`, apply the escape (Step 2), push, open
  fix PR, admin-merge it (it will also fail markdownlint since its merge-base still has the
  bad file — that is expected).
- **Track B — drain the stuck queue:** admin-merge each verified-uniform PR
  **sequentially, not in parallel** (parallel admin-merges cause base-branch races; see
  `tooling-gh-pr-merge-admin-parallel-base-branch-race`).

Observed total recovery: **~2 minutes** for 17 stuck PRs.

### Step 4 — Fix mkdocs --strict out-of-tree links

mkdocs `--strict` rejects ANY relative link whose resolved target is outside `docs/`,
regardless of `../` depth.

**Reproduce locally:**

```bash
pixi run mkdocs build --strict
# Warning format: Doc file 'X.md' contains a link 'Y', but the target 'Z' is not found
```

**Fix:** rewrite each offending relative link as an absolute GitHub blob URL:

```markdown
<!-- WRONG (mkdocs --strict aborts) -->
See [wrapper](../../scripts/mojo-under-gdb.sh).

<!-- CORRECT -->
See [wrapper](https://github.com/<org>/<repo>/blob/main/scripts/mojo-under-gdb.sh).
```

**Decision rule for links from `docs/`:**

| Target location | Link format |
| --------------- | ----------- |
| Inside `docs/` | Relative link within `docs/` — count `../` carefully to stay inside `docs/` |
| Outside `docs/` (repo root, scripts/, .github/) | Absolute GitHub URL: `https://github.com/<org>/<repo>/blob/main/<path>` |
| External site | Absolute `https://...` URL |

**Re-verify:**

```bash
pixi run mkdocs build --strict
# Must complete: "Documentation built in N.NN seconds" — no WARNING lines
# INFO lines are tolerated; only WARNING-level entries abort --strict
```

### Step 5 — Trim CLAUDE.md token budget

**Baseline before touching anything:**

```bash
wc -l CLAUDE.md
pixi run npx markdownlint-cli2 CLAUDE.md 2>&1 | tee /tmp/baseline-lint.txt
git stash && pixi run npx markdownlint-cli2 CLAUDE.md 2>&1 > /tmp/before.txt
git stash pop && pixi run npx markdownlint-cli2 CLAUDE.md 2>&1 > /tmp/after.txt
diff /tmp/before.txt /tmp/after.txt   # distinguish pre-existing vs. introduced errors
```

**Classify each section:**

- **Keep full:** CRITICAL RULES, decision trees, quick-ref tables, any section with no link destination
- **Trim examples:** remove code-block examples illustrating points already stated in bullets
- **Move + link:** pure reference content that belongs in `.claude/shared/`

**Never trim:** `## ⚠️ CRITICAL RULES`, Mojo critical patterns, Pre-Commit Hook Policy,
Git workflow with concrete `gh pr create` examples, any section prefixed with `⚠️`.

**Fix MD060 table style errors** (compact `|---|` → spaced `| --- |`):

```markdown
<!-- BEFORE (triggers MD060) -->
| Task | Budget | Examples |
|------|--------|----------|

<!-- AFTER (passes MD060) -->
| Task | Budget | Examples |
| ---- | ------ | -------- |
```

**Validate and commit:**

```bash
wc -l CLAUDE.md
pixi run npx markdownlint-cli2 CLAUDE.md 2>&1   # must be 0 errors
git add CLAUDE.md
git commit -m "docs(claude-md): trim CLAUDE.md from X to Y lines"
```

**Note on pre-commit:** if `mojo-format` fails due to GLIBC incompatibility and no `.mojo`
files were changed, skip it: `SKIP=mojo-format pre-commit run --all-files`. All other hooks
(markdownlint, trailing-whitespace, check-yaml) must pass.

### Step 6 — Audit shared-link drift

**Manual audit:**

```bash
grep -n "shared/" CLAUDE.md | head -30
ls .claude/shared/
python scripts/audit_shared_links.py   # exit 0 = all linked; exit 1 = missing files
```

**Add missing entries** to the Quick Links / Core Guidelines section:

```markdown
- [Git Commit Policy](/.claude/shared/git-commit-policy.md)
- [Output Style Guidelines](/.claude/shared/output-style-guidelines.md)
```

**Regex for link extraction** (handles absolute, relative, anchors):

```python
re.compile(r"\(/?\.claude/shared/([^)#\s]+)(?:#[^)]*)?\)")
```

**Wire pre-commit hook** to prevent future drift:

```yaml
- repo: local
  hooks:
    - id: audit-shared-links
      name: Audit shared/ links in CLAUDE.md
      entry: python scripts/audit_shared_links.py
      language: system
      files: ^(CLAUDE\.md|\.claude/shared/.*)$
      pass_filenames: false
```

### Step 7 — False-positive escape catalog (MD033, MD018, MD059, MD056-non-GHA)

These four rules routinely misfire on ordinary documentation prose. Each has a
character-level escape recipe — DO NOT reword the prose.

#### MD033/no-inline-html on `<placeholder>` in prose

**Trigger:** angle-bracket placeholders like `<version>`, `<dep>`, `<thing>` appearing
in prose. The linter parses them as HTML tags.

**Fix:** backtick-wrap the placeholder so it renders as code.

```markdown
<!-- BEFORE (MD033 fires) -->
Upgrade <dep> to <version> before running migrations.

<!-- AFTER (passes MD033, renders as code in marketplace UI) -->
Upgrade `<dep>` to `<version>` before running migrations.
```

DO NOT use HTML entities (`&lt;version&gt;`) — they render as literal entities in the
marketplace UI. DO NOT remove the angle brackets — they convey "this is a substitution
slot" semantically.

#### MD018/no-missing-space-atx on line-start `#NNN`

**Trigger:** any line beginning at column 1 with `#` followed by digits, e.g.,
`#5453 fixed the issue.` — the linter reads `#5453` as a malformed ATX heading.

**Fix (preferred):** reflow the preceding paragraph so `#NNN` is no longer at column 1.

```markdown
<!-- BEFORE (MD018 fires) -->
See the following PR for details.
#5453 introduced the regression.

<!-- AFTER (preferred — reflow) -->
See the following PR for details. #5453 introduced
the regression.
```

**Fix (escape):** if reflow is awkward, backslash-escape the `#`.

```markdown
\#5453 introduced the regression.
```

#### MD059/descriptive-link-text

**Trigger:** generic link text — `[link]`, `[here]`, `[click]`, `[this]`, `[more]`.

**Fix:** rewrite using the actual subject as link text. Rewording to another generic
word (e.g., `[see here]`) does NOT fix it — "here" is also on the non-descriptive list.

```markdown
<!-- BEFORE (MD059 fires) -->
See PR #5453 ([link](https://github.com/org/repo/pull/5453)) for context.

<!-- AFTER (descriptive — passes MD059) -->
See [PR #5453](https://github.com/org/repo/pull/5453) for context.
```

#### MD056 on non-GHA pipes inside table cells

**Trigger:** any literal `|` inside a table cell (not just GHA expressions). Common
offenders: CLI option syntax `{dry-run|smoke|full}`, regex alternations `(a|b|c)`,
nested markdown-table example fragments `|---|---|---|`.

**Fix:** backslash-escape every literal `\|` inside the cell, exactly as for GHA
expressions (Step 2).

```markdown
<!-- BEFORE (MD056 fires: cell adds 2 phantom columns) -->
| Flag | Values |
| ---- | ------ |
| --mode | `{dry-run|smoke|full}` |

<!-- AFTER (passes MD056) -->
| Flag | Values |
| ---- | ------ |
| --mode | `{dry-run\|smoke\|full}` |
```

**Validate the file:**

```bash
npx --yes markdownlint-cli2 "skills/<name>.md"
# Must be "Summary: 0 error(s)"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Wrapped GHA expression in HTML code tags | Used `<code>...</code>` instead of backticks hoping HTML would protect pipes | MD056 tokenizes the row on `\|` before HTML parsing — bare pipes inside HTML code tags are still counted as cell separators | Tag substitution does not help; backslash-escape each pipe individually |
| Used HTML entity `&#124;` for pipe inside backticks | Replaced `\|` with `&#124;` inside backtick code spans | Backticks render the entity verbatim — readers see literal entity text instead of a pipe | Use `&#124;` only outside backticks; inside inline code, use `\|` backslash-escape |
| Tried `--fix` on markdownlint-cli2 | Ran `markdownlint-cli2 --fix '**/*.md'` hoping autofix would handle MD056 | MD056 has no autofix implementation — reports 0 modifications and the error persists | Manual escape required; do not waste time on autofix for MD056 |
| Assumed PR-introduced regression | Saw multiple PRs failing markdownlint on the same file; planned to rebase each | The failing file was untouched by every PR — the bug had been merged to main earlier | Always `gh pr diff <num> -- <file>` to confirm a PR changed the failing file before blaming/rebasing |
| Parallel admin-merge of 17 stuck PRs | Ran `gh pr merge --admin` against all 17 PRs concurrently | Only 4 succeeded; 13 hit "base branch was modified" race conditions | Admin-merge stuck queues sequentially, one at a time |
| Bulk admin-merge without per-PR check audit | Trusted uniform "all red on markdownlint" surface signal | Risk: admin-merge bypasses required checks — a PR with hidden real failures could land broken code | Always run the Step 3 per-PR `statusCheckRollup` loop before bulk admin-merge |
| Trusted `.history` snapshots to be markdownlint-safe | Snapshotted existing skill files into `.history` without pre-flight lint | Original skill files often contain unescaped pipes in code spans in their Failed Attempts tables; `.history` IS linted by CI | Pre-flight markdownlint on BOTH the `.md` AND `.history` file before pushing |
| Assumed a Wave 1 queue-block fix would last | Fixed shared markdownlint errors that blocked Wave 1 and assumed the next wave would be clean | Each new wave of merge PRs re-introduces both error classes (MD056 from new canonicals, MD018 from `\#N` references) | Bake the markdownlint gate into the merge-agent prompt template so prevention is per-agent |
| Adding more `../` hops to relative links | Bumped `../../scripts/foo.sh` to `../../../scripts/foo.sh` | Still escapes the `docs/` tree; mkdocs only resolves links to files it knows about | mkdocs `--strict` rejects ANY relative link whose target is outside `docs/`, regardless of depth |
| HTML anchor with relative href for mkdocs | Replaced `[text](../../scripts/foo.sh)` with `<a href="../../scripts/foo.sh">text</a>` | mkdocs still parses HTML anchors and runs the same target resolution | Cannot smuggle relative out-of-tree links past `--strict` with HTML |
| Symlink `docs/scripts -> ../scripts` | Created symlink inside `docs/` to expose repo-root scripts as docs files | mkdocs tries to render `.sh` files as docs; build polluted and brittle on Windows | Link to non-doc files on GitHub instead |
| Running `just pre-commit-all` as validation | Used `just pre-commit-all` as the validation step for CLAUDE.md edits | Fails with unrelated pixi "Text file busy" errors — exit 1 even when all hooks pass | Run `pixi run npx markdownlint-cli2 CLAUDE.md` directly |
| Editing main repo instead of worktree | Made CLAUDE.md edits to the main repo path instead of the active worktree | Worktree on a feature branch tracks a different commit | Edit the worktree directly or `cp` changes from main repo to the worktree path |
| Regex `[^)#\s]+` as full shared-link pattern | Pattern stopped capture at `#` but required `)` immediately after | Links with anchors like `foo.md#section` never matched | Use `([^)#\s]+)(?:#[^)]*)?` — optional non-capturing group consumes the anchor before `)` |
| HTML-entity escape for MD033 placeholders | Replaced `<version>` with `&lt;version&gt;` to silence MD033 | Renders as literal HTML entities in the marketplace UI — readers see `&lt;version&gt;` text instead of `<version>` | Backtick-wrap (`` `<version>` ``) is both lint-clean AND renders correctly as code |
| Removed angle brackets to dodge MD033 | Replaced `<placeholder>` with `placeholder` to avoid the rule entirely | Lost semantic meaning — readers cannot tell it is a substitution slot vs. a literal word | Backtick-wrap preserves both lint-cleanness and substitution-slot semantics |
| Reworded link text from `[link]` to `[here]` for MD059 | Assumed any non-`link` word would satisfy descriptive-link-text | Still fires — `here`, `click`, `this`, `more` are all on the rule's non-descriptive blocklist | Use the actual subject as link text (e.g., `[PR #5453](url)`), not another generic word |
| Adding a leading space to dodge MD018 on `#NNN` | Indented `#5453.` by one space hoping to escape the ATX-heading parser | Linter still treats it as malformed heading after stripping leading whitespace | Reflow the preceding line so `#NNN` is mid-sentence, OR backslash-escape as `\#NNN` |
| Assuming MD056 only fires on GitHub Actions expressions | Searched only for `${{` patterns when triaging MD056 errors | Missed CLI syntax cells like `{dry-run\|smoke\|full}` and regex-alternation cells — same root cause, different content | Triage by counting literal `\|` inside backticks per cell; the content type does not matter |
| Trusted "backticks delimit a code span" intuition | Assumed `\|` inside `` `pip list \| grep x` `` was treated as code, not a column separator | markdownlint's table parser counts unescaped `\|` BEFORE applying any code-span semantics — so the row gains a phantom cell anyway | Backslash-escape every internal pipe with `\|` regardless of backtick context |
| Adding columns to the table header to match cell count | Saw a 2-column header become a 3-cell row and tried to bump header to 3 columns | Destroyed the table's semantics — the new column had no meaning, and authors hit the same bug on the next row | Never change table arity to absorb phantom cells; escape the pipe in the offending code span |
| Removing the pipe from the code example | Rewrote `` `pip list \| grep hephaestus` `` to `` `pip list` (then grep ...) `` | Lost the documented behavior — the example no longer showed the working command | Preserve the example verbatim; escape with `\|` and let CommonMark render it back to `\|` |
| Searching for MD056 by line number alone | Read the cited line but missed which cell contained the surplus pipe | The MD056 error reports a column number that points directly at the surplus `\|` — using only the line wastes a search | Open at `line:col` from the error; the column lands on the offending character |
| Treating jq filters as a structural error | Saw a 4-column table report 6 cells and assumed two cells got merged or split | The two `\|` operators inside the jq code span `` `[.comments[]\|select(.body\|test(...))]` `` each added one phantom cell | Run the file through a grep that matches backtick code spans containing internal pipes |

## Results & Parameters

### MD056 reproducer

```markdown
| A | B | C | D |
| - | - | - | - |
| x | y | `cmd \|\| other` | z |
```

`markdownlint-cli2 --config .markdownlint.yaml file.md` → exit 0. Without the
backslashes: `MD056 Expected: 4; Actual: 6`.

### Tooling versions verified

| Tool | Version | Result |
| ---- | ------- | ------ |
| markdownlint-cli2 | 0.20.0 (local) | 0 errors after escape |
| markdownlint-cli2 | 0.22.1 (CI) | green after pipe-escape fix |
| markdownlint | 0.40.0 (CI underlying) | green |

### Queue-recovery telemetry

| Metric | Value |
| ------ | ----- |
| PRs blocked on the same MD056 line | 17 (\#1724, \#1751–\#1767) |
| Fix PR | \#1756 |
| Track-A admin-merge wall time | ~30 s |
| Track-B sequential admin-merge of remaining 16 | ~90 s |
| Total queue recovery | ~2 minutes |

### CLAUDE.md trim results

| Session | Before | After | Reduction | Technique |
| ------- | ------ | ----- | --------- | --------- |
| 2026-03-15 (markdownlint + MD060) | 1,257 lines | 1,012 lines | 19% | Remove duplicate sections, fix MD060 in 3 tables |
| 2026-03-05 (move+link) | 1,786 lines | 1,199 lines | 33% | Move reference sections to `.claude/shared/` |

### Shared-link audit script exit codes

- `0` — all `.claude/shared/*.md` files linked in Quick Links
- `1` — one or more files missing, or CLAUDE.md / shared-dir not found

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectMnemosyne | PR \#1755 — `fix/markdownlint-table-pipe-escape` unblocks 5 PRs | File: `skills/ci-cd-gated-debug-instrumentation-workflow-dispatch.md` line 107 |
| ProjectMnemosyne | PR \#1756 — same root cause across 17 PRs; two-track recovery in ~2 minutes | Diagnostic: `gh run view --log-failed \| grep MD056` |
| ProjectMnemosyne | 2026-05-18 skill-corpus consolidation (\#1813); Wave 2 hit CI 100% clean after pre-flight discipline added | self |
| ProjectOdyssey | PR \#5381 (commit 63b9db7f9) — mkdocs --strict out-of-tree links fixed in `docs/dev/mojo-jit-crash-capture-core.md` | Replaced `../../scripts/` and `../../.github/` style links with absolute GitHub URLs |
| ProjectOdyssey | PR \#4763 — CLAUDE.md trim from 1,257 to 1,012 lines; MD060 fixed in 3 tables | Issue \#3158: reduce token consumption |
| ProjectOdyssey | PR \#4024 — shared-link audit script + pre-commit hook | Issue \#3366: 3 missing `.claude/shared/` entries; 20 pytest tests all passed |
| ProjectMnemosyne | PR \#1937 (`65fa3558`) — MD033 placeholder backtick-wrap | 5-PR parallel swarm false-positive fix wave |
| ProjectMnemosyne | PR \#1959 (`3fa354e1`) — MD059 descriptive link text rewrite | 5-PR parallel swarm false-positive fix wave |
| ProjectMnemosyne | PR \#1960 (`f2aa0aaa`) — MD018 line-start `\#NNN` reflow | 5-PR parallel swarm false-positive fix wave |
| ProjectMnemosyne | PR \#1965 — MD056 non-GHA pipe escape in cells | 5-PR parallel swarm false-positive fix wave |
| ProjectMnemosyne | PR \#1978 (`b2a3150d`) — combined false-positive catalog fixes | 5-PR parallel swarm false-positive fix wave |
| ProjectMnemosyne | PR \#2046 (`821a217`) — MD056 fix for `` `pip list \| grep hephaestus` `` in 2-col table line 217 | 10-PR queue triage 2026-05-29 |
| ProjectMnemosyne | PR \#2049 (`0bb8e69`) — MD056 fix for jq `` `[.comments[]\|select(.body\|test(...))]` `` in 4-col table line 133 | 10-PR queue triage 2026-05-29 |
| ProjectMnemosyne | PR \#2030 (`99b8026`) — MD056 fix for jq pipe filters in 4-col table lines 153-154 | 10-PR queue triage 2026-05-29 |
