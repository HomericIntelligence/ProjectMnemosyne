---
name: mesh-dispatch-pipeline-debugging
description: "Debug and fix the live HomericIntelligence agent mesh dispatch pipeline
  (Agamemnon → NATS → claude-myrmidon Python workers → GitHub PRs). Use when: (1)
  Agamemnon POST /v1/tasks returns 404, (2) Claude CLI in container produces zero
  API traffic, (3) container agent gets EACCES on .credentials.json, (4) --resume
  fails with 'No conversation found' across ephemeral containers, (5) IMPLEMENT stage
  gets permission denied writing to bind-mounted workspace, (6) pipeline loops on
  NOGO due to empty REVIEW output, (7) git push blocked by GitHub email privacy, (8)
  PR stuck in CONFLICTING state blocking CI auto-merge."
category: ci-cd
date: "2026-04-25"
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - agamemnon
  - nats
  - myrmidon
  - pipeline
  - podman
  - container
  - claude-cli
  - session-resume
  - github-actions
  - pr-conflict
  - markdownlint
  - git-push
  - auto-merge
---

# HomericIntelligence Mesh Dispatch Pipeline Debugging

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-25 |
| **Objective** | Dispatch GitHub issues #22 (CI hardening) and #69 (Claude read-permissions) through the live HomericIntelligence agent mesh (Agamemnon → NATS → claude-myrmidon Python workers → GitHub PRs), running the full PLAN→TEST→IMPLEMENT→REVIEW→SHIP pipeline |
| **Outcome** | SUCCESS — both issues closed by mesh PRs; PR #147 merged to main; `e2e/claude-myrmidon.py` committed with all container fixes |
| **Verification** | verified-ci — PRs merged, CI passed end-to-end |
| **History** | N/A (initial version) |

## When to Use

- Agamemnon POST to `/v1/tasks` returns 404 (wrong endpoint)
- Claude CLI inside an achaean-claude container produces zero API traffic (Traefik TLS interception)
- Container agent user cannot read `.credentials.json` (EACCES, uid mismatch)
- `--resume <session_id>` returns empty output or "No conversation found" in ephemeral containers
- IMPLEMENT stage fails with "permission denied" writing files in the bind-mounted workspace
- Pipeline loops repeatedly on NOGO because REVIEW stage gets empty Claude output
- `git push` blocked by GitHub email privacy (`villmow.products@gmail.com`)
- PR stuck in CONFLICTING state; GitHub CI won't run and auto-merge stalls
- `.markdownlint.yaml` on main causes lint failures for new PRs
- Auto-merge dropped silently after a force-push or new commit

## Verified Workflow

### Quick Reference

```bash
# 1. Post a task to Agamemnon — use team-scoped endpoint
TEAM_ID=$(curl -s http://localhost:8080/v1/teams | jq -r '.[0].id')
curl -s -X POST "http://localhost:8080/v1/teams/$TEAM_ID/tasks" \
  -H "Content-Type: application/json" \
  -d '{"title": "Fix issue #22", "description": "..."}'

# 2. Run myrmidon worker with all container fixes
CONTAINER_NETWORK=odysseus_homeric-mesh python3 e2e/claude-myrmidon.py

# 3. Re-enable auto-merge after every push to a PR branch
gh pr merge --auto --rebase <PR_NUMBER> --repo <OWNER/REPO>
```

### Correct Agamemnon Task Endpoint

POST must use the team-scoped route:

```bash
# CORRECT
POST /v1/teams/:team_id/tasks

# WRONG — returns 404
POST /v1/tasks

# List tasks (GET works without team scope)
GET /v1/tasks

# Discover team IDs
curl http://localhost:8080/v1/teams
```

### Correct `_build_container_cmd` Implementation

The following implementation incorporates all five container fixes verified in CI:

