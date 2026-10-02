# Gahyeon G1 resume checkpoint — 2026-08-13

This document is the authoritative resume point for the current Blender character work.
It records what was actually produced and what must remain unclaimed.

## Current decision

- Long-term quality plan: 40 closed authoring/QA passes.
- Current progress: pass 32 of 40 authoring/QA iterations.
- Current best artifact: `artifacts/gahyeon-ch/models/gahyeon-g1-mpfb-v79.blend`.
- Review state: `draft-for-human-review` only.
- `artifacts/gahyeon-ch/g1-review.json` remains `draft`, with zero evidence,
  no `modelArtifact`, and no approvals.
- Do not register v79, transition G1 to `candidate`, or record an approval yet.

The v79 model is a real humanoid artifact, but it is not a likeness-approved G1
candidate and is far from the final AAA target.

## Fab-grade target reset

The minimum target is now explicitly the paid-product quality bar represented by
Fab's `3D / Characters & Creatures / Humans` category, not merely a functioning
humanoid or a polished MPFB demo. The enforceable interpretation is recorded in
`docs/GAHYEON_FAB_HUMAN_QUALITY_BAR.md`, with current machine-readable gaps in
`artifacts/gahyeon-ch/g2-readiness.json`.

This changes the route after pass 32:

- v79 is retained as the G1 identity/proportion blockout and comparison authority;
- the final face master, skin maps, facial rig, production groom and garments must
  be replacement-scale G2/G3 work;
- the existing 53-bone rig is not a facial-performance rig;
- no further sub-centimeter MPFB tuning may count as a pass without a clear visual
  improvement under identical cameras.

The v90 layered procedural skin experiment was rendered at identical 1024px front
and three-quarter cameras. It produced no user-visible quality jump over v79 and
cannot replace a high-resolution sculpt plus authored skin map set. It is rejected,
does not advance the pass count, and its node-graph change was removed from the
authoring source. The v90 `.blend`, provenance and preview remain audit material.

The G2 readiness audit currently reports, truthfully: G1 `draft`, evidence 0/15,
no registered model or approvals, no G2 high-poly/animation artifacts, and missing
Unreal production plugins `HairStrands`, `RigLogic`, and `ChaosCloth`. Do not create
a release-facing G2 candidate by bypassing these gates.

No Unreal Editor, MetaHuman Creator Core Data, MetaHuman DNA or assembled MetaHuman
asset was found on this workstation. Therefore actual MetaHuman production is
`not-started`; the existing Unreal project contains a replaceable hero boundary,
not a MetaHuman.

To avoid losing all usable G1 work, a portable Mesh-to-MetaHuman solve input was
exported to `artifacts/gahyeon-ch/metahuman-identity-input-v79/`. It contains one
neutral OBJ (21,184 vertices / 20,466 polygons), MTL, 2K skin albedo, 1K eye
albedo, and a checksummed manifest whose claim is explicitly
`neutral-static-mesh-input-not-metahuman-not-dna`. A clean Blender 5.2 round trip
loaded one object with 14 materials and dimensions 103.815 × 175.951 × 41.467 cm.
Run `scripts/verify_gahyeon_metahuman_identity_input.py` before importing it.

The first evaluated-modifier export inflated the input to 189,347 vertices and
failed to package the eye texture. It is retained only under
`metahuman-identity-input-v79-rejected-evaluated/`; never feed it to Identity Solve.

Next external-state steps are mandatory: install Unreal Engine 5.6+ with MetaHuman
Creator Core Data through Epic Games Launcher, install/enable MetaHuman Creator and
MetaHuman Animator Depth Processing, import the verified OBJ with Combine Meshes,
track a neutral frame, run Identity Solve, then conform a MetaHuman Character from
that Identity. Only the resulting DNA/RigLogic character begins the real G2 path.

## Verified v79 artifact

| Property | Value |
| --- | --- |
| Blender | 5.2.0 LTS, build `fbe6228777e7` |
| Model SHA-256 | `8f7ea9605ca2a108d05c05611768e40f4b09b399132a1e926c0fb3fc3c2199f1` |
| Model bytes | `75,412,366` |
| Authoring script SHA-256 | `4a9f88230cedfc3e2692c32cef7afae3ada5eca85bbda84d7c59714aae9b7b33` |
| Scene-plan SHA-256 | `6f5dbd0e895f90341c586417c9b60f22bb1b08f53c824c477f78fa055627bba7` |
| Mesh objects | 21 |
| Base vertices / polygons | 29,796 / 28,275 |
| Armature | 1 armature, 53 bones |
| Height | 172.0 cm |
| Hair guides | 252 curves / 4,032 points |
| Evaluated groom | 10,191 curves / 621,651 points |
| Pose | neutral A-pose |

The model and provenance hashes agree. The file opens headlessly in Blender 5.2.
The groom evaluates with no Geometry Nodes warnings.

