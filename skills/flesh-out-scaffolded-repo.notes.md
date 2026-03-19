# Session Notes — flesh-out-scaffolded-repo

## Session Info

- **Date**: 2026-03-15
- **Repos**: AchaeanFleet, Myrmidons (both HomericIntelligence)
- **Duration**: Single session

## Context

Both repos were scaffolded and pushed to GitHub. An audit revealed:
- Missing: justfile, pixi.toml, README, build scripts
- Compose files with hardcoded `/home/mvillmow/ai-maestro/agent-container/agent-server.js`
- Nomad HCL with hardcoded `http://172.20.0.1:23000` and paths
- Bash syntax error in `compute_drift()`: `[[ ... && (...) ]]` with `\` continuation
- `|| true` suppressing errors in `apply.sh`
- `pre-commit` exiting 0 on missing `yq` (silently skipping validation)
- `export.sh` hardcoding `achaean-claude:latest` for all agent programs
- Dagger `buildVessels()` accepting `bases: Map` but never using it
- Missing tag comparison in `compute_drift()`
- No `normalize_path()` for tilde expansion in workdir comparison

## AchaeanFleet specifics

### Repo structure
```
bases/          3 base Dockerfiles (node, python, minimal)
vessels/        9 agent vessel Dockerfiles (FROM a base)
compose/        Docker Compose files
nomad/          Nomad job specs
dagger/         Dagger CI/CD pipeline (TypeScript)
.github/        GitHub Actions
```

### Port mapping
```
23000     ai-maestro dashboard
23001     aim-aindrea (claude)
23003     aim-baird (claude)
23004     aim-vegai (claude)
23010     aim-codex-1
23020     aim-aider-1
23030     aim-goose-1
23040     aim-cline-1
23050     aim-opencode-1
23060     aim-codebuff-1
23070     aim-ampcode-1
23080     aim-worker-1
```

### Base→vessel mapping
- Node base: claude, codex, cline, codebuff, ampcode
- Python base: aider
- Minimal base: goose, opencode, worker

## Myrmidons specifics

### Scripts
- `export.sh` — Bootstrap: ai-maestro → YAML
- `plan.sh` — Dry-run reconciliation
- `apply.sh` — Reconcile desired → actual
- `status.sh` — Table of desired vs actual
- `lib/api.sh` — ai-maestro REST API client
- `lib/reconcile.sh` — Drift computation

### Agent YAML format
```yaml
apiVersion: myrmidons/v1
kind: Agent
metadata:
  name: <tmux-session-name>
  host: hermes
spec:
  label: DisplayName
  program: claude-code  # or aider, codex, goose, etc.
  model: null
  workingDirectory: /home/mvillmow/Project
  programArgs: ""
  taskDescription: "..."
  tags: [tag1, tag2]
  owner: mvillmow
  role: member
  deployment:
    type: local   # or docker
    docker:
      image: achaean-claude:latest
      cpus: 2
      memory: 4g
  desiredState: active
```

### compute_drift() signature (after fix)
```bash
compute_drift "$name" "$desired_state" "$actual_json" \
    "$label" "$program" "$workdir" "$args" "$desc" "$tags"
# 9 positional args — $9 is desired_tags_csv (comma-separated)
```

## Key observations

1. **Read files directly**: An Explore subagent was asked to return exact file contents but returned summaries instead. Always use `Read` tool directly for files that will be edited.

2. **Bash compound tests**: `[[ a && (b || c) ]]` with `\` line continuation causes a syntax error. The parentheses are treated as subshells in some contexts. Always split into separate `[[ ]]` blocks when using compound OR logic.

3. **YAML anchor parameterization**: `x-agent-server-mount: &agent-server-mount` anchor values support `${VAR:-default}` syntax in Docker Compose — the variable substitution applies to the anchor value, not just inline uses.

4. **Nomad HCL variables**: Nomad v1.3+ supports `variable` blocks at the top of job files. Override with `-var="key=value"` at `nomad job run` time. No separate `.tfvars`-style file needed for simple cases.

5. **ProjectMnemosyne skill structure**: The validator requires `.claude-plugin/plugin.json` (NOT a flat `plugin.json`). Some older skills in the repo use the flat format but would fail current CI. Always check `scripts/validate_plugins.py` before creating skill files.