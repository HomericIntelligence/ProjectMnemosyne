# Raw Session Notes: Containerize E2E Experiments

## Session Timeline

### Phase 1: Initial Request (00:00-00:30)
**User Request:** "I don't want containers to be optional, it must always be used, if the container doesn't exist, then I want the script to build it"

**Actions Taken:**
1. Removed `--use-containers` CLI flag from `scripts/run_e2e_experiment.py`
2. Changed `ExperimentConfig.use_containers` default to `True`
3. Added `ensure_docker_image()` function to auto-build missing images
4. Integrated Docker check into `main()` before experiment starts

**Initial Issues Found:**
- Container image didn't exist: `Unable to find image 'scylla-runner:latest' locally`
- Built image successfully with `docker build -t scylla-runner:latest ./docker`

### Phase 2: Credential Mapping (00:30-01:30)
**User Request:** "I don't need ANTHROPIC_API_KEY set as I'm using claude code, so when executing, it should get the credentials from the users ~/.claude/.credentials.json and map it to the docker containers ~/.claude/.credentials.json at runtime"

**Problem:** `ANTHROPIC_API_KEY is not set` error in container

**Attempted Solutions:**
1. ❌ Direct mount: `-v ~/.claude:/home/scylla/.claude:ro` - Permission denied
2. ❌ Mount credentials file directly - Docker creates directory instead
3. ✅ Temp directory approach:
   - Create temp dir with proper permissions
   - Copy credentials with 644 permissions
   - Mount temp dir to `/tmp/host-creds`
   - Entrypoint copies to container home with 600 permissions

**Agent Involved:** a340122 - Fixed credential mapping

### Phase 3: Architecture Refactor (01:30-02:30)
**User Request:** "This isn't working, lets remove the container from execution and instead we will launch the container and inside the container run `run_e2e_experiment.py`"

**Major Architecture Change:**
- OLD: Host orchestrates containers for each agent/judge
- NEW: Single container runs entire experiment

**Actions:**
1. Disabled container orchestration in `SubTestExecutor.__init__()`
2. Simplified `_run_agent_execution()` to always use direct adapter
3. Updated Dockerfile to install scylla package
4. Enhanced entrypoint to support arbitrary commands
5. Created `scripts/run_experiment_in_container.sh` wrapper

**Agent Involved:** a39c717 - Refactored architecture

### Phase 4: Python Version Upgrade (02:30-03:00)
**User Request:** "I want python 3.14.2 and i also want a script to launch a container without starting the e2e experiment so I can run multiple experiments in the same container"

**Actions:**
1. Updated Dockerfile: `FROM python:3.10-slim` → `FROM python:3.14.2-slim`
2. Fixed `datetime.UTC` compatibility across 22 files
   - Changed to `timezone.utc` for Python 3.10+ compatibility
3. Created `scripts/launch_container_shell.sh` for interactive sessions

**Agent Involved:** a0ffecb - Fixed Python 3.10 compatibility (works on 3.14.2)

### Phase 5: Authentication Fix (03:00-03:30)
**User Report:** "the container didn't properly let claude login"

**Problem:** Interactive bash shell wasn't calling credential setup

**Root Cause:**
```bash
bash|sh)
    # Missing credential setup!
    exec "$@"
    ;;
```

**Fix:**
```bash
bash|sh)
    # Now properly sets up credentials
    ensure_clean_claude_environment
    # Show welcome message
    exec "$@"
    ;;
```

**Additional Improvements:**
- Added welcome message showing credential status
- Made `.claude` directory writable (700) for token refresh
- Made `.credentials.json` writable (600) for OAuth updates
- Added helpful usage instructions in welcome message

### Phase 6: Final Validation (03:30-04:00)
**User:** Ran experiment inside container

**Results:**
```
Duration: 256.0s
Total Cost: $0.1087
Best Tier: T0
Best Sub-test: 00
Frontier CoP: $0.1087
T0: PASS (score: 0.840, cost: $0.1087)
```

**Validation:**
- ✅ Agent executed successfully (133s)
- ✅ Judge evaluated successfully (118s)
- ✅ Credentials worked properly
- ✅ Python 3.14.2 verified
- ✅ Cache efficiency 99.97%
- ✅ Grade A (84% score)

## Technical Details

### Docker Image Build
```dockerfile
FROM python:3.14.2-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    git make curl gcc g++ build-essential ca-certificates gnupg

# Node.js 20.x (for Claude CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Scylla package
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .
```

### Credential Mount Flow
```
Host: ~/.claude/.credentials.json (600)
  ↓ copy to
Host: .tmp-container-creds/.credentials.json (644)
  ↓ mount to
Container: /tmp/host-creds/.credentials.json (ro)
  ↓ copy to
Container: /home/scylla/.claude/.credentials.json (600)
  ↓ used by
Claude CLI
```

### Permission Matrix