## Pass-30 eye checkpoint

- Replaced the four overlapping flat semantic iris/pupil discs with one continuous
  193-vertex, 192-face recessed radial mesh per eye.
- The 0.54 cm iris and 0.17 cm pupil now sit between the fitted eyeball surface and
  transparent corneal shell. The pupil center is recessed 0.15 cm behind the rim.
- Both eye meshes are bound to the head group and 53-bone armature. Their three
  material regions each own exactly 64 faces.
- Direct 1024x512 front and three-quarter QA renders are under
  `artifacts/gahyeon-ch/g1-preview-v75-eyes/`. The same-camera v66 comparison is
  under `artifacts/gahyeon-ch/g1-preview-v66-eyes/`.
- v75 is a clear structural/readability improvement over v66's clipped flat discs,
  but the concentric material boundaries remain too graphic for AAA. A future eye
  pass needs non-uniform iris fibers and a physically modeled wet tearline; this is
  not an approval claim.

## Pass-31 iris checkpoint

- Increased each continuous iris mesh to 481 vertices and 480 faces across 96
  angular segments and five recessed radial levels.
- Replaced the three perfect concentric material bands with deterministic irregular
  ring boundaries and five brown/hazel material variations distributed as radial
  fibers. The outer radius remains 0.54 cm and the pupil remains 0.17 cm.
- Direct front and three-quarter QA renders are under
  `artifacts/gahyeon-ch/g1-preview-v76-eyes/`. Compared with v75, the graphic ring
  appearance is materially reduced and the curved silhouette remains visible at
  three-quarter angle.
- Blender runtime verification reports 53 bones, 252 source hair guides, 10,191
  evaluated groom curves, zero Geometry Nodes warnings, and 39 packed file images.
- The fiber colors still resolve as discrete wedges under extreme close-up. Future
  eye work should move this variation into a continuous procedural/texture shader
  and add a modeled wet tearline rather than increasing polygon-color complexity.

## Pass-32 face-framing checkpoint

- v77 tested a 0.052 cm glass tear tube. It rendered as a bright cyan wire and was
  rejected. v78 tested an embedded 0.012 cm alpha wet-coat ribbon; its measurable
  delta was only 143 front pixels and 56 three-quarter pixels above 2/255, so it was
  rejected as visually immaterial. Neither experiment counts as a closed pass.
- v79 preserves the v76 eye structure and increases the center-part guide clearance
  from 1.5 to 3.0 cm while raising front-layer ends from 4.0 to 6.0 cm. Roots,
  Surface Deform, guide count, and Geometry Nodes settings are unchanged.
- The same-camera close render under `artifacts/gahyeon-ch/g1-preview-v79-eyes/`
  removes the strand that crossed the left eye and exposes both eyebrows and cheeks.
  The wider face render is under `artifacts/gahyeon-ch/g1-preview-v79-face/`.
- Runtime validation still reports 53 bones, 252 source guides, 10,191 evaluated
  curves, zero Geometry Nodes warnings, and 39 packed file images.
- The remaining hair P0 is crown/side helmet volume and overly uniform strand
  density. Do not solve it by simply widening the part further.
- Post-pass experiments v80-v82 were rejected and do not advance the pass count:
  v80 applied a 1.2 cm mid-length radial inward taper, but reintroduced a strand
  over the left eye without materially improving the side silhouette. v81 reduced
  nominal profile radius and added clump/noise; it again obscured the eye and kept
  the curtain-like side. v82 changed only the nominal profile radius from 0.0097 to
  0.0076 cm, but all three 768px hair QA renders were pixel-identical to v79 (zero
  pixels above 2/255 in front/rear, effectively zero at side). This proves that
  exposed profile input is not controlling the evaluated final groom in this stack.
  Source was restored to the accepted v79 behavior.
- A direct nested-node audit then found the real global density control inside
  `Duplicate Hair Curves`: Amount 200 produces 10,191 evaluated curves. v83 at 120
  produced 6,100 curves but exposed broad scalp stripes. v84 at 165 produced 8,395
  curves but increased the side-view skin proxy from 884 to 1,391 pixels (+57%).
  v85 at 180 produced 9,109 curves, yet reduced the dark area by only 0.9% while
  increasing rear scalp exposure from 126 to 216 pixels. All three were rejected.
  Global density reduction is therefore not the next solution; use a crown-only
  scalp cap or a spatial density mask while preserving the accepted 200 amount.
- v86 combined Amount 165 with a 217-vertex/130-polygon identity-fitted scalp cap.
  It technically passed rig and topology checks and hid the exposed skin stripes,
  but the z-threshold polygon selection produced a clearly visible horizontal black
  cut line in the side render. It was rejected. Any future cap must have a feathered
  boundary (shader alpha/vertex mask) or tint the existing scalp surface region;
  never use a hard polygon-height cut as visible geometry.
