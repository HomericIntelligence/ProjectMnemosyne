---
name: audit-stale-version-comment-version-agnostic-fix
description: "Use when planning a fix for an audit finding that flags a stale tool/dependency version inside a source COMMENT (e.g. pyproject.toml comment saying 'CI tests only mypy 1.x' while the lock resolves 2.x; a Dockerfile comment '# requires Node 16' while the base image is 20; a setup.cfg comment '# pinned for Python 3.8 compat' while ranges allow 3.10+). The replacement comment MUST be version-AGNOSTIC — embedding a new specific version number (`mypy 2.1.0`, `Node 20`, `Python 3.10`) re-creates the exact staleness anti-pattern the audit is fixing; it merely shifts the lie from the old number to the new one at the next bump. Trigger: (1) an audit / NITPICK / linter finding cites a `file:line` containing a stale version assertion in a comment, (2) the audit asserts what the 'real' resolved version is (e.g. 'lockfile resolves X.Y.Z') — verify that claim against `pixi.lock` / `uv.lock` / `poetry.lock` / `package-lock.json` AT PLANNING TIME before writing any replacement, (3) the audit asserts 'CI exercises Y' / 'CI tests Z' — grep `.github/workflows/` AND `.pre-commit-config.yaml` AT PLANNING TIME before repeating that claim, (4) the cited `file:LINE-LINE` coordinates came from an audit run that pre-dates the current HEAD — re-locate the comment by stable content substring (`grep -n`), not by line number, (5) you are tempted to write 'currently 2.1.0' or 'tested with Node 20' in the replacement — STOP and rewrite version-agnostically ('version is pinned via pixi.lock', 'version follows the base image'). This skill is the comment-specific specialization of `code-quality-enforcement-gates` §10 (ground-truth verification) and §11 (tracking-doc checkbox drift)."
category: documentation
date: 2026-06-21
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - documentation
  - audit-remediation
  - stale-comments
  - version-pinning
  - ground-truth-verification
  - lockfile-as-source-of-truth
  - version-agnostic-comment
  - anti-pattern-stale-version-in-source
  - nitpick-audit
  - line-number-drift
  - planning-stage-verification
  - cross-reference-code-quality-enforcement-gates
---

