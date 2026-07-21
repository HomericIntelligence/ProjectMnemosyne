---
name: ci-merge-preview-script-count-drift
description: "Use when: (1) CI fails with 'prose says N console scripts but pyproject.toml [project.scripts] has N+1 entries', (2) pre-commit fails with '[missing-from-docs] hephaestus-<script> is in [project.scripts] but has no row in COMPATIBILITY.md', (3) a branch cut before parallel PRs landed now has stale script counts in README/docs/COMPATIBILITY.md on the merge-preview SHA, (4) updating prose counts in README.md or docs/index.md that reference the number of console scripts, (5) a strict audit flags a stale literal count in a roadmap/planning doc (e.g. ROADMAP.md) where the number contradicts pyproject.toml [project.scripts] but CI is not currently failing, (6) a doc, ADR, or module docstring advertises a console script that is absent from [project.scripts] entirely — reference drift, not count drift; diff backticked doc command tokens against declared entry points and decide register-vs-remove from evidence, (7) a prose script count lives in a file no validator scans (e.g. COMPATIBILITY.md 'installs N console scripts') so every checker is green while the number is wrong."
category: ci-cd
date: 2026-07-21
version: "1.3.0"
user-invocable: false
history: ci-merge-preview-script-count-drift.history
verification: verified-ci
tags:
  - ci-cd
  - merge-preview
  - console-scripts
  - pyproject-toml
  - compatibility-md
  - prose-count
  - branch-drift
  - pre-commit
  - hephaestus
  - roadmap
  - audit
  - reference-drift
  - missing-entry-point
  - register-vs-remove
---