- v87 replaced the cap with a position-based smootherstep mix in the existing skin
  shader and kept Amount 165. It did not contaminate the face, but all three renders
  were pixel-identical to v84 (zero pixels above 2/255), proving that the exposed
  scalp pixels in this groom path were not affected by that material output. It was
  rejected and source was restored to v79. Stop iterating global density/scalp cover
  on this template until a spatial density attribute or a replacement groom exists.
- v88 reduced jacket back clearance from a fixed 2.25 cm to a 1.35→1.15 cm
  height taper. The geometric envelope changed, but sealed-camera deltas were only
  16 pixels at front and 904 pixels at side above 2/255; the visible slab silhouette
  and existing artifacts remained. It was rejected as immaterial and source was
  restored to v79. Further jacket work must replace the blockout pattern/topology,
  not continue sub-centimeter envelope tuning.
- A clean v89 reproduction from the restored source matched accepted v79 exactly
  across all six 768px hair/outfit QA renders (five exact; side hair differed by at
  most 1/255 with zero pixels above 2/255). This proves functional restoration even
  though source formatting changed its checksum. v89-repro is validation material,
  not a new accepted pass.
- The local asset audit found only the 2K young-Asian-female diffuse skin image; no
  dedicated face normal, roughness, displacement, pore scan, or identity sculpt
  source exists. The current Hair Editor template and procedural jacket are likewise
  blockout sources. The remaining eight passes must not be spent on sub-centimeter
  tuning. Require replacement-scale work: a high-resolution identity face sculpt
  plus skin texture set, a replacement production groom/spatial density map, or a
  newly patterned garment with deformation-ready topology.

## Work completed in passes v1–v66

- Built an actual MPFB humanoid instead of treating an empty/bootstrap scene as a model.
- Preserved the canonical identity authority order: reference 03 is the neutral face
  master, references 06/07/08 constrain depth, and 16/19/20 constrain body shape.
- Created a 172 cm grounded body with a 53-bone game-engine rig.
- Kept face/body topology stable while applying identity changes before rig creation.
- Added fitted eyes, eyebrows, eyelashes, tongue, teeth, base clothing, sneakers,
  and an open white/turquoise jacket blockout.
- Fixed shoes that previously penetrated the ground and shortened their silhouette.
- Added rigid G1 bindings to jacket and shoe pieces instead of leaving them root-only.
- Corrected dark evidence lighting and preserved transparent official-evidence output.
- Replaced the helmet-like `long01` mesh hair with the official MakeHuman Hair Editor
  CC0 `straight_hair_to_shoulder` Blender Curves template.
- Pinned the Hair Editor archive and blend checksums:
  - archive: `39420056faba6aaa0726a5168c9c41f2d01e278a12e216c0385e8f13d4d98ab7`
  - `hair.blend`: `93aedaef061dc14618a0fcfad33c3df816fa755e8093381cbdfd0fd4c34527f5`
- Baked the meter-to-centimeter conversion into guide coordinates, all exposed
  Geometry Nodes distance inputs, and the nested interpolation radius.
- Added the required 19,158-point `rest_position` attribute and retargeted the groom
  to the MPFB body's `UVMap` and deformation surface.
- Fixed the sparse-groom regression found in v8/v9. v10 visibly covers the scalp on
  a neutral gray background; this is not a black-background illusion.
- Partitioned eye, brow, cheek, lip, nose, and lower-face sculpt regions to reduce
  accidental double transformation.
- Produced eight standard v66 previews under
  `artifacts/gahyeon-ch/g1-preview-v66/`, plus retained v58 close shoe QA views.
- Reduced the fitted-eye iris appearance by scaling only the two 276-vertex
  eyeball UV islands by `1.08`; the two corneal shell components remain untouched.
- Tested full-guide-vector hair extension in v12 and rejected it after visual QA
  showed lateral over-expansion and a worse blunt silhouette. v13 restores the
  stable vertical guide method while preserving a 1.5 cm front-center clearance.
- Re-measured canonical reference 03 and hair-hidden renders with the same macOS
  Vision landmark pipeline instead of relying on remembered v10 ratios.
- Moved all four fitted-eye/cornea mesh components inward by 0.33 cm per side so
  the actual pupil centers follow the eyelid correction; this reduced measured eye
  separation error from +14.2% in v13 to +9.0% in v17.
- Added an explicit lower-face lift region after proving that the previous compounded
  distance/falloff scale barely moved the rendered chin.
- Rejected v14's over-compressed lips and v15's over-converged eyeballs; v17 combines
  the best measured eye, mouth, and nose settings without promoting either regression.
- Separated the fitted eye asset into two textured 276-vertex eyeballs and two
  256-vertex corneal shells. v18/v19 shader regressions were rejected; v20+ use a
  low-weight Transparent/Anisotropic shader mix on exactly 490 cornea polygons.
