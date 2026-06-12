---
name: stale-documentation-audit-and-broken-reference-repair
description: "Use when: (1) running a doc-drift audit across a corpus — detecting stale counts, metric discrepancies, cross-doc contradictions, ecosystem-role drift; (2) removing phantom directory references from documentation when a path no longer exists; (3) fixing broken documentation references (dead links, stale headings); (4) auditing documentation examples for policy violations; (5) auditing and rewriting getting-started stubs by sourcing real commands from justfile and versions from pixi.toml; (6) fixing incorrect tier labels or version numbers in docs that have drifted from implementation; (7) managing the full lifecycle of placeholder and stub documentation — deletion under YAGNI, deferred-comment placeholders, rewriting with accurate codebase-grounded content; (8) resolving audit nitpicks for monolithic code by documenting verified design rationale; (9) resolving CONTRIBUTING.md case-clashes and circular cross-references in docs/; (10) validating anchor fragments in markdown deep-links to detect broken headings."
category: documentation
date: 2026-06-12
version: "1.1.0"
user-invocable: false
verification: unverified
history: stale-documentation-audit-and-broken-reference-repair.history
tags: [doc-drift, stale-doc, broken-references, phantom-dir, placeholder, stub, anchor-validation, tier-labels, doc-audit, doc-sync, drift-detection-test, ci-effective, version-currency, merged]
---

# Stale Documentation Audit and Broken Reference Repair

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | Canonical workflow for auditing stale documentation and repairing broken references: drift audits, phantom-dir/dead-link removal, placeholder lifecycle, getting-started rewrites, tier-label fixes, anchor validation |
| **Outcome** | Consolidated from 10 skills covering doc-drift audits, broken-reference repair, policy-violation audits, placeholder/stub lifecycle, monolith-rationale docs, CONTRIBUTING case-clash, and anchor validation |
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
gh api orgs/<ORG>/repos --paginate --jq '.[] | "\(.name) -- \(.description)"' | sort  # role truth

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

# ── TIER-LABEL FIXES ─────────────────────────────────────────────────────────
grep -n "T[0-9]" .claude/shared/metrics-definitions.md      # scan all tier refs

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

Fix patterns: `Planned → Implemented` in status tables; round counts with `+` for forward
compatibility (`"2026+ tests" → "3,000+ tests"`) but exact counts (no `+`) for deterministic
sums; correct `--cov` path to the installed package name. Annotate deleted entries with
strikethrough rather than removing them: `~~`.claude/agents/deleted.md`~~ — converted to skill`.
Add a self-verifying command to the doc so future readers can re-check:
`` `ls .github/workflows/*.yml | wc -l` ``. Authority order for contradictions:
`CLAUDE.md > .claude/shared/pr-workflow.md > CONTRIBUTING.md` — edit only the wrong file.

**Example** — agent count drift after agents converted to skills: update both the Quick Links
bullet (`- N agents` → `- M agents`) and the Agent Hierarchy line (`All N agents` → `All M agents`).

Optionally add a drift-detection regression test (see Results & Parameters) and an ADR.

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

#### 6. Tier-label / version fixes

Labels drift off-by-one from the authoritative table after a renumbering. Scan ALL occurrences
(prior partial fixes are common — issues recur), then cross-check each against the table.

Authoritative tiers: T0 Prompts · T1 Skills · T2 Tooling · T3 Delegation · T4 Hierarchy · T5
Hybrid · T6 Super.

**Example** — `.claude/shared/metrics-definitions.md` had `T3 (Tooling)`, `T4 (Delegation)`,
`T5 (Hierarchy)`: fix to `T2 / T3 / T4`. Hotspots: the Token Tracking section (`T2 vs T3
Analysis` → `T1 vs T2`) and the 9-row Component Cost table. Only named references (`(Name)` or
`-` dashes) need fixing; bare tier numbers in formula example data are correct as-is.

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

#### 10. Drift-detection test fragility — anti-patterns and CI-effective resolutions (Proposed)

> **⚠️ Proposed (unverified).** The resolutions below come from ProjectHephaestus #1208
> planning round R1 (a re-plan after R0 got NOGO for shipping a no-op drift guard). The
> CI-checkout root cause was **verified by inspection** (reading `test.yml` showed a bare
> `actions/checkout` step). The end-to-end fix (test actually runs+passes in CI with the new
> checkout config) is **NOT** verified — no edits were applied, no `pixi run pytest`, no CI run.
> Treat as a design blueprint, not a CI-green claim.

