---
name: flesh-out-scaffolded-repo
description: 'Fill gaps in scaffolded repos to make them production-ready: add justfile
  + pixi.toml, build scripts, READMEs, and fix bash syntax bugs, hardcoded values,
  and suppressed failures. Use when: a repo was scaffolded and pushed but is missing
  task runner files, compose/Nomad files have hardcoded paths, or shell scripts have
  syntax errors.'
category: tooling
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# flesh-out-scaffolded-repo

Systematic process for auditing and completing scaffolded repositories: adding justfile + pixi.toml, build scripts, READMEs, and fixing bash syntax bugs, hardcoded values, and suppressed failures — executed across multiple repos in one session.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-15 |
| Objective | Make two scaffolded Docker/GitOps repos production-ready after an audit revealed missing files, bugs, hardcoded values, and inconsistencies |
| Outcome | Success — all 7 new files created, all 11 modifications made, both repos committed and pushed to GitHub |
| Repos | AchaeanFleet (Docker image infrastructure), Myrmidons (GitOps agent provisioning) |

## When to Use

- A repo was scaffolded and committed but lacks a `justfile` / `pixi.toml` for task running
- Compose files or Nomad HCL have hardcoded absolute paths (e.g., `/home/username/...`)
- Shell scripts use `|| true` to suppress failures instead of tracking errors
- Bash `[[ ]]` compound tests use `\` line continuation with parentheses (syntax error)
- A `pre-commit` hook silently exits 0 on a missing dependency instead of failing
- An export script generates YAML with unquoted string values that may contain special characters
- A TypeScript function receives a parameter but never uses it (unused dependency)
- Missing README or build helper scripts

## Verified Workflow

### Phase 1: Read all existing files before making any changes

Always read the actual file contents — do not rely on summaries:

```bash
# Get a full file listing first
find <repo> -type f ! -path '*/.git/*' | sort

# Read every file that will be modified
# Use parallel reads for independent files
```

Key files to read in a Docker/infrastructure repo:
- All compose files (`.yml`)
- Nomad HCL files
- CI/CD TypeScript pipeline files
- All shell scripts in `scripts/` and `scripts/lib/`
- Git hooks in `hooks/`
- Agent template YAML files

### Phase 2: Identify all gaps

Create a mental checklist of:
1. **Missing files**: justfile, pixi.toml, README, build scripts
2. **Hardcoded values**: paths, hostnames, ports in compose/Nomad/HCL
3. **Bash bugs**: syntax errors, `|| true` suppression, missing `exit 1` on errors
4. **Logic gaps**: unused parameters, missing field comparisons, wrong default values

### Phase 3: Create new files in parallel

Create independent new files simultaneously. For each repo, standard files are:

**justfile** (HomericIntelligence convention):
```makefile
# Default: show help
default:
    @just --list

# Variables at top
registry := env_var_or_default("REGISTRY", "...")

# Grouped sections with comments
# === Build ===
build-all:
    bash scripts/build-all.sh

# === Test ===
test:
    ...
```

**pixi.toml** (minimal — establish convention):
```toml
[project]
name = "<repo-name>"
version = "0.1.0"
description = "..."
channels = ["conda-forge"]
platforms = ["linux-64"]

[dependencies]
just = ">=1.13"
# Add: yq, jq for GitOps repos; nothing extra for Docker-only repos

[tasks]
build-all = "just build-all"
```

**scripts/build-all.sh** (for Docker repos):
```bash
#!/usr/bin/env bash
set -euo pipefail
TAG="${TAG:-latest}"
built=0; failed=0

build_image() {
    local tag="$1" dockerfile="$2"
    shift 2; local extra_args=("$@")
    if docker build -f "$dockerfile" -t "$tag" "${extra_args[@]}" .; then
        built=$((built + 1))
    else
        failed=$((failed + 1)); return 1
    fi
}

# Build bases first (dependency order matters)
build_image "base-node:${TAG}" "bases/Dockerfile.node"
build_image "base-python:${TAG}" "bases/Dockerfile.python"

# Build vessels (--build-arg BASE_IMAGE=...)
build_image "vessel-claude:${TAG}" "vessels/claude/Dockerfile" \
    --build-arg "BASE_IMAGE=base-node:${TAG}"

echo "=== ${built} built, ${failed} failed ==="
[[ $failed -gt 0 ]] && exit 1
```

### Phase 4: Fix bash syntax bugs

**Fix 1 — HIBERNATE compound test (syntax error)**:

The `[[ ... && (... || ...) ]]` pattern with `\` continuation is broken in bash:

```bash
# BROKEN — parentheses inside [[ ]] with backslash continuation
if [[ "$desired" == "hibernated" && \
      ("$actual" == "active" || "$actual" == "online") ]]; then

# FIXED — split into two [[ ]] checks
if [[ "$desired" == "hibernated" ]] && \
   [[ "$actual" == "active" || "$actual" == "online" ]]; then