- Replaced six disconnected upper/lower/cuff sleeve meshes with two continuous
  shoulder-to-wrist meshes. Each sleeve has five bridged rings, 120 vertices,
  98 polygons, and blended upperarm/lowerarm weights.
- Rejected v21 after a world-axis ring bug exposed skin along the lower arms. v22
  constructs every ring in the local arm tangent frame, eliminating the elbow gap.
- Rejected v23 and v24 after render QA exposed torso penetrations. v25 replaces the
  flat v22 torso boxes with two open-front, body-sampled curved panels. Each panel
  has 16 height rings, 288 vertices, 255 quads, three blended spine groups, and
  Armature/Solidify/Bevel modifiers. Dense eighth-order superellipse envelopes remove
  the v23/v24 penetrations while preserving a fitted waist silhouette.
- Rejected v26–v28 after testing guide-level rear hair clearance. v26's falloff acted
  on the wrong half of each guide; v27 moved the tips out but formed a central black
  clump; v28 split that clump laterally but produced two broad hair patches over the
  jacket. The authoring source was restored byte-for-byte to the verified v25 SHA.
  Do not resume by pushing guide points farther out. Preserve the v25 groom and solve
  the crossing with a garment-side collision/clearance shape or a dedicated rear
  layer authored from visually controlled guide groups.
- Rejected v29 because its first hood shell rose into horn-like side tips. v30 lowers
  and widens the four-ring fold into a neck-following garment shell: 96 vertices,
  69 quads, Solidify/Bevel, and a spine_03 Armature binding. It is still a G1
  blockout but replaces the old turquoise curve tube with an actual weighted surface.
- v31 replaces the full-width rectangular hem bar with two body-following ribbed
  waistband panels. Each side has 54 vertices, 34 quads, three spine groups, an
  open-front zipper gap, and Armature/Solidify/Bevel modifiers. The front and side
  silhouette now follow the waist instead of extending as a rigid box.
- Rejected v32 and v33 sneaker experiments after full-body/front/side/rear render QA.
  Enlarging the existing ring upper in v32 still read as a long gray wedge; adding
  separate box toe, tongue, and side accents in v33 read as floating toy-sandal bars.
  The authoring source was restored exactly to the verified v31 SHA. Do not add more
  box accents to this shoe. The next footwear pass must construct one continuous,
  foot-oriented upper surface with integrated toe box, quarters, heel collar, and
  tongue, then validate a close shoe camera in addition to the full-body views.
- v34 tested a conservative eyelid-height increase but produced too little visible
  change to close a pass. v35 raises only the partitioned eye-region height scale
  from 1.07 to 1.28 while preserving width, spacing, nose, mouth, and jaw values.
  Hair-hidden and three-quarter renders show more lid opening and sclera without
  topology or profile collapse. Do not increase global eye height again; the next
  eye work must reduce apparent iris size and author the upper-lid arc separately.
- Rejected v36 and v37 after testing fitted-eyeball UV island scales 1.15 and 1.30
  against v35's 1.08. Hair-hidden, hair-visible, and three-quarter renders showed no
  meaningful apparent-iris reduction, so this UV-center scaling technique is now
  exhausted. The authoring source was restored exactly to the verified v35 SHA.
  Do not keep increasing this UV scale. The next eye pass must separate semantic
  sclera/iris/pupil geometry or materials and size the visible iris explicitly.
- v38 proves the semantic-eye approach by adding two 0.72 cm iris discs and two
  0.28 cm pupil discs over the retained CC0 eyeball/cornea assembly. Each 49-vertex
  disc is head-weighted to the game rig. The warm-brown iris, dark pupil, and exposed
  sclera remain aligned in front and three-quarter renders without obvious floating
  or cornea intersection. This is still G1: production eyes need curved iris depth,
  limbal detail, tear line, caruncle, wetness, and authored catchlights.
- Rejected v39 because its dark limbal disc overwhelmed the warm iris and read as a
  black eye block; v40 restores the validated v38 semantic eye assembly. v40 changes
  only lip-group vertical scale from 0.60 to 0.72. Front and three-quarter renders
  show a more legible lip body and center seam without mouth opening or profile
  protrusion. Do not keep increasing lip height; next author cupid shape and lip
  material color/wetness separately.
- v41 tested a 0.85 cm lower-face lift but remained too subtle to close a pass. v42
  raises the same partitioned, lip-excluding lower-face falloff to 1.10 cm. The
  rendered chin tip rises modestly and the lip-to-chin region reads shorter without
  moving the lips or breaking the jaw/neck profile. Stop increasing this lift;
  subsequent chin work must target jaw width/volume independently.
- v43 relaxes only the lower-jaw side width scale from 0.95 to 0.98; the central
  chin, lips, and lower-face lift remain unchanged. The front jaw contour is less
  sharply V-shaped while the three-quarter jaw/neck connection remains stable.
