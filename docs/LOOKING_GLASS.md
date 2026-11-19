# Looking Glass display adapter

Gahyeon treats Looking Glass Go as the primary production deployment surface for
the same Desktop stage. The monitor renderer is a development, diagnostics, and
device-recovery fallback; it cannot satisfy production acceptance. Looking Glass
is not a second Core, agent, session, behavior engine, or world-state owner.

## Integration choice

The Desktop renderer uses Looking Glass's official WebXR library rather than
the legacy HoloPlay/Core JS stack. The library converts the existing Three.js
perspective scene into multi-view light-field output through Looking Glass
Bridge.

Official references:

- <https://lookingglassfactory.com/webxr>
- <https://lookingglassfactory.com/software>
- <https://www.npmjs.com/package/@lookingglass/webxr>
- <https://lfdocs.lookingglassfactory.com/software/looking-glass-bridge-sdk/native-function-reference>

## Setup

On the canonical Apple Silicon Mac, run the one-stop installer:

```bash
python3 scripts/setup_looking_glass_macos.py
```

It reuses an installed Bridge or an official installer already in `~/Downloads`.
If neither exists, it opens the official vendor page and waits for the login-gated
download, installs the resulting DMG/PKG, starts Bridge, and fails closed unless a
Looking Glass Go is exposed at its native 1440x2560 desktop resolution. To launch
the canonical Gahyeon Unreal runtime after setup, add `--launch-gahyeon`.

The vendor account login is the only interactive gate; credentials are never read
or stored by this repository.

1. Connect Looking Glass Go in desktop mode.
2. Install and run Looking Glass Bridge.
3. In `desktop/.env`, enable the adapter:

   ```dotenv
   VITE_GAHYEON_LOOKING_GLASS=true
   ```

4. Start Desktop, click `ENABLE LOOKING GLASS`, then use the generated
   `ENTER VR` button.

The SDK is dynamically imported only after the first button click. With the
flag disabled, no WebXR polyfill is loaded. With the flag enabled but no device
or Bridge present, the monitor renderer, conversation, audio, and World State
continue to operate normally.

## Framing and depth

`@lookingglass/webxr` 0.6 poses every view around a fixed reference-space
target and places the view origin at `0.5 * targetDiam / tan(fovy / 2)` in
front of it (about 13 m for the full-body framing). The Desktop stage therefore:

- parents the camera to a rig that follows the character while presenting, so
  the focal plane stays on her when she walks to another room;
- derives `targetY` from the active camera preset and narrows `targetDiam` for
  bust (1.5 m) and face (0.75 m) framing; `targetDiam` is the vertical extent of
  the focal plane on the portrait Go panel;
- shifts the fog by the extra camera distance, so the character is not hazed
  while the far room still fades out;
- does not pass `numViews` or `tileHeight`: 0.6 takes quilt columns, rows and
  resolution from the device serial (Go: 11 x 6 views, 4092 px quilt).

View-control updates reallocate the quilt texture, so they are only pushed when
the camera preset changes, never per frame.

## Shared-state invariant

Both outputs use the same in-memory Three.js scene and the same reduced
`StageState`:

```text
Core World/Event snapshot
          │
          ▼
      StageState
          │
          ▼
   Shared Three.js scene
      ├─ normal perspective frame → Desktop monitor
      └─ WebXR multi-view frame    → Looking Glass Bridge → Go
```

No Looking Glass calibration, view count, quilt layout, or device connection
state is persisted in Gahyeon Core.

## Verification status

- Production bundle and lazy WebXR chunk: verified.
- Adapter opt-in and `ENTER VR` creation without Bridge: verified.
- Desktop fallback with Bridge absent: verified.
- Calibrated light-field output, depth tuning, and performance on physical Go:
  requires the target device and Looking Glass Bridge and remains a hardware
  acceptance test.