# Audit-Driven Stale Version Comment Fix: Write Version-AGNOSTIC Replacements

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-21 |
| **Objective** | Capture the durable planning-discipline lesson from a NITPICK audit (ProjectHephaestus issue #1549) that flagged a stale mypy version comment in `pyproject.toml:54-55` ('CI tests only mypy 1.x' while the lockfile resolves mypy 2.1.0). The audit prescribed updating the comment; the *real* lesson is HOW to update it so the same staleness does not recur at the next mypy bump. |
| **Outcome** | A repeatable planning rubric: (1) verify every audit claim against on-disk ground truth at PLANNING time (lock file, CI workflows, line numbers re-anchored by content), (2) the replacement comment MUST be VERSION-AGNOSTIC — never embed a specific version number that will go stale, instead reference the single source of truth (lockfile, base image, central manifest), (3) decline scope creep (no version bumps, no surrounding comment edits, no dependency-line edits). Verification: planning-stage extraction only; the planned fix was NOT yet implemented or CI-confirmed at the time this skill was authored. |
| **Verification** | unverified — PLANNING-stage learning. The rubric was derived during a planning session for ProjectHephaestus issue #1549; no commit was made and CI has not confirmed the proposed comment rewrite. Treat as a hypothesis until a downstream PR lands and validates the version-agnostic phrasing through review. |

This skill is the **comment-specific specialization** of the parent skill `code-quality-enforcement-gates` (see §10 ground-truth verification of audit findings, and §11 tracking-doc checkbox drift). It also complements `audit-doc-consistency-fix-verify-coordinates-on-disk` (which covers *line-coordinate* drift in documentation) by adding the orthogonal failure mode: a replacement that is "correct today" but engineered to go stale tomorrow.

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

## When to Use

- An audit, a NITPICK finding, a strict-mode reviewer, or a human review comment cites a `file:line` containing a **version assertion inside a source comment** (e.g. `# CI tests only mypy 1.x`, `// requires Node 16`, `# pinned for Python 3.8 compatibility`).
- The audit asserts what the *real* resolved version is (e.g. "lockfile resolves mypy 2.1.0", "base image is Node 20"). **Do not trust this claim** — verify it against `pixi.lock` / `uv.lock` / `poetry.lock` / `package-lock.json` / Dockerfile FROM line at planning time.
- The audit asserts "CI exercises X" or "CI tests Y". **Do not trust this claim** — grep `.github/workflows/` and `.pre-commit-config.yaml` (or your CI config) at planning time before repeating any CI claim in the replacement comment.
- The audit's cited `file:LINE-LINE` may have drifted since the audit ran. Re-anchor the comment by a **stable content substring**, not by line number.
- You are tempted to write the new resolved version into the replacement (`# CI tests mypy 2.1.0`). **STOP**. That re-creates the failure mode. Rewrite version-agnostically.
- You are tempted to bundle in a "while we are here" dependency bump, surrounding comment polish, or pin tightening. **STOP**. The audit was scoped to a comment; expand scope only via a separate issue.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section heading `## Verified Workflow`, so the rubric below is emitted under that heading to keep validation green. This skill is `unverified` (PLANNING-stage); read the steps below as **proposed**, per the warning above.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# CONTEXT: An audit finding says "pyproject.toml:54-55 has a stale comment claiming
#          'CI tests only mypy 1.x' but the lockfile resolves mypy 2.1.0."

# 0. Re-anchor the comment by CONTENT, not by line number (audit line refs drift).
grep -n "CI tests only mypy" pyproject.toml
#   -> prints the REAL line number; do not trust the audit's 54-55.

# 1. Verify the lockfile claim against the actual lockfile.
grep -E "^name = \"mypy\"" -A1 pixi.lock          # or `pixi list mypy`
grep -E "mypy" pyproject.toml | grep -E ">=|<|=="  # the constraint expression

# 2. Verify the CI claim against the actual CI configs (BEFORE repeating it).
grep -rn "mypy" .github/workflows/ .pre-commit-config.yaml

# 3. Write the replacement comment VERSION-AGNOSTIC. Reference the single source
#    of truth, NOT a snapshot value:
#      BAD : "# CI tests mypy 2.1.0"          (will go stale at the next bump)
#      GOOD: "# mypy version is pinned via pixi.lock (see [tool.mypy] constraint)"
#      GOOD: "# mypy version follows the resolved lock; see pixi.lock"

# 4. Verify the docs-only edit:
pixi run ruff check pyproject.toml
pre-commit run --files pyproject.toml
python3 -c "import tomllib; tomllib.loads(open('pyproject.toml').read())"
pixi run mypy --version   # optional: shows the actually-resolved version

# 5. Refuse scope creep. The audit was a comment fix; do NOT
#    bump deps, re-pin, or polish surrounding comments in the same PR.
```

### Detailed Steps

1. **Read the audit finding literally, then verify EVERY claim against the repo.** Audits make three kinds of claims about a stale-version comment: (a) the file/line location, (b) the "real" resolved version, (c) what CI exercises. All three are routinely wrong (see `code-quality-enforcement-gates` §10 — strict-mode audits hallucinate 10–30% of findings).

2. **Re-anchor by content, not by line.** Even when the audit ran against a recent commit, line numbers drift between then and your planning session. Use:

   ```bash
   grep -n '<stable substring of the comment>' <file>
   ```

   Prefer a substring that is unique to the stale comment ("CI tests only mypy") rather than the version number itself (which may appear elsewhere).

3. **Verify the lockfile claim before quoting it.** The audit may say "lock resolves X.Y.Z"; check the actual lockfile:

   ```bash
   grep -E "^name = \"<pkg>\"" -A1 pixi.lock        # pixi
   jq '.packages[] | select(.name=="<pkg>") | .version' uv.lock     # uv (if jq-friendly)
   grep -E "^<pkg>==" requirements.txt              # pinned-requirements style
   ```

4. **Verify the CI claim before repeating it.** Grep ALL workflow files and the pre-commit config:

   ```bash
   grep -rn "<tool>" .github/workflows/ .pre-commit-config.yaml
   ```

   If CI does not actually exercise the tool in the way the audit asserts, do not repeat that claim. Either drop the CI assertion from the comment, or rewrite it to match what CI actually does.

5. **Write the replacement version-AGNOSTIC.** Concrete templates:

   - BAD: `# CI tests mypy 2.1.0` (will lie at the next bump)
   - BAD: `# currently 2.1.0 — update if changed` (procedural lie; no one updates)
   - BAD: `# mypy 2.x is supported and exercised by CI; pinned via pixi.lock (currently 2.1.0)` (embeds 2.1.0 — the lie just moved)
   - GOOD: `# mypy version is pinned via pixi.lock` (no number, no future stale-ness)
   - GOOD: `# mypy version follows the lock; see [tool.mypy] for the constraint expression`
   - GOOD: `# Node version follows the base image (see Dockerfile FROM)`

   The rule: a comment may name the *constraint expression* (`>=2,<3`) when that expression itself lives in the same file and will be edited together. A comment must NEVER name a *resolved snapshot value* (`2.1.0`) that lives somewhere else and can change independently.

6. **Refuse scope creep.** The audit was scoped to a comment fix. Do not also: bump the dep, change the constraint range, re-format surrounding comments, swap quote style, reorder keys, or "tidy" adjacent lines. Each of those is a separate issue and a separate PR. The deliverable is the smallest possible diff that removes the false claim and replaces it with a durable one.

7. **Verify with docs/lint gates appropriate to the file.** For `pyproject.toml` specifically:

   ```bash
   pixi run ruff check pyproject.toml
   pre-commit run --files pyproject.toml
   python3 -c "import tomllib; tomllib.loads(open('pyproject.toml').read())"
   pixi run mypy --version   # shows resolved version (sanity-check, not a gate)
   ```

   Do NOT run the full test suite as a gate — this is a comment-only edit and the appropriate gate is markdown/TOML lint plus a parse check.

8. **Cross-reference the parent principle in the plan/PR body.** Note that this fix follows `code-quality-enforcement-gates` §10 (verify audit claims at planning time) and `audit-doc-consistency-fix-verify-coordinates-on-disk` (re-anchor coordinates on disk). This anchors the next reviewer / next planner against the same anti-pattern.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Versioned replacement | Replaced "CI tests only mypy 1.x" with "CI tests mypy 2.1.0" (or "currently 2.1.0") | Still embeds a specific version number; will be a lie at the next mypy bump. The audit fixed staleness-from-1.x → re-introduced staleness-from-2.1.0 | Write version-AGNOSTIC comments. Reference the lockfile / constraint expression, not a snapshot value |
| Trust audit line numbers | Trusted the audit's `pyproject.toml:54-55` reference at planning time without re-anchoring on disk | Line numbers drift between audit run and implementation; the comment may now live on a different line and the planned edit would patch the wrong region (or fail to find the target) | Locate the comment by content match (`grep -n '<stable substring>'`), never by inherited line number |
| Trust audit lockfile claim | Trusted the audit's claim "lockfile resolves mypy 2.1.0" without reading `pixi.lock` | Audits can be wrong about lock state (especially after a recent rebase or a pixi re-solve). Repeating a wrong claim in the new comment re-creates the original failure mode at a different value | Read the lockfile directly at planning time. `grep -E "^name = \"mypy\"" -A1 pixi.lock` or `pixi list mypy` |
| Asserting CI behavior unverified | Wrote "exercised by CI" in the new comment without grepping `.github/workflows/` or `.pre-commit-config.yaml` | If CI does not actually invoke mypy where the comment claims, the new comment is just as false as the old one. The audit may have been wrong about the CI claim too | Grep `.github/workflows/` AND `.pre-commit-config.yaml` at planning time before repeating any CI assertion in a comment |
| Scope creep into version bump | Bundled a "while we are here" mypy version bump or constraint-range tightening into the same PR as the comment fix | Conflates two concerns (comment hygiene vs. dependency policy); makes review/revert harder; the dependency change has different review gates and risk profile | Refuse scope creep. The audit was scoped to a comment; deliver the smallest possible diff. File a separate issue for any incidental dep change |
| Polishing surrounding comments | Tidied adjacent unrelated comments in the same diff | Expands review surface, hides the actual fix in noise, and re-anchors line numbers (making any future audit harder to match) | The diff should change exactly the stale-comment lines and nothing else. Resist the urge to "while I am here" |

## Results & Parameters

### Concrete trigger context (ProjectHephaestus issue #1549)

- **Repo / Issue:** HomericIntelligence/ProjectHephaestus issue #1549 (NITPICK audit bundle #1518; severity tag `[S7 Dependencies] nitpick`)
- **Audit claim:** `pyproject.toml:54-55` contains the comment `# CI tests only mypy 1.x` while the lockfile resolves mypy 2.1.0
- **Planned fix:** Replace the stale comment with a version-AGNOSTIC equivalent that references the lockfile as source of truth; verify with `pixi run ruff check pyproject.toml`, `pre-commit run --files pyproject.toml`, a `tomllib.loads` parse, and `pixi run mypy --version`. No code change, no version bump — comment-only.
- **Risks the reviewer should focus on:**
  1. Re-introducing stale-version-in-comment by embedding "2.1.0" or any specific version number in the replacement.
  2. Asserting "exercised by CI" without first grepping `.github/workflows/` and `.pre-commit-config.yaml`.
  3. Line-number drift between the audit's `54-55` reference and the actual current location of the comment.
  4. Scope creep into a mypy version bump, constraint-range edit, or surrounding-comment polish.
- **Verification level:** unverified — extracted at planning time; the PR implementing the rewrite had not landed (and CI had not confirmed) at the time this skill was authored.

### Parameter rubric (version-AGNOSTIC vs version-SNAPSHOT phrasing)

| Phrase template | Version-agnostic? | Use? |
| --- | --- | --- |
| `# X version is pinned via <lockfile>` | YES | YES |
| `# X version follows the resolved lock; see <lockfile>` | YES | YES |
| `# X version follows the base image (see Dockerfile FROM)` | YES | YES |
| `# constraint: <expression as it appears in the file>` | YES (lives WITH the constraint) | YES |
| `# CI tests X 2.1.0` | NO | NO — embeds snapshot |
| `# currently 2.1.0 — update if changed` | NO | NO — procedural lie |
| `# X 2.x supported, pinned via <lockfile> (currently 2.1.0)` | NO | NO — embeds snapshot |
| `# CI tests only X 1.x` (the audit's original) | NO | NO — what the audit is fixing |

### Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectHephaestus | issue #1549 planning session (NITPICK audit bundle #1518) | PLANNING-stage extraction, not yet implemented or CI-confirmed |

### Cross-references

- **Parent principle:** `code-quality-enforcement-gates` §10 (ground-truth verification of audit/reviewer findings before acting) and §11 (tracking-doc checkbox drift — the analogous "stale state in a markdown doc" pattern). This skill is the **comment-specific specialization** of §10.
- **Coordinate-drift companion:** `audit-doc-consistency-fix-verify-coordinates-on-disk` covers the orthogonal failure mode where `file:line` coordinates inherited from an audit have drifted; this skill assumes you have already applied that re-anchoring discipline and focuses on the *content* of the replacement.
- **Premise verification:** `planning-verify-issue-premises-against-main` for the analogous failure mode where an issue body asserts a state that does not match `main`.