- v44 adds a conservative 0–4 cm guide-end shortening falloff to front/side outer
  hair layers. It slightly breaks up v43's uniform V-shaped front hem without
  reopening the scalp or disturbing the center part and face-framing locks. The
  three-quarter and rear silhouettes remain too blunt, so this is one closed draft
  iteration rather than a groom-quality milestone.
- v45 tested moving the lower rear guides 3.2 cm toward the rear camera. Render QA
  exposed large black hair fragments through the jacket, proving the coordinate
  direction was wrong; v45 is rejected and must not be registered.
- v46 applies the inverse, tapered 2.4 cm underlay inset only to lower rear-center
  guides. The rear render no longer shows v44's small hair/jacket fragments or
  v45's severe breakthrough, while front and three-quarter groom views remain stable.
- v47 compares canonical face master 03 directly against the v46 hair-hidden front
  render and isolates the largest immediately actionable perceptual defect: the dark,
  oversized button-eye appearance. It reduces semantic iris/pupil radii from
  0.72/0.28 cm to 0.60/0.22 cm and lightens the brown iris. More sclera and a distinct
  brown iris/pupil hierarchy are visible in front and three-quarter renders without
  moving the eyeballs or changing face topology. Production tear line, iris depth,
  and corneal detail remain G2+ work.
- v48 reruns the same macOS Vision landmark pipeline on canonical 03 and the v47
  hair-hidden render. Mouth height was the largest isolated shape error at +26.0%.
  Reducing only the lip-group vertical scale from 0.72 to 0.60 lowers the remeasured
  mouth-height error to +9.8%. The closed lip seam remains legible and the three-quarter
  view shows no mouth opening or profile collapse. Remaining normalized errors include
  nose-to-mouth spacing +19.2%, eye-to-nose spacing +15.9%, and lip-to-contour distance
  +14.3%; these are directional Vision measurements, not identity approval.
- v49–v51 are rejected lower-face spacing experiments and are not checkpoints.
  v49 moved lips up 0.35 cm and increased the existing lower-face lift to 1.55 cm;
  nose-to-mouth error improved, but the lips floated while the visible chin did not
  follow. v50 reduced the lip move to 0.20 cm and raised the broad lift to 2.00 cm,
  but could not improve both nose-to-mouth and lip-to-contour ratios over v48. v51
  added a 0.75 cm `joint-jaw`-centered lift and worsened the Vision lip-to-contour
  error to +26.2%, proving that the MPFB joint center is not a safe proxy for the
  rendered chin contour. The authoring script was restored byte-for-byte to the
  verified v48 SHA after these tests. A future chin pass must identify the actual
  front-contour vertices from projection, not infer them from `joint-jaw`.
- v52 projects v48 body vertices through the sealed front camera and compares them
  to Vision's 17-point face contour. The diagnostic proves that 2D proximity alone
  is ambiguous: vertices at the same screen point can lie on front, rear, or internal
  surfaces, so a future chin pass requires depth/occlusion-aware selection. Rather
  than force an unsafe chin edit, v52 addresses the stable measured mouth-width error.
  Reducing the isolated lip-group width scale from 0.74 to 0.69 lowers mouth-width
  error from +8.2% to +5.3%. Front and three-quarter renders retain a closed seam and
  show no profile collapse.
- v53 extends the contour audit with Blender scene ray casts and a subdivision-disabled
  cage scan. The Vision chin point intersects neck/under-chin surfaces along the same
  orthographic ray and therefore cannot safely identify the visible chin boundary;
  automated chin edits remain deferred until a silhouette/occlusion buffer is available.
  v53 instead narrows the already-partitioned nose region from 0.76 to 0.70. The
  remeasured nose-width error falls from +9.3% to +7.3%, and front/three-quarter QA
  shows no pinching or profile collapse. The nose remains vertically too long.
- v54 and v55 are rejected facial micro-adjustments, not checkpoints. v54 added a
  0.94 radial nose-height scale, but the measured nose-height error changed from
  +10.3% to +10.7% and the render delta was negligible. v55 moved eyelid-region
  vertices inward by another 0.13 cm without moving the separate semantic eyeball
  assembly; eye-separation error worsened from +6.3% to +8.2% and eye width/height
  detection became unstable. Both changes were removed, and the authoring script was
  restored exactly to the verified v53 SHA. Further face refinement must use an
  authored sculpt/semantic-eye coupled workflow rather than isolated Vision chasing.
- v56 replaces the old flat, eight-point slipper blockout with a continuous 24-point
  anatomical upper and a separate rounded sole. Close QA exposed severe foot
  penetration and a floating turquoise accent, so v56 is rejected. v57 widens and
  raises the upper and removes the floating accent, reducing the defect to small toe
  protrusions. v58 extends and widens the toe envelope conservatively: the major skin
  breakthrough is gone, the side silhouette fully covers the foot, and only a tiny
  pixel-level inner-toe exposure remains. Both uppers are closed manifold 72-vertex,
  50-polygon meshes; both soles are closed manifold 48-vertex, 26-polygon meshes,
  grounded at z=0, foot-bone weighted, and bound to the 53-bone rig. This closes the
  footwear blockout pass, not production footwear quality.
