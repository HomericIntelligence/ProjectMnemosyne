# Changelog

All notable changes to the Mnemosyne skills/memory store are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: semver,
sourced from `pyproject.toml` `[project].version`.

Release policy: patch = fixes/CI/infra, minor = new tooling or skill-format
features, major = breaking layout/format changes (e.g. the flat-skills migration).

## [Unreleased]

## [3.0.0] - 2026-07-13

### Changed

- **Mnemosyne is no longer a plugin marketplace.** Athena is the plugin
  distribution; Mnemosyne is now purely a skills/session-memory store. Removed
  the generated `.claude-plugin/marketplace.json` (823 KB), `.claude-plugin/plugin.json`,
  `scripts/generate_marketplace.py`, `scripts/build_package.py`,
  `schemas/marketplace.schema.json`, the `update-marketplace.yml` and dead
  `_checks.yml` workflows, and every marketplace-parsing step in `_required.yml`.
- The `package` CI gate now builds the Python wheel/sdist (`mnemosyne_skill_utils`)
  instead of a marketplace bundle; `release.yml` publishes a skills-corpus snapshot.
- Skill-file validation (`scripts/validate_plugins.py`) and the wheel are retained
  as the memory store's quality gates.

## [2.1.0] - 2026-07-03

- Baseline release-contract anchor for the existing 2.1.0 marketplace
  (flat `skills/` layout, `once: true` hook support). Establishes the
  version-sync + changelog contract validated by the `release` CI check
  (#2913). Earlier history predates this changelog.
