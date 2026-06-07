---
name: stale-documentation-audits-and-sync
description: "Canonical workflow for detecting and remediating stale documentation: doc-drift grep audits, stale-count fixes, metric discrepancy reconciliation, ecosystem-role drift detection, multi-file doc sync, README audit workflows, cross-doc citation drift defenses, doc-contradiction resolution. Use when: (1) running a doc-drift audit across a corpus, (2) reconciling docs to current implementation, (3) fixing stale agent/file/test counts in README, (4) catching cross-doc contradictions before publication, (5) syncing docs after a structural change."
category: documentation
date: 2026-06-07
version: "1.1.0"
user-invocable: false
verification: verified-local
history: stale-documentation-audits-and-sync.history
tags: [merged, doc-drift, stale-doc, doc-sync, doc-audit, citation-drift]
---

# Stale Documentation Audits and Sync

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Canonical workflow for auditing, detecting, and remediating stale documentation across a project corpus |
| **Outcome** | Consolidated from 12 skills covering Future Improvements audits, count reconciliation, metric discrepancy fixes, ecosystem role drift, multi-file sync, workflow README audits, cross-doc citation drift, and contradiction resolution |
| **Verification** | verified-local — validated across ProjectScylla, ProjectOdyssey, ProjectMnemosyne |

## When to Use

- A "Future Improvements" or "Future Work" section lists a feature that was already shipped
- Documentation states a metric (test count, coverage %, file count) that doesn't match the codebase
- `CLAUDE.md` and `pyproject.toml` contradict each other on thresholds
- A code registry (e.g., `FIGURE_REGISTRY`, agent list) changed size but docs still reference old counts
- Agents were deleted or converted to skills and doc counts are out of sync
- External architecture docs describe a project's role differently than its actual implementation
- Same ecosystem repo listing appears in multiple files and needs consistent updates
- Workflows were added/deleted but `README.md` was not updated
- Two project docs give contradictory guidance on the same topic (labels, branch naming, commit format)
- Inter-citing markdown corpus has reorganized sections with stale `§`-references across files
- An issue's fix already exists in scripts but docs lag behind

## Verified Workflow

### Quick Reference

```bash
# ── FUTURE IMPROVEMENTS DRIFT ──────────────────────────────────────────────
# Find stale Future Improvements / Future Work across docs
grep -rn "Future Improvements\|Future Work\|Coming Soon\|Planned\|Not Implemented" \
  docs/ --include="*.md" | grep -v "docs/arxiv/"

# Cross-reference adapters listed as Planned vs actual files
ls <project-root>/adapters/

# ── STALE NUMERIC COUNTS ────────────────────────────────────────────────────
# Actual test count
pixi run python -m pytest --collect-only -q tests/ 2>/dev/null | tail -3

# Actual file/agent count
find tests/ -name "test_*.py" | wc -l
ls .claude/agents/*.md | wc -l

# Coverage threshold in pyproject.toml
grep "fail_under" pyproject.toml

# Search ALL markdown files for remaining stale references (critical step)
grep -r "<old_count>" . --include="*.md" --exclude-dir=.git

# ── ECOSYSTEM ROLE DRIFT ─────────────────────────────────────────────────────
# Build alignment matrix — audit all role references
grep -rn "chaos\|resilience testing\|failure injection" README.md CLAUDE.md docs/

# Verify repos against GitHub org API
gh api orgs/<ORG>/repos --paginate \
  --jq '.[] | "\(.name) -- \(.description // "no description")"' | sort

# ── WORKFLOW README AUDIT ────────────────────────────────────────────────────
# Ground truth workflow list
ls .github/workflows/*.yml
ls .github/workflows/*.yml | wc -l

# Find inline duplication
grep -rl "prefix-dev/setup-pixi" .github/workflows/*.yml | wc -l

# ── CONTRADICTION DETECTION ──────────────────────────────────────────────────
# Cross-reference policy between CLAUDE.md and CONTRIBUTING.md
grep -n "label\|Never use" CLAUDE.md CONTRIBUTING.md .claude/shared/pr-workflow.md

# ── CITATION DRIFT (§-REFERENCES) ────────────────────────────────────────────
# List every §-reference across corpus
grep -rEn "[A-Z_]+\.md *§[0-9]+(\.[0-9]+)*" <docs-dir>/ \
  | awk -F'§' '{print $1, "§"$2}' | sort -u

# Extract every §-heading in target docs
grep -rEn "^#{2,4} §[0-9]+(\.[0-9]+)*" <docs-dir>/ | sort -u

# Find unverified arXiv citations
grep -rn 'ASSUMPTION — to validate' <docs-dir>/
```

