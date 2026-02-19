# Skill: Pin npm Packages in Dockerfile

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Objective** | Pin npm packages to specific versions in Dockerfiles for build reproducibility |
| **Outcome** | ✅ Success - Pinned @anthropic-ai/claude-code to v2.1.42 with regression test |
| **Issue** | #650 |
| **PR** | #717 |

## When to Use This Skill

Use this skill when:

- You see `npm install -g <package>` without a version specifier in a Dockerfile
- Docker builds are non-reproducible due to unpinned dependencies
- You need to ensure consistent builds across environments
- You want to prevent breaking changes from new npm package versions
- You're setting up CI/CD for a project with npm dependencies

**Triggers**:

- "npm install without version"
- "docker build reproducibility"
- "pin npm package version"
- "unpinned dependencies in Dockerfile"
- "version pinning best practices"

## Verified Workflow

### 1. Identify Current Version

First, determine what version is currently being installed:

```bash
# Build the Docker image
docker build -t test-image docker/

# Check installed npm package version
docker run --rm test-image npm list -g <package-name>
```

### 2. Update Dockerfile with Version Pin

**Pattern**: Add version specifier to npm install command

```dockerfile
# BEFORE (unpinned - BAD)
RUN npm install -g @anthropic-ai/claude-code

# AFTER (pinned to specific version - GOOD)
# Install Claude Code CLI (pinned to specific version for reproducibility)
# This is the primary tool for agent-based test execution
# Version 2.1.42 verified working in #601
# See: https://github.com/mvillmow/ProjectScylla/issues/650
RUN npm install -g @anthropic-ai/claude-code@2.1.42
```

**Best Practices**:

- Pin to exact version (not `^` or `~` ranges)
- Add inline comment explaining version choice
- Reference the issue/PR where version was verified
- Follow existing Dockerfile patterns (e.g., pinning base images)

### 3. Add Regression Test

Create a test to prevent future unpinned dependencies:

```python
def test_npm_packages_are_pinned(self, dockerfile_path):
    """Dockerfile pins npm packages to specific versions for reproducibility."""
    import re

    content = dockerfile_path.read_text()

    # Find all npm install -g commands
    npm_install_pattern = r"npm\s+install\s+-g\s+((?:@[\w-]+/)?[\w-]+(?:@[\w.-]+)?)"
    matches = re.findall(npm_install_pattern, content)

    # Check that each package has a version specifier (@version)
    for package in matches:
        # Count @ symbols: scoped packages have 1, scoped+versioned have 2
        # Non-scoped packages should have 1 for version
        at_count = package.count("@")
        is_scoped = package.startswith("@")

        if is_scoped:
            # Scoped package needs 2 @ symbols (@scope/name@version)
            assert at_count >= 2, (
                f"npm package '{package}' should be pinned to specific version "
                f"(e.g., {package}@2.1.42) for build reproducibility. "
                f"See: https://github.com/mvillmow/ProjectScylla/issues/650"
            )
        else:
            # Non-scoped package needs 1 @ symbol (name@version)
            assert at_count >= 1, (
                f"npm package '{package}' should be pinned to specific version "
                f"(e.g., {package}@1.0.0) for build reproducibility. "
                f"See: https://github.com/mvillmow/ProjectScylla/issues/650"
            )
```

**Key Points**:

- Handles both scoped (`@scope/package`) and non-scoped packages
- Provides helpful error messages with examples
- Prevents future regressions

### 4. Verify Locally

```bash
# Validate Dockerfile syntax
docker build --check docker/

# Run all Docker tests
pytest tests/docker/test_docker_build.py -v

# Specifically verify version pinning test
pytest tests/docker/test_docker_build.py::TestDockerfileContent::test_npm_packages_are_pinned -v

# Optional: Verify installed version in built image
docker build -t scylla-test:local docker/
docker run --rm scylla-test:local npm list -g @anthropic-ai/claude-code
```

### 5. Create PR with Full Context