A drift-detection regression test (§1, Results & Parameters) is only worth shipping if it can
actually **go red in CI**. Three fragility anti-patterns make a drift guard a silent no-op; each
has a concrete resolution.

##### Making the drift guard CI-effective (resolutions)

**(a) Silent-skip → hard-fail + fetch-tags (THE headline fix).** A test that calls
`pytest.skip()` when it cannot resolve the git tag is a silent no-op gate: it shows green in CI
while guarding nothing. **Root cause (verified-by-inspection):** GitHub Actions `actions/checkout`
with a **bare** `uses:` (no `with:` block) does a shallow, single-commit, **tag-less** fetch, so a
helper that shells `git describe --tags` returns `None`. **Resolution — take BOTH halves
(belt-and-suspenders):**

1. Add `fetch-depth: 0` and `fetch-tags: true` to the test job's checkout step. Mirror an existing
   workflow in the repo that already does this (e.g. an auto-tag / release workflow) rather than
   inventing config.
2. Replace `pytest.skip(...)` with `pytest.fail(...)` carrying remediation text. If the checkout
   config ever regresses, the test goes **RED loudly** instead of green-but-skipped.

> **Lesson: a guard that silently skips is not a guard.** Never use `pytest.skip` for the absence
> of the very authority (here, the git tag) that the test exists to check.

**(b) `==`-to-latest-tag race → `>=` / "does not trail" comparison.** Asserting
`documented == latest_tag` reds `main` the instant a *new* tag is pushed — before anyone edits the
doc — reintroducing the manual chore the drift test was meant to kill. **Resolution:** assert the
documented version is **not strictly older** than the latest tag
(`documented_tuple >= canonical_tuple`). A freshly-pushed newer tag does **not** instantly fail,
but a genuinely-stale doc (e.g. `0.9.2` vs `0.9.5`) still fails. Reuse the repo's existing
version-tuple parser; do not hand-roll the comparison.

**(c) Verified helper detail (worked):** the repo's `_version_from_git_tag(repo_root)` **strips the
leading `v`** (returns `"0.9.5"`, not `"v0.9.5"`), matching the doc's printed form. Verify the
return form before assuming the comparison is like-for-like — a `v`-prefixed tuple parse vs a
bare-version doc string would mis-compare.

**(d) TDD RED step must assert NON-SKIP, not just "fails".** Because of the skip trap, a developer
can see a green run that is actually a SKIP and conclude the test passed. **Resolution:** run the
RED step with `pytest -rs` and require the summary line read `1 failed` (NOT `1 skipped` / `1
passed`); the GREEN / sanity steps require `0 skipped`. To prove the guard is load-bearing, add a
verification snippet that temporarily flips the doc back to the stale version and asserts a
**non-zero** exit.

```bash
# RED must be a genuine FAIL, not a SKIP (the skip trap masquerades as green)
pixi run pytest -rs tests/unit/docs/test_version_currency.py | tail -3   # expect "1 failed", 0 skipped
# Prove it is load-bearing: flip the doc back to the stale version → non-zero exit
git stash && <revert doc to stale 0.9.2> && pixi run pytest -q tests/unit/docs/...; echo "exit=$?"  # expect non-zero
```

