# Reference Notes: parallel-issue-wave-execution

## Session Context

- **Project**: ProjectScylla (AI agent testing framework)
- **Date**: 2026-03-01
- **Scope**: 35 LOW-difficulty issues from a 71-issue backlog, classified into LOW/MEDIUM/HIGH

## Issue Classification (35 LOW issues implemented)

Issues grouped by area:

| Area | Count | Examples |
|------|-------|---------|
| Config (pyproject.toml) | 7 | #1156 markers, #1192 --cov=scripts, #1191 pythonpath, #1167 py3.13 classifier, #1212 S101, #1207 hatchling pin, #1192 cov |
| Docker | 4 | #1141 hatchling pin, #1209 pip pins, #1138 tomllib fallback, #1176 tomllib .get() |
| Tests | 8 | #1165 TierID, #1197 figs, #1213 checkout, #1155 config hash, #1175 Dockerfile layers, #1218 sleep mock, #1128 conftest, #1188 process metrics |
| Code | 7 | #1222 heartbeat, #1178 numstat, #1185 strategic drift, #1219 jitter, #1130 rubric_weights, #1184 dropna, #1129 rubric_conflict |
| CI | 3 | #1229 doc consistency, #1123 structure check, #1160 entrypoint trigger |
| Docs | 3 | #1169 SHA256 procedure, #1161 docker secrets, #1205 EXTRAS |
| Config (pixi.toml) | 1 | #1119 upper bounds |
| Scripts | 2 | #1193 pythonpath audit, #1227 cov-fail-under check |

## Wave Execution Timeline

Each wave took ~5-10 minutes. All 8 waves completed sequentially with parallel agents within each wave.

## Coverage Fix (PR #1266) — Key Enabler

The most impactful fix of the session was identifying that `--cov-fail-under=75` in `addopts` applied globally to ALL pytest runs including integration tests which only reach ~12% coverage. This caused every PR that touched `pyproject.toml` to fail CI on the integration test step.

**Before fix** (pyproject.toml):
```toml
addopts = ["-v", "--strict-markers", "--cov=scylla", "--cov-report=term-missing", "--cov-report=html", "--cov-fail-under=75"]
```

**After fix** (pyproject.toml):
```toml
addopts = ["-v", "--strict-markers", "--cov=scylla", "--cov=scripts", "--cov-report=term-missing", "--cov-report=html", "--cov-fail-under=9"]
```

**After fix** (test.yml unit step):
```yaml
pixi run pytest "$TEST_PATH" --override-ini="addopts=" -v --strict-markers --cov=scylla --cov-report=term-missing --cov-report=xml --cov-fail-under=75
```

The fix was PR #1266 which merged before fix-pass PRs (#1272–#1277) were created.

## PRs Created

| Wave | PRs | Notes |
|------|-----|-------|
| 1 | #1231–#1235 | All merged |
| 2 | #1236–#1240 | All merged |
| 3 | #1241–#1244 | All merged |
| 4 | #1245–#1249 | All merged |
| 5 | #1250–#1253 | All merged |
| 6 | #1254–#1257 | All merged |
| 7 | #1258–#1261 | All merged |
| 8 | #1262–#1265 | #1265 superseded (2x) |
| Fix pass | #1266–#1277 | #1266 coverage fix; #1267–#1276 replacements for stale PRs |

## PRs Superseded / Closed

| Old PR | New PR | Reason |
|--------|--------|--------|
| #1231 → #1269 → #1270 → #1272 | #1272 | pixi.lock stale, pre-#1266 main |
| #1237 | #1266 | Redesigned per user feedback (9% threshold) |
| #1262 | #1267 | pixi.lock conflict |
| #1265 | #1268 → #1271 → #1276 | Python constraint, then altair <6 issue |
| #1170 | #1271 (→ #1276) | Pre-#1266 main |
| #1183 | #1273 | Pre-#1266 main + cherry-pick conflict |
| #1195 | #1274 | Pre-#1266 main + ruff-format failure |
| #1203 | #1275 | Pre-#1266 main; hatchling version bumped 1.27→1.29 |
| #1109 | #1277 | 66 commits stale; complex cherry-pick into ResumeManager/TierActionBuilder |

## altair Version Discovery

The altair `<6` vs `<7` issue was discovered by comparing:
- PR #1271 (failing): `altair 5.5.0` installed → Python 3.14t TypeError
- Main branch (passing): `altair 6.0.0` installed (no upper bound → latest)

The fix required BOTH editing `pixi.toml` to `<7` AND running `pixi update altair` because `pixi install` alone keeps the cached 5.5.0 entry.

## PR #1109 Rebase Details

The ProcessPool checkpoint fix PR had 6 original commits but main had undergone major refactoring since it was created:
- `_initialize_or_resume_experiment()` was decomposed into `ResumeManager` class
- `_build_tier_actions()` was moved into `TierActionBuilder` class

All 6 commits had conflicts. The agent had to port the fixes into the new code structure:
- Resume bug fixes → `ResumeManager._restore_failed_state()`, `_reset_incomplete_tiers()`
- Checkpoint merge fix → `TierActionBuilder.action_config_loaded()` with `checkpoint_merge_lock`
- `stage_execute_agent` guard → lazy reconstruction (HEAD had `RuntimeError`)

Final result: 9 commits on PR #1277, all 1382 tests passing.