```bash
# Stage changes
git add docker/Dockerfile tests/docker/test_docker_build.py

# Commit with descriptive message
git commit -m "fix(docker): Pin @anthropic-ai/claude-code to version 2.1.42

Pin the Claude Code CLI npm package to a specific version (2.1.42) in the
Dockerfile to ensure build reproducibility and prevent unexpected breaking
changes when new versions are released.

Changes:
- Update docker/Dockerfile to pin @anthropic-ai/claude-code@2.1.42
- Add inline comments explaining version choice and linking to issue
- Add test_npm_packages_are_pinned() to validate npm packages are versioned
- Test uses regex to detect all npm install -g commands and verifies version pins

Closes #650

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push and create PR
git push -u origin <branch-name>
gh pr create --title "fix(docker): Pin @anthropic-ai/claude-code to version 2.1.42" \
  --body "Closes #650"
gh pr merge --auto --rebase
```

## Failed Attempts

### ❌ Attempt 1: Using package.json for Docker npm installs

**What we tried**: Creating a `package.json` file to manage npm dependencies

**Why it failed**:

- Adds unnecessary complexity for a single global CLI tool
- Docker best practice is to keep images minimal
- Global npm installs (`-g`) don't use package.json
- Violates KISS principle (Keep It Simple Stupid)

**Lesson**: For global CLI tools in Docker, pin directly in the `npm install -g` command rather than introducing additional dependency management files.

### ❌ Attempt 2: Using `latest` tag with comment

**What we tried**: Using `@latest` tag with a comment documenting the version

**Why it failed**:

- `@latest` is dynamic and defeats the purpose of version pinning
- Comments can become stale and misleading
- Doesn't prevent unexpected updates
- Violates the goal of reproducible builds

**Lesson**: Always use exact version numbers (e.g., `@2.1.42`), never tags like `@latest` or `@stable`.

## Results & Parameters

### Configuration Used

```dockerfile
# Dockerfile location
docker/Dockerfile:79

# npm install command (BEFORE)
RUN npm install -g @anthropic-ai/claude-code

# npm install command (AFTER)
RUN npm install -g @anthropic-ai/claude-code@2.1.42
```

### Test Results

```bash
# Test execution
pixi run python -m pytest tests/docker/test_docker_build.py -v

# Results: 20/20 tests passed
# - test_npm_packages_are_pinned() PASSED
# - test_dockerfile_syntax_valid() PASSED
# - All existing Docker tests PASSED
```

### Version Selection Rationale

| Factor | Decision |
|--------|----------|
| **Version chosen** | 2.1.42 |
| **Why this version** | Verified working in #601 during Docker testing |
| **Compatibility** | Tested with Python 3.14.2-slim base image |
| **Risk** | Minimal - pinning to already-verified version |

## Related Skills

- **containerize-e2e-experiments** (evaluation) - Also used version pinning for Python base image
- **fix-docker-platform** (ci-cd) - Docker CI/CD configuration patterns
- **fix-docker-image-case** (ci-cd) - Docker workflow best practices

## Development Principles Applied

1. **KISS** - Minimal change, only pin the version
2. **YAGNI** - Don't add package.json or complex version management
3. **TDD** - Write test to validate the constraint
4. **DRY** - Test is reusable for future npm packages
5. **Best Practices** - Follow existing Dockerfile patterns

## Key Takeaways

1. ✅ **Always pin npm packages in production Dockerfiles** - Use exact versions (`@2.1.42`) not tags (`@latest`)
2. ✅ **Add regression tests** - Prevent future unpinned dependencies with automated tests
3. ✅ **Document version choices** - Use inline comments linking to verification issues/PRs
4. ✅ **Handle both package types** - Tests must cover scoped (`@scope/package`) and non-scoped packages
5. ✅ **Follow existing patterns** - Match the project's approach (e.g., pinned Python base images)

## Files Modified

```
docker/Dockerfile                      # Pinned npm package to v2.1.42
tests/docker/test_docker_build.py      # Added version pinning test
```

## CI/CD Integration

The `docker-test.yml` GitHub Actions workflow automatically validates:

- Dockerfile syntax (`docker build --check`)
- docker-compose.yml configuration
- All pytest tests including new `test_npm_packages_are_pinned()`

This ensures unpinned npm packages are caught in CI before merging.

---

**Status**: ✅ Verified and production-ready
**Maintainer**: ProjectScylla Team
**Last Updated**: 2026-02-15
