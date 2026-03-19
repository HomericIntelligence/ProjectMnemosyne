# Session Notes: docker-optional-dep-layer-caching

Additional context, raw logs, and detailed findings from verified implementations.

## Verified Examples

### Example 1: ProjectScylla

**Date**: 2026-02-27
**Context**: Issue #1139 (follow-up from #998) — Layer 2 only cached runtime deps; analysis extras bypassed cache

**Problem**:
```dockerfile
# Before: only runtime deps cached in Layer 2
RUN pip install --user --no-cache-dir \
    $(python3 -c "import tomllib; data=tomllib.load(open('/opt/scylla/pyproject.toml','rb')); print(' '.join(data['project']['dependencies']))")
```
If `pip install /opt/scylla/[analysis]` was used to install analysis extras, those packages were
reinstalled on every source change because they weren't in Layer 2.

**Fix Applied**:
```dockerfile
# After: ARG EXTRAS="" + optional-dep extraction
ARG EXTRAS=""
COPY pyproject.toml /opt/scylla/
RUN pip install --user --no-cache-dir \
    $(python3 -c "
import tomllib, os
data = tomllib.load(open('/opt/scylla/pyproject.toml', 'rb'))
deps = list(data['project']['dependencies'])
opt = data['project'].get('optional-dependencies', {})
for group in [g.strip() for g in os.environ.get('EXTRAS', '').split(',') if g.strip()]:
    deps.extend(opt.get(group, []))
print(' '.join(deps))
" EXTRAS="$EXTRAS")
```

**docker-compose.yml change**:
```yaml
build:
  context: ..
  dockerfile: docker/Dockerfile
  args:
    EXTRAS: ${EXTRAS:-}
```

**Tests added**: `tests/unit/docker/test_dockerfile_optional_deps.py` — 7 static-analysis assertions, no Docker daemon needed, run in 0.04 s

**Links**:
- PR: https://github.com/HomericIntelligence/ProjectScylla/pull/1202
- Issue: https://github.com/HomericIntelligence/ProjectScylla/issues/1139
- Branch: `1139-auto-impl`

---

## Raw Findings

- `ARG` values are available as shell variables inside the `RUN` command's shell, but Python processes
  launched from `$(...)` subshells do NOT inherit them via `os.environ` unless explicitly forwarded as
  `KEY=value python3 -c ...`. This is a common source of confusion.
- `tomllib` is in the Python 3.11+ stdlib; the Dockerfile uses Python 3.12 so no extra install needed.
- Ruff auto-formatted the test file (removed blank lines in generator expressions) on first pre-commit run;
  re-staging after the format fix was required before the commit.
- `docker-compose.yml` `${EXTRAS:-}` syntax provides an empty default when `EXTRAS` is not set in the host
  environment, matching the `ARG EXTRAS=""` default in the Dockerfile.

## External References

- Related skills: `python-version-alignment`
- Docker ARG scoping: https://docs.docker.com/reference/dockerfile/#arg