```

**Fix 2 — Replace `|| true` with error tracking**:

```bash
# BAD — silently swallows failures
for yaml_file in "${yaml_files[@]}"; do
    apply_agent "$yaml_file" "$agents_json" || true
done

# GOOD — track failures, continue loop
for yaml_file in "${yaml_files[@]}"; do
    if ! apply_agent "$yaml_file" "$agents_json"; then
        echo "ERROR: apply_agent failed for ${yaml_file}" >&2
        ERRORS=$((ERRORS + 1))
    fi
done
```

**Fix 3 — pre-commit hook must exit 1 on missing dependency**:

```bash
# BAD — silently passes through without validation
if ! command -v yq &>/dev/null; then
    echo "WARNING: yq not found — skipping YAML validation" >&2
    exit 0  # BUG: allows invalid YAML through
fi

# GOOD — fail fast
if ! command -v yq &>/dev/null; then
    echo "ERROR: yq not found — cannot validate YAML before commit" >&2
    exit 1
fi
```

### Phase 5: Parameterize hardcoded values

**Docker Compose** — parameterize host paths:
```yaml
# BAD
volumes:
  - /home/mvillmow/ai-maestro/agent-container/agent-server.js:/app/agent-server.js:ro

# GOOD — add to .env.example, use in compose
volumes:
  - ${AGENT_SERVER_JS:-/home/mvillmow/ai-maestro/agent-container/agent-server.js}:/app/agent-server.js:ro
```

Note: YAML anchors (`x-agent-server-mount: &agent-server-mount`) also support variable substitution — just update the anchor value.

**Nomad HCL** — add `variable` blocks:
```hcl
variable "aim_host" {
  description = "URL of the ai-maestro orchestrator"
  type        = string
  default     = "http://172.20.0.1:23000"
}

variable "agent_server_path" {
  description = "Absolute path to agent-server.js on the Nomad client host"
  type        = string
  default     = "/home/mvillmow/ai-maestro/agent-container/agent-server.js"
}

# In tasks:
env {
  AIM_HOST = var.aim_host
}
volumes = ["${var.agent_server_path}:/app/agent-server.js:ro"]
```

Override at runtime: `nomad job run -var="aim_host=http://hermes:23000" mesh.nomad.hcl`

### Phase 6: Fix logic gaps in reconciliation scripts

**Add missing field comparisons** (e.g., tags):
```bash
# Get actual tags sorted for stable comparison
actual_tags_sorted="$(echo "$actual_json" | jq -r '.tags // [] | sort | join(",")')"

# Sort desired tags the same way
desired_tags_sorted="$(echo "$desired_tags_csv" | tr ',' '\n' | sort | tr '\n' ',' | sed 's/,$//')"

[[ "$actual_tags_sorted" != "$desired_tags_sorted" ]] && drifted_fields+=("tags")
```

**Normalize tilde paths**:
```bash
normalize_path() {
    local p="$1"
    echo "${p/#\~/$HOME}"
}

# Use before comparison:
actual_workdir="$(normalize_path "$actual_workdir")"
desired_workdir="$(normalize_path "$desired_workdir")"
```

**Fix an API client to add timeouts and HTTP error logging**:
```bash
_aim_curl() {
    local http_code response tmpfile
    tmpfile="$(mktemp)"
    http_code="$(curl -s --max-time 10 -w "%{http_code}" -o "$tmpfile" "$@")"
    local curl_exit=$?
    response="$(cat "$tmpfile")"; rm -f "$tmpfile"

    if [[ $curl_exit -ne 0 ]]; then
        echo "ERROR: curl failed (exit ${curl_exit}) for: $*" >&2; return 1
    fi
    if [[ "${http_code:0:1}" != "2" ]]; then
        echo "ERROR: HTTP ${http_code} from API" >&2
        [[ -n "$response" ]] && echo "  Body: ${response}" >&2
        return 1
    fi
    echo "$response"
}
```

**Map program → correct Docker image** (avoid hardcoded fallback):
```bash
program_to_image() {
    case "$1" in
        claude-code|claude) echo "achaean-claude:latest" ;;
        aider)              echo "achaean-aider:latest" ;;
        codex)              echo "achaean-codex:latest" ;;
        none|worker|"")     echo "achaean-worker:latest" ;;
        *)                  echo "achaean-worker:latest" ;;
    esac
}
docker_image="$(program_to_image "$program")"
```

### Phase 7: Fix Dagger TypeScript unused parameter

When a TypeScript function receives a `Map` of built base images but ignores it:

```typescript
// BEFORE — builtBases parameter accepted but never used
async function buildVessels(
  client: Client,
  bases: Map<string, any>,  // unused!
  registry?: string
): Promise<void> { ... }