# CI Merge-Preview Script Count Drift

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-21 |
| **Objective** | Diagnose and fix CI failures caused by `[project.scripts]` count drift between a feature branch and main's merge-preview SHA, and fix stale literal counts in planning/roadmap docs discovered by strict audits |
| **Outcome** | Successfully applied to 8 PRs in one session (2026-06-07); also covers single-token doc-only fixes for roadmap/planning files where CI is not failing; v1.2.0 adds reference-drift diagnosis (a doc advertises a command absent from `[project.scripts]`) and the register-vs-remove decision rule (ProjectHephaestus issue #2169); v1.3.0 closes that loop in PR #2323 with the command registered, the inventory surfaces kept in sync, and a verified NOGO->GO->merge path |
| **Verification** | verified-ci |

## When to Use

- CI fails with: `ERROR: Prose counts disagree with pyproject.toml [project.scripts]: README.md: prose says 'N console scripts' but pyproject.toml [project.scripts] has N+1 entries`
- Pre-commit fails with: `FAIL: 1 tier-doc violation(s): [missing-from-docs] hephaestus-<script> is in pyproject.toml [project.scripts] but has no row in COMPATIBILITY.md`
- The failure appears on the **merge-preview SHA** (e.g., `refs/pull/<N>/merge`), not the branch's own HEAD
- A branch was cut before parallel PRs merged new console scripts into main
- Updating documentation that includes a prose count of console scripts
- **A strict audit flags a stale literal count in a roadmap or planning doc (e.g., `ROADMAP.md`) where the number contradicts `pyproject.toml [project.scripts]` but CI is not currently failing** — fix is a single-token edit; verify the count from the authoritative source (pyproject.toml), not from corroborating docs
- A doc or a module's own docstring advertises a `hephaestus-*` command that is **absent from `[project.scripts]` entirely** (reference drift, not count drift) — the count and tier checkers stay green because neither validates command references across docs
- A prose script count lives in a file **no validator scans** (e.g., `COMPATIBILITY.md` "installs N console scripts") — every check is green while the number is wrong
- An issue or audit body quotes a script count — treat it as suspect prose and recount from `pyproject.toml` (issue #2169 claimed 51; the real count was 48)
- A reviewer NOGO tells you the checker stopped guarding the full inventory surface — restore the missing docs surfaces rather than narrowing the check to the easiest file

## Verified Workflow

### Quick Reference

```bash
# 1. Find the current script count on main (what the merge-preview will see)
git fetch origin main
git show origin/main:pyproject.toml | grep -c "hephaestus-"

# 1b. Count-verification command (matches pyproject.toml [project.scripts] entry format)
grep -cE '^\s*[a-z][a-z0-9-]*\s*=\s*"[^"]+:[^"]+"' pyproject.toml

# 2. Find scripts missing from COMPATIBILITY.md
diff \
  <(git show origin/main:pyproject.toml | grep "hephaestus-" | sed 's/ = .*//' | sort) \
  <(grep "^| \`hephaestus-" COMPATIBILITY.md | sed "s/^| \`//;s/\` |.*//" | sort)

# 3. Update prose counts in README.md and docs/index.md
#    (replace the N in "N console scripts" with the count from step 1)

# 4. Add missing scripts to COMPATIBILITY.md Console-Script Stability Tiers table

# 5. Scope check: grep all doc files for the stale number to find every affected location
grep -rn "<STALE_N>" docs/ README.md COMPATIBILITY.md
```

### Detailed Steps

#### Step 1 — Understand the merge-preview mechanism

GitHub CI runs tests against the **merge-preview commit** (`refs/pull/<N>/merge`) — the result
of merging the PR branch into current `main`. This means:

- `pyproject.toml [project.scripts]` in the merge-preview comes from **main** (no conflict), so the installed package has ALL console scripts from main.
- Prose counts in `README.md` / `docs/index.md` come from the **PR branch** (if the branch didn't update them).
- `COMPATIBILITY.md` comes from the **PR branch** (if the branch didn't update it).

When parallel PRs merge new scripts into main after a branch is cut, that branch's docs become stale **only on the merge-preview SHA**, not on the branch's own HEAD.

#### Step 2 — Find the authoritative count

```bash
# Count how many scripts main's pyproject.toml declares
git fetch origin main
MAIN_COUNT=$(git show origin/main:pyproject.toml | grep -c "hephaestus-")
echo "Main has $MAIN_COUNT console scripts"

# List all script names from main
git show origin/main:pyproject.toml | grep "hephaestus-" | sed 's/ = .*//'
```

#### Step 3 — Fix prose counts in README.md and docs/index.md

```bash
# Find the current prose reference
grep -n "console script" README.md docs/index.md 2>/dev/null

# Update the count to match main's pyproject.toml
# Example: change "45 console scripts" to "46 console scripts"
sed -i "s/45 console scripts/$MAIN_COUNT console scripts/" README.md docs/index.md
```

#### Step 4 — Fix COMPATIBILITY.md missing rows

```bash
# Identify which scripts are in pyproject.toml but missing from COMPATIBILITY.md
diff \
  <(git show origin/main:pyproject.toml | grep "hephaestus-" | sed 's/ = .*//' | sort) \
  <(grep "^| \`hephaestus-" COMPATIBILITY.md | sed "s/^| \`//;s/\` |.*//" | sort)

# For each missing script, add a row to the appropriate tier in COMPATIBILITY.md
# Format: | `hephaestus-<name>` | `hephaestus.<module>:<function>` | <tier> | <since-version> |
```

#### Step 5 — Fix roadmap/planning doc stale counts (audit-discovered, no CI failure)

When a strict audit flags a stale literal in a planning doc (e.g., `ROADMAP.md` says "13 of **37** declared tools" but pyproject.toml has 47):

```bash
# Verify the count from the authoritative source — do NOT trust corroborating docs
grep -cE '^\s*[a-z][a-z0-9-]*\s*=\s*"[^"]+:[^"]+"' pyproject.toml

# Scope check: find every file containing the stale number
grep -rn "37" docs/ README.md COMPATIBILITY.md

# Apply a single-token fix to only the files that are in scope
# Leave the numerator (e.g., "13 of N") untouched if the issue only covers N
```

**Key scope principle**: when prose says "M of N declared tools", only fix N if the audit issue is about the total count; leave M unless that is separately tasked.

#### Step 6 — Verify locally before pushing

```bash
# Confirm the count now matches
COMPAT_COUNT=$(grep -c "^| \`hephaestus-" COMPATIBILITY.md)
echo "COMPATIBILITY.md rows: $COMPAT_COUNT, main scripts: $MAIN_COUNT"
[ "$COMPAT_COUNT" -eq "$MAIN_COUNT" ] && echo "MATCH" || echo "MISMATCH — fix COMPATIBILITY.md"

# Verify README count
grep "console script" README.md
```

#### Step 7 — Reference drift: a doc advertises an unregistered command

Count checks cannot catch a command that was **never registered**. Diff every backticked
command token in the docs against `[project.scripts]`:

```bash
python3 - <<'EOF'
import re, pathlib, tomllib
rx = re.compile(r"`(hephaestus-[a-z0-9-]+)`")   # full inline-code span only
scripts = set(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["scripts"])
files = list(pathlib.Path("docs").rglob("*.md"))
files += [pathlib.Path(p) for p in ("README.md", "COMPATIBILITY.md", "CLAUDE.md")]
for f in files:
    for m in sorted(set(rx.findall(f.read_text(encoding="utf-8"))) - scripts):
        print(f"{f}: `{m}` not in [project.scripts]")
EOF
```

The inline-backtick regex is deliberate: a loose `hephaestus-[a-z-]+` grep false-positives
on HTML comment markers (`<!-- hephaestus-severity: X -->`), mktemp templates
(`hephaestus-issue-2025.XXXXXX`), and fenced-block text. Requiring the whole inline-code
span to be exactly the command name eliminated every false positive (ProjectHephaestus,
2026-07-17: one true offender remained).

For each offender, decide **register vs remove** from evidence, not preference:

| Evidence | Points to |
|----------|-----------|
| `git log --oneline -S "<cmd>" -- pyproject.toml` is empty | Never registered — an omission; lean register |
| The same name appears in a removal commit | Deliberately removed — fix the doc instead |
| The module has a working `main()` and its docstring self-describes as this CLI | Register |
| Every sibling stage CLI is registered | Register (consistency) |
| A shell wrapper works around the absence via `python -m package.module` | Register, then simplify the wrapper |
| The checker is narrowed to README/pyproject and stops scanning the other documented surfaces | The PR no longer guards the full inventory drift class | Keep the validation surface aligned with the issue scope; if docs are part of the contract, the checker must still read them |

Registering cascades: the pyproject `[project.scripts]` entry, a COMPATIBILITY.md tier row,
a README CLI-table row, and prose counts incremented in every file from Steps 3–4. Prefer
extending the existing sync checker (one home for doc-to-scripts logic) over adding a new
validator, and drop hardcoded counts from prose that no validator enforces (e.g., an ADR
saying "Six console scripts" while another line of the same ADR says "seven").

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | Checked branch HEAD's `pyproject.toml` to find the script count | Branch HEAD has N-2 scripts (pre-parallel-PR state); the merge-preview has N from main. Fixing to N-2 breaks the merge-preview | Always use `git show origin/main:pyproject.toml` to get the authoritative count, not the branch's local file |
| Attempt 2 | Ran pre-commit locally on branch HEAD and saw no failures | The check compares installed package scripts (branch) vs. docs (branch) — they agree locally. The discrepancy only appears when CI installs from the merge-preview's merged `pyproject.toml` | Local pre-commit green ≠ CI green when the failure is a merge-preview artifact |
| Attempt 3 | Updated README prose count but not `docs/index.md` | The `hephaestus-check-cli-tier-docs` hook scans BOTH files; partial fix still fails | Always grep for ALL prose count references: `grep -rn "console script" README.md docs/index.md` |
| Attempt 4 | Updated prose counts but forgot to add the missing script to COMPATIBILITY.md | Two separate checks run: (a) prose count vs. `[project.scripts]`, (b) `[project.scripts]` entries vs. COMPATIBILITY.md rows. Both must pass | Fix both the prose count and the COMPATIBILITY.md row in the same commit |
| Attempt 5 | Verified the stale count by checking README or COMPATIBILITY.md (which already showed the correct number) instead of counting from `pyproject.toml` directly | Cross-referencing docs can agree with each other while still being wrong if they were updated inconsistently; the roadmap file was missed | The authoritative source for the script count is always `pyproject.toml [project.scripts]`, not corroborating docs — count from the code, not from other prose |
| Attempt 6 | Trusted the audit issue's quoted count ("pyproject declares 51") | The actual `[project.scripts]` count was 48; the issue body was itself stale prose | Recount from `pyproject.toml` before editing anything — issue bodies drift exactly like docs |
| Attempt 7 | Swept docs with a loose `grep -oE "hephaestus-[a-z-]+"` to find advertised commands | Matched HTML comment markers, mktemp templates, and fenced-block text — 3 of 4 hits were false positives | Match only full inline-code spans (backtick immediately before and after the command name) so hits are real advertised commands |

## Results & Parameters

**Root cause pattern:** Branch cut before PR N-1 and PR N-2 merged into main. Those PRs each added one new `hephaestus-*` console script. The branch's `pyproject.toml` has N-2 scripts; after merge-preview, `pyproject.toml` has N scripts from main. The branch's `README.md`, `docs/index.md`, and `COMPATIBILITY.md` still reference N-2.

**Affected files (always three for merge-preview failures):**

| File | What to Fix |
|------|------------|
| `README.md` | Prose count: `"N console scripts"` → `"(N+K) console scripts"` |
| `docs/index.md` | Same prose count reference |
| `COMPATIBILITY.md` | Add missing row(s) to Console-Script Stability Tiers table |

**Affected files (single-token audit fix for roadmap/planning):**

| File | What to Fix |
|------|------------|
| `docs/ROADMAP.md` (or similar) | Single literal number: `37` → `47` (or whatever pyproject.toml reports) |

**Diagnostic commands:**

```bash
# Count scripts on main
git show origin/main:pyproject.toml | grep -c "hephaestus-"

# Count using entry-format regex (most precise — matches [project.scripts] entries)
grep -cE '^\s*[a-z][a-z0-9-]*\s*=\s*"[^"]+:[^"]+"' pyproject.toml

# List script names (sorted for diff)
git show origin/main:pyproject.toml | grep "hephaestus-" | sed 's/ = .*//' | sort

# List scripts already in COMPATIBILITY.md (sorted for diff)
grep "^| \`hephaestus-" COMPATIBILITY.md | sed "s/^| \`//;s/\` |.*//" | sort

# Find prose count references
grep -n "console script" README.md docs/index.md

# Find ALL files containing a specific stale number (for audit-discovered fixes)
grep -rn "<STALE_N>" docs/ README.md COMPATIBILITY.md

# Evidence for register-vs-remove on an unregistered advertised command (Step 7)
git log --oneline -S "<cmd>" -- pyproject.toml   # empty output = never registered
```

**Reference-drift diagnostic (v1.2.0):** run the Step 7 python snippet before scoping any
CLI-doc reconciliation so count fixes and reference fixes land in one change. Known
validator blind spots it catches that count checks miss: commands advertised only in
architecture docs or ADRs, and prose counts in files outside the checker's scan set.

**Session results:** Applied fix to 8 PRs in one session (2026-06-07). All 8 passed CI after updating prose counts + COMPATIBILITY.md rows. PR #2323 / issue #2169 later completed the same register-vs-remove path: the automation worktree was salvaged, rebased onto current main, and merged after the reviewer moved from NOGO to GO. The failure was caused by two parallel PRs (#1046 adding `hephaestus-check-cli-tier-docs` and #1067 adding `hephaestus-audit-prs`) merging into main after the affected branches were cut.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #2323, issue #2169, 2026-07-21 | `hephaestus-drive-prs-green` was registered, the inventory surfaces stayed aligned, and the review path moved from an initial NOGO on a partial checker to GO after the full validation surface was restored; PR merged after rebasing onto current main. verified-ci |
| ProjectHephaestus | 8 PRs in session 2026-06-07 | Merge-preview SHA showed N+2 scripts from main vs. N in branch docs; fixed by updating README.md, docs/index.md, COMPATIBILITY.md |
| ProjectHephaestus | PR #1270, issue #1190, 2026-06-13 | Strict audit found `docs/ROADMAP.md:15` said "37 declared tools" but pyproject.toml had 47; single-token fix (`37`→`47`); README and COMPATIBILITY.md already correct; CI passed cleanly on first push |
| ProjectHephaestus | Issue #2169 planning, 2026-07-17 | Both existing checkers green while COMPATIBILITY.md said 53 vs actual 48, and an architecture doc advertised unregistered `hephaestus-drive-prs-green` (module had a working `main()`, self-describing docstring, registered siblings; `git log -S` empty = never registered). Diagnosis verified locally with the Step 7 snippet — exactly one true offender, zero false positives; register-side fix is planned in the issue #2169 implementation plan (not yet CI-verified) |
