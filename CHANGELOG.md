# Changelog

All notable changes to the Mnemosyne skills marketplace are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: semver,
sourced from `pyproject.toml` `[project].version`.

Release policy: patch = fixes/CI/infra, minor = new tooling or marketplace-format
features, major = breaking layout/format changes (e.g. the flat-skills migration).

## [Unreleased]

## [2.1.0] - 2026-07-03

- Baseline release-contract anchor for the existing 2.1.0 marketplace
  (flat `skills/` layout, `once: true` hook support). Establishes the
  version-sync + changelog contract validated by the `release` CI check
  (#2913). Earlier history predates this changelog.
