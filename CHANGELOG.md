# Changelog

All notable changes to ProjectMnemosyne will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Renamed `skills-registry-commands` plugin to `mnemosyne`.
- Renamed `/retrospective` command to `/learn`.

### Added
- `CONTRIBUTING.md` with skill contribution guidelines, quality standards, and PR process.
- `CHANGELOG.md` in Keep a Changelog format.

## [2.1.0] - 2026-03-22

### Added
- New skills: container-image-security-patching, tooling-shared-scripts-pypi-centralization, mojo-circular-import-type-identity-fix, documentation-strict-audit-remediation-workflow, mojo-overload-ambiguity-typed-tensor-isolation, pypi-trusted-publishing-setup, tensor-dtype-native-ops-inversion, resource-manager-pattern, e2e-resource-exhaustion.
- Hook support for `once: true` field to execute hooks only once per session.

## [2.0.1] - 2026-03-20

### Fixed
- Removed legacy `build/$$` and `build/ProjectMnemosyne` directory references.
- Corrected mnemosyne source path in marketplace.
- Resolved marketplace validation issues and missing frontmatter fields.
- Enforced kebab-case names in skill frontmatter.
- Migrated 29 remaining old-format skills to flat structure.

### Added
- New skills: mojo-escaping-signature-regression, batch-subprocess-signal-hang, fix-podman-rootless-ci.

## [2.0.0] - 2026-03-19

### Changed
- **BREAKING**: Migrated all 930 skills from nested directory format to flat file format.
- Skills are now single `.md` files with YAML frontmatter in the `skills/` directory.
- Branch naming changed from `skill/<category>/<name>` to `skill/<name>`.
- Skill filenames follow `<topic>-<subtopic>-<short-4-word-summary>.md` convention.
- Updated `/advise` and `/learn` commands for flat file format.
- Updated validation scripts, marketplace generation, templates, docs, and CI.

### Added
- New skills: podman-from-source-install, docker-to-podman-migration, podman-nextjs-ci-container.

## [1.2.0] - 2026-03-17

### Added
- New skills: checkpoint-test-fixture-patterns, docker-pixi-isolation, batch-pr-rebase-conflict-resolution, semantic-pr-rebase-at-scale, audit-implementation, mass-pr-rebase-parallel-agents, checkpoint-intermediate-state-resume, mojo-bitcast-uaf-blog-and-ci-fix.

## [1.1.0] - 2025-12-29

### Added
- `/advise` and `/learn` slash commands.
- mnemosyne plugin infrastructure.
- Initial batch of skills: batch-pr-ci-fix, claude-plugin-format, retrospective-hook-integration.

### Fixed
- Corrected plugin schema for Claude Code compatibility.
- Updated marketplace to official Claude Code plugin format.
- Removed non-standard fields from plugin.json and SKILL.md files.

## [1.0.0] - 2025-12-28

### Added
- Skills marketplace with `/advise` and `/learn` commands.
- `marketplace.json` for searchable skill index.
- Plugin validation with `validate_plugins.py`.
- CI pipeline for PR validation.

## [0.1.0] - 2025-12-12

### Added
- Initial project setup.
- README with project overview and installation instructions.

[Unreleased]: https://github.com/HomericIntelligence/ProjectMnemosyne/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/HomericIntelligence/ProjectMnemosyne/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/HomericIntelligence/ProjectMnemosyne/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/HomericIntelligence/ProjectMnemosyne/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/HomericIntelligence/ProjectMnemosyne/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/HomericIntelligence/ProjectMnemosyne/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/HomericIntelligence/ProjectMnemosyne/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/HomericIntelligence/ProjectMnemosyne/releases/tag/v0.1.0
