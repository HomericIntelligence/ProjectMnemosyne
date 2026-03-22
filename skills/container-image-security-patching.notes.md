# Session Notes: Container Image Security Patching

## Date: 2026-03-22

## Context
- docker-build-timing CI workflow failing on ALL branches since 2026-03-19
- Trivy scan found 13 HIGH CVEs (2 OS, 11 npm)
- Pinned base images: python:3.12-slim and node:20-slim with SHA256 digests

## CVEs Found
- libc-bin CVE-2026-0861 (glibc integer overflow, fixed in 2.41-12+deb13u2)
- cross-spawn CVE-2024-21538 (ReDoS)
- glob CVE-2025-64756 (command injection)
- minimatch CVE-2026-26996, CVE-2026-27903, CVE-2026-27904 (DoS)
- tar CVE-2026-23745, CVE-2026-23950, CVE-2026-24842, CVE-2026-26960, CVE-2026-29786, CVE-2026-31802 (file overwrite/traversal)

## Fix Applied
1. Bumped python:3.12-slim digest from f3fa41d... to 3d5ed97...
2. Bumped node:20-slim digest from eef3816... to 17281e8...
3. Added `apt-get upgrade -y` in runtime stage
4. Added `npm audit fix --force` after claude-code install
5. Updated both docker/Dockerfile and ci/Containerfile