- v59 is a rejected jacket-readability experiment, not a checkpoint. It replaced the
  two dark front zipper bars with turquoise tapered plackets and a small pull. The
  scene remained structurally valid, but front and side render QA showed the new
  pieces as two long hanging cords rather than a constructed open collar. The source
  was restored to the verified v58 implementation. The next garment pass must reshape
  the jacket panel boundaries and side volume themselves; do not stack more thin box
  or strip details over the current slab silhouette.
- v60 reshapes the two 288-vertex jacket panels themselves. Their front three vertex
  columns now open progressively above the upper chest into a panel-integrated V,
  and the actual 15 front-edge faces per side carry the turquoise trim material.
  The two dangling full-height zipper bars are removed and replaced with one small
  rig-bound zipper pull. Front QA now separates a dark inner shirt from two white
  outer panels instead of reading as a closed sports jersey. Both panels retain 255
  polygons, their three-spine weights, Armature/Solidify/Bevel stack, and the full
  v58 shoe invariants. Side and rear volume remain G1 blockout quality.
- v61 is a rejected rear-volume experiment. It tapered only the rear 40% of each
  panel by at most 0.90 cm and retained a naive nearest-vertex clearance of 0.52 cm,
  but rear render QA exposed dark inner-shirt diamonds through the lower back panel.
  This proves that nearest-vertex distance is not a sufficient garment collision
  test: intervening faces can still cross. The source was restored exactly to v60.
  Do not repeat uniform rear shrinkage; the next pass needs evaluated-surface ray
  casts or a signed-distance/cage check before moving any rear-panel vertices.
- v62 is a second rejected rear-volume experiment. Inspection proved the two panel
  halves merely touched at center-back (x=±0.002 cm), so v62 added a 0.70 cm center
  overlap and reduced the taper to 0.45 cm. This removed most of v61's large dark
  diamonds, but rear render QA still exposed the separate dark inner garment through
  the waistband/back-panel stack. The defect is therefore a multi-layer depth-order
  problem, not just an open center seam. Source was restored to v60. Stop shrinking
  this rear shell until the inner garment, waistband, and outer panel are evaluated
  together; continue with independent hood or groom improvements instead.
- v63 is a rejected hood-silhouette experiment. It reshaped the existing four open
  semicircular rings into a deeper shoulder drape while preserving the 96-vertex,
  69-polygon topology and spine_03 binding. Rear QA showed a broad turquoise sailor
  collar rather than a folded hood, and side QA exposed a pointed wing at the open
  ring end. The source was restored to v60. The open semicircular strip topology is
  exhausted for this purpose; a future hood must be a closed pocket/bag volume with
  a bounded face opening and deliberately capped side seams.
- v64 and v65 are rejected closed-hood experiments. v64 replaced the open strip with
  a rigorously closed 64-vertex/50-polygon four-ring pocket; all 112 edges were
  manifold and the spine_03 Armature binding passed, but rear/side QA read it as an
  oval neck pad with a fin. v65 used two capped 24-point teardrop surfaces joined by
  side walls; it read as a circular back patch and a rectangular plate. Both prove
  that simple procedural cross-sections are structurally valid but visually wrong for
  this garment. Source was restored to v60. Defer the hood to an authored clothing
  pattern or cloth-simulation pass; stop spending G1 iterations on primitive shells.
- v66 preserves the validated v60 groom roots, scalp coverage, unit conversion,
  Surface Deform retarget, and rear-jacket inset while adding a second S-wave only
  after 62% of each guide. Its 1.15 cm lateral/0.55 cm depth wave and deterministic
  0–2.20 cm tip-length step break the former uniform V hem into layered locks. Front
  and three-quarter QA show a less helmet-like outline without reopening the scalp;
  rear outfit clearance remains stable. Evaluation still produces 10,191 curves from
  252 guides with zero Geometry Nodes warnings. Fine strand clumping, end-radius
  taper, and flyaway control remain G2 work.
- v67 is a rejected conservative face-volume experiment. It moved 304 non-eyelid,
  non-lip under-eye soft-tissue vertices forward by at most 0.12 cm in two symmetric
  bounded ellipses. Topology, rig, hair, and all structural checks remained valid,
  but hair-hidden front and three-quarter comparisons showed no reliably visible
  reduction in the orbital hollow or likeness improvement. The source was restored
  exactly to v66. Further identity work should use a reviewable Blender shape key or
  authored Sculpt pass against canonical 03/06/07/08, not another hard-coded ellipse.
