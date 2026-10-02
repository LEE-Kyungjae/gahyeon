# Gahyeon Donor Outfit Pipeline Resume

## Current visible runtime

- UE 5.8 preview: `/Game/Gahyeon/CharacterPipeline/v053/Preview/L_Skotukeda_RefinedGarment_v053`
- Status: stable static desktop fallback, fixed full-body camera, not animation-ready.
- Dark Knight v057 was rejected by direct review and is no longer the visible runtime.

## Completed donor proof

The free `Free Rigged Female 3D Character Game Animation Ready` package was inspected without trusting or overwriting its source archives.

- Six archives passed archive-path safety checks.
- Blender scene: 238 objects, 230 meshes, two armatures.
- Separated garments: `top_cloth` (462 vertices) and `bottome` (524 vertices).
- Extraction, height normalization, MetaHuman surface conform, Unreal import, and fixed-camera rendering all completed.
- v055 was rejected after render because the garments are undergarment-like, low resolution, open at the waist, and unsuitable for Gahyeon's hero style.
- Do not transfer skin weights for this rejected donor.

Authoritative evidence:

- `artifacts/gahyeon-ch/donor-assets/free-rigged-female/extraction-report-v002.json`
- `artifacts/gahyeon-ch/donor-assets/free-rigged-female/transfer-report-v054.json`
- `artifacts/gahyeon-ch/donor-assets/free-rigged-female/evaluation-v055.json`

## Dark Knight proof

`Dark Knight - Female Character`, Fab listing `5be9349e-acb1-4a0b-8811-9e999e036755`, has been downloaded and processed.

- The original Blender archive is preserved and passed archive-path safety inspection.
- Source inspection found 33 renderable meshes, one 417-bone Rigify armature, 80 deform bones, and 4K armor color/metallic/normal/roughness maps.
- Twenty torso, arm, lower-body, and footwear objects were selected. Sword, large neck/shoulder spikes, hands, and fingers were excluded from the assistant silhouette.
- Blender v056 preserves all selected modules separately and produces a deterministic 1024x1536 fit render.
- A separate combined preview FBX works around UE 5.8 Interchange ignoring the requested combine-meshes flag for a multi-object FBX.
- UE 5.8 successfully built the v057 static mesh, imported the PBR textures, saved the map, and loaded it in game mode, but direct review found that none of the anatomical regions matched.
- v058 proved that `Cloth_*` and `Boot` are donor skin chunks rather than reusable clothing and that independent region Z fitting breaks seams.
- v059 excluded donor skin and shared height landmarks, but the donor-specific breastplate remained oversized and limb/boot bands remained discontinuous. It was rejected before UE import.
- This proves geometry/material ingestion only. It does not prove MetaHuman skin weights, deformation, Chaos Cloth, or final styling.

Authoritative evidence:

- `artifacts/gahyeon-ch/donor-assets/dark-knight/inspection/blender.json`
- `artifacts/gahyeon-ch/donor-assets/dark-knight/blender-scene-inventory.json`
- `artifacts/gahyeon-ch/donor-assets/dark-knight/v056/fit-report-v056.json`
- `artifacts/gahyeon-ch/donor-assets/dark-knight/v056/fit-preview-v056.png`
- `artifacts/gahyeon-ch/donor-assets/dark-knight/v057/evaluation-v057.json`

## Next gate

1. Do not attempt another global or per-role affine fit.
2. Align the donor Rigify rest pose to MetaHuman landmarks, deform a donor cage, and drive the original armor through the cage so local ornamentation and seams are preserved.
3. Transfer MetaHuman skin weights only after neutral-pose cage validation passes.
4. Validate neutral, arm raise, walk, sit, shoulder, hip, elbow, knee, and boot deformation.
5. Produce a modern assistant outfit separately; Dark Knight remains reference-only unless the cage route passes.
6. Preserve listing attribution and do not redistribute the donor source.

## Current blocker

The direct v057 review failed. The next technical blocker is robust donor-rig/cage registration; simple static scaling is now explicitly prohibited by the recorded pipeline decision.