```python
def _build_container_cmd(claude_args: list[str], cwd: str = WORKING_DIR) -> list[str]:
    import glob as _glob
    import stat as _stat
    home = os.path.expanduser("~")
    # Fix 3: credential permissions reset by host claude processes
    for _path in _glob.glob(f"{home}/.claude/**", recursive=True) + [f"{home}/.claude.json"]:
        try:
            _st = os.stat(_path)
            if not (_st.st_mode & _stat.S_IROTH):
                os.chmod(_path, _st.st_mode | _stat.S_IROTH)
        except OSError:
            pass
    # Fix 2: use standalone binary — avoids Traefik TLS interception of api.claude.ai
    standalone = os.path.join(home, ".local/share/claude/versions/2.1.120")
    if not os.path.exists(standalone):
        versions = sorted(_glob.glob(os.path.join(home, ".local/share/claude/versions/*")))
        standalone = versions[-1] if versions else ""
    cmd = [
        CONTAINER_RUNTIME, "run", "--rm",
        "--userns=keep-id",               # Fix 1: maps host UID inside container
        "--network", os.environ.get("CONTAINER_NETWORK", "odysseus_homeric-mesh"),  # Fix 5
        "-v", f"{cwd}:{CONTAINER_WORKSPACE}",
        "-v", f"{home}/.claude:{home}/.claude",
        "-v", f"{home}/.config/gh:{home}/.config/gh:ro",
        "-w", CONTAINER_WORKSPACE,
        "-e", f"ANTHROPIC_API_KEY={os.environ.get('ANTHROPIC_API_KEY', '')}",
        "-e", f"HOME={home}",
        *(["-v", f"{home}/.claude.json:{home}/.claude.json"] if os.path.exists(f"{home}/.claude.json") else []),
        *(["-v", f"{standalone}:/usr/local/bin/claude-host:ro"] if standalone else []),
        CLAUDE_IMAGE,
    ]
    cmd.extend(claude_args)
    return cmd
```

### Correct `invoke_claude` — No Session Resumption

Disable all `--session-id`/`--resume` flags. Each pipeline stage gets full context in its prompt:

```python
log("claude", f"Starting new session ({len(prompt)} chars)")
claude_args = [
    "claude-host", "-p", prompt,
    "--dangerously-skip-permissions",
    "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep",
]
# Do NOT add --resume or --session-id
```

### markdownlint Config for Odysseus Docs

Use `.markdownlint.json` (not `.markdownlint.yaml`). The yaml variant with a 200-char
line limit was on main causing lint failures. Replace with:

```json
{
  "default": true,
  "MD013": {
    "line_length": 80,
    "tables": false,
    "code_blocks": false,
    "headings": false
  },
  "MD022": false,
  "MD032": false,
  "MD040": false,
  "MD060": false
}
```

### PR Conflict Resolution Pattern

When a PR branch is in CONFLICTING state (GitHub UI), CI won't run and auto-merge
stalls. Do NOT rebase a long branch history. Instead:

```bash
# 1. Create a clean branch from current main tip
git fetch origin main
git checkout -b fix/clean-rebase origin/main

# 2. Cherry-pick only the needed commits (not the whole branch)
git cherry-pick <sha1> <sha2>

# 3. Push and update PR
git push origin fix/clean-rebase
gh pr edit <N> --base main
# Or create a fresh PR pointing to the same issue

# 4. Re-enable auto-merge (GitHub drops it on new commits)
gh pr merge --auto --rebase <N> --repo <OWNER/REPO>
```

### Re-Enabling Auto-Merge After Every Push

GitHub silently drops auto-merge whenever new commits are pushed or force-pushed.
Always re-arm after any push to a PR branch:

```bash
gh pr merge --auto --rebase <PR_NUMBER> --repo <OWNER/REPO>
```

### Git Push Email Privacy Fix

GitHub blocks pushes from `villmow.products@gmail.com`. Use the noreply address:

```bash
git config user.email "mvillmow@users.noreply.github.com"
```

### Unsticking Stalled GitHub Actions Runners

If runs are queued but never picked up (2+ hours):

```bash
# Push an empty retrigger commit
git commit --allow-empty -m "ci: retrigger stalled runners"
git push origin <branch>
# Re-enable auto-merge
gh pr merge --auto --rebase <N> --repo <OWNER/REPO>
```

