---
name: stale-documentation-audit-and-broken-reference-repair
description: "Use when: (1) running a doc-drift audit across a corpus — detecting stale counts, metric discrepancies, cross-doc contradictions, ecosystem-role drift; (2) removing phantom directory references from documentation when a path no longer exists; (3) fixing broken documentation references (dead links, stale headings); (4) auditing documentation examples for policy violations; (5) auditing and rewriting getting-started stubs by sourcing real commands from justfile and versions from pixi.toml; (6) fixing incorrect tier labels or version numbers in docs that have drifted from implementation; (7) managing the full lifecycle of placeholder and stub documentation — deletion under YAGNI, deferred-comment placeholders, rewriting with accurate codebase-grounded content; (8) resolving audit nitpicks for monolithic code by documenting verified design rationale; (9) resolving CONTRIBUTING.md case-clashes and circular cross-references in docs/; (10) validating anchor fragments in markdown deep-links to detect broken headings; (11) an issue claims a file contains a specific string — verify it before trusting the claim; (12) a doc or test comment references a line number in another file that may have shifted; (13) PLANNING a doc-drift consolidation — issue line numbers are stale and more copies exist than cited; (14) a flagged stale count is ambiguous which set the doc counts — disambiguate before bumping; (15) planning a phantom-path fix — applying the remove-vs-redirect decision rule and confirm-then-fix audit discipline; (16) a dated currency claim in a doc trails the git tag and you want a CI-effective version-currency guard; (17) a README/CLAUDE.md directory tree omits or miscounts a subpackage; (18) syncing a stale doc-version claim to the correct version authority and deciding whether to add a drift-detection regression test; (19) a doc count annotates a human-curated enumeration (tree, tier table, bullet list) and you must reconcile number-to-list not number-to-filesystem; (20) a replacement command must be verified to actually run in THIS repo before shipping — feature names are not environment names in pixi; (21) a pixi-only repo has bare env-tool invocations (pre-commit, pytest, mypy, ruff) that fail on clean machines; (22) an audit issue quotes conflicting numbers — treat both as suspect prose and count from the enforced artifact; (23) re-deriving a count from the authoritative manifest/code and hunting all stale copies with a phrase-scoped grep; (24) locating and repairing dangling file:line citations by content-match not coordinate, and confirming markdownlint was not silently skipped; (25) an issue reports multiple phantom command/recipe references in a doc — some may already be fixed; always re-grep against justfile ground truth before editing each one; (26) a justfile with mixed naming conventions (verb-first vs prefix-first recipes) is referenced in docs — cross-check ALL table entries, not just the reported phantom."
category: documentation
date: 2026-06-19
version: "1.11.0"
user-invocable: false
history: stale-documentation-audit-and-broken-reference-repair.history
tags: [doc-drift, stale-doc, broken-references, phantom-dir, placeholder, stub, anchor-validation, tier-labels, doc-audit, doc-sync, merged, merge-method, consolidation-planning, count-disambiguation, remove-vs-redirect, confirm-then-fix, version-currency, git-tag-authority, subpackage-count, pattern-d, drift-test-fragility, count-annotates-list, pixi-environment, pixi-run-prefix, enforced-artifact, phrase-scoped-grep, file-line-citation, markdownlint-skipped, phantom-recipe, justfile-ground-truth, stale-issue-description, mixed-naming-convention]
---

# Stale Documentation Audit and Broken Reference Repair

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-13 |
| **Objective** | Canonical workflow for auditing stale documentation and repairing broken references: drift audits, phantom-dir/dead-link removal, placeholder lifecycle, getting-started rewrites, tier-label fixes, anchor validation, ADR LoC figure updates, stale line-number citations |
| **Outcome** | Consolidated from 10 skills covering doc-drift audits, broken-reference repair, policy-violation audits, placeholder/stub lifecycle, monolith-rationale docs, CONTRIBUTING case-clash, and anchor validation; v1.1.0 adds ADR LoC drift pattern; v1.2.0 adds stale line-number citation audit and issue-body claim verification; v1.9.0 adds merge-method per-repo note, doc-drift consolidation PLANNING, count-set disambiguation, phantom-path remove-vs-redirect, git-tag version-currency guard, subpackage counting, and Pattern D drift-test fragility; v1.10.0 salvages 6 dropped learnings: count-annotates-list rule, pixi env verification before shipping, pixi-run prefix for bare env tools, enforced-artifact > prose for conflicting counts, phrase-scoped grep for count-drift, and content-anchored file:line citation repair with markdownlint-Skipped caveat |
| **Verification** | verified-ci |

## When to Use

- A "Future Improvements" / "Future Work" section lists a feature that already shipped
- Docs state a metric (test count, coverage %, file/agent count) that disagrees with the codebase
- `CLAUDE.md` contradicts `pyproject.toml`/`CONTRIBUTING.md` on thresholds or policy
- External architecture docs describe a project's ecosystem role inaccurately
- A directory/file was removed but docs still reference the path (phantom dir / dead link)
- Documentation examples contain commands that violate repo policy (e.g. `--label`, `--no-verify`)
- Getting-started stubs contain fabricated APIs, placeholder prose, or malformed code fences
- Tier labels / version numbers in docs have drifted from the authoritative table
- Stub files contain only boilerplate and should be deleted, deferred, or rewritten
- An audit nitpick questions a monolithic file's organization and needs a documented rationale
- Both `CONTRIBUTING.md` and `docs/contributing.md` exist with a circular cross-reference
- README/docs deep-link to specific installation headings and you need CI to catch broken anchors
- An ADR file (e.g. `docs/adr/`) cites LoC figures or percentage metrics that have drifted as the codebase grew since the ADR was authored; `CLAUDE.md` or other doc files repeat the same stale counts
- An issue claims a file "contains" a specific string — grep for that exact string before trusting the claim (issue bodies may have been written against an older version of main)
- A doc or test file references another file by line number (e.g. `install.sh:137–141`) — the cited line numbers may have shifted independently across files that reference the same construct
- **PLANNING** a doc-drift consolidation: two+ onboarding/setup blocks have drifted from a canonical recipe and you must write an implementation plan before touching files
- An audit flags a stale file/subpackage/skill/test count, but it is unclear *which set* the doc counts (documented packages vs filesystem dirs; skill DEFINITIONS vs every dir incl. `_`-prefixed partials) — disambiguate before assuming the number is arithmetically wrong
- You are **planning** (not yet executing) a phantom-path / stale-reference fix and must decide between *removing* the dead pointer and *redirecting* it, and want a confirm-then-fix audit recipe
- A dated currency claim (latest-released-version / last-updated) in a doc trails the git tag line and you want a CI-effective guard (one that actually runs, not silently skips)
- A README/CLAUDE.md directory tree omits or miscounts a subpackage and you must re-derive the true package count from the filesystem (not trust the doc's own number or the issue's)
- A doc states a stale released-version claim (e.g. `MIGRATION.md` says "latest released version is 0.9.2" but `git tag` shows v0.9.5) and you must sync it to the correct version authority — AND decide whether to add a drift-detection regression test (see §18 for the fragility traps before you couple a prose regex to a git-tag-derived authority)
- A doc count annotates an adjacent human-curated enumeration (tree, tier table, bullet list) — the fix is to reconcile number-to-list (clarify scope/unit), NOT number-to-filesystem; bumping the number to a raw `find … | wc -l` result while the curated list is unchanged produces an internally-contradictory doc (POLA NOGO)
- A replacement command was copied from another doc or from the issue body — verify it actually runs in THIS repo (e.g. `pixi run -e dev true` to confirm `dev` is an environment, not just a feature) before shipping
- A pixi-managed repo has bare env-tool invocations (`pre-commit install`, `pytest`, `mypy`, `ruff`) in docs or README that will fail with `command not found` on a clean machine because `.pixi/envs/default/bin` is not on PATH after `pixi install`
- An audit issue quotes conflicting numbers (e.g. "6 vs 11 excluded modules") — treat BOTH quoted counts as suspect prose and count from the enforced artifact (a passing frozen-allowlist test or `expected_modules` set) instead
- Docs or test comments state a count that must be re-derived from the authoritative manifest (e.g. `pyproject.toml [project.scripts]`) — use a phrase-scoped grep to BOTH locate the stale copy AND confirm no other stale copies survive
- A doc carries a dangling `file.py:NN-MM` reference — locate the construct by content-match grep (not the audit's reported coordinate, which is off-by-one), replace with a content-anchored durable citation; after the fix, verify `pre-commit run --files <doc>` actually LINTED the file (a "Skipped" status means the hook's file filter excluded the path — linting did NOT occur)
- An issue reports multiple phantom command/recipe references in a doc — issue descriptions may cite several broken lines where only a subset are still live; always re-grep against the justfile (or authoritative source) before editing each reported location; fix only the live defects, not the stale issue claims
- A justfile uses a mixed naming convention (e.g. verb-first `start-agamemnon` for some recipes, prefix-first `hermes-start` for others) — cross-check ALL doc table entries against the real recipe list, not just the reported phantom; a mixed convention makes it easy to trust adjacent already-correct entries as evidence that ALL entries must be correct

