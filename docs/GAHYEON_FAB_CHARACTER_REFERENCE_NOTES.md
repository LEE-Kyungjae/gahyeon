# Gahyeon Fab Character Reference Notes

The canonical catalog is `artifacts/gahyeon-ch/reference/fab-character-reference-catalog.json`.

These listings are references and possible licensed donor assets, not identity authority. Gahyeon's canonical source images remain authoritative for the face and body. A marketplace character may contribute construction patterns or separable assets only after its purchased license, AI-use flag, object separation, and source files are verified.

## What to learn from the set

- Clothing: separate upper/lower meshes, clean openings, thickness, seam topology, skin clearance, modular materials, and weight transfer.
- Materials: Base Color, normal, roughness, metallic/ORM, opacity, skin SSS, and hair flow-map organization.
- Hair: card or groom silhouette, hairline, parting, bangs, side locks, and alpha sorting.
- Rigging: Epic Skeleton retargeting, donor-to-MetaHuman weight transfer, corrective shapes, and clipping tests.
- Packaging: FBX/Blender/MHPKG ingestion, Unreal material instances, deterministic import, and provenance receipts.
- Quality gates: close-up legibility, LOD stability, animation deformation, clothing/body penetration, and license compliance.

## Current priority

1. Use a free rigged candidate to prove object discovery, clothing extraction, provenance, conform, weight transfer, and UE import.
2. Inspect Leather Girl 13 as the leading modern fitted-outfit reference, but do not use it with AI tooling while its listing says AI use is not allowed.
3. Inspect Dark Knight when modular armor construction or garment layering is useful; retain author attribution requirements.
4. Keep Seo as an MHPKG/MetaHuman packaging reference, not an outfit donor.
5. Keep the static wedding dress as silhouette/material reference only until a later Chaos Cloth milestone.

## Acceptance rule for a donor outfit

A donor advances only if the source contains a genuinely separate garment mesh, usable UVs and PBR maps, an acceptable license, and geometry that can be conformed without destroying openings or seams. It must then pass MetaHuman skeleton weight transfer, neutral and motion penetration tests, fixed-camera UE renders, and Looking Glass portrait framing. No marketplace listing is approved merely because its promotional still looks good.
