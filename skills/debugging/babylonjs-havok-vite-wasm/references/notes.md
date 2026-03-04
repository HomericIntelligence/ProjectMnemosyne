# Session Notes: babylonjs-havok-vite-wasm

## Verified Examples

### Example 1: SoccerGame

**Date**: 2026-03-03
**Context**: Babylon.js 7.x soccer game (TypeScript + Vite 5). Clicking "Start Match" showed a persistent blue screen. No error was visible on screen because `_init()` errors were caught and displayed as text on the loading UI — but the WASM failure caused `_init()` to throw before `_showErrorUI()` could render.

**Symptoms in DevTools console**:
```
wasm streaming compile failed: TypeError: Failed to execute 'compile' on 'WebAssembly': Incorrect response MIME type. Expected 'application/wasm'.
falling back to ArrayBuffer instantiation
failed to asynchronously prepare wasm: CompileError: WebAssembly.instantiate(): expected magic word 00 61 73 6d, found 3c 21 44 4f @+0
Aborted(CompileError: ...)
RuntimeError: Aborted(...)
Uncaught Error: No camera defined  ← from scene.render() in render loop
```

**Root cause**: `3c 21 44 4f` = `<!DO` = `<!DOCTYPE` — Vite was returning its index.html SPA fallback for the WASM request, because `/HavokPhysics.wasm` was not a recognized static file path.

**Fix applied**:
```bash
cp node_modules/@babylonjs/havok/lib/esm/HavokPhysics.wasm public/HavokPhysics.wasm
```

```typescript
// MatchScene.ts constructor
this._tempCam = new FreeCamera('_tempCam', new Vector3(0, 10, 0), this._scene);
this._tempCam.setTarget(Vector3.Zero());

// MatchScene.ts _init() — HavokPhysics call
const havok = await HavokPhysics({
  locateFile: (path: string) => {
    console.log('[MatchScene] HavokPhysics locateFile:', path, '->', `/${path}`);
    return `/${path}`;
  }
});

// MatchScene.ts _init() — before real camera
this._tempCam.dispose();
this._camera = new CameraManager(this._scene);
```

**Stack**: Babylon.js 7.x, `@babylonjs/havok` npm package, Vite 5.6, TypeScript, WSL2/Linux

---

## Raw Findings

- `optimizeDeps.exclude: ['@babylonjs/havok']` was already set (correctly) but didn't help WASM serving
- `assetsInclude: ['**/*.wasm']` was tried first — confirmed ineffective for dev server static serving
- The WASM file is 2MB at `node_modules/@babylonjs/havok/lib/esm/HavokPhysics.wasm`
- Vite's `.vite/deps/_metadata.json` correctly showed `@babylonjs/havok` excluded from pre-bundling
- The "No camera" error is a secondary failure that occurs because the render loop starts in the constructor, before the async init that creates the camera
- Both bugs (WASM + camera) need fixing together — fixing only WASM makes the scene load but you'll still see the "No camera" flicker on slower machines

## External References

- Babylon.js Havok integration: https://doc.babylonjs.com/features/featuresDeepDive/physics/usingPhysicsEngine
- Vite static asset serving: https://vitejs.dev/guide/assets.html (public/ directory section)