// AFTER — sync() each base container to enforce build ordering
async function buildVessels(
  client: Client,
  builtBases: Map<string, any>,
  registry?: string
): Promise<void> {
  // Force bases to build before vessels start
  for (const [baseName, baseContainer] of builtBases.entries()) {
    console.log(`Syncing base: ${baseName}`);
    await baseContainer.sync();
  }
  // ... vessel builds
}
```

### Phase 8: Syntax-check all scripts before committing

```bash
bash -n scripts/lib/api.sh
bash -n scripts/lib/reconcile.sh
bash -n scripts/export.sh
bash -n scripts/apply.sh
bash -n hooks/pre-commit
bash -n scripts/build-all.sh
```

### Phase 9: Commit with descriptive messages

Group changes by repo and commit each separately. Include:
- Which files were created vs modified
- What bug was fixed and why
- Co-Authored-By line

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Using `replace_all: true` on compose file for agent-server-mount anchor | Tried to replace all occurrences of the hardcoded path at once | The YAML anchor line and the individual service volume lines had different surrounding context | Use `replace_all: true` only when all occurrences have identical surrounding context; otherwise use targeted edits |
| Delegating file reads to a subagent | Asked Explore agent to read files and return exact contents | Agent returned summaries and paraphrases, not exact file content | For files that will be edited, always use the Read tool directly — never rely on an agent's description of content |
| Assuming the `python-repo-modernization` skill in ProjectMnemosyne represented the current validation format | Copied its flat `plugin.json` structure (no `.claude-plugin/` directory) | The validator (`validate_plugins.py`) requires `.claude-plugin/plugin.json` — the flat format would fail CI | Always read `scripts/validate_plugins.py` to understand the exact expected structure before creating skill files |

## Results & Parameters

### Files created (7 total across 2 repos)

| Repo | File | Purpose |
| ------ | ------ | --------- |
| AchaeanFleet | `justfile` | Task runner with build, test, push, compose recipes |
| AchaeanFleet | `pixi.toml` | just dependency via conda-forge |
| AchaeanFleet | `scripts/build-all.sh` | Build 3 bases then 9 vessels in dependency order |
| AchaeanFleet | `README.md` | Architecture diagram, quick start, port map |
| Myrmidons | `justfile` | status, plan, apply, apply-prune, export, validate, install-hooks |
| Myrmidons | `pixi.toml` | just, yq, jq dependencies via conda-forge |
| Myrmidons | `README.md` | Quick start, agent YAML format, workflows |

### Files modified (11 total)

| Repo | File | Change |
| ------ | ------ | -------- |
| AchaeanFleet | `compose/.env.example` | Added `AGENT_SERVER_JS` variable |
| AchaeanFleet | `compose/docker-compose.claude-only.yml` | Parameterized 3 agent-server.js mounts |
| AchaeanFleet | `compose/docker-compose.mesh.yml` | Parameterized YAML anchor |
| AchaeanFleet | `nomad/mesh.nomad.hcl` | Added 3 variable blocks, replaced hardcoded paths |
| AchaeanFleet | `dagger/pipeline.ts` | Fixed unused `bases` param via `sync()` |
| Myrmidons | `scripts/lib/api.sh` | All curl via `_aim_curl` with `--max-time 10` + HTTP error logging |
| Myrmidons | `scripts/lib/reconcile.sh` | Fixed HIBERNATE syntax; added `normalize_path()`; added tag drift |
| Myrmidons | `scripts/export.sh` | `program_to_image()` mapping; YAML string quoting via `jq -Rr` |
| Myrmidons | `scripts/apply.sh` | Replaced `\|\| true` with error tracking; passed tags to `compute_drift()` |
| Myrmidons | `hooks/pre-commit` | Changed missing-yq from `exit 0` to `exit 1` |
| Myrmidons | `agents/_templates/*.yaml` | Added clarifying comments about docker block |

### justfile recipe checklist for HomericIntelligence repos

For **Docker/infrastructure** repos:
- `default` → `@just --list`
- `build-bases` → build base images
- `build-vessel NAME` → build one vessel + its base
- `build-all` → `bash scripts/build-all.sh`
- `test` → Dagger/smoke tests
- `push` → push to registry
- `compose-up` / `compose-down` → start/stop compose
- `clean` → remove all local images

For **GitOps/provisioning** repos:
- `default` → `@just --list`
- `status HOST` → desired vs actual comparison
- `plan HOST` → dry-run apply
- `apply HOST` → reconcile desired → actual
- `apply-prune HOST` → apply + prune unmanaged
- `export HOST` → bootstrap from current state
- `validate` → validate all YAML schemas
- `install-hooks` → install pre-commit hook

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| AchaeanFleet | Post-scaffold flesh-out — Docker image infrastructure | [notes.md](../../references/notes.md) |
| Myrmidons | Post-scaffold flesh-out — GitOps agent provisioning | [notes.md](../../references/notes.md) |

## References

- Related skills: `python-repo-modernization`, `generate-boilerplate`
- HomericIntelligence conventions: justfile + pixi (never Makefiles)
- `just` docs: https://just.systems/man/en/
- `pixi` docs: https://pixi.sh/
