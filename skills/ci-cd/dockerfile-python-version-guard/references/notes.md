# Session Notes: dockerfile-python-version-guard

## 2026-02-27: ProjectScylla Issue #1138 / PR #1195

**Context**: Dockerfile used `tomllib` (Python stdlib since 3.11, PEP 680) inline in a `RUN` command
to extract dependencies from `pyproject.toml`. Issue #1138 asked to either add a try/except fallback
(importing `tomli` as a backport for Python < 3.11) OR explicitly document the Python 3.11+ requirement.

**Decision**: Documentation-only approach chosen under KISS principle.

- Base image was already `python:3.11-slim` — constraint already satisfied
- Adding `tomli` as a pip dependency would violate YAGNI (no runtime risk today)
- Inline comment block documents the constraint clearly for future maintainers
- 14 static pytest tests added as regression guard

**Specific commands used**:

```bash
# Read Dockerfile, identify tomllib RUN layer
grep -n "tomllib" docker/Dockerfile

# Run tests after changes
pixi run python -m pytest tests/unit/scripts/test_dockerfile_constraints.py -v

# Verify full suite still passes
pixi run python -m pytest tests/ -v --tb=short

# Git operations
git add docker/Dockerfile tests/unit/scripts/test_dockerfile_constraints.py
git commit -m "fix(docker): document Python 3.11+ constraint for tomllib in Dockerfile"
git push -u origin 1138-auto-impl
gh pr create \
  --title "[Fix] Document Python 3.11+ constraint for tomllib in Dockerfile" \
  --body "Closes #1138"
gh pr merge --auto --rebase 1195
```

**Files modified**:

- `docker/Dockerfile` — added constraint comment block above the tomllib RUN layer
- `tests/unit/scripts/test_dockerfile_constraints.py` — 14 new static regression tests (new file)

**Test results**:

- 3197 total tests passing (was 3183 before adding 14 new tests)
- Coverage: 78.31% (above 75% threshold)

**Key implementation detail — regex for FROM parsing**:

```python
pattern = re.compile(r"^FROM\s+python:(\d+)\.(\d+)", re.MULTILINE)
```

This correctly handles multi-stage builds (multiple FROM lines), ignores `COPY --from=builder` patterns,
and ignores non-python base images like `FROM ubuntu:22.04`.

**Links**:

- Issue: <https://github.com/HomericIntelligence/ProjectScylla/issues/1138>
- PR: <https://github.com/HomericIntelligence/ProjectScylla/pull/1195>

## Raw Findings

- `tomllib` was added to Python stdlib in Python 3.11 via PEP 680
- The `tomli` package on PyPI is the backport for Python < 3.11 — identical API, different import name
- `from sys import version_info; assert version_info >= (3, 11)` is an alternative runtime guard
  but static tests are preferable (fail at test time, not at container build time)
- Static Dockerfile tests belong in `tests/unit/scripts/` alongside other Dockerfile/script tests
  (e.g., `test_dockerfile.py` for build validation)

## External References

- PEP 680: <https://peps.python.org/pep-0680/>
- tomli backport: <https://pypi.org/project/tomli/>
- Python 3.11 What's New: <https://docs.python.org/3/whatsnew/3.11.html>
- Related skill: `docker-ci-dead-step-cleanup`