**(e) Reviewer-confirmed non-issue (record so future plans don't re-litigate):** placing a *new*
test dir like `tests/unit/docs/` with **no** corresponding source package does **not** trip a
one-directional test-structure mirror check — `src_packages − test_packages` only flags **source**
dirs MISSING a test dir, not test-only dirs. A no-loose-files check is also satisfied because the
test lives inside a subpackage, not at the test-root.

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
| Deleting `docs/contributing.md` to resolve the case-clash | Removed the file entirely | Breaks inbound links from the docs index | Reduce to a redirect; keep root as canonical |
| Per-file reviewers for citation corpus | Reviewed each entry individually | Could not see cross-document §-drift or arXiv ID-to-title swaps | Both failure modes need a cross-corpus structural audit, not per-file review |
| `pytest.skip(...)` when the git tag can't be resolved (drift test) | Skipped the drift assertion if `git describe --tags` returned None | A bare `actions/checkout` does a shallow tag-less fetch → the test silently SKIPPED in CI, guarding nothing while showing green (R0 NOGO) | A guard that silently skips is not a guard; `pytest.fail(...)` + add `fetch-depth: 0` / `fetch-tags: true` to the checkout step (belt-and-suspenders) |
| `assert documented == latest_tag` for version currency | Required the doc version to equal the latest git tag exactly | Reds `main` the instant a NEW tag is pushed, before anyone edits the doc — reintroduces the manual chore the test was meant to kill | Assert "does not trail": `documented_tuple >= canonical_tuple` (a newer tag passes; a genuinely-stale doc still fails); reuse the repo's version-tuple parser |
| RED step that only checks "the run failed" | Treated any non-pass as a successful RED | A SKIP also isn't a pass, so a silent-skip masquerades as a satisfied RED step | Run `pytest -rs`; require the summary be `1 failed` (NOT `1 skipped`/`1 passed`); GREEN steps require `0 skipped` |
| Comparing a `v`-prefixed tag tuple to a bare doc version | Assumed `git describe` form matched the doc's printed form | `_version_from_git_tag` strips the leading `v` (returns `"0.9.5"`) — a `v`-prefixed parse would mis-compare | Verify the helper's return form before assuming the comparison is like-for-like |

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

### Version-currency drift test — CI-effective form (Proposed, unverified)

For a *version-currency* drift guard (doc version vs latest git tag), the naive form is a no-op in
CI. Apply the §10 resolutions: **never `pytest.skip` on a missing tag** (that is exactly the
authority under test), assert **does-not-trail** (`>=`) not `==`, and ensure CI checkout fetches
tags.

```python
def test_documented_version_not_stale() -> None:
    canonical = _version_from_git_tag(REPO_ROOT)  # strips leading "v" → "0.9.5"
    if canonical is None:
        # HARD FAIL, never skip: a tag-less checkout (bare actions/checkout) must surface loudly.
        pytest.fail(
            "Could not resolve the latest git tag — the CI checkout step likely lacks "
            "fetch-depth: 0 / fetch-tags: true. This guard is a no-op without tags."
        )
    documented = parse_version_tuple(read_documented_version())     # reuse repo's parser
    assert parse_version_tuple(canonical) <= documented, (          # doc must NOT trail the tag
        f"Documented version {documented} trails latest tag {canonical}; bump the doc."
    )
```

```yaml
# CI: the test job's checkout MUST fetch tags (mirror the repo's auto-tag/release workflow)
- uses: actions/checkout@<pinned>
  with:
    fetch-depth: 0
    fetch-tags: true
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

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectScylla | Issues #880, #759, #1112, #1477, #1503, #1507 | Future-work audits, metric/count fixes, ecosystem role |
| ProjectScylla | Issues #753, #758; #848 (PR #954); #752 (PR #811); #878 (PR #925); #1348 (PR #1362); #881 (PR #990) | Contradiction, phantom-dir, broken-ref, policy-audit, tier-label, Future-Improvements annotation |
| ProjectOdyssey | Issues #3344, #3365; PR #3320; PR #4847 | Workflow README audit, agent-count fix, post-migration README sync |
| ProjectOdyssey | Issues #3142/#3308, #3304/#3913, #3305/#3917, #3918/#4830, #3141/#3303, #3914/#4828, #3915/#4829 | Stub deletion, installation/quickstart rewrite, IDE-setup extend, getting-started audit, anchor validator |
| ProjectHephaestus | Issue #792 (PR #984); Issue #630 (PR #667) | Monolith-rationale ADR; CONTRIBUTING case-clash redirect |
| ProjectHephaestus | Issue #1208 R1 (post-NOGO replan) — **Proposed/unverified** | Drift-guard CI-effectiveness: silent-skip→hard-fail+fetch-tags, `==`→`>=` currency, RED-must-not-skip; CI-checkout root cause verified-by-inspection, end-to-end fix unverified |
| mvillmow/Random | Predictive-Coding-in-Mojo Phase 0 | Cross-doc citation drift: 8 stale §-refs, 2 arXiv ID swaps caught |