### Phase 1: Identify the Staleness Pattern

Classify the staleness before acting:

| Pattern | Symptom | Primary Tool |
| ------- | ------- | ------------ |
| Future Improvements drift | Doc says "Planned" but `.py` exists | grep + ls + Read |
| Stale numeric counts | README says N but actual count is M | pytest/find/grep |
| Metric discrepancy | CLAUDE.md ≠ pyproject.toml thresholds | grep both files |
| Agent/file count drift | CLAUDE.md count ≠ `ls .claude/agents/ \| wc -l` | ls + grep |
| Ecosystem role drift | External docs describe wrong project role | grep + alignment matrix |
| Multi-file inconsistency | Same table in 3 files, all different | grep across files |
| Workflow README drift | README lists deleted/missing workflows | ls vs README table |
| Doc contradiction | Policy in CLAUDE.md conflicts with CONTRIBUTING | grep policy term |
| Citation §-drift | §-ref in file A points to old §-number in file B | grep §-pattern |
| Implementation lag | Issue fix pre-exists; docs didn't follow | Read pre-commit config |

### Phase 2: Verify Actual Values from Authoritative Sources

**For numeric counts** — always count from code, never from other docs:

```bash
# Registry count (figures, adapters, agents)
grep -c '"fig' scripts/generate_figures.py
ls .claude/agents/*.md | wc -l
find tests/ -name "*.yaml" | wc -l

# For code registries, use AST for accuracy
python3 -c "
import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
for node in ast.walk(tree):
    if isinstance(node, ast.List):
        print(f'Entries: {len(node.elts)}')
" scripts/generate_tables.py
```

**For Future Improvements** — verify each claimed-future item in source:

```bash
ls <project-root>/adapters/          # Does the file exist?
head -3 <project-root>/adapters/<name>.py   # Is it real code, not stub?
grep -n "def <function>" <project-root>/<module>.py
```

**For ecosystem role** — use GitHub API as truth for repo listings:

```bash
gh api orgs/<ORG>/repos --paginate \
  --jq '.[] | "\(.name) -- \(.description // "no description")"' | sort
```

**For citations** — WebFetch every arXiv ID against its abstract page:

```text
https://arxiv.org/abs/<NNNN.NNNNN>
```

Verify returned title and first author match the citation entry's claim.

### Phase 3: Apply Minimal Targeted Fixes

**Rule**: Use `Edit` tool with exact string replacement. Never rewrite whole sections.
Use `replace_all: true` when the same stale phrase appears multiple times.

#### Future Improvements fixes

- Update `Planned` → `Implemented` in adapter/component status tables
- Add missing components to ASCII diagrams
- Move "implemented but not yet integrated" items out of "Future Work" with accurate status note
- Remove stale numbered list item; renumber if needed
- Add proper documented section near the component it belongs to

#### Count fixes

Use round numbers with `+` suffix for forward-compatibility in README:

```text
"2026+ tests"   →  "3,000+ tests"
"115+ test files"  →  "127+ test files"
```

Use exact counts (no `+`) for deterministic values like YAML subtest counts.

#### Metric discrepancy fixes

```text
CLAUDE.md: "73%+ test coverage"  →  "75%+ test coverage"
--cov=scylla/scylla  →  --cov=scylla
```

#### Agent count fixes

```bash
# Update CLAUDE.md in two places
# Quick Links section: "- N agents" → "- M agents"
# Agent Hierarchy section: "All N agents" → "All M agents"
```

Annotate tracking docs with strikethrough rather than deleting entries:

```markdown
- ~~`.claude/agents/deleted-agent.md`~~ — converted to skill
```

#### Ecosystem role fixes

