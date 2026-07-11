---
name: multi-repo-governance-and-ecosystem-setup
description: "Provision and govern multiple HomericIntelligence repositories at scale. Use when: (1) rolling out governance files (LICENSE/CODE_OF_CONDUCT/SECURITY/CONTRIBUTING) to 10+ repos in an org, (2) onboarding a new Tailnet host with the full HomericIntelligence dependency stack, (3) fleshing out scaffolded repos with justfile/pixi.toml/READMEs and fixing bash bugs, (4) centralizing external repo clones to save disk and avoid scattered dependencies, (5) configuring the Claude Code plugin marketplace for auto-update via cron, (6) migrating enabled plugins between marketplaces, or (7) setting up SessionEnd hooks or pipeline integration for automatic /learn retrospectives."
category: tooling
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: multi-repo-governance-and-ecosystem-setup.history
tags:
  - multi-repo
  - governance
  - ecosystem
  - installer
  - scaffold
  - plugin-marketplace
  - cron
  - retrospective
  - hooks
  - ssh-fanout
  - gh-cli
  - git-worktree
  - tailnet
  - debian
---

# Multi-Repo Governance and Ecosystem Setup

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-19 |
| **Objective** | Bring N HomericIntelligence repositories to a baseline standard: governance files, ecosystem deps, scaffold completion, plugin marketplace config, and retrospective automation |
| **Outcome** | Consolidated from 8 member skills covering governance rollout (11 PRs), ecosystem installer (5/7 hosts), scaffold flesh-out (7 files created, 11 modified), centralized clones (37–73% disk savings), marketplace cron, plugin migration, and session-end hook integration |
| **Verification** | verified-local across HomericIntelligence org and Tailnet |

## When to Use

- Rolling out identical or templated governance files (LICENSE, CODE_OF_CONDUCT.md, SECURITY.md, CONTRIBUTING.md) across 5+ repos
- Onboarding a new Tailnet host for the HomericIntelligence mesh (Go, NATS, cmake, templ, pixi, gh CLI)
- Completing a scaffolded repo that is missing a justfile, pixi.toml, README, or build scripts
- Centralizing external repo clones to avoid duplicated 8 MB+ clones across parallel experiments
- Setting up an hourly cron to auto-update a Claude Code plugin marketplace (Mnemosyne)
- Migrating `enabledPlugins` in `~/.claude/settings.json` from one marketplace to another
- Integrating SessionEnd hooks or a CI/CD pipeline phase to automatically trigger `/learn`

## Verified Workflow

### Quick Reference

```bash
# --- Governance file rollout ---
# 1. Survey missing files
gh api repos/HomericIntelligence/{repo}/contents/ --jq '.[].name' | grep -E "LICENSE|CODE_OF_CONDUCT|SECURITY|CONTRIBUTING"

# 2. Clone all repos shallow, create branch
for repo in repo1 repo2 repo3; do
  git clone --depth 1 "https://github.com/HomericIntelligence/$repo" "/tmp/$repo"
  git -C "/tmp/$repo" checkout -b chore/add-governance-files
done

# 3. Copy identical files, then write custom per-repo files
# 4. Batch commit, push, create PRs
for repo in repo1 repo2 repo3; do
  git -C "/tmp/$repo" add . && git -C "/tmp/$repo" commit -m "chore: add governance files"
  git -C "/tmp/$repo" push origin chore/add-governance-files
  gh pr create -R "HomericIntelligence/$repo" --head chore/add-governance-files \
    --title "chore: add governance files" --body "..."
done

# 5. Enable auto-merge
gh api -X PATCH repos/HomericIntelligence/{repo} --field allow_auto_merge=true
gh pr merge "$PR_NUM" -R HomericIntelligence/{repo} --auto --rebase

# --- Ecosystem installer ---
just install-check            # check only
just install                  # install all deps
bash scripts/shell/install.sh --role worker --install
bash scripts/shell/install.sh --role control --install

# --- SSH fan-out to all Tailnet hosts ---
ssh-keyscan -H aeolus apollo artemis athena hephaestus hermes titan >> ~/.ssh/known_hosts
for host in aeolus apollo artemis athena hephaestus hermes titan; do
  ssh -o ConnectTimeout=6 -o BatchMode=yes "$host" \
    'mkdir -p ~/Projects && git clone https://github.com/HomericIntelligence/ProjectHephaestus.git ~/Projects/ProjectHephaestus || git -C ~/Projects/ProjectHephaestus pull && bash ~/Projects/ProjectHephaestus/scripts/shell/install.sh --install' &
done; wait

# --- Plugin marketplace cron ---
(crontab -l 2>/dev/null; echo "0 * * * * /home/<user>/.local/bin/claude plugin marketplace update Mnemosyne >> /tmp/claude-plugin-update.log 2>&1 && /home/<user>/.local/bin/claude plugin update mnemosyne@Mnemosyne >> /tmp/claude-plugin-update.log 2>&1") | crontab -
```