## Verified Workflow

### Quick Reference

```bash
# ── DRIFT AUDIT (counts / metrics / roles / future-work / citations) ─────────
grep -rn "Future Improvements\|Future Work\|Coming Soon\|Planned\|Not Implemented" \
  docs/ --include="*.md" | grep -v "docs/arxiv/"
pixi run python -m pytest --collect-only -q tests/ 2>/dev/null | tail -3   # real test count
ls .claude/agents/*.md | wc -l                                              # real agent count
grep "fail_under" pyproject.toml                                            # real coverage threshold
grep -r "<old_count>" . --include="*.md" --exclude-dir=.git                 # find ALL stale copies

# ── COUNT-ANNOTATES-LIST: verify documented_count == enumeration_count ────────
# The number annotating a tree/table/list counts THAT LIST, not the filesystem.
# 1. Count items in the curated list
grep -c "^  ├\|^  └\|^  │" README.md                 # tree entries (example)
# 2. Count real packages / dirs
git ls-files 'hephaestus/*/__init__.py' | wc -l       # tracked packages
# 3. If number != list_count: clarify scope ("19 documented subpackages"), never
#    just bump to filesystem count — that leaves number > list_count (contradictory).

# ── PIXI ENV VERIFICATION before shipping a replacement command ───────────────
pixi run -e dev true 2>&1 | grep -q "unknown environment" && echo "NOGO: not an env" \
  || echo "OK"
# 'dev' may be a feature (in [features]) not an environment (in [environments]).
# An un-sourced/uncertain command is a STOP — verify or drop; never ship on a hunch.

# ── PIXI-ONLY REPOS: detect bare env-tool invocations ────────────────────────
grep -rnE '^[[:space:]]*(pre-commit|pytest|mypy|ruff)\b' docs/ README*
# Bare invocations fail on a clean machine (PATH does not include .pixi/envs/default/bin).
# Fix: prepend 'pixi run' — e.g. 'pre-commit install' → 'pixi run pre-commit install'
# Verify: grep -rnE '^[[:space:]]*(pixi run )?(pre-commit|pytest|mypy|ruff)\b' docs/ README*

# ── ENFORCED ARTIFACT > PROSE for conflicting issue counts ─────────────────────
# When issue body says "6 vs 11 excluded modules", count from the test itself:
grep -rn 'expected_modules\|All 11\|the 11 automation\|11 modules' pyproject.toml docs/ tests/
# A passing frozen-allowlist test (expected_modules set + "N modules" comment) is
# stronger ground truth than any prose. Only add a doc-grep regression guard when
# no enforced guard already exists.

# ── PHRASE-SCOPED GREP: re-derive count + hunt all stale copies ───────────────
# Count from the authoritative manifest (never a second doc):
grep -cE '^[a-z_-]+ =' pyproject.toml     # project.scripts entry count (example)
# Phrase-scope the stale-number re-grep to BOTH scope the edit AND prove no copies survive:
grep -rn 'of 37|37 declared|37 tools' docs/ README* ROADMAP*
# Prefer exact-string Edit over replace_all on bare digits — bare digits false-positive.

# ── BROKEN / PHANTOM REFERENCES ──────────────────────────────────────────────
grep -rn "<removed-path>" docs/ README.md CONTRIBUTING.md   # find dead refs
ls <removed-path> 2>/dev/null || echo "Confirmed removed"   # confirm gone

# ── POLICY-VIOLATION AUDIT ───────────────────────────────────────────────────
pixi run python scripts/audit_doc_examples.py --verbose     # scans fenced shell blocks only

# ── PLACEHOLDER / STUB LIFECYCLE ─────────────────────────────────────────────
grep -rl "Content here\." docs/                             # confirm stubs
grep -rl "stub-name" docs/                                  # find referencers BEFORE deleting

# ── GETTING-STARTED REWRITE (source ground truth, never invent) ──────────────
grep -E "^[a-z]" justfile                                   # real recipes
grep -E "mojo|version" pixi.toml                            # pinned versions
grep -r "TensorDataset\|class Trainer" shared/ papers/      # verify API exists
# Bulk cross-check ALL doc table recipe entries at once (catches mixed-convention repos):
for r in start-agamemnon start-nestor keystone-start hermes-start argus-start; do
  grep -qE "^${r}( |:)" justfile && echo "OK $r" || echo "MISSING $r"
done

# ── TIER-LABEL FIXES ─────────────────────────────────────────────────────────
grep -n "T[0-9]" .claude/shared/metrics-definitions.md      # scan all tier refs

# ── ADR LOC FIGURES (re-measure at implementation time, never trust issue body) ──
find hephaestus -name '*.py' | xargs wc -l | tail -1          # total LoC
find hephaestus/automation -name '*.py' | xargs wc -l | tail -1  # subpackage LoC
# Then grep for ALL copies of the stale figure across the corpus:
grep -rn "19,726\|19\.7k\|41,034" docs/ CLAUDE.md README.md    # replace with real old values

# ── STALE LINE-NUMBER CITATIONS ──────────────────────────────────────────────
# Step 1: Before trusting the issue body, grep for the exact claimed-incorrect string
grep -n "claimed incorrect string" path/to/file.md  # returns nothing → claim is stale
# Step 2: Find the actual current line of the referenced construct
grep -n "guard_pattern\|function_name" path/to/source.sh
# Step 3: Search for ALL stale variants — docs and test files updated independently
grep -rn "old_ref_1\|old_ref_2" docs/ tests/ --include="*.md" --include="*.bats" --include="*.sh"

# ── FILE:LINE CITATION REPAIR (content-anchored, not coordinate-anchored) ─────
# 1. Locate the construct by content, not the audit's line number (off-by-one risk):
grep -n "construct_keyword\|function_name" path/to/source.py
# 2. Replace with a content-anchored durable citation (package __init__ or durable text),
#    NOT a fresh ':NN' that will re-rot.
# 3. Re-grep corpus after fix:
grep -rn "old_file_ref\|stale_coord" docs/ tests/
# 4. Verify markdownlint actually LINTED the file (not silently skipped):
#    Look for "Markdown Lint … Skipped" in pre-commit output → hook's file filter
#    excluded the path; the file was NOT linted. Verify manually or adjust hook scope.
pixi run pre-commit run markdownlint-cli2 --files path/to/file.md

# ── DISAMBIGUATE A FLAGGED COUNT (which set does the doc count?) ─────────────
find hephaestus -maxdepth 1 -mindepth 1 -type d ! -name __pycache__ | wc -l  # real subpackage dirs
find skills -name SKILL.md | wc -l                                          # skill DEFINITIONS (usual unit)
find skills -maxdepth 1 -mindepth 1 -type d | wc -l                         # dirs (incl. _-prefixed partials)
grep -rn "<stale phrase>" . --include="*.md" | grep -v ".claude/worktrees/" # corpus re-grep, no worktree mirrors
git ls-files <path>                                                         # confirm a hit is a tracked file

# ── ANCHOR VALIDATION ────────────────────────────────────────────────────────
python3 scripts/validate_installation_anchors.py README.md docs/getting-started/installation.md

# ── VALIDATE / COMMIT (markdownlint runs in the pre-commit hook) ─────────────
git diff --stat
pre-commit run --all-files            # or: SKIP=mojo-format pixi run pre-commit run --all-files
```

**Universal rules**: count from code (never from other docs); use `Edit` with exact strings, not
whole-section rewrites; use `replace_all: true` when a stale phrase repeats; after fixing the
primary file, re-grep the whole corpus — stale copies survive in `docs/`, `references/notes.md`,
`docs/analysis-prompt.md`. Always Read a file before Editing it.

### Detailed Steps

#### 1. Drift audit (counts, metrics, roles, contradictions)

Classify the staleness, then verify against an authoritative source before editing:

| Pattern | Symptom | Authoritative source |
| ------- | ------- | -------------------- |
| Future-work drift | Doc says "Planned" but `.py` exists | `ls`/`head` the file |
| Stale counts | README says N, actual is M | pytest collect / `find … \| wc -l` |
| Metric discrepancy | CLAUDE.md ≠ pyproject.toml | grep both files |
| Ecosystem role drift | External docs describe wrong role | `gh api orgs/<ORG>/repos` |
| Doc contradiction | Policy conflict across files | grep policy term |
| Citation §-drift | §-ref points to old §-number | global mapping table + WebFetch per arXiv ID |
| ADR LoC drift | ADR cites old `N LoC / M% of codebase`; codebase has grown | `find … -name '*.py' \| xargs wc -l \| tail -1` — re-measure at implementation time |
| Line-number citation drift | Doc/test cites `file.sh:N–M`; construct moved after code churn | `grep -n <guard_pattern> <file>` to find current line; then `grep -rn "old_N\|old_M"` across all referencing files |
| Issue-body fabricated claim | Issue says file "contains" a string that no longer exists in main | `grep -n "<exact claimed string>" <file>` before planning; returns nothing → issue written against older main |
| Count-annotates-list drift | Doc bumps a number to match `find \| wc -l` but the adjacent curated list is unchanged | Reconcile number-to-list; clarify scope/unit (e.g. "19 documented subpackages"); never let number exceed list length |
| Conflicting-count prose | Issue quotes two different numbers for the same thing | Count from the enforced artifact (passing test, expected_modules set); treat both prose counts as suspect |
| Manifest-to-doc count drift | ROADMAP/README count trails `pyproject.toml [project.scripts]` or equivalent | Grep the manifest; phrase-scope re-grep to catch all stale copies |

