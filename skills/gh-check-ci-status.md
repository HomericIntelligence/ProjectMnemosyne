---
name: gh-check-ci-status
description: Check CI/CD status of a pull request including workflow runs and test
  results
category: ci-cd
date: 2026-05-28
version: 1.1.0
verification: verified-ci
history: gh-check-ci-status.history
---
# Check CI Status

Verify CI/CD status of a pull request and investigate failures.

## Overview

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2025-12-30 | Efficiently monitor and debug CI status | Faster identification of CI failures |

## When to Use

- (1) Verifying PR checks are passing before merge
- (2) Investigating CI failures
- (3) Monitoring long-running CI jobs
- (4) Checking before pushing changes
- (5) Constructing or validating a `gh ... --json <fields>` field list for automation
  (the valid field set differs per subcommand — get it wrong and gh rejects the
  entire call non-zero)

## Verified Workflow

1. **Check status**: Run `gh pr checks <pr>` to see all checks
2. **Identify failures**: Look for X (failed) or O (pending)
3. **View logs**: Use `gh run view` to see failure details
4. **Fix locally**: Reproduce issue locally and test
5. **Push fix**: Commit and push changes
6. **Verify**: Watch CI with `--watch` flag

## Results

Copy-paste ready commands:

```bash
# Check PR CI status
gh pr checks <pr>

# Watch CI in real-time
gh pr checks <pr> --watch

# Get detailed status
gh pr view <pr> --json statusCheckRollup

# View failed logs
gh run view <run-id> --log-failed

# Rerun failed checks
gh run rerun <run-id>
```

### gh pr checks --json schema (valid fields)

`gh pr checks <pr> --json` has a **narrow, easy-to-get-wrong schema**. The ONLY
valid `--json` fields are:

```text
bucket, completedAt, description, event, link, name, startedAt, state, workflow
```

There is **NO `status`, NO `conclusion`, and NO `required`** field on
`gh pr checks`. Those belong to a *different* gh surface (e.g.
`gh api .../check-runs` or `gh pr view --json statusCheckRollup`). Requesting any
invalid field makes gh reject the **entire** call with
`Unknown JSON field: "<x>"` and exit non-zero.

Field semantics that matter:

- **`state`** — per-check state, e.g. `SUCCESS`, `FAILURE`, `PENDING`,
  `SKIPPED`, `CANCELLED`.
- **`bucket`** — coarse rollup, one of `pass`, `fail`, `pending`, `skipping`,
  `cancel`. This is the field to map "did it conclude? did it pass?" from:

  | bucket | meaning |
  | -------- | --------- |
  | `pass` | success |
  | `fail` | failure |
  | `cancel` | failure |
  | `skipping` | skipped |
  | `pending` | not concluded yet |

To read CI status reliably from automation, request only `state,bucket` (plus
`name,workflow` for identification):

```bash
gh pr checks <pr> --json name,workflow,state,bucket
```

### Validate --json field names before shipping

The valid field set differs per subcommand (`gh pr view` has
`statusCheckRollup`; `gh pr checks` does NOT have `status`/`conclusion`/
`required`). Query the real schema once by passing a bogus field — gh prints the
valid set in the error:

```bash
# Prints "Unknown JSON field: ... Available fields: <the real list>"
gh pr checks 1 --json __bogus__ 2>&1 | sed -n 's/.*Available fields://p'
# Or just read the per-subcommand help:
gh pr checks --help
```

In test suites, add a guard test asserting the requested `--json` field list is
a **subset** of the known-valid schema set for that subcommand. (The original
bug shipped because every unit test *mocked* the gh wrapper and fabricated the
output dict, so the wrong field list was never exercised against real gh.)

### Automation: deterministic CLI errors must NOT be retried

A deterministic CLI-arg error (`Unknown JSON field`, `invalid argument`,
`unknown flag`) is **non-transient** — it will fail identically on every retry.
Classify it **fail-fast**, never transient:

- Retrying a deterministic error is pure harm — it wastes calls and, worse, each
  failure counts toward shared circuit breakers.
- Real incident (ProjectHephaestus): an automation loop called
  `gh pr checks <pr> --json name,status,conclusion,workflow,required`. Every
  call failed with `Unknown JSON field: "status"`, was misclassified as
  *transient*, retried, and each failure counted toward a `gh_cli` circuit
  breaker. After 5 consecutive failures the breaker OPENED, and ALL remaining
  work items then failed instantly (`0 successful, 10 failed`) — one wrong field
  name bricked the entire batch.

### Status Indicators

- `PASS` - Check passed
- `FAIL` - Check failed
- `PENDING` - In progress
- `SKIPPED` - Check was skipped

### Common CI Failures

**Pre-commit issues** (formatting/linting):
```bash
just pre-commit-all  # Fix locally
git add . && git commit --amend --no-edit
git push --force-with-lease
```

**Test failures**:
```bash
mojo test tests/          # Run locally
pytest tests/             # Python tests
# Fix code and retest
```

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | `gh pr checks <pr> --json name,status,conclusion,workflow,required` | gh rejected the whole call with `Unknown JSON field: "status"` (also no `conclusion`/`required`) and exited non-zero | `gh pr checks --json` valid fields are `bucket,completedAt,description,event,link,name,startedAt,state,workflow`; read status from `state,bucket`. `status`/`conclusion`/`required` belong to other gh surfaces. |
| 2 | Classified the `Unknown JSON field` error as transient and retried it in an automation loop | Deterministic error failed identically every retry; 5 consecutive failures tripped the `gh_cli` circuit breaker, then ALL remaining items failed instantly (`0 successful, 10 failed`) | Classify deterministic CLI-arg errors (`unknown json field`, `invalid argument`, `unknown flag`) as non-transient / fail-fast — never retry them; they only waste calls and trip shared circuit breakers. |
## Error Handling

| Problem | Solution |
| --------- | ---------- |
| No checks found | PR may not trigger CI (check workflow) |
| Pending forever | Check logs for stuck jobs |
| Auth error | Verify `gh auth status` |
| API rate limit | Wait or authenticate properly |

## Pre-Merge Verification

Before merging:

- [ ] All required checks passing
- [ ] No pending checks
- [ ] Latest commit has checks
- [ ] Branch up-to-date with base

```bash
gh pr checks <pr>          # All passing?
gh pr view <pr>            # Up-to-date?
gh pr diff <pr>            # Changes correct?
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | CI status monitoring workflow | Generic patterns applicable to any GitHub project |

## References

- See verify-pr-ready for complete pre-merge checklist
- See analyze-ci-failure-logs for debugging failures
- GitHub CLI docs: https://cli.github.com/manual/gh_pr_checks
