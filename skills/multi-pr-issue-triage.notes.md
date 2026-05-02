# Multi-PR Issue Triage — Session Notes

Date: 2026-02-25
Project: ProjectScylla
Session: Fix open issues — Health Check, Preflight Check, pip-audit

## Issue triage decisions

| Issue | Decision | Rationale |
| ------- | ---------- | ----------- |
| #909 | Code (PR #1093) | Mock bug + missing BATS regression tests |
| #913 | Code (PR #1096) | N+1 REST scalability problem |
| #914 | Code (PR #1096) | --limit 100 silently misses older PRs |
| #915 | Code (PR #1097) | Missing integration test coverage |
| #918 | Code (PR #1095) | Script buried in test path, hard to reference |
| #919 | Close (not planned) | worktree-sync never creates branches |
| #983 | Code (PR #1094) | pip-audit not in pre-commit hooks |
| #984 | Close (completed) | Already done by PR #869 / security.yml |
| #993 | Close (not planned) | --min-severity approach abandoned; filter_audit.py replaced it |

## Bash operator gotcha

The `:-` vs `-` distinction in bash parameter expansion:
- `${VAR:-default}` — use default if VAR is unset OR empty
- `${VAR-default}` — use default only if VAR is unset

This is critical in test mocks where empty string is a meaningful value
(e.g., "no issues closed" = empty string, not the default value).

## GraphQL mock structure

For BATS mocks, the GraphQL response needs this structure:
```json
{
  "data": {
    "search": {
      "nodes": [
        {
          "number": 42,
          "title": "Fix the bug",
          "state": "MERGED",
          "closingIssuesReferences": {
            "nodes": [{"number": 800}]
          }
        }
      ]
    }
  }
}
```

The `_graphql_check3()` function extracts:
```bash
echo "$result" | jq -c '.data.search.nodes[]'
```

Then per-entry:
```bash
echo "$pr_entry" | jq -e ".closingIssuesReferences.nodes[] | select(.number == ${issue})"
```

## git rev-parse for portable test paths

When tests move or are referenced from different locations, use:
```bash
SCRIPT="$(git -C "$(dirname "$BATS_TEST_FILENAME")" rev-parse --show-toplevel)/scripts/preflight_check.sh"
```

This works regardless of where bats is invoked from.