Fix patterns: `Planned → Implemented` in status tables; round counts with `+` for forward
compatibility (`"2026+ tests" → "3,000+ tests"`) but exact counts (no `+`) for deterministic
sums; correct `--cov` path to the installed package name. Annotate deleted entries with
strikethrough rather than removing them: `~~`.claude/agents/deleted.md`~~ — converted to skill`.
Add a self-verifying command to the doc so future readers can re-check:
`` `ls .github/workflows/*.yml | wc -l` ``. Authority order for contradictions:
`CLAUDE.md > .claude/shared/pr-workflow.md > CONTRIBUTING.md` — edit only the wrong file.

**ADR LoC drift (extended pattern)**: When an audit flags that an ADR's LoC figures are stale:

1. **Re-measure at implementation time** — never use figures from the issue body (they reflect the audit
   snapshot, not the current state). Run `find <package> -name '*.py' | xargs wc -l | tail -1` directly.
2. **Use content-match grep, not line numbers** — issue bodies cite line numbers from the audit snapshot;
   those numbers are stale by the time you implement. Find the actual string with
   `grep -rn "<old_figure>" docs/ CLAUDE.md README.md`.
3. **Read the ADR before planning** — the ADR may document why decomposition is rejected and identify
   the already-implemented remedy (e.g., an optional-extra install boundary). The correct fix may be
   documentation-only, not structural refactoring.
4. **Grep the whole corpus** — the same stale figure often appears in both the ADR and `CLAUDE.md`
   (and possibly `README.md`). Fix all occurrences in one PR.
5. **Skip `ruff check` for doc-only changes** — `ruff` does not lint `.md` files; the run is a no-op.
   Use `markdownlint-cli2` instead: `pixi run pre-commit run markdownlint-cli2 --files <file.md>`.

**Example** — agent count drift after agents converted to skills: update both the Quick Links
bullet (`- N agents` → `- M agents`) and the Agent Hierarchy line (`All N agents` → `All M agents`).

Optionally add a drift-detection regression test (see Results & Parameters) and an ADR.

#### 1a. Count-annotates-curated-list rule

A doc count typically annotates an adjacent human-curated enumeration (a tree, tier table, or
bullet list). Its **contract** is "this number = the count of the list beside it," NOT
"this number = `find … | wc -l`."

**The POLA NOGO**: bumping the number to the raw filesystem count while the curated list is
unchanged produces an internally-contradictory doc — a number promising N over a list of N-1.
This is **worse than the original staleness**.

**Correct fix**: reconcile number-to-LIST:

1. Count items in the curated list (e.g. tree entries).
2. Count items in the filesystem (tracked packages).
3. If they differ, the list is missing an entry — add the missing entry AND update the number,
   OR clarify the scope/unit in the number annotation (e.g. "19 documented subpackages").
4. Never let `number > list_count` in the final doc.

**Verification one-liner** — assert documented_count equals enumeration_count:

```bash
# documented_count: the number in the caption/heading
documented_count=19
# enumeration_count: count lines in the adjacent curated list
enumeration_count=$(grep -c "^  ├\|^  └" README.md)
[ "$documented_count" -eq "$enumeration_count" ] && echo "CONSISTENT" || echo "MISMATCH: $documented_count vs $enumeration_count"
```

**Common confusion**: the audit issue may itself cite a stale count (e.g., "21 subpackages")
derived from an earlier filesystem snapshot (`ls -d */ | wc -l` overcounts, including
`__pycache__`). Always re-derive: `git ls-files 'pkg/*/__init__.py' | wc -l` (tracked packages).

#### 2. Phantom-directory references

A referenced path no longer exists. Find every hit, confirm the dir is gone, then fold or remove.

**Example** — `tests/integration/` was removed; integration-style tests now live in
`tests/unit/analysis/` (`test_integration.py`, `test_cop_integration.py`). Fix README test
categories by folding the count into Unit Tests with a clarifying note, and replace the dead
invocation:

```bash
# Before:  pixi run pytest tests/integration/ -v   # Integration tests
# After:   pixi run pytest tests/unit/analysis/ -v # Includes integration-style tests
```

Verify clean: `grep -r "tests/integration" docs/ README.md CONTRIBUTING.md` returns nothing.
Archived snapshots (`docs/arxiv/` dryrun workspaces) are out of scope.

#### 3. Broken links and anchors

A directory/file was deleted but CLAUDE.md / other docs still link to it. Four edit categories
for a deleted-directory case: (a) Quick Links bullets → remove dead links; (b) narrative
`See [file](path)` → plain text describing the current location; (c) Documentation Rules → update
path from removed dir to current dir; (d) Architecture tree → remove the removed-dir block.

**Example** — after `agents/` was deleted in a refactor, replace
`See [agents/hierarchy.md](agents/hierarchy.md)` with
`Agent hierarchy is defined in .claude/agents/ and tests/claude-code/shared/agents/`. Verify the
old refs are gone and the new location is mentioned.

**Anchor validation (CI)** — when docs deep-link to specific headings
(`installation.md#prerequisites`), add a focused additive script implementing GitHub's slug
algorithm; do NOT modify an existing `validate_links.py` that intentionally strips anchors.

```python
def heading_to_anchor(heading: str) -> str:
    slug = heading.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9\-]", "", slug)     # strip non-alphanumeric except hyphen
    slug = re.sub(r"-{2,}", "-", slug)          # collapse consecutive hyphens
    return slug.strip("-")
```