1. Build alignment matrix (see template in Results & Parameters)
2. Decide: update docs or add code (update docs when zero implementation exists for stale claim)
3. Make minimal doc fix — often only ONE bullet needs updating
4. Create ADR in `docs/dev/adr/`
5. Add drift-detection tests (see template in Results & Parameters)
6. File cross-repo issues for external docs you cannot PR directly

#### Multi-file ecosystem sync

Apply identical table to all locations. Consistency rules:

- Same column headers: `Repository | Role`
- Same descriptions for same repo across all files
- Mark current project with `(this project)` suffix

#### Workflow README audit

| Finding | Action |
| ------- | ------ |
| File in README but not on disk | Remove from README |
| File on disk but not in README | Add to README (read first 20 lines for `name:` and `on:`) |
| Filename mismatch | Correct the filename |

Add shell command in README so future readers can verify without trusting hardcoded count:

```markdown
`ls .github/workflows/*.yml | wc -l`
```

#### Post-Migration README Cleanup

Use when a prior consolidation pass migrated workflow steps to composite actions but left the
README describing the old inline pattern. Effort: ~15 min, low-risk (documentation only).

**Step 1 — Verify migration is complete before touching README:**

```bash
# Should return 0 results if migration is complete
grep -rn "prefix-dev/setup-pixi" .github/workflows/*.yml | grep -v README | wc -l

# Positive check — verifies new composite action pattern is present (not just absence-check)
grep -rn "uses: ./.github/actions/setup-pixi" .github/workflows/*.yml | wc -l
```

If the inline pattern is still present in `.yml` files, do the workflow migration first.

**Step 2 — Find all stale prose in the README:**

```bash
grep -n "inline\|Not Yet Migrated\|Remaining Duplication\|no composite action" .github/workflows/README.md
```

There are typically 6 stale locations in a post-migration README:

1. Individual workflow description bullets — e.g. "Uses inline `prefix-dev/setup-pixi`"
2. "Remaining Duplication" section — lists workflows as not-yet-migrated
3. "Common Patterns > Composite Actions" — says no composite actions exist
4. "Pixi-Based Environment Setup" examples — shows old inline YAML snippet
5. "Adding New Workflows" checklist — tells contributors to add to the duplication table
6. Audit quick-reference commands — grep command checks for inline usage count

**Step 3 — Apply targeted edits using `replace_all: true`** for phrases that appear multiple times.

#### Contradiction resolution

Authority order: `CLAUDE.md` > `.claude/shared/pr-workflow.md` > `CONTRIBUTING.md`

Edit only the file(s) that are wrong. Never modify the canonical source.

#### Citation §-drift repair

When reorganizing a document's §-numbering, produce a mapping table BEFORE renaming:

```text
| Old §-number | New §-number | Notes                       |
| ------------ | ------------ | --------------------------- |
| §6.2.2       | §2.2         | Layer-type rule for Linear  |
| §6.4         | §7           | Promoted to top-level       |
```

Apply via global find-replace across all citing files in one commit.

#### Implementation-lag fixes

```bash
# Confirm fix exists before writing any new code
ls scripts/<wrapper>.sh
grep -A3 "id: <hook>" .pre-commit-config.yaml
ls docs/dev/<topic>.md
```

If all three exist, only docs need updating (2 targeted `Edit` calls typically sufficient).

### Phase 4: Validate, Commit, and PR

```bash
# Confirm only intended files changed
git diff --stat

# Run pre-commit (runs markdownlint automatically)
pre-commit run --all-files

# Commit (doc-only change)
git add <changed-files>
git commit -m "docs(<scope>): <description>

Refs #<issue>"

git push -u origin <branch>
gh pr create --title "docs(<scope>): <description>" --body "Refs #<issue>"
gh pr merge --auto --squash
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Running `just pre-commit-all` | Used `just` command runner | `just` not in PATH | Use `pre-commit run --all-files` directly |
| Expecting mojo-format to pass | Ran full pre-commit suite | `mojo` binary requires GLIBC 2.32+; host has older version | Pre-existing env limitation; only non-Mojo hooks matter for doc-only changes |
| Deleting tracking doc entries outright | Removed lines for deleted agents | Lost historical context of what was converted | Use strikethrough annotation: `~~file~~` — converted to skill |
| `pixi run npx markdownlint-cli2` pre-validation | Run markdownlint before committing | `npx` not in PATH; pixi env setup takes > 2 min | Use `git commit` — pre-commit hook runs markdownlint and gives precise line numbers |
| `find ~/.pixi -name "markdownlint*"` | Locate markdownlint outside pixi | Ran for > 3 min without completing | Use `git commit` to trigger hook directly |
| Closing ` ``` ` fences with `text` on same line | Kept ` ```text ` style from original README | MD031/MD040 lint failures | Always use bare ` ``` ` for closing fences |
| Editing `.claude/agents/` in worktree | Update agent refs in restricted paths | Permission denied in don't-ask mode | Note for follow-up; don't block on restricted paths |
| Edit before Read | Attempted Edit on files not yet read | Edit tool requires prior Read | Always Read target files before editing |
| Fixing only the primary file for stale counts | Updated README but not docs/ or references/ | Stale occurrences survived in `docs/analysis-prompt.md` and `references/notes.md` | Always run project-wide grep after fixing primary file |
| Two prior review cycles on citation corpus | Per-file reviewers passed individual entries | Could not see cross-document §-drift or intra-author arXiv swaps | Both failure modes need cross-corpus reviewer, not per-file reviewer |
| Genre-tag shorthand for citations | Used "energy-based" descriptors instead of full titles | Swapped IDs were invisible to downstream readers | Always include full titles in citation entries |
| Pattern-based scrubs for citation residue | Ran text-pattern scrubs to find stale refs | Cannot detect §-number drift or ID-to-title swaps (both are structural, not textual) | Cross-doc citation drift needs structural audit: global mapping tables + WebFetch per ID |
| Skill invocation for commit | Used `Skill commit-commands:commit-push-pr` | Permission denied in don't-ask mode | Fall back to manual `git add && git commit && git push && gh pr create` |
| Removing `--label` from CONTRIBUTING without checking `.claude/shared/` | Only grepped CONTRIBUTING.md | Third file (`.claude/shared/pr-workflow.md`) could also contain the contradiction | Always verify all related files before declaring fix complete |
| Using `replace_all: false` for repeated phrases | First bullet tried individually | Context string not unique — edit tool reported string not found | When the same phrase appears multiple times, use `replace_all: true` |
| Updating SHA-pinning documentation examples | Considered replacing `prefix-dev/setup-pixi@v0.9.3` in the SHA-pinning examples section | Those lines are intentional documentation of the pinning pattern, not actual workflow steps | Always check whether a reference is in a concept-explaining code example block vs. a step to be migrated |

## Results & Parameters

### Commit Format

| Pattern | Commit Type |
| ------- | ----------- |
| Future Improvements fix | `docs(design): audit and fix stale Future Improvements entries` |
| Count/metric fix | `docs(readme): fix test counts, file counts, and --cov path typo` |
| Agent count fix | `fix: update stale agent count references (N → M agents)` |
| CLAUDE.md status fix | `fix(docs): Update CLAUDE.md 'Current Status' to reflect operational state` |
| Workflow README | `docs(ci): update workflow README to reflect post-consolidation inventory` |
| Contradiction fix | `fix(docs): Remove --label flag from CONTRIBUTING.md PR example` |
| Ecosystem sync | `docs(ecosystem): update repo listing from N to M repos` |
| Implementation lag | `docs(CLAUDE.md): update <tool> hook documentation for <fix-description>` |

### Drift-Detection Test Pattern (Python)

```python
"""Drift-detection tests for ecosystem role description."""
from pathlib import Path
import re
import pytest

PROJECT_ROOT = Path(__file__).parents[3]

DOC_FILES = [
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "CLAUDE.md",
    PROJECT_ROOT / "docs" / "design" / "architecture.md",
]

FORBIDDEN_PHRASES = [
    r"chaos\s+(?:engineering|testing)",
    r"inject\s+failures",
    r"resilience\s+testing",
]

@pytest.mark.parametrize("doc_path", [p for p in DOC_FILES if p.exists()])
@pytest.mark.parametrize("pattern", FORBIDDEN_PHRASES)
def test_no_stale_claims(doc_path: Path, pattern: str) -> None:
    content = doc_path.read_text()
    matches = re.findall(pattern, content, re.IGNORECASE)
    assert not matches, f"{doc_path.name} contains forbidden phrase: {matches}"
```

### Ecosystem Alignment Matrix Template

| Location | Current Description | Accurate? | Action |
| -------- | ------------------- | --------- | ------ |
| `README.md` | "..." | Yes/No | Update/No change |
| `CLAUDE.md` | "..." | Yes/No | Update/No change |
| External repo | "..." | No | File cross-repo issue |

### Citation Entry Template

```text
**Citation:** Author1, Author2 et al. "Full Paper Title." *Venue*, vol/issue, year. DOI/URL.
**arXiv ID** (if applicable): <NNNN.NNNNN>
**Status:** [verified-via-WebFetch on YYYY-MM-DD] | [ASSUMPTION — to validate]
```

### §-Reorganization Mapping Table Template

When reorganizing section numbering, produce this BEFORE renaming sections:

```text
| Old §-number | New §-number | Notes                       |
| ------------ | ------------ | --------------------------- |
| §6.2.2       | §2.2         | Layer-type rule for Linear  |
| §6.3.1       | §4.1         | Energy update equation      |
| §6.4         | §7           | Promoted to top-level       |
```

### Workflow README Table Template

```markdown
| Workflow | Trigger | Purpose | Duration |
| -------- | ------- | ------- | -------- |
| **Category** | | | |
| [name.yml](#anchor) | PR, push main | Short description | < N min |
```

### Key Observations

1. **ASCII diagrams and directory listings go stale faster than tables** — when a component
   is added, the status table may be updated but the diagram is forgotten. Always check both.

2. **"Implemented but not integrated" is a valid intermediate state** — don't conflate
   "function exists" with "fully integrated". Document the distinction accurately.

3. **Use `+` suffix for forward-compatibility on counts** — prefer `3,000+` over `3,016`
   for test counts in README. Exact numbers go stale; round numbers with `+` remain accurate.

4. **Exact subtest counts should not have `+`** — deterministic counts (sum of tier table = 120)
   should be exact; remove the `+` to avoid implying uncertainty.

5. **Search ALL markdown files after fixing the primary file** — stale counts commonly survive
   in `docs/analysis-prompt.md` and `references/notes.md` after README is fixed.

6. **When implementation is overwhelmingly one thing, update docs** — don't add code
   to match stale claims when the implementation contradicts them with 69K+ lines.

7. **Both citation failure modes survive multi-reviewer rotation** — §-drift and arXiv
   ID-to-title swaps need cross-corpus audit roles, not per-file reviewers.

8. **Pre-commit hook is the authoritative linter** — use `git commit` to trigger it
   rather than running `npx markdownlint-cli2` directly.

9. **Worktrees may already have partial fixes** — always read files before editing to
   avoid re-applying changes that a prior commit already landed.

10. **`--cov` path must match installed package name** — `--cov=scylla/scylla` is wrong
    when the package is installed as `scylla`; check `pyproject.toml` to confirm.

11. **MD029 ordered lists reset per logical group** — markdownlint requires each new
    independent numbered list to start at 1. Two separate lists (e.g., "PR/push jobs" and
    "weekly jobs") each start at 1 independently; do not continue numbering across groups.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectScylla | Issues \#880, \#759, \#1112, \#1477, \#1503, \#1507 | Future Improvements audits, metric fixes, count fixes, ecosystem role reconciliation |
| ProjectOdyssey | Issues \#3344, \#3365 | Workflow README audit, implementation-lag doc sync |
| ProjectOdyssey | PR \#3320 (issue \#3145) | Stale agent count fix after agents converted to skills |
| ProjectScylla | Issues \#753, \#758 | CLAUDE.md status fix, doc contradiction resolution |
| mvillmow/Random | Predictive-Coding-in-Mojo Phase 0 | Cross-doc citation drift: 8 stale §-refs, 2 arXiv ID swaps caught |
| ProjectOdyssey | Issue (post-migration), PR \#4847 | README-only sync after pixi composite action migration; 26 insertions, 45 deletions |
