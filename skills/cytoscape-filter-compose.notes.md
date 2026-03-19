# Raw Session Notes — cytoscape-filter-compose

## Session Context

**Project**: TitanSchedule — tournament sorting network visualization
**Stack**: Cytoscape.js 3.28, cytoscape-node-html-label, Tailwind CSS (CDN), Python/pixi backend
**Date**: 2026-02-27

## Bug Report (6 bugs fixed)

### Bug 1: Constant re-rendering on every interaction
- `_applyFilters()` unconditionally called `rerunLayout()` (300ms animation + 350ms `fitToVisible`)
- Triggered on background clicks, "All Days" toggle when already active, status filter toggles
- Fix: only call `relayoutVisible()` when a filter is active; just `fitToVisible(40)` otherwise

### Bug 2: Intermediate ranking only shows for last selected day
- `_initDayFilter()` assigned `ranking_intermediate` phases only to `p.date` (the day before the boundary)
- Selecting Day 2 never included the Day 1→Day 2 boundary because it was keyed to Day 1
- Fix: register each boundary phase under BOTH adjacent dates using `sortedMatchDates.find(d => d > p.date)`

### Bug 3: Intermediate ranking nodes are orphans (no edges)
- `_build_team_flow_edges()` only inserted boundaries between `if i < len(timeline) - 1` pairs
- If all matches are on Day 1 and boundary is after last match, boundary never inserted in `result_seq`
- Fix: after main loop, also check `boundary_phase > last_phase` and `boundary_phase < first_phase`

### Bug 4: Team selection ignores day/status filters
- `_applyFilters()` called `clearTrajectory(cy)` in step 1 (reset to visible)
- Steps 2-4 applied day/status filter (hide nodes)
- Step 5 called `activateTrajectory(cy, teamId)` which internally called `clearTrajectory(cy)` again → wiped steps 2-4
- Then hid non-team elements from the FULL graph, not the filtered graph
- Fix: remove `clearTrajectory` from `activateTrajectory`; use `.filter(e => e.visible())` in hide step

### Bug 5: Edges not visible
- CSS: `#cy-wrap { overflow: auto }` conflicted with Tailwind `overflow-hidden` (CSS wins by specificity)
- Edge opacity: 0.5 too low on light background at compact node sizes → raised to 0.7
- The `clearTrajectory` bug also contributed (edges were being re-shown then incorrectly hidden)

### Bug 6: Dead code cleanup
- Dead `sequence: list = list(timeline)` variable in builder.py (assigned, never read)
- `_applyTeamHighlight` one-line wrapper → inlined as direct `activateTrajectory()` call
- `clearTrajectory()` removed `dimmed highlighted` classes that are never applied (hide-based not dim-based)
- Removed unused `.dimmed`, `.highlighted`, `node[type="match"].highlighted`, `node[type="ranking"].highlighted`, `edge.highlighted` selectors from graph.js

## Test Results

Before: 154 tests (all passing)
After: 163 tests (all passing, +9 new)

New test added: `test_no_orphan_intermediate_ranking_nodes` in `TestIntermediateRankings`

## Key Insight: Single-Owner Pattern for Composed Visibility

When multiple independent filters must compose (AND logic) over a Cytoscape graph:
1. One function owns the full visibility lifecycle: reset → apply filter A → apply filter B → apply filter C
2. Each subsequent filter reads `e.visible()` to respect prior filters
3. NO helper function resets visibility — they only add hiding on top of the current state
4. `clearTrajectory()` (full reset) is kept only for user-initiated "reset everything" actions

This is the same pattern as CSS cascade / layered rendering — later layers compose on top of earlier ones without resetting the canvas.

## Re-scrape Requirement

Bug 3 (orphan nodes) is in builder.py and affects `tournament.json` output. If the tournament has matches on multiple days, the JSON must be regenerated with `pixi run scrape <URL>`. Single-day tournaments are unaffected.