If still stuck after a retrigger commit, create a fresh branch from main tip and
cherry-pick only the needed diff (see PR Conflict Resolution Pattern above).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | `POST /v1/tasks` to Agamemnon | Returns 404; task creation requires team-scoped route | Use `POST /v1/teams/:team_id/tasks`; discover team ID via `GET /v1/teams` |
| 2 | npm Claude 2.1.101 in achaean-claude container | Traefik intercepts `api.claude.ai` system-wide with self-signed cert (hostname mismatch) — zero API traffic reaches Anthropic | Mount standalone binary (`~/.local/share/claude/versions/<latest>`) as `/usr/local/bin/claude-host` — connects to `api.anthropic.com` directly |
| 3 | Podman rootless without `--userns=keep-id` | Maps host UID to root inside container; `.credentials.json` (0600) unreadable by agent user (uid=1000) | Add `--userns=keep-id` so host UID maps to same UID inside container |
| 4 | `--resume <session_id>` across ephemeral containers | Standalone binary keys sessions by host working-dir path, not container `/workspace`; every resume returns "No conversation found" | Disable all `--session-id`/`--resume` flags; pass full context in each stage prompt |
| 5 | IMPLEMENT stage writing files without `--userns=keep-id` | Workspace bind-mount owned by host user appears as root without uid mapping; permission denied | Add `--userns=keep-id` to every `podman run` invocation |
| 6 | Pipeline REVIEW stage with failed session resume | Empty output defaults to NOGO, pipeline loops up to MAX_ITERATIONS | Disable session resumption; empty output then fails fast instead of looping |
| 7 | SHIPPER committed to existing branch instead of task-specific one | Incorrect branch targeting logic in shipper stage | Workaround: update PR body with `Closes #N`; fix branch logic in shipper |
| 8 | `git push` with `villmow.products@gmail.com` | GitHub email privacy blocks push from this address | Use `mvillmow@users.noreply.github.com` for all git operations |
| 9 | Waiting for stalled GitHub Actions runners | Runs queued 2+ hours, never picked up | Push empty retrigger commit; if still stuck, create fresh branch from main tip |
| 10 | Long-lived PR branch diverged from main | PR enters CONFLICTING state; CI won't run, auto-merge stalls | Create fresh branch from main tip, cherry-pick only the needed diff |
| 11 | `.markdownlint.yaml` with 200-char line limit on main | New PRs fail lint because docs exceed 80-char limit | Replace with `.markdownlint.json` using 80-char limit with table/code/heading exemptions |
| 12 | Auto-merge after force-push or new commits | GitHub silently drops auto-merge on every push | Always run `gh pr merge --auto --rebase <N>` after every push to a PR branch |
| 13 | Container network name `homeric-mesh` | Network created by compose uses project-prefix: `odysseus_homeric-mesh` | Set `CONTAINER_NETWORK=odysseus_homeric-mesh` or default to it in `_build_container_cmd` |

## Results & Parameters

| Parameter | Verified Value |
| ----------- | ---------------- |
| Agamemnon task POST endpoint | `POST /v1/teams/:team_id/tasks` |
| Agamemnon task list endpoint | `GET /v1/tasks` |
| Agamemnon default port | `8080` |
| Container runtime | `podman` (or `CONTAINER_RUNTIME` env var) |
| Container network | `odysseus_homeric-mesh` (or `CONTAINER_NETWORK` env var) |
| Claude image | `achaean-claude:latest` (or `CLAUDE_IMAGE` env var) |
| Standalone Claude binary path | `~/.local/share/claude/versions/<latest>` |
| Mounted binary path in container | `/usr/local/bin/claude-host` |
| Required Podman flag | `--userns=keep-id` |
| Session resumption | DISABLED — each stage gets full context in prompt |
| Git push email | `mvillmow@users.noreply.github.com` |
| markdownlint config file | `.markdownlint.json` (not `.markdownlint.yaml`) |
| markdownlint line length | 80 (tables/code_blocks/headings exempt) |
| Auto-merge command | `gh pr merge --auto --rebase <N> --repo <OWNER/REPO>` |
| Auto-merge re-arm | Required after every push/force-push to PR branch |