- v68–v70 are rejected but informative reversible face-shape experiments. v68 first
  proved a valid `Basis` + review-key workflow: topology stayed identical and sealed
  cameras rendered the same model at key values 0 and 1. v68/v69 combined malar
  volume and lower-face lift, but their maximum 0.269 cm and then stronger candidate
  deltas remained visually negligible. v70 expanded the front gate and allowed up to
  1.10 cm chin lift plus 4.5% jaw narrowing; identical-camera comparison still barely
  changed the rendered silhouette. The coordinate predicates are selecting too much
  internal/side surface and not the true visible contour. Source was restored to v66
  and no shape key is retained in the best artifact. The 0/1 review method is sound,
  but the next identity pass requires interactive Sculpt or projection/occlusion-based
  visible-surface selection, not larger analytic XYZ regions.
- The post-v70 camera-space contour audit fixed an orthographic-depth assumption and
  successfully projected front-facing lower-face vertices into the sealed face camera.
  A red-marker render then proved the remaining ambiguity directly: upper extrema
  touched parts of the jaw, but lower extrema followed the neck rather than the chin.
  Front-facing normals plus per-row screen extrema are therefore still insufficient
  to separate jaw from neck. Keep `/tmp/v66-jaw-markers.png` as local diagnostic
  evidence; a future selector needs occlusion-aware semantic segmentation or manual
  Sculpt masking.
- v71 is a rejected material-only attempt. It increased warm albedo mixing, SSS,
  brightness, and lip color while lowering skin roughness, but identical v66/v71
  front and three-quarter renders were nearly indistinguishable under the sealed
  lighting. The authoring source was restored to v66. Do not count small packed-shader
  parameter shifts as progress without a measurable or clearly visible render delta.
- v72/v73 are rejected semantic-eye detail experiments. v72 added a limbal ring,
  inner amber ring, and emissive catchlights; the close render became visibly more
  detailed but read as bright doll eyes and repeated v39's dark-ring failure. v73
  removed catchlights and halved ring widths/contrast. Standard face views then looked
  nearly unchanged, while 1024×512 eye closeups exposed three concentric flat discs;
  the three-quarter view confirmed that the semantic planes do not follow corneal
  depth. Source was restored to v66. Future eye work needs a single curved iris/pupil
  assembly recessed behind the cornea, not more coplanar rings or painted highlights.

## Pass-29 milestone truth

Pass 29 means 29 of the planned 40 iterative authoring/QA loops, not 72.5% of AAA
completion. The current pipeline report still proves: G1 review `draft`, 0/15 G1
evidence views, G2–G5 `not-started`, Hero `not-started`, and
`qualityChainApproved: false`. The report's `hasCandidateModel: true` indicates that
model-shaped files exist; it does not override the empty G1 review lifecycle.

## Current visual truth

v66 is technically stronger than v17, especially in eye material semantics,
continuous weighted sleeves, while retaining the improved pupil alignment and measured
readability. Its torso is less box-like than v22, but it still does not resemble the
canonical face closely enough.

Blocking defects:

1. The face still reads as a generic, older character. The eye sockets, nose/mouth
   relationship, jaw softness, and youthful mid-face need an authored sculpt pass.
2. The fitted eye texture has oversized, dark irises and lacks a production eye
   assembly with semantic sclera/cornea/iris/pupil/tear-line separation.
3. The groom is now dense and near-black, but it remains too straight and blunt.
   It needs canonical center-part clumps, face-framing locks, layered tips, loose
   waves, and a better rear/top design.
4. v60 finally reads as a dark inner shirt under two open white/turquoise jacket
   panels, and v58's curved upper/grounded sole remains intact. The jacket side and
   rear still read as broad blockout shells; hood, waistband, shorts, socks, and shoes
   require production topology and weights. Hair crosses the rear jacket near the
   shoulder blades.
5. Skin uses a 2K MPFB diffuse and procedural response. It has no authored 4K
   normal/displacement/roughness set, pore sculpt, tear line, or facial peach fuzz.
6. The 53-bone rig has no facial bones or expression shape keys.

The same macOS Vision pipeline produced these current directional ratios. They are
not identity truth and must be cross-checked visually:

| Ratio | Canonical 03 | v13 hair-hidden | v17 hair-hidden |
| --- | ---: | ---: | ---: |
| eye separation / face box | 0.3659 | 0.4180 | 0.3990 |
| mean eye width / face box | 0.1647 | 0.1808 | 0.1780 |
| mean eye height / face box | 0.0629 | 0.0658 | 0.0628 |
| nose width / face box | 0.1610 | 0.1823 | 0.1804 |
| mouth width / face box | 0.2592 | 0.2970 | 0.2865 |
| mouth height / face box | 0.1135 | 0.1458 | 0.1287 |
| lip-to-chin / face box | 0.2232 | 0.2526 | 0.2706 |

Do not measure the hair-visible render with Vision: foreground strands alter its
face bounding box and produce invalid comparisons.

## Exact next work

