# Gahyeon Fab human minimum quality bar

## Decision

The minimum visual and technical target is a human character that would not look
out of place as a paid product in Fab's **3D → Characters & Creatures → Humans**
category. This is stricter than "a working humanoid" and is not satisfied by the
current MPFB G1 blockout.

The accepted G1 v79 file remains the identity and proportion blockout. It is not
the production face, skin, groom, garment, facial rig, or Unreal hero package.
Procedural noise on the existing 2K diffuse texture cannot close those gaps and
must not be counted as another authoring pass unless side-by-side review shows a
material improvement.

## External benchmark evidence

The benchmark was sampled on 2026-08-13 from:

- <https://www.fab.com/category/3d-model/characters-creatures--humans>
- <https://www.fab.com/listings/7ee99009-5bce-4922-98e1-68cf9e4175fb>
  (`N5: Human Base`)
- <https://www.fab.com/listings/7587d7f6-047f-4a28-bd7b-b97014f34573>
  (`Cyberpunk Girl - Lily`)

These are quality references, not source assets. The project must not download,
copy, train on, or redistribute a listing whose license or `Allows usage with AI`
field prohibits that use.

## Minimum release bar

| Area | Minimum evidence before calling the character Fab-grade |
| --- | --- |
| Identity | Canonical 03/06/07/08 likeness survives neutral front, 3/4 and profile review; no generic-face substitution |
| Face master | High-resolution sculpt plus animation topology; stable eyelid, nasolabial, mouth and ear forms in close-up |
| Skin | At least 4K authored albedo/base color, normal, displacement or micro-normal, roughness and masks; no baked lighting |
| Eyes/mouth | Separate sclera, iris, pupil, cornea and tear line; teeth, gums, tongue and mouth occlusion |
| Facial performance | Production facial rig or equivalent; eyelid contact, lip seal, jaw and cheek-volume tests; Korean ten-viseme set |
| Body | Game-ready deformation topology and UE5-compatible production skeleton; clean extreme-pose skinning |
| Hair | Authored scalp/hairline/parting/clumps/flyaways, strand master and cards/mesh fallback LOD |
| Outfit | Patterned garment topology, authored PBR maps, body-penetration-free shoulder/hip/sit/extreme poses, runtime cloth policy |
| Runtime | Unreal 5.6 hero package with Control Rig, HairStrands/groom binding, physics policy, LODs and verified dependency inventory |
| Presentation | Neutral beauty scene plus unflattering neutral-light inspection, wireframes, texture channels, rig tests and performance captures |

The aspirational upper benchmark additionally includes ARKit-class facial coverage
(the sampled Lily listing advertises 120+ facial/body morph targets). That count is
not a loophole: fewer controls are acceptable only if the approved G4 deformation
and Korean speech evidence is equivalent or better.

## Rebase boundary

Reuse from v79:

- canonical identity and modeling manifests;
- measured height, broad proportions and reviewed likeness deltas;
- G1 camera/evidence contracts and provenance discipline;
- runtime semantic boundaries and the replaceable hero pawn;
- v79 as a visual comparison source, never as an approved predecessor.

Replace for G2/G3:

- MPFB face surface as the final close-up master;
- the 2K diffuse-only skin source;
- 53-bone body-only rig as the final facial performance solution;
- generic Hair Editor shoulder groom as the production hairstyle;
- procedural jacket and sneaker blockouts as representative outfit assets.

## Entry rule

G2 cannot formally become a candidate until G1 has 15/15 legible evidence views,
an actual registered model artifact, no unresolved blocking likeness finding, and
the required independent human approvals. Planning and prototype work may proceed,
but `--allow-unapproved-predecessor` output is never release evidence.

Run the machine-readable audit with:

```bash
python3 scripts/report_gahyeon_g2_readiness.py \
  --workspace artifacts/gahyeon-ch \
  --project unreal/GahyeonStage/GahyeonStage.uproject
```