| File/Dir | Host | Container | Purpose |
|----------|------|-----------|---------|
| `~/.claude/` | 700 | - | Host credentials (owner-only) |
| `.tmp-container-creds/` | 755 | - | Temp mount point (world-readable) |
| `/tmp/host-creds/` | - | ro | Mounted credentials (read-only) |
| `/home/scylla/.claude/` | - | 700 | Container .claude dir (owner-only) |
| `.credentials.json` | - | 600 | Credentials file (owner read/write) |
| `results/` | 777 | rw | Results directory (world-writable) |

## Code Changes Summary

### Files Created
1. `scripts/run_experiment_in_container.sh` - Single experiment wrapper
2. `scripts/launch_container_shell.sh` - Interactive shell launcher
3. `docs/container-usage.md` - Usage guide
4. `docs/container-authentication.md` - Auth troubleshooting
5. `docs/container-architecture.md` - Architecture details

### Files Modified

**Dockerfile:**
- Changed base image to Python 3.14.2
- Added scylla package installation

**Entrypoint:**
- Added credential setup to bash shell case
- Added welcome message with auth status
- Fixed permission handling (700/600)

**Python Files (22 total):**
- `src/scylla/e2e/` (8 files)
- `src/scylla/adapters/` (4 files)
- `src/scylla/executor/` (2 files)
- `src/scylla/reporting/` (4 files)
- `src/scylla/cli/main.py`
- `src/scylla/orchestrator.py`
- `tests/unit/e2e/test_resume.py`
- Plus 1 more

**CLI Script:**
- Removed `--use-containers` flag
- Removed Docker image check from main()

**Models:**
- Changed `use_containers` default to False (deprecated field)

**Executor:**
- Disabled nested container orchestration

## Debugging Commands Used

```bash
# Check Docker image
docker images | grep scylla-runner

# Test credential mounting
docker run --rm -v .tmp-container-creds:/tmp/host-creds:ro \
    scylla-runner:latest \
    ls -la /tmp/host-creds/

# Verify Python version
docker run --rm scylla-runner:latest python --version

# Check container user
docker run --rm scylla-runner:latest whoami

# Test credential setup
docker run --rm -v .tmp-container-creds:/tmp/host-creds:ro \
    scylla-runner:latest \
    bash -c "ls -la ~/.claude/"

# Test experiment
./scripts/run_experiment_in_container.sh \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T0 --runs 1 --max-subtests 1 -v

# Interactive shell
./scripts/launch_container_shell.sh test-session
```

## Lessons Learned

### What Worked Well
1. **Single container architecture** - Much simpler than nested containers
2. **Temp directory for credentials** - Solved permission issues elegantly
3. **Interactive shell script** - Enabled fast iteration
4. **Welcome message** - Immediately shows auth status
5. **Python compatibility fix** - `timezone.utc` works across versions

### What Took Longest
1. **Credential mounting** (1.5 hours) - Multiple attempts to get permissions right
2. **Python compatibility** (1 hour) - Finding all 22 files with `datetime.UTC`
3. **Architecture refactor** (1 hour) - Removing nested container logic
4. **Auth in bash shell** (30 min) - Missing `ensure_clean_claude_environment()` call

### Surprising Discoveries
1. **Docker creates directories for missing file mounts** - Have to mount directory containing file
2. **Cache hit rate 99.97%** - Excellent caching by Claude API
3. **Container user UID 999** - Different from host, causes permission issues
4. **Python 3.14.2 already available** - Recent release (Jan 2025)
5. **Entrypoint case order matters** - `bash|sh` must handle credentials

## Performance Metrics

**Build Times:**
- Docker image build: ~30s (cached), ~2min (fresh)
- Container startup: <1s
- Credential copy: <0.1s

**Experiment Times:**
- Agent execution: 133s
- Judge evaluation: 118s
- Total: 256s (4.3 min)

**Cost Efficiency:**
- Input tokens: 25,010 (8 fresh + 25,002 cached)
- Output tokens: 251
- Cache created: 24,892
- Total cost: $0.1087
- Cache hit rate: 99.97%

## Next Steps Suggested

1. ✅ Test experiment execution - DONE
2. ⚠️ Add pre-commit hooks to lint container scripts
3. ⚠️ Add CI job to build Docker image
4. ⚠️ Document credential refresh workflow
5. ⚠️ Add health check to container
6. ⚠️ Consider persistent named containers for long experiments
7. ⚠️ Add container resource limits (CPU/memory)

## Related Issues

- #150 - CLI container flag (completed this session)
- Related to credential management
- Related to Python version upgrades
- Related to Docker integration

## Agent Summary

| Agent ID | Purpose | Outcome |
|----------|---------|---------|
| a9dbcee | Run experiment and fix errors | ✅ Found credential issues |
| a079476 | Configure thinking mode | ✅ Settings configured |
| a340122 | Fix Docker credential mapping | ✅ Credentials mounted |
| a39c717 | Refactor to single container | ✅ Architecture simplified |
| a0ffecb | Fix Python 3.10 compatibility | ✅ 22 files updated |
| a6a59d3 | Fix output directory permissions | ✅ chmod 777 results/ |

Total agents used: 6
Total time with agents: ~2.5 hours
Direct coding time: ~1.5 hours
