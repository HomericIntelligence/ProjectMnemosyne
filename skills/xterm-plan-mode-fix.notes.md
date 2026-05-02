# xterm-plan-mode-fix — Session Notes

## Project Context

- **Project:** AI Maestro (Claude Code Dashboard)
- **Repository:** 23blocks-OS/ai-maestro
- **Issues Filed:** #279 (xterm /plan fix), #280 (navigation buttons), #281 (layout toggle)
- **Date:** 2026-03-13

## Problem Statement

Claude Code's `/plan` mode renders correctly in the native CLI terminal but displays with corrupted layout in the browser-based xterm.js terminal. The raw PTY data is sent unfiltered through the WebSocket pipeline (server.mjs → WebSocket → xterm.js), so no data loss occurs. The corruption manifests as:

- Box-drawing characters rendered at wrong widths
- Emoji/wide characters causing column misalignment
- TUI layout shifted/broken on initial render

A secondary problem discovered during the session: the dashboard auto-detected the user's WSL/touch-capable laptop as a "tablet," forcing a mobile-style layout that hid the desktop navigation header entirely.

## Root Cause Analysis

### Rendering Corruption (3 causes)

1. **Missing Unicode11 addon** — xterm.js defaults to Unicode 6 character width tables. Claude Code `/plan` uses Unicode box-drawing, emojis, and wide characters that need Unicode 11+ width calculations.

2. **Binary WebSocket data dropped** — PTY can emit binary frames. Without `ws.binaryType = 'arraybuffer'`, the browser delivers a Blob object that the existing JSON parser silently drops.

3. **Resize timing gap** — PTY spawns at hardcoded 80x24. The client only sends a resize after the `history-complete` event (with delays). If `/plan` renders before resize arrives, it uses wrong dimensions.

### Layout Misdetection (1 cause)

4. **`useDeviceType` hook** classifies devices by screen width + touch capability. On WSL with a touch-capable display, it returns "tablet" even on a desktop. This loads `TabletDashboard` instead of the desktop `Header`, hiding all navigation buttons.

## Files Modified

| File | Change |
| ------ | -------- |
| `package.json` | Added `@xterm/addon-unicode11: ^0.9.0` |
| `hooks/useTerminal.ts` | Load Unicode11Addon, set activeVersion to '11' |
| `hooks/useWebSocket.ts` | Set binaryType='arraybuffer', handle ArrayBuffer in onmessage, pass cols/rows in URL |
| `components/TerminalView.tsx` | Track terminal dims in ref, pass to useWebSocket, send resize on open |
| `server.mjs` | Read cols/rows from query params for PTY spawn |
| `app/page.tsx` | Added layoutOverride state with localStorage, toggleLayout function |
| `components/Header.tsx` | Added Settings link, Tablet toggle button, onSwitchLayout prop |
| `components/TabletDashboard.tsx` | Added Monitor toggle button, onSwitchLayout prop |
| `app/settings/page.tsx` | Added useSearchParams for ?section= deep-linking, Suspense boundary, dynamic import for OnboardingSection |

## Iteration History

1. Implemented the 3-part xterm fix (Unicode11, binary WS, resize timing)
2. User couldn't see navigation buttons → discovered they were on TabletDashboard
3. Added buttons to TabletDashboard → worked but wrong UX (inline create form)
4. Tried linking + button to /zoom → wrong destination
5. Linked to /settings?section=onboarding → hydration error (localStorage in SSR)
6. Fixed hydration with dynamic() import and Suspense
7. User realized the real problem was auto-detection → implemented layout toggle
8. Removed the + button entirely, kept Settings and layout toggle

## Key Learnings

- **Always check which layout component is active** before adding UI elements. Auto-detection can route to unexpected components.
- **`dynamic(() => import(...), { ssr: false })`** is the correct fix for components that read localStorage/sessionStorage during render.
- **`useSearchParams()` requires a Suspense boundary** in Next.js App Router.
- **xterm.js Unicode version must be explicitly activated** — loading the addon alone is not enough.
- **Layout auto-detection is unreliable** on hybrid devices (WSL, touch laptops, Chromebooks). Prefer user-controlled toggles with auto-detection as a default.
