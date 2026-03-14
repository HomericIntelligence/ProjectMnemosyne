---
name: xterm-plan-mode-fix
description: Fix xterm.js rendering of TUI modes (Claude Code /plan) in browser-based terminals with Unicode11 addon, binary WebSocket handling, and resize timing
category: architecture
date: 2026-03-13
user-invocable: false
---

# xterm.js /plan Mode Rendering Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-13 |
| **Objective** | Fix Claude Code `/plan` mode rendering in browser-based xterm.js terminal (box-drawing characters, emojis, and TUI layout corruption) |
| **Outcome** | Successful — 3-layer fix (Unicode11 addon + binary WebSocket + resize timing) resolves all rendering issues |

## When to Use

- xterm.js renders TUI apps (Claude Code `/plan`, vim, htop) with corrupted layout
- Box-drawing characters (Unicode) display as `?` or wrong-width glyphs
- Emojis and wide characters cause column misalignment
- Terminal dimensions are wrong on initial connection (80x24 default instead of actual size)
- WebSocket drops binary PTY data silently
- Auto-detected device type forces wrong UI layout on touch-capable laptops/WSL

## Verified Workflow

### Step 1: Add `@xterm/addon-unicode11`

The Unicode11 addon fixes wide character width calculations. Without it, xterm.js uses Unicode 6 tables which miscalculate widths for box-drawing, emojis, and CJK characters.

```bash
yarn add @xterm/addon-unicode11
```

```typescript
// hooks/useTerminal.ts — load after fit/weblinks, before clipboard
try {
  const { Unicode11Addon } = await import('@xterm/addon-unicode11')
  const unicode11Addon = new Unicode11Addon()
  terminal.loadAddon(unicode11Addon)
  terminal.unicode.activeVersion = '11'
} catch (e) {
  console.warn('[Terminal] Unicode11Addon not available:', e)
}
```

**Key detail:** Must set `terminal.unicode.activeVersion = '11'` after loading — loading alone doesn't activate it.

### Step 2: Handle binary WebSocket data

PTY can send binary frames. Without explicit handling, `event.data` may be a Blob that xterm.js silently drops.

```typescript
// hooks/useWebSocket.ts
ws.binaryType = 'arraybuffer'

ws.onmessage = (event) => {
  if (event.data instanceof ArrayBuffer) {
    onMessageRef.current?.(new TextDecoder().decode(event.data))
    return
  }
  // ... existing JSON parsing
}
```

### Step 3: Fix resize timing

PTY spawns with hardcoded 80x24. If `/plan` renders before resize arrives, layout is wrong.

**Client side** — pass dimensions in WebSocket URL and send resize on open:

```typescript
// hooks/useWebSocket.ts — add cols/rows to URL
const url = `ws://host/term?name=${session}&cols=${cols}&rows=${rows}`

// components/TerminalView.tsx — send resize immediately on open
onOpen: () => {
  const term = terminalInstanceRef.current
  if (term) {
    const resizeMsg = createResizeMessage(term.cols, term.rows)
    setTimeout(() => sendMessage(resizeMsg), 0)
  }
}
```

**Server side** — use client dimensions for PTY spawn:

```javascript
// server.mjs
const initialCols = parseInt(query.cols, 10) || 80
const initialRows = parseInt(query.rows, 10) || 24
ptyProcess = pty.spawn(cmd, args, {
  name: 'xterm-256color',
  cols: initialCols,
  rows: initialRows,
  // ...
})
```

### Step 4: Layout toggle (bonus discovery)

Auto-detection of device type (`useDeviceType` hook) can misclassify touch-capable laptops and WSL environments as tablets, forcing a mobile-style layout that hides navigation. Replace auto-detection with a user-controlled toggle persisted in localStorage.

```typescript
const [layoutOverride, setLayoutOverride] = useState<'tablet' | 'desktop' | null>(() => {
  const saved = localStorage.getItem('aimaestro-layout-mode')
  return saved === 'tablet' || saved === 'desktop' ? saved : null
})
const effectiveLayout = isMobile ? 'phone' : (layoutOverride || deviceType)
```

## Failed Attempts

| Attempt | Why It Failed |
|---------|---------------|
| Adding navigation buttons only to `Header.tsx` (desktop layout) | User was on TabletDashboard (auto-detected as tablet on WSL/touch laptop). Buttons never appeared. |
| Inline agent creation form in sidebar | Too complex for the sidebar UI; user just wanted navigation to the setup wizard |
| Linking `+` button to `/zoom` page | Wrong destination — user wanted the agent creation/setup wizard, not the zoom view |
| Linking `+` button to `/settings?section=onboarding` | Correct destination but caused hydration error (OnboardingSection reads localStorage on render). Fixed with `dynamic(() => import(...), { ssr: false })` |
| Auto-detecting tablet vs desktop via `useDeviceType` | Unreliable on WSL, touch-capable laptops, and hybrid devices. Root cause of the entire navigation issue. |

## Results & Parameters

### Dependencies

```json
{
  "@xterm/addon-unicode11": "^0.9.0"
}
```

### Terminal Configuration

```typescript
// Critical xterm.js settings for PTY/tmux
{
  convertEol: false,           // PTY handles line endings
  unicode: { activeVersion: '11' },  // After loading Unicode11Addon
  windowOptions: { setWinLines: true }  // Alternate buffer support
}
```

### WebSocket Configuration

```typescript
{
  binaryType: 'arraybuffer',   // Handle binary PTY frames
  // Pass initial dimensions in URL: ?cols=X&rows=Y
}
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| AI Maestro | Issue #279 (xterm fix), #280 (nav buttons), #281 (layout toggle) | [notes.md](../references/notes.md) |
