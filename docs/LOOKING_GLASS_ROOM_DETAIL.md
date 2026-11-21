# Looking Glass room v013

v013 adds window casing, curtain folds, wall panels, drawer fronts, shelf brackets,
wood and fabric surfaces, and shallow exterior layers to the v011 room. Character
mesh, materials, camera and the unmixed 66-view presenter remain unchanged.

The exterior is a static autumn daylight art-direction candidate. It does not
consume Seoul weather or implement real-time rain, snow, time-of-day or curtain
animation. The presenter still replays a four-second cached idle sample; it is
not a live conversational animation surface.

## Build and preview

Use the canonical local Unreal project with the v011 map and character assets
already available. Generated textures are original deterministic PNGs, with no
external model or texture downloads. Do not overwrite an existing iteration map.

```sh
python3 scripts/build_gahyeon_room_v012.py
python3 scripts/build_gahyeon_room_v012.py --validate
python3 scripts/launch_gahyeon_looking_glass_room_v011.py \
  --serial LKG-E08611 --smooth \
  --room-config looking-glass-room-v013.json \
  --evidence-dir artifacts/looking-glass-room-v013
```

The launcher uses the canonical macOS runtime and a map-specific cache. Omitting
`--room-config` retains v011. Stop the current preview before launching another.
Scene and validation evidence are written to `artifacts/looking-glass-room-v013`.
The candidate requires physical-display review; a center-view image cannot prove
optical clarity. The fallback is v011, selected by the original launch command.

## References

Architecture layering, material separation and shallow window composition were
informed by [Astra 3D Mini Worlds](https://github.com/greenwoodpro/astra-3d-mini-worlds).
No source code, textures or models were copied from that repository. The scene
uses Unreal engine basic shapes and newly generated surface textures.

The retained v012 comparison exposed overly dense wood grain and a cropped window.
v013 reduces the texture contrast/frequency and brings more of the window assembly into
the portrait composition without changing the character camera. The window remains partly cropped
at the top and left; this is a candidate, not an approved final composition. Build scripts
retain their v012 filenames and default to v013; `--iteration v012` is available
for inspecting the earlier map with `--validate`.
