# Liquid Glass rendering strategy

## Goal

The character controls should read as a transparent, deformable optical material
over the Windows desktop, not as a gray translucent CSS card. The material must
remain usable over both bright and dark backgrounds and must degrade safely when
Windows transparency effects or GPU composition are unavailable.

## What creates the effect

Apple's public description makes lensing the defining property. A convincing
implementation needs these layers to work together:

1. live background transmission;
2. edge refraction and a thicker refractive rim;
3. modest blur/scattering, not blur as the primary effect;
4. Fresnel-like edge highlights and ambient color spill;
5. adaptive tint, contrast, glyph color, and shadow;
6. interaction-driven illumination and elastic shape/motion;
7. a thicker optical profile when the control expands.

Static gradients, borders, and `backdrop-filter: blur()` can suggest glass, but
cannot provide the missing optical evidence by themselves.

## Rendering boundary in Gahyeon Desktop

The controls live in a transparent Electron `BrowserWindow`. Web liquid-glass
libraries normally refract DOM or media that belongs to the same renderer. They
do not automatically receive pixels from applications or the wallpaper behind
the native window. This distinction determines the implementation.

### Tier 1: native backdrop plus optical overlay

Use a small controls-only native window/surface and apply Electron's Windows
`backgroundMaterial: "acrylic"` (or `setBackgroundMaterial("acrylic")`). Keep
the character window transparent and visually separate. Restrict the acrylic
window to the compact/expanded control bounds so it does not create a visible
rectangle around the character.

Compose the following renderer layers above that native backdrop:

- a rounded capsule mask;
- a generated signed-distance displacement map for the rim;
- three displacement samples for subtle RGB dispersion;
- geometry-aware inner highlight and dark opposing edge;
- selected-control tint and local illumination;
- spring interpolation between compact and expanded geometry.

This tier provides real desktop blur/transmission through the OS compositor and
high-quality optical cues, but Windows Acrylic does not provide arbitrary
pixel-accurate refraction.

Electron documents `backgroundMaterial` for Windows 11 22H2 and newer. On the
current `land` host (Windows 10 Home, build 19045), applying it to the original
640x700 transparent character window produced no visible material. Applying the
same option to a separate 44x128 shaped, click-through controls window did
produce live desktop blur in the target capsule. This observed Windows 10
behavior is useful but outside Electron's documented support contract, so it
must retain a transparent CSS fallback and remain covered by target-host smoke
evidence. Native addons last published against old Electron ABIs must not be
adopted without a rebuild, crash test, resize/move test, and license review.

### Tier 2: captured desktop texture plus GPU refraction

For actual bending of desktop pixels, obtain a Windows Graphics Capture frame,
crop the region under the controls, and feed it to a WebGL/DirectComposition
shader. The shader should implement a rounded-rectangle SDF, surface normals,
IOR-based UV displacement, chromatic dispersion, Fresnel reflectance, specular
lighting, and blur/scattering.

This path requires explicit handling for capture permission, protected content,
self-capture feedback, multi-monitor coordinates, DPI scaling, frame latency,
GPU/context loss, and privacy. It must fail back to Tier 1. It should not ship
until self-capture exclusion and latency are proven on the target Windows host.

## Candidate implementations studied

- `archisvaze/liquid-glass`: useful reference for Chromium SVG
  `feDisplacementMap` and a Three.js GLSL alternative with configurable IOR.
- `ybouane/liquidglass`: strongest shader/compositing reference; includes
  refraction, RGB aberration, Fresnel, multi-light specular, rim and shadow.
- `rdev/liquid-glass-react`: useful interaction reference for elasticity and
  pointer-responsive light, but React-specific and Chromium displacement is not
  sufficient for an OS-transparent Electron window.
- `samasante/liquid-glass` and `PallavAg/liquid-glass-web-react`: useful SDF
  displacement-map math and efficient lens movement without regenerating maps.

Do not copy implementation code without recording its license and attribution.
Prefer reproducing the optical model in a small Vue/Electron-native component.

## Initial optical parameters

Use these as experiment ranges rather than hard-coded design constants:

| Parameter | Compact | Expanded |
| --- | ---: | ---: |
| rim depth | 18-26% of minimum dimension | 12-20% |
| displacement | 3-7 px | 5-10 px |
| RGB dispersion | 0.4-1.2 px | 0.6-1.6 px |
| blur sigma | 2-6 px | 5-10 px |
| tint opacity | 3-9% | 5-12% |
| highlight opacity | 18-38% | 22-45% |
| spring damping ratio | 0.72-0.9 | 0.72-0.9 |

Expanded glass must appear optically thicker: deeper shadow, broader scattering,
and stronger lensing. Tint should remain restrained except for active controls.

## Acceptance gates

1. A checkerboard or text window moving behind the control is visibly blurred by
   the native backdrop in Tier 1.
2. Tier 2, when enabled, visibly bends straight grid lines at the rim; a still
   border/gradient does not count as refraction.
3. Compact-to-expanded motion preserves a single continuous material instead of
   swapping two unrelated panels.
4. Icons meet contrast requirements over sampled bright, dark, and mixed scenes.
5. Mic/speaker/close hit targets remain reliable through drag and click-through
   modes.
6. Reduced-transparency and reduced-motion settings have stable fallbacks.
7. Target host evidence records Windows build, Electron/Chromium version, GPU,
   DPI, FPS, frame latency, and screenshots/video over a moving test background.

## Recommended implementation sequence

1. Extract the controls island into a controls-only Electron window while
   preserving existing IPC and click behavior.
2. Enable Windows Acrylic on that window and verify it on `land` over a moving
   checkerboard/text background.
3. Add a renderer-owned SDF optical overlay and spring morphing.
4. Add adaptive luminance/tint and accessibility fallbacks.
5. Prototype Windows Graphics Capture behind a feature flag, then measure
   self-capture behavior and end-to-end latency before choosing Tier 2.

Native glass defaults to `auto` for the character preset now that it is confined
to the controls-only window. Set `GAHYEON_DESKTOP_NATIVE_GLASS=off` for an
explicit transparent CSS fallback.