Plain links (no `#`) are always valid; only fragments are checked against the set of computed
heading anchors. Edge cases: `` `pixi install` fails `` → `pixi-install-fails`;
`Run Tests (without shell)` → `run-tests-without-shell`; `Step 1 Setup` → `step-1-setup`. Add a
step to `.github/workflows/link-check.yml` after the lychee step. Test hermetically with
`TemporaryDirectory` (portable in class-based tests where `tmp_path` fixtures aren't injected).

#### 3b. Content-anchored file:line citation repair and markdownlint-Skipped caveat

**File:line citation repair** — when an audit flags a dangling `file.py:NN-MM` reference:

1. **Locate by content, not coordinate.** The audit's reported line number is itself off-by-one
   (it reflects the audit snapshot). Use `grep -n "<construct_keyword>" path/to/source.py` to
   find the current location.
2. **Replace with a content-anchored durable citation** — cite the package `__init__.py` or a
   durable function/class name rather than a raw `:NN` coordinate that will re-rot with the next
   code churn.
3. **Re-grep the corpus post-fix** to confirm no other files carry the stale coordinate:
   `grep -rn "old_file.py:NN" docs/ tests/`.
4. **Historical-accuracy guardrail** — repair only the broken citation; do not "modernize"
   historical narrative (e.g. `APPROVED/REVISE/BLOCK` vocabulary from a prior review round).
   Changing historical status labels corrupts the audit trail.

**markdownlint-Skipped caveat** — after running `pre-commit run --files <doc>`, check the
output line for `Markdown Lint`. A status of `Skipped` means the hook's file filter excluded
the path — the file was **NOT linted**. Do not assume a clean pre-commit run implies markdownlint
was satisfied. Verify explicitly:

```bash
pixi run pre-commit run markdownlint-cli2 --files path/to/file.md
# If this also skips, the hook's 'files:' pattern excludes the path.
# In that case lint manually or adjust the hook scope.
```

#### 4. Placeholder / stub lifecycle (delete · defer · annotate · rewrite)

```text
Stub has only boilerplate ("Content here.")?  → Delete (YAGNI) after grep -rl for referencers
Index lost a section after stub deletion?      → Insert HTML-comment placeholder + tracking issue
Future Improvements has bare bullets?          → Annotate each: Status / Why deferred / Acceptance
Placeholder must hold real content?            → Verify paths+APIs first, then rewrite
Real installation doc missing a section?       → Extend (e.g. add ## IDE Setup before Troubleshooting)
```

Do NOT use on auto-generated files, in-flight WIP, or when only one link is missing (inline TODO).

**Example — deferred index placeholder** (HTML comment passes markdownlint MD033, as comments
are not HTML elements):

```markdown
<!-- DEFERRED: Advanced Topics section
  Source files were placeholder stubs deleted in #<issue> (YAGNI). Re-add each entry
  once the corresponding doc is written.
  - <topic> (<path>) — Status: Deferred; Why: stub deleted in #<issue>
  Tracking issue: #<follow-up>
-->
```

**Example — annotate Future Improvements**: inspect implementation files first (Dockerfile,
scripts, source); for each item write `Status` / `Why deferred` / `Acceptance criteria`
sub-bullets, and surface already-implemented items with a source reference.

#### 5. Getting-started rewrite (codebase-grounded)

Never invent commands or APIs. Source recipes from `justfile`, versions from `pixi.toml`, and
verify every import exists by grepping the codebase (read `__init__.mojo`/package index, not
aspirational `EXAMPLES.md`). When the APIs shown don't exist yet, rewrite as a conceptual
orientation (what exists today / what is planned / how to use what exists) rather than fabricating.

**Example** — `first_model.md` imported `TensorDataset`, `Trainer`, `EarlyStopping` that don't
exist in `shared/`; full rewrite (760 → 252 lines) replacing them with real recipes. Use the
version *range* from `pixi.toml` (`mojo >= 0.26.1, < 0.27`), never a nightly build string.

Common lint fixes: MD001 (h5 after h3 — flatten inner subsections or demote `#####` to `####`);
MD040 (add a language tag); fix malformed fences (one open delimiter, one language tag, one close).

#### 5b. Pixi-only setup docs: prefix env tools with `pixi run`

In a pixi-managed repo, bare env-tool invocations (`pre-commit install`, `pytest`, `mypy`, `ruff`)
in docs or README **fail with `command not found`** on a clean machine. After `pixi install`,
`.pixi/envs/default/bin` is NOT added to `PATH` unless you `pixi shell` — which itself may not
work (see env-vs-feature caveat below).

**Detection**:

```bash
grep -rnE '^[[:space:]]*(pre-commit|pytest|mypy|ruff)\b' docs/ README*
```

**Fix**: edit to `pixi run <tool>` for each bare invocation found.

**Verification** (positive + negative):

```bash
# Negative: no bare invocations remain
grep -rnE '^[[:space:]]*(pre-commit|pytest|mypy|ruff)\b' docs/ README*
# Positive: pixi run form present
grep -rnE '^[[:space:]]*pixi run (pre-commit|pytest|mypy|ruff)\b' docs/ README*
```

Then run markdownlint to confirm no lint regressions from the edits.

#### 5c. Verify the replacement command actually runs before shipping

A replacement command must be verified to run in **THIS repo**, not just look canonical.

**The feature-vs-environment trap (pixi)**: `pixi.toml` defines environments under `[environments]`
and features under `[features]`. A `dev` feature composed into `default` is **NOT** an environment.
`pixi run -e dev` / `pixi shell -e dev` will fail with "unknown environment" if `dev` is only a
feature:

```bash
# Verification check:
pixi run -e dev true 2>&1 | grep -q "unknown environment" && echo "NOGO: dev is a feature, not an env" \
  || echo "OK: dev environment exists"
```

**Rule**: an un-sourced or uncertain command (copied from a sibling doc without verification) is
a **STOP** signal. Verify it runs or drop it — never ship on a hunch. Do not propagate a sibling
doc's error into a new doc.

#### 6. Tier-label / version fixes

Labels drift off-by-one from the authoritative table after a renumbering. Scan ALL occurrences
(prior partial fixes are common — issues recur), then cross-check each against the table.

Authoritative tiers: T0 Prompts · T1 Skills · T2 Tooling · T3 Delegation · T4 Hierarchy · T5
Hybrid · T6 Super.

**Example** — `.claude/shared/metrics-definitions.md` had `T3 (Tooling)`, `T4 (Delegation)`,
`T5 (Hierarchy)`: fix to `T2 / T3 / T4`. Hotspots: the Token Tracking section (`T2 vs T3
Analysis` → `T1 vs T2`) and the 9-row Component Cost table. Only named references (`(Name)` or
`-` dashes) need fixing; bare tier numbers in formula example data are correct as-is.

#### 6b. Enforced artifact > prose for conflicting counts

When an audit issue quotes conflicting numbers (e.g., "6 vs 11 excluded modules"), treat
**BOTH** as suspect prose and count from the executable/enforced artifact:

- A passing frozen-allowlist test (`expected_modules` set + "N modules" comment) is stronger
  ground truth than any prose.
- Grep the whole corpus for paraphrased counts:

  ```bash
  grep -rn '11 modules\|All 11\|the 11 automation' pyproject.toml docs/ tests/
  ```

  Copies of the count hide in test docstrings, PR descriptions, and design docs — find all of them.

- Only add a doc-grep regression guard when **no enforced guard already exists**. If a passing
  test already asserts the count, a prose guard is redundant and fragile.

#### 6c. Count-drift: re-derive from single source of truth with phrase-scoped grep

Re-derive counts from the authoritative manifest or code — **never from a second doc**:

```bash
# Example: count declared CLI tools from pyproject.toml [project.scripts]
grep -c '^\s*[a-z_-]' pyproject.toml    # count non-empty lines in [project.scripts] block
```

**Phrase-scope** the stale-number re-grep to BOTH scope the edit AND prove no stale copies
survive elsewhere:

```bash
grep -rn 'of 37\|37 declared\|37 tools' docs/ README* ROADMAP*
```

- **Prefer exact-string `Edit`** over `replace_all` on bare digits — a bare digit like `37`
  false-positives on unrelated numbers in the same file.
- **Risk caveat**: every stale copy must be updated atomically (one PR). A partial update that
  fixes the primary file but leaves copies in ROADMAP or test docstrings produces a contradictory
  corpus.

**Concrete example**: `ROADMAP.md` said "13 of 37 declared tools"; `pyproject.toml
[project.scripts]` had 47 entries (real count). Fix phrase: `"13 of 47 implemented tools"`.
After fixing, re-grep: `grep -rn 'of 37\|37 declared' docs/ README* ROADMAP*` — must return
nothing.

#### 7. Audit-nitpick: monolith rationale (optional)

When a nitpick questions a monolithic file's SRP, document the rationale instead of splitting.
Fact-verify claims with grep (mechanism ≠ usage — "can be sourced" ≠ "is sourced anywhere").
Identify the pillars that make splitting expensive (shared state/counters, a unified filter, an
aggregated summary), add a short architecture comment block to the source pointing to a standalone
ADR (`docs/<COMPONENT>_ARCHITECTURE.md`), include accuracy caveats for any unverified claim, and
list triggers that would justify revisiting. Verify zero external callers with a negative grep.

#### 8. CONTRIBUTING case-clash redirect (optional)

When both root `CONTRIBUTING.md` (canonical) and `docs/contributing.md` exist with a circular
"See also" ↔ "Canonical source" reference, reduce the docs copy to a 5-line redirect and strip
the back-reference from root. Reduce to a redirect rather than deleting (preserves inbound links);
keep root canonical (it is the GitHub-visible file).

#### 9. Policy-violation audit (optional)

Scan only fenced shell code blocks (never prose, to avoid matching prohibition text). Rules:
`gh pr create --label`, `git commit --no-verify`, `gh pr merge --merge/--squash`,
`git push origin main`. Exclude archived paths (`docs/arxiv/`, `tests/claude-code/`, `.pixi/`,
`build/`). Anchor command rules to line starts and exclude `#`-commented lines (intentional
"BLOCKED" demonstrations are not violations). Add a regression test per new pattern.

### Validate, Commit, and PR

```bash
git diff --stat                                  # confirm only intended files changed
pre-commit run --all-files                       # runs markdownlint with precise line numbers
git add <changed-files>
git commit -m "docs(<scope>): <description>

Closes #<issue>"
git push -u origin <branch>
gh pr create --title "docs(<scope>): <description>" --body "Closes #<issue>"
gh pr merge --auto --rebase
```

### Disambiguate a flagged count (which set does the doc count?)

**Disambiguate WHICH set is counted before bumping a number.** A doc count flagged as stale can
disagree with `find … | wc -l` for two different reasons: (a) genuine staleness (a real dir was
added and never documented), or (b) the doc counts a *narrower set on purpose* (documented
packages, skill DEFINITIONS, public modules) that legitimately differs from the raw filesystem
count. Before editing, run BOTH a structural count AND a "what does the surrounding text
enumerate?" check, then reconcile three numbers — dir count, definition-file count, total-file
count — with the doc's claimed unit. Use `git ls-files <path>` to confirm a grep hit is actually
tracked (worktree mirrors false-positive with raw `grep -rn`). Exclude `.claude/worktrees/` when
re-grepping the corpus (`grep -v ".claude/worktrees/"`).

#### 10. Doc-drift consolidation PLANNING (proposed)

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

Use when an issue asks you to *consolidate* two or more drifted onboarding/setup blocks onto a
single canonical recipe and you must produce an **implementation plan** before editing. The core
durable lesson: **the issue's cited file:line ranges are frequently STALE and the duplicated
content frequently appears in MORE places than the issue cites — always re-grep directory-wide
and verify every line number on disk before planning any edit.**

Proposed planning steps:

1. **Distrust the issue's line numbers.** Do not plan against `file.md:34-45` from the issue body.
   `grep -n` for the actual heading or recipe and confirm where it really lives.

   ```bash
   # Issue claimed canonical block at CONTRIBUTING.md:34-45; reality:
   grep -n "just bootstrap\|^## Development Setup" CONTRIBUTING.md   # → 53-65, NOT 34-45
   ```

2. **Directory-wide grep, never single-file, to find ALL copies.** The issue usually cites one
   drifted block; there are often more.

   ```bash
   grep -rn "pre-commit install\|pixi install" README.md CONTRIBUTING.md docs/
   # Cited block: README.md:54-61. Grep ALSO found README:130-138
   # ("Setup Development Environment") with the SAME drift — patching only the
   # cited block would have left the drift alive.
   ```

3. **Classify each grep hit by surrounding context** before deciding to edit. Incidental keyword
   matches are not drift. (e.g. README:50/252/515 matched `pixi install` but were an extras note,
   a dependency-add example, and a branch-protection example — correctly left untouched.)

4. **Source ground truth for the canonical command from the authoritative file — never invent it.**

   ```bash
   sed -n '20,24p' justfile   # bootstrap recipe: pixi install / pixi run dev-install / pixi run pre-commit install
   ```

   The README was "subtly wrong" precisely because it predated `dev-install` and the
   `pixi run pre-commit` wrapper — read the recipe, do not reconstruct it from memory.

5. **Reduce-to-redirect, do not delete.** Keep the section heading + anchor and replace the command
   block with a pointer to the canonical recipe. This preserves inbound anchors and reading flow.

6. **Verify the redirect target anchor resolves.** When a redirect points at
   `CONTRIBUTING.md#development-setup`, add a plan step that confirms the GitHub-rendered slug exists.

   ```bash
   grep -n "^## Development Setup" CONTRIBUTING.md   # confirms the #development-setup anchor
   ```

7. **Gate:** docs-only change → markdownlint is the only gate (MD032 blanks-around-lists is the
   usual offender); no unit tests.

#### 10. Doc-version-currency sync + drift-test fragility (Pattern D) — UNVERIFIED

> **Warning:** This sub-section is a **planning hypothesis** from ProjectHephaestus #1208 — the
> plan was NOT executed (no edits applied, no tests run, no CI). The drift-test fragility modes
> below are reasoning, not observed CI failures. Treat the drift-test recommendation as a caution,
> not a verified recipe. The *sync* half (find the authority, edit the prose, distinguish currency
> claims from historical references) follows the same verified mechanics as §1.

A doc names a stale released version (`MIGRATION.md`: "latest released version is **0.9.2**" while
`git tag` shows `v0.9.5`). Two parts: (a) **sync the prose to the version authority**, and
(b) **decide whether to add a drift-detection regression test** — the trap is that such a test is
fragile and can red CI for reasons unrelated to the doc being wrong.

**(a) Verify the version authority FIRST — do not trust a precedent skill's source-of-truth.**
In a **hatch-vcs** repo the canonical version is the latest git tag, NOT a static
`[project].version` (that field does not exist — `pyproject.toml` declares `dynamic = ["version"]`):

```bash
git tag --sort=-v:refname | head -1          # the real authority in a hatch-vcs repo
grep -n "version" pyproject.toml | head      # confirm there is NO static [project].version
```

The sibling skill `security-md-version-sync` assumes `pyproject.toml [project].version` is the
source of truth — that is **WRONG for a hatch-vcs repo**. Always confirm the version authority for
*this* repo before reusing any precedent.

**(a cont.) Scope precisely, and distinguish currency claims from historical references.** Grep the
version AND any associated date, but do not blindly edit every hit:

```bash
grep -rn "0\.9\.2\|2026-05-28" docs/ README.md CLAUDE.md   # find every candidate
```

A match like `ROADMAP.md:9 … "the strict 2026-05-28 audit"` names a **historical event**, not a
current-version claim — editing it would be wrong. **Edit currency claims; leave historical
references that legitimately name a past date/version.**

**(b) Drift-detection regression test — three fragility modes (anti-patterns, do NOT ship blindly).**
The tempting test asserts the MIGRATION.md prose names the latest git tag, e.g. via a helper like
`hephaestus/version/consistency._version_from_git_tag` and a regex
`latest released version is \*\*(\d+\.\d+\.\d+)\*\*`. It is fragile because:

1. **Regex brittleness** — the regex is coupled to exact prose + bold markup. A future copy-edit
   ("the most recent release is …") or removing `**` makes the test RED even though the doc is
   *correct*. The test now guards the wording, not the version.
2. **Silent skip on shallow CI checkout** — `_version_from_git_tag` returns `None` when tags aren't
   fetched (common with `actions/checkout` `fetch-depth: 1` / no `fetch-tags: true`). A
   `pytest.skip` on `None` means **the gate silently does nothing** — it can pass forever while the
   doc drifts. **A guard that skips in CI is not a guard.**
3. **Release-time race** — asserting the doc `==` latest tag turns every new `vX.Y.Z` push into a
   RED main until someone edits the doc. Pattern D ("stop maintaining the number") ironically
   **re-introduces a manual chore**: now you must edit the doc with/before every tag or main breaks.

**Mitigations (Proposed — not yet verified):**

- **Prefer a live source over an assertion.** Make the doc *link* to GitHub Releases / `git tag`
  output instead of hardcoding a number. This kills the maintenance burden with no brittle gate —
  the same "stop maintaining the number" philosophy used for badge/count drift (see the badges
  skill), applied to version prose.
- If a test is used, assert the doc version is **`<=` latest tag** (drift-direction guard), not
  `==`, so a fresh release tag does not instantly red main.
- If `_version_from_git_tag` returns `None` in CI, **fail loud or fetch tags** (`fetch-tags: true`)
  — never silently `skip`. A loud `xfail`/explicit-fail with a message beats a green no-op.

### Validate, Commit, and PR (Version Currency)

```bash
git diff --stat                                  # confirm only intended files changed
pre-commit run --all-files                       # runs markdownlint with precise line numbers
git add <changed-files>
git commit -m "docs(<scope>): <description>

Closes #<issue>"
git push -u origin <branch>
gh pr create --title "docs(<scope>): <description>" --body "Closes #<issue>"
gh pr merge --auto --rebase
```

#### Variant: doc-version-currency guard anchored to the git TAG (hatch-vcs repos)

When a doc carries a *currency claim* (e.g. "the latest released version is **0.9.5**" or
"Last updated: 0.9.5") that must not trail the real release, the authority is the **latest
`vX.Y.Z` git tag**, NOT `pyproject.toml`. A hatch-vcs / dynamic-versioning repo has **no static
`[project].version`** field, so the older `security-md-version-sync` pattern (pyproject as source
of truth) is WRONG here and must be rejected. Three non-obvious rules — apply ALL THREE:

1. **Authority = the git tag**, resolved with the project's own helper (do not re-implement):

   ```python
   from hephaestus.version.consistency import _version_from_git_tag   # "0.9.5" (leading v stripped)
   from hephaestus.version.parsing import parse_version_tuple          # ("0","9","5") -> (0, 9, 5)

   canonical = _version_from_git_tag(repo_root)   # internally: git describe --tags --abbrev=0 --match 'v[0-9]*'
   ```

2. **Compare with `>=` / "does-not-trail", NEVER `==`.** Drift = the doc trailing the tag:

   ```python
   documented_tuple = parse_version_tuple(documented, on_non_numeric="raise")
   canonical_tuple  = parse_version_tuple(canonical,  on_non_numeric="raise")
   assert documented_tuple >= canonical_tuple, (
       f"doc trails git tag: documented {documented} < tag {canonical}"
   )
   ```

   `==` reintroduces a release-time race: a freshly-pushed *newer* tag would instantly red `main`
   before anyone edits the doc. With `>=`, "doc merely not ahead" passes; only a doc that has
   fallen *behind* fails.

3. **The guard must RUN in CI — a `pytest.skip` is a silent no-op gate** that guards nothing.
   - **WARN/comment + assert-not-None on the regex** (POLA): the regex
     (`r"latest released version is \*\*(\d+\.\d+\.\d+)\*\*"`) is coupled to the exact doc
     wording. Put an in-code `# WARNING:` comment above it telling future editors to update it in
     lockstep with the doc phrasing, and `assert match is not None` so a reword fails LOUD, not silent.
   - **Absent tags → hard `pytest.fail(...)`, never `pytest.skip`** — with remediation guidance
     (run `git fetch --tags`; set `fetch-tags: true`). If the workflow ever regresses to a
     tag-less checkout, the test goes RED loudly instead of green-but-skipped.

   ```python
   def test_doc_version_not_behind_git_tag(repo_root: Path) -> None:
       canonical = _version_from_git_tag(repo_root)
       if canonical is None:
           pytest.fail(  # NOT pytest.skip — a skip makes this guard a no-op
               "No vX.Y.Z git tag reachable. CI checkout must be deep + tagged: "
               "run `git fetch --tags` locally; in the workflow set "
               "`fetch-depth: 0` and `fetch-tags: true` on actions/checkout."
           )
       text = (repo_root / "MIGRATION.md").read_text()
       # WARNING: this regex is coupled to MIGRATION.md's exact wording.
       # If you reword that sentence, update this pattern IN LOCKSTEP.
       match = re.search(r"latest released version is \*\*(\d+\.\d+\.\d+)\*\*", text)
       assert match is not None, "MIGRATION.md currency sentence reworded — update the regex"
       documented = match.group(1)
       assert parse_version_tuple(documented, on_non_numeric="raise") >= parse_version_tuple(
           canonical, on_non_numeric="raise"
       ), f"MIGRATION.md version {documented} trails git tag {canonical}"
   ```

   The companion fix lives in the **workflow**, not the test: the unit-test job's
   `actions/checkout` step needs `fetch-depth: 0` + `fetch-tags: true` (a bare checkout is shallow
   and tag-less, so `_version_from_git_tag` returns `None`). Mirror the config already in
   `auto-tag.yml` / `release.yml`.

   ```yaml
   - uses: actions/checkout@<sha>
     with:
       fetch-depth: 0      # full history
       fetch-tags: true    # tags are required for _version_from_git_tag
   ```

   **TDD non-skip discipline:** the RED step must assert the test FAILS (`1 failed`) against the
   stale state — explicitly NOT "1 skipped" masquerading as a pass. GREEN runs with `-rs` and
   asserts `0 skipped`.

   **Distinguish a currency claim from a historical event name:** "Last updated: <date>" is a
   currency claim to sync; "the strict <date> audit" is an *event name* — leave it untouched.

   **Test placement:** a new `tests/unit/docs/` dir does NOT trip a one-directional source↔test
   mirror-structure check (no `hephaestus/docs/` source is required), and the no-loose-files check
   is satisfied because the test lives inside a subpackage.

### Reliable markdownlint invocation

```bash
# WORKS
pixi run pre-commit run markdownlint-cli2 --files <path/to/file.md>
pre-commit run --all-files
# FAILS — npx/just not in pixi conda env; pixi env init ~2 min
pixi run npx markdownlint-cli2 <file>
```

### Key parameters

- **Counts**: round + `+` for non-deterministic (`3,000+`); exact (no `+`) for deterministic sums.
- **Mojo version in docs**: range from `pixi.toml` (`>=0.26.1,<0.27`), never a nightly string.
- **HTML comments** pass MD033 (comments aren't elements) — safe for deferred-section placeholders.
- **Files most likely to hold stale refs**: `docs/index.md`, `docs/README.md`, `docs/glossary.md`,
  `references/notes.md`, `docs/analysis-prompt.md`.
- **Policy-audit exclusions**: `docs/arxiv/`, `tests/claude-code/`, `.pixi/`, `build/`, `node_modules/`.
- **Doc-version authority on hatch-vcs repos**: the latest `vX.Y.Z` git tag (via
  `_version_from_git_tag`), NOT `pyproject.toml` — there is no static `[project].version` field.
  `security-md-version-sync`'s pyproject-as-source-of-truth assumption does NOT apply to
  dynamic-versioning repos.
- **Count-annotates-list**: a doc count annotates its adjacent curated list — reconcile
  number-to-list, never number-to-filesystem; `number > list_count` is always a POLA NOGO.
- **Pixi env vs feature**: `[environments]` defines runnable environments; `[features]` does not.
  `pixi run -e <name>` fails if `<name>` is only a feature. Verify before shipping.
- **markdownlint Skipped**: `pre-commit run --files <doc>` may print `Skipped` for markdownlint —
  the file was NOT linted. Verify with `pixi run pre-commit run markdownlint-cli2 --files <doc>`.

#### 1b. Counting subpackages for a directory-tree drift fix (planning)

> **Warning:** This subsection is `unverified` — derived from an implementation *plan* for
> ProjectHephaestus #1188 (README directory tree omits the `scripts_lib/` subpackage). The plan was
> not executed end-to-end (no pre-commit run, no regression test executed). Treat the counting
> recipe as verified, but treat the proposed regression test and edit-placement assumptions as
> hypotheses until CI confirms.

When a README/CLAUDE.md directory tree omits a subpackage and quotes a package count, **re-derive
the count from the filesystem yourself** — trust neither the doc's claim nor the audit issue's
number. Both can carry the same off-by-one error.

```bash
# WRONG — overcounts: includes __pycache__/ and any dot-dirs
ls -d hephaestus/*/ | wc -l            # returned 21 (20 real + __pycache__)

# RIGHT — count only real packages (those with an __init__.py)
find hephaestus -maxdepth 2 -name __init__.py -printf '%h\n' | sort -u | wc -l
# or, tracked files only (ignores cache entirely):
git ls-files 'hephaestus/*/__init__.py' | wc -l   # → 20
```

Then re-grep the **bare number** across the whole corpus and disambiguate every hit before editing —
the same stale count usually lives in more than one file, and an unrelated metric will false-positive:

```bash
grep -rn "19" README.md CLAUDE.md
# README.md:tree caption "19 ... subpackages"  → REAL stale copy (fix)
# CLAUDE.md:28 "19 documented subpackages"      → REAL second stale copy (fix)
# CLAUDE.md:62 "19.7k LoC"                       → FALSE POSITIVE, unrelated metric (do NOT change)
```

For the tree insertion itself, the new entry must sort into the existing order — verify the **local
neighborhood** is alphabetical (e.g. `scripts_lib/` sorts between `resilience/` and `system/`) by
reading the adjacent lines; do not assume the entire tree is sorted. The inserted comment text is
planner-authored prose, not a copied docstring — flag it for maintainer wording review. The real
acceptance gate is a regression test that asserts every `*/__init__.py` package appears in the tree,
not the greps (the greps are for human/CI reproduction). The CLAUDE.md "avoid raw grep" guidance
applies to agent tool-use, not to a doc's copy-paste verification block.

## Planning Discipline (remove-vs-redirect + confirm-then-fix)

> **Verification of this section:** `verified-local`. The audit/verification *technique* below was
> directly verified on disk (`ls .claude/` proved `.claude/shared/` is absent; `grep -rn` found one
> tracked occurrence). The downstream PR outcome is **pending** — the plan that produced this
> learning had not yet been implemented or merged when captured. Treat the decision rule as sound;
> treat any claim about the eventual fix landing cleanly as unverified.

### Remove-vs-redirect decision rule

When a doc points at a path/file/section that no longer exists, choose deliberately:

| Situation | Action | Why |
| --------- | ------ | --- |
| An **adjacent surviving line already covers the same intent** | **REMOVE** the dead pointer | KISS/YAGNI — the redirect would be pure redundancy |
| **No surviving pointer covers the intent** and the information would otherwise be lost | **REDIRECT** to the current location | Preserves the reader's path to the information |

**Worked example** (ProjectHephaestus #1211): `CLAUDE.md` "Getting Help" list item 4 pointed at
`.claude/shared/` (a phantom dir). The adjacent item 3 (`CLAUDE.md:415`, "Review documentation in
`docs/` directory") already covered the shared-docs intent, so item 4 was redundant → **remove**,
not redirect.

### Confirm-then-fix audit sequence (the verified-local technique)

1. `grep -rn "<stale-string>" . --include="*.md"` — find **every** hit across the whole tree, not
   just the line the audit cited.
2. `ls <path>` — prove the directory/file is actually absent (don't trust the audit's claim).
3. Check whether an **adjacent line already covers the intent** → drives remove-vs-redirect.
4. Make a **minimal single-line `Edit`** (don't rewrite the section).
5. **Re-grep the whole corpus** before declaring done — sibling stale copies (worktree mirrors,
   `docs/` duplicates) survive a single-line patch.

### Reviewer-risk checklist for the resulting plan

Surface these as explicit risks; each is a place where a phantom-path plan commonly goes wrong:

- **Ephemeral / worktree copies.** A `.claude/worktrees/agent-*/CLAUDE.md` mirror is often assumed
  out-of-scope (regenerated/discarded by the worktree lifecycle) but that assumption is rarely
  verified. Run `git ls-files <path> | head` to confirm it is **untracked** before excluding it; if
  it is tracked, the plan misses an occurrence.
- **Line numbers drift.** An audit's cited `file:N` (e.g. `CLAUDE.md:417`) can shift between the
  audit date and the edit. Mitigation: re-`grep -n` on disk and edit by matched string, never by the
  audit's stale line number.
- **Markdownlint blank-line regressions.** Deleting a list item can trip MD022/MD032 — reason about
  it, but the proof is `pre-commit run markdownlint --files <file>`, not inspection.
- **Memory-sourced external invariants.** Policy facts pulled from prior memory rather than
  re-verified this session (e.g. the `pr-policy` auto-merge gate requiring a `state:implementation-go`
  label; the GPG committer-email-must-match-key rule; a specific signing email) should be flagged as
  assumed-from-memory so the reviewer re-confirms them against the live repo config.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Fixing only the primary file for stale counts | Updated README but not `docs/` or `references/` | Stale copies survived in `docs/analysis-prompt.md` and `references/notes.md` | Always re-run a project-wide grep after fixing the primary file |
| Deleting stub/tracking entries outright | `rm` stubs / removed deleted-agent lines immediately | Left broken links across docs and lost historical context | grep `-rl` for all referencers first; use `~~strikethrough~~` for converted entries |
| Keeping fabricated APIs in getting-started docs | Preserved `TensorDataset`, `Trainer`, `EarlyStopping` imports | Those types don't exist in `shared/`; docs mislead and fail when run | grep the codebase to verify every API/import before keeping it |
| `#####` subsections inside a `####` block containing `###` headings | Kept original heading structure | markdownlint MD001: a `###` resets the running level, so the next `#####` jumps 2 levels | Flatten inner subsections to bold, or demote `#####` to `####` |
| Hardcoding the Mojo nightly version string | Wrote `0.26.1.0.dev2025122805` | Full nightly strings go stale immediately | Use the version range from `pixi.toml` (`>=0.26.1,<0.27`) |
| Editing the SHA-pinning documentation examples | Considered replacing `setup-pixi@v0.9.3` in pinning examples | Those lines document the pattern; they are not workflow steps to migrate | Distinguish concept-explaining code blocks from actual steps |
| Modifying `validate_links.py` to also check anchors | Extending the existing script | It intentionally strips anchors for file-existence checks; changing it breaks callers | Create a focused additive anchor script instead |
| Sourceable-contract / mechanism tests as monolith justification | Cited a source guard and ran `source … && type fn` to "prove" usage | Mechanism (can be sourced) ≠ usage (zero actual callers per grep); baking it into docs misleads auditors | Verify usage with grep; demote unverified claims to caveats |
| Removing `--label` from CONTRIBUTING without checking `.claude/shared/` | Only grepped `CONTRIBUTING.md` | A third file (`.claude/shared/pr-workflow.md`) could hold the same contradiction | Verify all related files before declaring a contradiction fixed |
| `replace_all: false` for a repeated phrase | Tried editing the first occurrence individually | Context string not unique — Edit reported "string not found" | Use `replace_all: true` when the same phrase appears multiple times |
| `pixi run npx markdownlint-cli2 <file>` / `just pre-commit-all` | Linting via npx or `just` | `npx`/`just` not in PATH; pixi env init takes ~2 min | Run `pre-commit run` (or `git commit`) to trigger markdownlint directly |
| Full pre-commit suite without skipping | Ran all hooks on a host with a GLIBC mismatch | `mojo-format` fails on GLIBC < 2.32 (environment, not code) | Use `SKIP=mojo-format`; only non-Mojo hooks matter for doc-only changes |
| Trusting issue body LoC figures for ADR updates | Used `25,403 / 46,697 = 54.4%` from the audit-generated issue body | Figures reflected the audit snapshot date, not the current on-disk state; re-measurement gave `26,125 / 48,498 = 53.9%` | Always re-measure LoC from disk at implementation time with `find … -name '*.py' \| xargs wc -l \| tail -1` |
| Using issue body line numbers to locate stale text in ADR | Jumped to `:9` / `:62` as cited in the issue | Issue line numbers were from the audit snapshot; the actual strings had shifted | Use content-match grep (`grep -rn "<old_figure>"`) to locate stale text — never trust issue-body line numbers |
| Planning structural decomposition for an ADR's god-package finding | Proposed splitting the `automation/` package before reading ADR-0001 | ADR-0001 explicitly documents that decomposition is rejected; the prescribed remedy (optional-extra install boundary) was already implemented | Read the referenced ADR in full before planning — it may document that the finding is intentional design with an approved alternative remedy; correct fix may be documentation-only |
| Running `pixi run ruff check docs/ CLAUDE.md` for doc-only changes | Ran ruff on markdown files expecting linting feedback | `ruff` does not lint `.md` files; the command is a no-op and produces no signal | Skip `ruff check` for doc-only changes; use `pixi run pre-commit run markdownlint-cli2 --files <file.md>` instead |
| Deleting `docs/contributing.md` to resolve the case-clash | Removed the file entirely | Breaks inbound links from the docs index | Reduce to a redirect; keep root as canonical |
| Per-file reviewers for citation corpus | Reviewed each entry individually | Could not see cross-document §-drift or arXiv ID-to-title swaps | Both failure modes need a cross-corpus structural audit, not per-file review |
| Trusting issue body claim of specific incorrect string | Planned to remove text the issue said was "incorrect" in a doc | That exact text no longer existed in main — a prior PR had already fixed it; issue body was written against an older version | Grep for the exact claimed string before planning any edit; if grep returns nothing the issue premise is stale |
| `pytest.skip` when no git tag is reachable | Skipped the doc-version drift test on a tag-less CI checkout | Silent no-op gate — the headline drift guard then guards nothing (green-but-skipped) | Make absent-tags a hard `pytest.fail(...)` with remediation, AND add `fetch-tags: true` so the test actually runs |
| `==`-to-latest-tag for the version-currency assert | `assert documented == canonical_tag` | Release-time race: a freshly-pushed newer tag instantly reds `main` before anyone edits the doc | Use `>=` / "does-not-trail" semantics — doc merely "not ahead" passes, only a trailing doc fails |
| Using pyproject `[project].version` as the authority on a hatch-vcs repo | Tried to read the canonical version from `pyproject.toml` | hatch-vcs / dynamic versioning has NO static `[project].version` field — `security-md-version-sync`'s pyproject-as-source assumption does not apply | Authority is the latest git tag via `_version_from_git_tag(repo_root)` |
| Bare `actions/checkout` for a job whose tests need tags | Left the default shallow checkout on the unit-test job | A bare checkout is shallow and tag-less, so `_version_from_git_tag` returns `None` and the guard skips/fails | Add `fetch-depth: 0` + `fetch-tags: true` (mirror auto-tag.yml / release.yml) |
| Regex coupled to doc wording with no guard | Relied on the regex silently returning no match after a reword | A reworded sentence makes the regex match nothing → test passes vacuously, drift undetected | `assert match is not None` (fail loud on reword) + an in-code `# WARNING:` comment to update the regex in lockstep |
| Searching only the issue-reported stale line-number value | Only grepped for `137-141` (the value cited in the issue) | The test file had a *different* stale value (`127-129`) from independent update history; missed it entirely | Search for all plausible old values across all referencing files — doc and test files may carry different stale numbers from independent update histories |
| Bumped doc count `19`→`20` to match `find \| wc -l` while curated list unchanged | Changed caption number to match filesystem count without adding the missing list entry | Produced an internally-contradictory doc: number promised 20 over a list of 19 entries — worse than the original staleness | Reconcile number-to-LIST: add the missing list entry AND update the number, or clarify scope in the annotation; never let `number > list_count` |
| Trusted audit issue's stated `21 subpackages` figure | Used 21 (the issue-filed count) as the target to bump to | Issue-filed counts are themselves stale: real filesystem was 20 dirs / 19 documented packages (ls -d overcounts, includes `__pycache__`) | Re-derive with `git ls-files 'pkg/*/__init__.py' \| wc -l` — never trust an issue's count claim |
| Shipped `pixi shell -e dev` / `pixi run -e dev` without verifying dev is an environment | Copied command from a sibling doc assuming dev was a pixi environment | `dev` is a *feature* in `[features]`, not an entry in `[environments]`; the command fails with "unknown environment" | Verify: `pixi run -e dev true 2>&1 \| grep -q "unknown environment"` before shipping; an un-sourced command is a STOP signal |
| Bare `pre-commit install` invocation in README of a pixi-managed repo | Wrote `pre-commit install` without `pixi run` prefix | Fails with `command not found` on a clean machine — `.pixi/envs/default/bin` is not on PATH after `pixi install` | Prefix all env-tool invocations with `pixi run`; detect bare invocations with `grep -rnE '^[[:space:]]*(pre-commit\|pytest\|mypy\|ruff)\b'` |
| Trusted audit issue's conflicting prose counts (`6 vs 11 modules`) | Tried to reconcile the two prose numbers by checking code | Both counts were suspect prose; the real count was in a passing frozen-allowlist test (`expected_modules` set) | Count from the enforced artifact first; only add a prose guard when no enforced guard already exists |
| Used `replace_all` on a bare digit when doing a count fix | Ran `replace_all: true` on `"37"` to update a tool count | Bare digit `37` matched unrelated occurrences in the same file (version strings, line numbers) | Use exact-phrase `Edit` (`"13 of 37 declared tools"`) and phrase-scoped grep (`grep -rn 'of 37\|37 declared'`) for precise targeting |
| Trusted the audit's reported `file.py:NN` coordinate to locate a dangling citation | Jumped directly to line NN of the cited source file | Audit coordinate was off-by-one from a prior code churn; the referenced construct was at a different line | Locate by content-match grep (`grep -n "<construct_keyword>" source.py`), not coordinate |
| Assumed `pre-commit run --files <doc>` linted the file when output showed `Skipped` | Counted a `Skipped` pre-commit result as lint-clean | `Skipped` means the hook's file filter excluded the path — markdownlint did NOT run; issues went undetected | Check the status word in the output; verify with `pixi run pre-commit run markdownlint-cli2 --files <doc>` |
| Trusted issue's phantom-recipe line references without re-grepping | Issue claimed both lines 232 and 233 of `docs/onboarding.md` had broken justfile recipes; patched both | Ground-truth grep showed line 232 (`just start-agamemnon`) was already correct — only line 233 (`just nestor-start` → `just start-nestor`) was live; the issue described a formerly-broken state | Always re-grep the doc against the justfile before editing each reported line; issue descriptions may cite multiple phantom references where only a subset are still live defects |
| Assumed uniform naming convention from a few correct justfile recipe names | Saw `start-agamemnon`, assumed verb-first was universal, relaxed verification on adjacent `hermes-start`, `argus-start` entries | The Odysseus justfile uses MIXED convention: verb-first (`start-agamemnon`, `start-nestor`) for Agamemnon/Nestor; prefix-first (`hermes-start`, `argus-start`, `keystone-start`) for infrastructure services | Run a bulk cross-check for ALL doc table entries: `for r in r1 r2 r3 r4 r5; do grep -qE "^${r}( \|:)" justfile && echo "OK $r" \|\| echo "MISSING $r"; done` |

## Results & Parameters

### Commit format

| Change | Commit message |
| ------ | -------------- |
| Drift / count / metric fix | `docs(readme): fix test counts, file counts, and --cov path` |
| Agent count fix | `fix(docs): update stale agent count references (N → M agents)` |
| Phantom dir | `fix(docs): Remove phantom tests/integration/ references` |
| Broken refs | `fix(docs): Remove broken <dir>/ references from CLAUDE.md` |
| Stub deletion | `docs: delete N empty placeholder documentation stubs` |
| Getting-started rewrite | `docs(getting-started): rewrite <files> with accurate commands` |
| Tier labels | `fix(docs): Fix all tier label mismatches in metrics-definitions.md` |
| Contradiction | `fix(docs): Remove --label flag from CONTRIBUTING.md PR example` |
| Anchor validator | `feat(scripts): add installation anchor validator + CI step` |

### Drift-detection test pattern (Python)

```python
"""Drift-detection test — fail if a stale/forbidden phrase reappears."""
from pathlib import Path
import re
import pytest

PROJECT_ROOT = Path(__file__).parents[3]
DOC_FILES = [PROJECT_ROOT / "README.md", PROJECT_ROOT / "CLAUDE.md"]
FORBIDDEN = [r"chaos\s+(?:engineering|testing)", r"resilience\s+testing"]

@pytest.mark.parametrize("doc", [p for p in DOC_FILES if p.exists()])
@pytest.mark.parametrize("pattern", FORBIDDEN)
def test_no_stale_claims(doc: Path, pattern: str) -> None:
    matches = re.findall(pattern, doc.read_text(), re.IGNORECASE)
    assert not matches, f"{doc.name} contains forbidden phrase: {matches}"
```

### Reliable markdownlint invocation

```bash
# WORKS
pixi run pre-commit run markdownlint-cli2 --files <path/to/file.md>
pre-commit run --all-files
# FAILS — npx/just not in pixi conda env; pixi env init ~2 min
pixi run npx markdownlint-cli2 <file>
```

### Key parameters

- **Counts**: round + `+` for non-deterministic (`3,000+`); exact (no `+`) for deterministic sums.
- **Mojo version in docs**: range from `pixi.toml` (`>=0.26.1,<0.27`), never a nightly string.
- **HTML comments** pass MD033 (comments aren't elements) — safe for deferred-section placeholders.
- **Files most likely to hold stale refs**: `docs/index.md`, `docs/README.md`, `docs/glossary.md`,
  `references/notes.md`, `docs/analysis-prompt.md`.
- **Policy-audit exclusions**: `docs/arxiv/`, `tests/claude-code/`, `.pixi/`, `build/`, `node_modules/`.
- **Merge method is per-repo policy** — verify squash vs rebase vs merge against the target repo's
  CLAUDE.md / branch-protection before copying any `gh pr merge` line. ProjectHephaestus: `--squash`
  (rebase disabled).

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectScylla | Issues #880, #759, #1112, #1477, #1503, #1507 | Future-work audits, metric/count fixes, ecosystem role |
| ProjectScylla | Issues #753, #758; #848 (PR #954); #752 (PR #811); #878 (PR #925); #1348 (PR #1362); #881 (PR #990) | Contradiction, phantom-dir, broken-ref, policy-audit, tier-label, Future-Improvements annotation |
| ProjectOdyssey | Issues #3344, #3365; PR #3320; PR #4847 | Workflow README audit, agent-count fix, post-migration README sync |
| ProjectOdyssey | Issues #3142/#3308, #3304/#3913, #3305/#3917, #3918/#4830, #3141/#3303, #3914/#4828, #3915/#4829 | Stub deletion, installation/quickstart rewrite, IDE-setup extend, getting-started audit, anchor validator |
| ProjectHephaestus | Issue #792 (PR #984); Issue #630 (PR #667) | Monolith-rationale ADR; CONTRIBUTING case-clash redirect |
| ProjectHephaestus | Issue #1177 (PR #1281) | Stale LoC figures in ADR + CLAUDE.md after `automation/` grew; re-measured on-disk (`26,125 / 48,498 = 53.9%`); doc-only fix; all CI passed |
| ProjectHephaestus | Issue #1222 (planning session) | Stale guard line-number citations in docs/INSTALLER_ARCHITECTURE.md and test comments after install.sh code churn; issue body described already-fixed content; 2 files had different stale values (137-141 vs 127-129) from independent update history; verified-local |
| ProjectHephaestus | Issue #1211 (PR #1236) | Phantom-dir removal (.claude/shared/ in CLAUDE.md); surfaced squash-only merge-method pitfall |
| ProjectHephaestus | Issue #1216 (planning artifact, **unverified**) | Consolidate two drifted README onboarding blocks onto canonical `just bootstrap` — PLANNING only; plan written but not executed end-to-end, no CI confirmation. Source of the §13 doc-drift consolidation planning workflow |
| ProjectHephaestus | Issue #1208 (planning artifact, **unverified**) | Doc-version-currency sync + drift-test fragility (Pattern D) — hatch-vcs repo, git-tag authority, `>=` semantics; plan not executed in CI. Source of §18 Pattern D workflow |
| ProjectHephaestus | Issues #2351/#2373 (closed, content salvaged) | Count-annotates-list rule: bumping 19→20 without updating tree produced contradictory doc; issue-filed count of 21 was stale (overcounted `__pycache__`); reconcile number-to-list not number-to-filesystem |
| ProjectHephaestus | Issue #2352 (closed, content salvaged) | Replacement command must run in THIS repo: `pixi run -e dev` failed because `dev` is a feature not an environment; un-sourced commands are a STOP signal |
| ProjectHephaestus | Issue #2372 (closed, verified-ci) | Pixi-only repo: bare `pre-commit install` fails on clean machine; prefix all env-tool invocations with `pixi run`; detect with `grep -rnE` |
| ProjectHephaestus | Issue #2397 (closed, content salvaged) | Conflicting prose counts (6 vs 11 modules); enforced-artifact (passing frozen-allowlist test) beats both; no redundant prose guard when test already exists |
| ProjectHephaestus | Issue #2398 (closed, content salvaged) | Count-drift from `[project.scripts]`: ROADMAP said 37, pyproject had 47; phrase-scoped grep to scope edit and prove no copies survive; exact-string Edit over bare-digit replace_all |
| ProjectHephaestus | Issues #2399/#2401 (closed, content salvaged) | Dangling file:line citation: locate by content not audit coordinate; content-anchored durable citation; markdownlint Skipped != linted; historical narrative left intact |
| mvillmow/Random | Predictive-Coding-in-Mojo Phase 0 | Cross-doc citation drift: 8 stale §-refs, 2 arXiv ID swaps caught |
| Odysseus | Issue #182, PR #312 (docs/onboarding.md:233 phantom recipe fix) | Issue claimed both lines 232–233 had broken recipes. Ground-truth grep showed line 232 (`just start-agamemnon`) was already correct; only line 233 needed fixing (`nestor-start` → `start-nestor`). Odysseus justfile uses mixed convention: verb-first for Agamemnon/Nestor, prefix-first for Hermes/Argus/Keystone. Signed commit `4d28379`; verified-local. |
