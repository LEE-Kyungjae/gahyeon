# Desktop + Looking Glass runtime POC v091

> Retired historical POC: Electron is not a supported Gahyeon service runtime. The canonical
> character service is Unreal and must be launched through
> `scripts/launch_canonical_macos_runtime.py`. Commands below are preserved only as historical
> evidence and are blocked by `desktop/package.json`.

This iteration keeps macOS and Windows as required Desktop targets. Looking Glass
physical presentation remains Win64-only because the pinned official plugin is
Win64-only. A monitor quilt is never physical-device evidence.

## Shared contracts

- Unreal Engine: 5.8
- Character Blueprint contract: `/Game/Gahyeon/CharacterPipeline/v088/AssembledMedium/Skotukeda_WardrobeGroomQA_v088/BP_Skotukeda_WardrobeGroomQA_v088`
- Retained QA source map: `/Game/Gahyeon/CharacterPipeline/v089/Preview/L_Skotukeda_WardrobeGroom_v089`
- Desktop runtime map: `/Game/Gahyeon/DesktopRuntime/v091/L_GahyeonDesktopRuntime_v091`
- Desktop states: `idle`, `listening`, `thinking`, `speaking`
- Optional inputs: emotion, gaze target, viseme
- Window presets: `standard`, `character`

## Electron Desktop

Build and test on either host:

```bash
cd desktop
npm test -- --run
npm run build
```

macOS package and launch:

```bash
npm run package -- --mac
GAHYEON_DESKTOP_WINDOW_PRESET=character \
GAHYEON_DESKTOP_ALWAYS_ON_TOP=true \
release/mac-arm64/Gahyeon.app/Contents/MacOS/Gahyeon
```

Windows package and launch in PowerShell:

```powershell
cd desktop
npm ci
npm run package -- --win --x64
$env:GAHYEON_DESKTOP_WINDOW_PRESET = 'character'
$env:GAHYEON_DESKTOP_ALWAYS_ON_TOP = 'true'
& .\release\win-unpacked\Gahyeon.exe
```

Set `GAHYEON_DESKTOP_CLICK_THROUGH=true` only with the `character` preset. Invalid
values fail closed. The character preset is transparent and frameless, removes the
conversation and environment surfaces, keeps a draggable stage region, and exposes
face/bust/full framing controls. Without `VITE_GAHYEON_HERO_MODEL_URL` it honestly
shows the geometric fallback character; no VRM or MetaHuman substitution is implied.

## Unreal Desktop runtime

macOS:

```bash
python3 scripts/run_desktop_runtime_poc_v091.py --platform macos
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_desktop_runtime_poc_v091_windows.ps1 `
  -UnrealRoot 'C:\Program Files\Epic Games\UE_5.8' `
  -EvidenceRoot artifacts\desktop-looking-glass-runtime-poc-v091\windows-native
```

The cross-platform Python launcher supervises Unreal Editor `-game` and is useful
for iteration. The PowerShell gate above is the Windows acceptance path: it
packages Win64, requires exactly one `GahyeonStage.exe`, observes a native window,
captures evidence, checks the v091 map and visual-host log contract, then shuts
down and restarts the executable. It fails closed on a non-Windows host.

For repeatable remote evidence, register a self-hosted GitHub Actions runner with
the labels `Windows`, `X64`, and `unreal-5.8`, set `GAHYEON_UE_ROOT` only when UE is
not installed at the default path, then manually dispatch `Unreal Runtime
Contracts` with `run_native_windows=true`. The job always uploads its logs,
screenshots, hashes, and manifest as `gahyeon-v091-windows-<run>-<attempt>`.

Build a real macOS game package with the v091 Desktop map explicitly cooked:

```bash
bash scripts/package_unreal_desktop_poc_v091.sh
```

UE 5.8 currently archives a thin macOS app without its staged `Contents/UE`
payload. The script preserves that thin output for diagnosis and promotes the
signed staged app only after verifying `libtbb.12.dylib`, the project `.utoc`, and
the project `.ucas`. `GAHYEON_PROMOTE_STAGED_ONLY=1` may only be used to inventory
an already successful staged build; it does not claim a new build/cook.

## Looking Glass pre-device check

```bash
python3 scripts/build_predevice_quilt_v091.py \
  artifacts/desktop-looking-glass-runtime-poc-v091/desktop-game-window-valid.png \
  artifacts/desktop-looking-glass-runtime-poc-v091/looking-glass-go-predevice-quilt.png
```

The generated report must say `hardware-unverified`, `physicalDeviceActive=false`,
`calibrationObserved=false`, and `realParallaxCapture=false`. It validates only the
4092x4092, 11x6, 66-view tile/order contract.

After a Looking Glass Go is physically connected to a Windows UE 5.8 host, install
the pinned plugin, start Looking Glass Bridge, and run:

```powershell
python scripts\install_looking_glass_unreal_plugin.py `
  --project unreal\GahyeonStage\GahyeonStage.uproject --download
powershell -ExecutionPolicy Bypass -File scripts\run_looking_glass_windows_gate.ps1 `
  -UnrealRoot 'C:\Program Files\Epic Games\UE_5.8'
```

The Windows gate applies the repository-owned, strict UE 5.8 compatibility
patch after verifying the pinned upstream 2.1.1 archive. Looking Glass Bridge is
still a separate, login-gated vendor install and is required for device discovery.

Physical acceptance remains fail-closed until device identity, Bridge calibration,
active player/capture, observed quilt frame, and exact quilt PNG evidence all pass.

## Verified on 2026-08-16

- macOS UE 5.8 Editor build: passed.
- macOS Gahyeon Automation: 18/18 passed.
- macOS UE 5.8 packaged game build/cook/stage: passed (733/733 packages);
  codesign verification, packaged launch, clean shutdown, and restart passed.
- macOS packaged runtime loaded the dedicated v091 map and displayed the configured
  v088 MetaHuman visual through the AI-capable source pawn. Hair rendered, and the
  diagnostic HUD and unbuilt-lighting warning were absent. Camera framing and the
  retained QA scene geometry remain POC-quality.
- The source runtime pawn now hosts the v088 Actor without reparenting it. It
  resolves the external Face/Body skeletal components for the presentation bridge,
  suppresses fallback geometry/HUD, and fails closed when the configured visual is
  unavailable. The v091 Desktop map uses movable scene components, removing the
  retained QA map's unbuilt-lighting warning.
- The optional generated `GahyeonGenerated` hero subclass is absent, so GameMode
  intentionally instantiates the source AI pawn. That pawn now owns/attaches the
  configured v088 visual actor, so this warning no longer means the visible
  character is disconnected from the AI runtime host.
- macOS Electron arm64 character-only package and packaged launch: passed,
  unsigned. Captured corner alpha is zero.
- Windows x64 Electron PE package creation: passed on macOS.
- Windows native Unreal packaged execution, clean screenshot, shutdown, and
  restart: passed on `land` (Windows 10, UE 5.8.1, GTX 1660 Ti).
- Looking Glass 2.1.1 Runtime, Editor, and Gahyeon adapter compiled and linked
  under UE 5.8 on `land`; Gahyeon Automation passed 18/18 and the independent
  engine evidence verifier passed. Evidence is under
  `artifacts/looking-glass-engine-gate-land-v091/`.
- Looking Glass Bridge is not installed on `land`. The current vendor download is
  account-login gated, so installation awaits authorized vendor credentials.
- Looking Glass physical output: not verified; device not delivered.