Pass 29 is closed as a draft iteration. Resume with a new `v67` output; never
overwrite v66. v45, v49–v51, v54/v55, v56, v59, v61–v65, and v67–v73 are retained rejected audit artifacts only.

1. Preserve v66 facial geometry. The next face pass must jointly move eyelids and the
   semantic eye assembly or use a dedicated sculpt session; do not continue isolated
   Vision-driven micro-adjustments.
2. Move the fitted eyeballs inward with the MPFB eye translation target and verify
   pupil centers, not only eyelid vertices. Reduce eye width without reducing the
   already-correct eye height.
3. Make lip width and height changes own the complete lip group, then verify both
   the closed seam and profile depth against 06/07/08.
4. Preserve the v66 groom's unit conversion, interpolation-radius fixes, layered
   front/side end-layer falloff. Modify
   guide shape only: introduce smooth long-range S-waves and layered ends without
   reopening scalp coverage.
5. Preserve the v66 integrated V opening and v58 curved shoe invariants. The next
   garment P0 is the slab-like side/rear volume: reduce excess back clearance using
   body-sampled taper without reintroducing torso penetration, then improve the hood.
6. Render face front, three-quarter, both profiles, hair front/side/rear/top, and
   body front before deciding whether to render the formal 15-view set.
7. Only after visual QA passes, render the 15 sealed views, package the submission,
   register the model/evidence in `g1-review.json`, and transition to `candidate`.
   Approvals must remain empty until the user reviews it.

## Recommended Codex model cadence

Do not spend the entire 40-pass plan at maximum reasoning effort.

- Use GPT-5.6 Sol at `low` or `medium` for deterministic author/render/verify loops.
- Raise Sol to `high` for identity-sculpt decisions, visual-delta diagnosis, and
  difficult Blender or Geometry Nodes failures.
- Use Sol `ultra` for milestone audits around passes 10, 20, 30, and 40, where a
  missed visual or lineage defect would invalidate substantial downstream work.
- If only one setting is available for an uninterrupted session, prefer Sol
  `high`; it is the safer compromise for this mixed visual and technical workload.

Quality must still be decided from rendered comparisons and gate evidence. A higher
reasoning setting is not a substitute for the 40 closed authoring/QA passes.

## Reproduction inputs

The public repository intentionally does not add the raw canonical source images in
this checkpoint. The local identity and modeling manifests used by v66 have hashes:

- `identity-reference.json`: `41653f14ce045ad86bcf703a806cd61a416ce284a3c831917bac899c901b0179`
- `modeling-input.json`: `914628a1597a0deb30fc172f5023e2bb2674ad9b141d404b0ca342f13544e29f`

Required local tools/assets:

- Blender 5.2.0 LTS with MPFB 2.0.17 (`80919fa4682335c41847f761a4d79dcad4124732`)
- MakeHuman system assets at `/tmp/gahyeon-mh-system-assets`
- Hair Editor `hair.blend`, verified against the checksum above
- `artifacts/gahyeon-g1-authoring/gahyeon-g1-authoring-bootstrap-v2.blend`
- `artifacts/gahyeon-g1-authoring/scene-plan-v2.json`

Author a new revision with unique fail-no-overwrite paths:

```sh
blender --background \
  artifacts/gahyeon-g1-authoring/gahyeon-g1-authoring-bootstrap-v2.blend \
  --python scripts/blender_author_gahyeon_g1.py -- \
  --asset-root /tmp/gahyeon-mh-system-assets \
  --hair-template /tmp/gahyeon-haireditor/hair/haireditor/hair.blend \
  --identity artifacts/gahyeon-ch/identity-reference.json \
  --modeling artifacts/gahyeon-ch/modeling-input.json \
  --output artifacts/gahyeon-ch/models/gahyeon-g1-mpfb-v67.blend \
  --provenance-output artifacts/gahyeon-ch/models/gahyeon-g1-mpfb-v67.provenance.json \
  --revision g1-mpfb-v67
```

When a revision is visually ready, the formal evidence command is:

```sh
blender --background artifacts/gahyeon-ch/models/gahyeon-g1-mpfb-v67.blend \
  --python artifacts/gahyeon-g1-authoring/handoff-v2/tools/blender-render-g1-evidence.py -- \
  --plan artifacts/gahyeon-g1-authoring/scene-plan-v2.json \
  --output-dir artifacts/gahyeon-ch/g1-evidence-v67
```

## Repository safety

- The worktree contains hundreds of unrelated backend, Desktop, Unreal, voice, and
  documentation changes from other concurrent work. Do not reset, clean, stash, or
  bulk-stage it.
- Stage G1 files by explicit path only.
- v1–v57 plus rejected v59/v61–v65/v67–v73 are retained locally as audit drafts/experiments but are not the
  resume artifact.
- The GitHub repository is public. Do not add raw identity reference images without
  a separate explicit publication decision.
