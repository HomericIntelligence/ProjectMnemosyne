# Session Notes: PyPI Trusted Publishing Setup

## Date: 2026-03-22

## Context
- Repository: HomericIntelligence/ProjectHephaestus
- Issues: #36, #37, #38
- Goal: Publish v0.4.0 to PyPI using OIDC trusted publishing

## Timeline

1. GitHub `pypi` environment had `protected_branches: true` — already fixed by user
2. v0.3.2 tag had broken workflow (hardcoded SHA + API token) — skipped, v0.4.0 supersedes
3. v0.4.0 triggered, got 403 Forbidden — added verbose logging via PR
4. Verbose revealed distribution name mismatch: `hephaestus` vs PyPI `HomericIntelligence`
5. User wanted namespace packages: changed to `HomericIntelligence-Hephaestus`
6. Had to update pixi.toml, pixi.lock, integration test wheel glob (lowercase), mypy issue
7. Got `400 Non-user identities cannot create new projects` — needed pending publisher
8. After pending publisher registered, v0.4.0 published successfully

## Key Insight
PyPI error messages are HTML-formatted and only visible with `verbose: true`. Without it you only get bare `403 Forbidden` or `400 Bad Request`.

## PRs Created
- #39: Enable verbose PyPI publish
- #40: Change distribution name + fix CI
