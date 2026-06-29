---
name: tooling-codex-plugin-symlink-empty-cache-fix
description: "Diagnose and fix Codex plugin marketplace installs that report enabled while the plugin cache is empty because the marketplace target contains symlinked .codex-plugin or skills directories. Use when: (1) a Codex plugin installs but exposes no skills, (2) the plugin cache is empty after marketplace install, (3) a repo-side materialized wrapper is needed while filing an upstream installer fix."
category: tooling
date: 2026-06-29
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [codex, plugin, marketplace, symlink, cache, packaging, drift]
---

# Codex Plugin Symlink Empty Cache Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-29 |
| **Objective** | Fix a Codex marketplace plugin that was enabled in config but installed an empty plugin cache because the marketplace target used symlinked `.codex-plugin` and `skills` directories |
| **Outcome** | Repo-side materialized wrapper merged and verified in CI; upstream installer follow-up documented separately because materialization duplicates the canonical skill payload |
| **Verification** | verified-ci |

## When to Use

- A Codex plugin appears enabled in config but none of its skills are available in a new session.
- `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/` is empty or missing `.codex-plugin/plugin.json` and `skills/*/SKILL.md`.
- `.agents/plugins/marketplace.json` points at a compatibility wrapper such as `plugins/<plugin>`, and that wrapper contains symlinks to the canonical plugin manifest or skill tree.
- You need a safe repo-side workaround now, but want to track the correct upstream installer behavior so the repo does not permanently duplicate thousands of lines.

## Verified Workflow

### Quick Reference

```bash
# Inspect the marketplace target and installed cache.
jq '.plugins[] | select(.name == "<plugin-name>")' .agents/plugins/marketplace.json
find plugins/<plugin-name> -maxdepth 2 -ls
find ~/.codex/plugins/cache/<marketplace-name>/<plugin-name>/<version> -maxdepth 3 -type f -print

# Repo-side workaround: materialize the wrapper instead of relying on symlinks.
rm -rf plugins/<plugin-name>/.codex-plugin plugins/<plugin-name>/skills
mkdir -p plugins/<plugin-name>/.codex-plugin plugins/<plugin-name>/skills
rsync -a --delete .codex-plugin/ plugins/<plugin-name>/.codex-plugin/
rsync -a --delete skills/ plugins/<plugin-name>/skills/

# Guard against regressing to an empty installable payload.
python3 -m pytest tests/unit/validation/test_codex_plugin_packaging.py -q --no-cov
bash scripts/check-symlinks.sh
```

### Detailed Steps

1. Confirm the observed symptom is a packaging/install issue, not a skill frontmatter issue:
   - Codex config lists the plugin as enabled.
   - The marketplace checkout contains the expected canonical `skills/<name>/SKILL.md` files.
   - The installed plugin cache is empty or lacks the manifest and skill files.
2. Inspect the marketplace entry:
   - Find the plugin in `.agents/plugins/marketplace.json`.
   - Resolve `source.path`, usually `./plugins/<plugin-name>`.
3. Inspect the wrapper path with `find <path> -maxdepth 2 -ls`.
   - If `.codex-plugin` or `skills` are symlinks, assume the installer may copy the wrapper without dereferencing the payload.
4. Fix the repo-side package by replacing those symlinks with physical directories and files:
   - `plugins/<plugin-name>/.codex-plugin/plugin.json`
   - `plugins/<plugin-name>/skills/<skill>/SKILL.md`
   - any non-skill helper files needed by the skill tree
5. Add a packaging regression test that enforces all of these conditions:
   - marketplace source points at the expected wrapper path;
   - wrapper contains no symlinks;
   - wrapper manifest bytes match the canonical `.codex-plugin/plugin.json`;
   - wrapper skill files match the canonical `skills/` tree byte-for-byte;
   - copying the wrapper into an install-cache-shaped temp directory leaves advertised skills present.
6. Run targeted validation and the repo's required checks.
7. File or update an upstream issue/comment for the installer behavior. The long-term fix should either safely dereference symlinks into the plugin cache or reject symlinked plugin payloads with a clear diagnostic instead of reporting an enabled empty plugin.

### Upstream Installer Requirements

If fixing the installer instead of a consuming repo, dereference only with containment checks:

1. Resolve each symlink target.
2. Require the resolved target to remain inside the marketplace checkout.
3. Reject symlink loops and missing targets.
4. Fail closed with a clear diagnostic on unsafe paths.
5. Add an installer-level regression test that installs a marketplace plugin whose wrapper symlinks `.codex-plugin` and `skills` back to canonical directories.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Symlinked marketplace wrapper | `plugins/<plugin>/.codex-plugin -> ../../.codex-plugin` and `plugins/<plugin>/skills -> ../../skills` | Codex reported the plugin enabled but installed an empty plugin cache, so no skills appeared in new sessions | Treat symlinked plugin payloads as unsupported until the installer explicitly dereferences or rejects them |
| Only checking canonical `skills/` | Verified the source checkout had `skills/advise/SKILL.md` and `skills/learn/SKILL.md` | The failing artifact was the installed plugin cache, not the canonical source tree | Always inspect the marketplace target and installed cache shape, not just the repo root |
| Generic plugin validation only | Relied on plugin/skill validators aimed at canonical skill trees | Repo-specific helper directories such as `_repo_analyze_common` can confuse generic validators, and validators may not simulate cache installation | Add a packaging regression targeted at the actual marketplace wrapper and install-cache shape |
| Repo-side materialization as the whole answer | Replaced symlinks with physical files under `plugins/<plugin>` | It fixed the immediate install failure but duplicated 8,646 mirrored lines and created drift risk | Use materialization as a workaround, then track the upstream installer fix so the repo can return to a single canonical payload |

## Results & Parameters

### Regression Test Shape

```python
def test_codex_marketplace_payload_is_materialized_and_installable(tmp_path):
    plugin_root = repo_root / "plugins" / "<plugin-name>"
    plugin_manifest = plugin_root / ".codex-plugin" / "plugin.json"
    plugin_skills = plugin_root / "skills"

    assert plugin_manifest.is_file()
    assert plugin_skills.is_dir()
    assert not [path for path in plugin_root.rglob("*") if path.is_symlink()]
    assert plugin_manifest.read_bytes() == (repo_root / ".codex-plugin" / "plugin.json").read_bytes()

    cache_dir = tmp_path / "cache" / "<marketplace-name>" / "<plugin-name>" / "<version>"
    shutil.copytree(plugin_root, cache_dir)
    assert (cache_dir / ".codex-plugin" / "plugin.json").is_file()
    assert (cache_dir / "skills" / "advise" / "SKILL.md").is_file()
```

### Verified Outcome

| Item | Result |
|------|--------|
| Immediate fix | Materialized `plugins/hephaestus/.codex-plugin` and `plugins/hephaestus/skills` |
| Regression coverage | No symlinks, byte-for-byte manifest/skill parity, install-cache-shaped copy |
| Local validation | Targeted pytest, ruff, format check, symlink check, and full pre-push pytest passed |
| CI validation | GitHub required checks passed before merge |
| Drift risk | 8,646 mirrored lines; track upstream installer fix to remove duplication later |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1644 / PR #1651 Codex marketplace plugin installed empty when wrapper used symlinked `.codex-plugin` and `skills` directories | PR #1651 merged with all checks passing; issue #1644 closed; upstream follow-up comment recorded installer dereference-or-fail-closed requirement |