### Governance File Rollout (Detailed)

1. **Survey each repo** — use `gh api repos/HomericIntelligence/{repo}/contents/` to list top-level files. Group repos into buckets by what is missing.

2. **Research tech stacks** (for CONTRIBUTING.md and SECURITY.md): fetch justfile, pixi.toml, CMakeLists.txt from each repo via `gh api ... | base64 -d`.

3. **Write identical files once** from the parent conversation (LICENSE, CODE_OF_CONDUCT.md) to `/tmp/template/`, then `cp` to each repo clone. Avoid repeated Write calls.

4. **Write custom files per repo** using the Write tool — SECURITY.md (scoped to each repo's attack surface) and CONTRIBUTING.md (referencing real build/test commands).

5. **Batch commit/push** with `git -C /tmp/{repo}` — never `cd` into each repo (shell cwd resets between Bash calls).

6. **Create PRs with `-R` flag** — `gh pr create -R HomericIntelligence/{repo} --head {branch}`. Works from any cwd.

7. **Enable auto-merge** — if `gh pr merge --auto` errors, first run `gh api -X PATCH repos/HomericIntelligence/{repo} --field allow_auto_merge=true`.

### Ecosystem Installer (Detailed)

Add `scripts/shell/install.sh` to ProjectHephaestus. Script sections in order:

| Section | Role Gate | Notes |
| --------- | ----------- | ------- |
| Core tooling: git, curl, jq, just, gh CLI | all | gh via official apt source |
| Tailscale | all | install script + tailscaled status |
| Python 3.10+, pip3, nats-py, pixi | all | nats-py: `--break-system-packages` then `--user` fallback |
| Go 1.23+ | worker | Official tarball; apt version is 1.19 on Debian 12 |
| templ | worker | `GOBIN=~/.local/bin go install github.com/a-h/templ/cmd/templ@latest` |
| nats-server 2.10+ | all | Native binary to `~/.local/bin` — NOT podman |
| nats CLI | all | zip from GitHub releases |
| Container: podman, podman-compose | worker | slirp4netns precludes podman for NATS |
| C++ build chain | control | cmake 3.20+ via pip or kitware; ninja, gcc, conan |
| PATH sanity | all | `~/.local/bin` and `/usr/local/go/bin` |

**Why NATS must be a native binary**: slirp4netns (rootless podman) creates a user-space NAT that hides the real Tailscale IP, breaking cross-host connections.

**Pre-flight checklist for SSH fan-out**:
```bash
# Probe: reachability, arch, Python version, git presence, sudo status
for host in aeolus apollo artemis athena hephaestus hermes titan; do
  echo -n "$host: "
  ssh -o ConnectTimeout=6 -o BatchMode=yes "$host" \
    'echo OK && uname -m && python3 --version 2>/dev/null && which git 2>/dev/null || echo no-git' \
    2>&1 | tr '\n' ' '; echo
  ssh -o ConnectTimeout=6 -o BatchMode=yes "$host" \
    'sudo -n true 2>&1 && echo NOPASSWD-OK || echo NEEDS-PASSWORD' 2>&1
done
```
Only dispatch agents to hosts where Python >= 3.10, git is installed, and sudo is NOPASSWD-OK.

### Scaffold Flesh-Out (Detailed)

**Phase 1** — Read ALL existing files before changing anything. Use parallel reads for independent files.

**Phase 2** — Identify all gaps: missing files (justfile, pixi.toml, README, build scripts), hardcoded values (paths, ports), bash bugs (`|| true`, `[[ ... && (...) ]]` syntax errors), logic gaps.

**Phase 3** — Fix bash bugs:

```bash
# BROKEN — parentheses inside [[ ]] with backslash continuation
if [[ "$desired" == "hibernated" && \
      ("$actual" == "active" || "$actual" == "online") ]]; then

# FIXED — split into two [[ ]] checks
if [[ "$desired" == "hibernated" ]] && \
   [[ "$actual" == "active" || "$actual" == "online" ]]; then
```

```bash
# BAD — silently swallows failures
apply_agent "$yaml_file" "$agents_json" || true

# GOOD — track failures, continue loop
if ! apply_agent "$yaml_file" "$agents_json"; then
    echo "ERROR: apply_agent failed for ${yaml_file}" >&2
    ERRORS=$((ERRORS + 1))
fi
```

**Phase 4** — Parameterize hardcoded values in compose/Nomad:
```yaml
# Use env vars in compose
volumes:
  - ${AGENT_SERVER_JS:-/home/user/agent-container/agent-server.js}:/app/agent-server.js:ro
```

**Phase 5** — Syntax-check all scripts before committing:
```bash
bash -n scripts/lib/api.sh && bash -n scripts/lib/reconcile.sh && bash -n hooks/pre-commit
```

### Centralized Repo Clones (Detailed)

Share a single base clone across all experiments using git worktrees:

```python
# Deterministic UUID from repo URL
repo_uuid = hashlib.sha256(repo_url.encode()).hexdigest()[:16]
base_repo = repos_dir / repo_uuid

# File locking around clone check/create
with open(lock_path, "w") as lock_file:
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    if base_repo.exists() and (base_repo / ".git").exists():
        return  # Reuse existing clone
    subprocess.run(["git", "clone", repo_url, str(base_repo)], check=True)

# Separate worktree creation from checkout
subprocess.run(["git", "-C", str(base_repo), "worktree", "add", "-b", branch, str(workspace)], check=True)
subprocess.run(["git", "-C", str(workspace), "checkout", commit], check=True)
```

Use full (non-shallow) clones for centralized repos so arbitrary commits can be fetched.

### Plugin Marketplace Auto-Update

```bash
# Install hourly cron (both commands required)
(crontab -l 2>/dev/null; echo "0 * * * * /home/<user>/.local/bin/claude plugin marketplace update Mnemosyne >> /tmp/claude-plugin-update.log 2>&1 && /home/<user>/.local/bin/claude plugin update mnemosyne@Mnemosyne >> /tmp/claude-plugin-update.log 2>&1") | crontab -
crontab -l  # verify
```

### Plugin Migration (`~/.claude/settings.json`)

```json
{
  "enabledPlugins": {
    "hephaestus@ProjectHephaestus": true
  },
  "extraKnownMarketplaces": [
    {
      "source": {
        "source": "git",
        "url": "https://github.com/HomericIntelligence/ProjectHephaestus.git"
      }
    }
  ]
}
```

Mnemosyne can be removed from `extraKnownMarketplaces` because ProjectHephaestus commands (`/advise`, `/learn`) clone it independently to `$HOME/.agent-brain/Mnemosyne/`.

### Retrospective Hook Integration

Configure `SessionEnd` hook in `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/learn-trigger.py\"",
            "timeout": 120,
            "once": true
          }
        ]
      }
    ]
  }
}
```

For pipeline integration, resume the session with explicit tool permissions:

```python
run([
    "claude", "--resume", session_id,
    "/mnemosyne:learn commit the results and create a PR",
    "--print",
    "--tools", "Bash",
    "--allowedTools", "Bash(git:*)",
    "--allowedTools", "Bash(gh:*)"
], cwd=worktree_path, timeout=600)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 11 parallel Sonnet sub-agents for governance files | Delegated CODE_OF_CONDUCT.md writing to 11 parallel sub-agents | All hit content filtering on CoC text | Write governance policy files from the parent Opus conversation, not from Sonnet sub-agents |
| `cd /tmp/{repo}` in bash loop | Used `cd repo && gh pr create` pattern inside a for loop | Shell cwd resets between Bash tool calls | Always use `gh pr create -R <owner>/<repo> --head <branch>` and `git -C /tmp/{repo}` |
| Overwrite existing files without surveying | Wrote all 4 governance files unconditionally | Some repos already had LICENSE or CODE_OF_CONDUCT.md | Always survey `gh api repos/.../contents/` first; only add missing files |
| `pip3 install nats-py` (plain) | `pip3 install nats-py` on Debian 12 | PEP 668 — system pip refuses without `--break-system-packages` | Use `--break-system-packages` first, then `--user` fallback |
| podman for NATS server | Run nats-server inside rootless podman | Slirp4netns NAT hides real Tailscale IP | NATS server must be a native binary bound to the Tailscale interface |
| apt cmake on Debian stable | `sudo apt install cmake` | Debian stable ships cmake 3.18.x; requires 3.20+ | Use `pip3 install cmake --break-system-packages` or kitware apt repo |
| apt go on Debian stable | `sudo apt install golang` | Debian stable ships Go 1.19; requires 1.23+ | Download official Go tarball from https://go.dev/dl/ |
| `pkill -f nats-server` | Kill stale server via pkill | Returns exit 144 on some hosts (pkill receives SIGTERM itself) | Use `kill $(ps aux \| grep nats-server \| grep -v grep \| awk '{print $2}')` |
| SSH without ssh-keyscan first | Probed new hosts over SSH without adding host key | Host key verification failed | Run `ssh-keyscan -H <host> >> ~/.ssh/known_hosts` before any batch SSH operation |
| sudo apt-get in BatchMode SSH | `ssh -o BatchMode=yes host 'sudo apt-get install -y git'` | sudo requires a terminal for password | Check `sudo -n true` first; escalate to user if NEEDS-PASSWORD |
| Cloning main before PR merged | Dispatched agents to clone main before install.sh PR merged | install.sh missing from main | Merge the PR first, or clone the feature branch |
| Python 3.7 on apollo | Dispatched installer agent to apollo (Python 3.7.3) | 3.10+ required | Check `python3 --version` before dispatching |
| git not pre-installed on athena/titan | Tried to clone ProjectHephaestus on athena/titan | Neither had git installed; clone fails silently in BatchMode | Check `which git` during probe step; give user a manual command if missing |
| Using `replace_all: true` on compose anchor | Replace all occurrences of hardcoded path at once | YAML anchor line and service volume lines had different surrounding context | Use `replace_all: true` only when all occurrences have identical surrounding context |
| Delegating file reads to a subagent | Asked Explore agent to read files and return exact contents | Agent returned summaries, not exact file content | For files that will be edited, always use the Read tool directly |
| Using just `claude` without full path in cron | `0 * * * * claude plugin marketplace update ...` | cron does not source `.bashrc`/`.profile` | Always use absolute path to binary in cron jobs |
| Updating only the marketplace in cron | `claude plugin marketplace update` alone | Marketplace index updates but installed plugin version does not change | Must also run `claude plugin update <plugin>@<marketplace>` |
| Missing tool permissions in retrospective pipeline | `claude --resume session_id --message "Use /mnemosyne:learn..."` | No git/gh permissions; retrospective cannot commit | Add `--allowedTools Bash(git:*)` and `--allowedTools Bash(gh:*)` |
| Shallow clone for centralized repos | `git clone --depth=1` for centralized base | Cannot fetch arbitrary commits from shallow clones | Use full clone for centralized repos |
| Including commit in `git worktree add` | `git worktree add -b branch /path commit` | Fails when base repo is on a different branch | Separate `git worktree add` and `git checkout` steps |

## Results & Parameters

### CONTRIBUTING.md Customization Matrix

| Tech Stack | Build Command | Test Command | Notes |
| ------------ | --------------- | -------------- | ------- |
| C++ + CMake + Conan | `just build` or `cmake --preset ...` | `ctest --preset ...` | Mention `conan install` as prereq |
| Mojo | `pixi run mojo build` | `pixi run mojo test` | Mention `pixi install` as prereq |
| Python (pixi) | `pixi run python -m build` | `pixi run pytest` | Mention `pixi install` |
| Nomad/HCL infra | N/A | `just validate` | Link to Nomad docs |

### Ecosystem Dependency Version Matrix

| Dependency | Minimum | Recommended | Install Method |
| ------------ | --------- | ------------- | ---------------- |
| Go | 1.23.0 | 1.23.4 | Official tarball → `/usr/local/go` |
| cmake | 3.20.0 | 3.28+ | `pip3 install cmake --break-system-packages` |
| nats-server | 2.10.0 | 2.10.21 | Native binary → `~/.local/bin` |
| nats CLI | 0.1.0 | 0.1.5 | zip from GitHub → `~/.local/bin` |
| Python | 3.10.0 | 3.11+ | System apt |
| pixi | any | latest | `curl -fsSL https://pixi.sh/install.sh \| bash` |
| templ | any | latest | `GOBIN=~/.local/bin go install github.com/a-h/templ/cmd/templ@latest` |
| gh CLI | any | latest | Official GitHub apt repo |

### justfile Recipe Checklist

For **Docker/infrastructure** repos: `default`, `build-bases`, `build-vessel NAME`, `build-all`, `test`, `push`, `compose-up`, `compose-down`, `clean`.

For **GitOps/provisioning** repos: `default`, `status HOST`, `plan HOST`, `apply HOST`, `apply-prune HOST`, `export HOST`, `validate`, `install-hooks`.

### Centralized Clone Disk Savings

| Experiments | Legacy | Centralized | Savings |
| ------------- | -------- | ------------- | --------- |
| 1 | 11 MB | 11 MB | 0% |
| 2 | 22 MB | 14 MB | 37% |
| 5 | 55 MB | 23 MB | 58% |
| 10 | 110 MB | 38 MB | 65% |
| 100 | 1.1 GB | 308 MB | 73% |

### Auto-Merge Enablement Check

```bash
gh api repos/HomericIntelligence/{repo} --jq '.allow_auto_merge'
# If false:
gh api -X PATCH repos/HomericIntelligence/{repo} --field allow_auto_merge=true
```

### Plugin CLI Reference

| Command | Purpose |
| --------- | --------- |
| `claude plugin marketplace update [name]` | Pull latest git for marketplace |
| `claude plugin update <plugin>@<marketplace>` | Update installed plugin to latest |
| `claude plugin marketplace list` | List configured marketplaces |
| `claude plugin list` | List installed plugins |

### Retrospective Pipeline Parameters

| Component | Value | Rationale |
| ----------- | ------- | ----------- |
| Session resume timeout | 600s | Retrospective involves cloning + PR creation |
| Hook `once` field | `true` | Prevents duplicate prompts per session |
| Minimum transcript length | 10 messages | Avoid triggering on trivial sessions |
| Default flag state | `false` | Opt-in — does not disrupt existing workflows |
| Error handling | Log warning, never raise | Non-blocking enhancement |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence org | 15 repos governance rollout, 11 PRs created | verified-local — PRs pushed, auto-merge enabled |
| ProjectHephaestus | install.sh PR #309 (2026-04-28) | bash -n check passed; ran on epimetheus |
| Tailnet fan-out | 7-host parallel SSH deploy (2026-04-28) | 2 fully done (aeolus, hephaestus); 3 partial; 2 failed |
| AchaeanFleet | Post-scaffold flesh-out — Docker image infrastructure | 7 files created, 11 modified |
| Myrmidons | Post-scaffold flesh-out — GitOps agent provisioning | Committed and pushed to GitHub |
| ProjectScylla | Centralized repo clones (2024-02-13) | 2100 tests pass; 37.3% savings on integration test |
| HomericIntelligence | Plugin marketplace cron + migration | Cron installed; plugins reloaded successfully |
| ProjectOdyssey | Retrospective hook integration | SessionEnd hook configured; pipeline PR #609 |
