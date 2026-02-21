# Skill: Sync Stale "Future Improvements" With Implementation

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-20 |
| Issue | #759 |
| PR | #877 |
| Category | documentation |
| Objective | Remove "Add container health checks" from `docs/design/container-architecture.md` Future Improvements and add a proper documented section since `docker/Dockerfile` already implemented it |
| Outcome | Success — documentation now matches implementation, PR created with auto-merge |

## When to Use

Trigger this skill when:

- A "Future Improvements" or "TODO" section in docs lists a feature that has already been shipped
- Code review / issue triage finds a doc that calls something "planned" but a quick `grep` shows it exists in source
- A Dockerfile, config, or script gains a new capability but only the code is updated, not the narrative docs
- CI or contributors are confused because docs say "not yet implemented" but the feature works

## Verified Workflow

### 1. Confirm the feature is implemented

```bash
# Grep for the actual implementation
grep -n "HEALTHCHECK\|health" docker/Dockerfile

# Read the relevant lines
# docker/Dockerfile:116-117 showed the HEALTHCHECK directive with all parameters
```

### 2. Read the stale documentation

```bash
# Identify the Future Improvements section
grep -n -i "health\|future" docs/design/container-architecture.md
```

Confirm the stale entry exists (e.g. line 249: `5. **Health checks**: Add container health checks`).

### 3. Add a proper documented section to the main body

Insert a subsection **near the component it belongs to** (e.g., under "Docker Image" for a Dockerfile feature).
Document all relevant parameters in a table:

```markdown
### Health Checks

The image includes a Docker health check that verifies the `scylla` package is importable:

\`\`\`dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c 'import scylla; print("OK")' || exit 1
\`\`\`

| Parameter | Value | Description |
|-----------|-------|-------------|
| `--interval` | 30s | Time between health checks |
| `--timeout` | 10s | Maximum time to wait for a check to complete |
| `--start-period` | 5s | Grace period before health check failures count |
| `--retries` | 3 | Consecutive failures before marking unhealthy |

Container orchestration platforms (Kubernetes, Docker Swarm) use this to detect and replace unhealthy containers.
```

### 4. Remove the stale "Future Improvements" entry

Edit the numbered list, removing only the item that was just implemented. Renumber if needed.

### 5. Scan remaining Future Improvements for other stale entries

Per the issue instructions: "also check the rest of the Future Improvements section to see if any other items have already been implemented." For this issue, all four remaining items (multi-platform, layer caching, resource limits, volume optimization) were genuinely unimplemented.

### 6. Commit, push, and PR

```bash
git add docs/design/container-architecture.md
git commit -m "fix(docs): Mark container health checks as implemented in container-architecture.md

- Add Health Checks subsection to Components documenting the HEALTHCHECK directive
  with parameters (interval=30s, timeout=10s, start-period=5s, retries=3) and CMD
- Remove stale 'Add container health checks' item from Future Improvements section

Closes #<issue>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push -u origin <branch>

gh pr create \
  --title "fix(docs): Mark container health checks as implemented in container-architecture.md" \
  --body "$(cat <<'EOF'
## Summary
- Added Health Checks subsection documenting the existing HEALTHCHECK directive
- Documented all parameters in a reference table
- Removed stale 'Add container health checks' from Future Improvements

Closes #<issue>
EOF
)"

gh pr merge --auto --rebase
```

## Failed Attempts

**Skill tool denied**: Attempted `commit-commands:commit-push-pr` skill but it was blocked by `don't ask mode`. Fell back to direct Bash git commands — this is the correct fallback and works identically.

**No other failures**: Task was purely a documentation edit. Pre-commit hooks passed on first attempt since only Markdown was modified (Python linters skipped).

## Results & Parameters

### Changes made to `docs/design/container-architecture.md`

| Location | Before | After |
|----------|--------|-------|
| After "Building the image" bash block | Nothing | New "### Health Checks" subsection with code block + parameter table |
| Future Improvements list | 5 items including "Health checks: Add container health checks" | 4 items (health checks removed) |

### Pre-commit hook behavior for Markdown-only changes

Skipped (no Python files modified):
- Ruff Format Python, Ruff Check Python, Mypy Type Check Python
- Check Type Alias Shadowing, Validate Model Config Naming
- Check Model Config Filename/model\_id Consistency
- YAML Lint, ShellCheck

Passed:
- Markdown Lint
- Trim Trailing Whitespace, Fix End of Files, Check for Large Files, Fix Mixed Line Endings

### Key insight: always check all Future Improvements items

When the issue asks to check whether other Future Improvements are stale, do it systematically — grep for each item in the actual source files before concluding they are still future work. For this issue, the remaining 4 items were confirmed unimplemented by checking Dockerfile, wrapper scripts, and CI configs.
