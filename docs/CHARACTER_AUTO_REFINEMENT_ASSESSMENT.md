# Gahyeon Character Auto-Refinement Pipeline — assessment and architecture

## A. Current-state assessment

### Proven and working

- Canonical identity inventory: 29 classified source images, 18 canonical
  references, immutable SHA-256 records, and explicit authority ordering.
- Identity anchors: face master 03; depth/profile 06/07/08; body 16/19/20.
- G1 Blender automation: repeatable authoring, fixed cameras, evidence rendering,
  packaging, provenance, topology checks, and non-overwriting outputs.
- Real G1 blockout: v79 has a coherent humanoid mesh, 53-bone body rig, eyes,
  mouth parts, groom prototype, clothing prototypes, and verified checksums.
- MetaHuman handoff input: a portable, checksummed neutral OBJ/MTL/skin/eye package
  exists under `artifacts/gahyeon-ch/metahuman-identity-input-v79/`.
- Gate lifecycle: G1–G5 JSON schemas and fail-closed draft/candidate/approved flows.
- Unreal runtime foundation: speech, lip-sync semantics, gaze/attention, ambient
  motion, gestures, persistence, interaction, replaceable hero pawn, packaging,
  and source-level automated tests.

### Incomplete or absent

- Canonical coverage does not meet the requested angular/expression matrix. Rear
  neutral body, rear/top hair, unobstructed ears/hands, eye/mouth close-ups, and
  canonical outfit rear are explicitly missing. Expressions are not a controlled
  same-camera identity set and do not cover the ten required visemes.
- TRELLIS.2 and Hunyuan3D are not installed or integrated. No candidate has been
  generated, normalized, rendered, or measured by either system.
- No common reconstruction candidate schema, runner adapter, model-version pin,
  or failure/retry contract exists.
- G1 remains draft with 0/15 registered evidence and no human approvals. G2–G5
  are not started.
- No Unreal Editor, MetaHuman Creator Core Data, MetaHuman DNA, RigLogic character,
  MetaHuman facial rig, or MetaHuman Identity Solve output exists locally.
- Existing skin is a 2K diffuse source with procedural response, not a production
  multi-channel skin set. Existing hair and garments are prototypes.
- No stable quantitative identity/geometry/deformation scoring implementation or
  calibrated thresholds exist. Previous visual iterations are documented but not
  represented by a reusable immutable iteration ledger.
- No Unreal asset-based fixed QA map or Movie Render Queue output has been proven.

## B. Preserve

- Original images, identity manifest, modeling input, authority rules, and hashes.
- v79 only as a shape hypothesis and regression reference, not as final topology.
- Existing G1–G5 review lifecycle, content-addressed packaging, and approval rules.
- Unreal runtime core and `AGahyeonCharacterPawn` replaceable character boundary.
- Fixed-camera principles, Blender validation utilities, and all rejected-version
  evidence needed to avoid repeating failed hypotheses.

## C. Replace

- MPFB final face/body topology with MetaHuman production topology and DNA/RigLogic.
- 53-bone rig as facial solution with a MetaHuman facial/deformation system.
- 2K diffuse-only skin with authored multi-channel 4K/8K source textures.
- generic shoulder Hair Editor groom with an identity-specific production groom.
- procedural jacket/shoes with separate, patterned, deformation-ready garments.
- ad-hoc version notes as the primary experiment record with the immutable iteration
  contract introduced here.

## D. Newly introduce

- Controlled canonical reference matrix, masks, landmarks, camera calibration, and
  uncertainty/authority metadata.
- Independent TRELLIS.2 and Hunyuan3D adapters with pinned environments and output
  manifests; neither output is a production mesh.
- Standard reconstruction cleanup, measurement, render, and candidate comparison.
- MetaHuman Identity/Conform automation boundary and post-conform same-camera QA.
- Skin, eyes, groom, garment, facial deformation, body deformation, and Unreal
  runtime QA subsystems.
- Versioned evaluation reports with defects, causes, confidence, suggested owner,
  hypothesis, expected outcome, actual delta, and keep/revert decision.

## E. Target architecture

```text
canonical ground truth
  -> reconstruction adapters [TRELLIS.2 | Hunyuan3D]
  -> common candidate contract
  -> Blender normalize/clean/measure/render
  -> geometry and identity ranking (no topology preservation requirement)
  -> MetaHuman Identity / conform
  -> DNA + production topology + RigLogic
  -> skin / eyes / groom / modular garment authoring
  -> deformation and animation tests
  -> fixed Unreal QA scene and renders
  -> scored report + human review
  -> immutable keep/revert iteration decision
```

Every arrow has explicit input, processing, output, validation, logs, and terminal
failure state. Stages do not infer success from file existence.

## F. Dependencies

### Installed

- Blender 5.2 LTS and Python tooling.
- Epic Games Launcher 20.1.4, signed and notarized.
- Unreal source project targeting 5.6, but no local engine binary.

### Required before MetaHuman execution

- Unreal Engine 5.8 (validated baseline: 5.8.1) or newer with MetaHuman Creator Core Data.
- MetaHuman Creator, MetaHuman Animator, Depth Processing, RigLogic, HairStrands,
  Control Rig, FullBodyIK, and Chaos Cloth plugins appropriate to the engine build.
- Epic account login and network access to MetaHuman solve/autorig/texture services.
- At least 80 GiB free installation headroom. Current machine has about 43 GiB.
- Current M3/16 GiB machine meets the Unreal minimum but not Epic's 32 GiB
  MetaHuman recommendation; heavy assembly may require a stronger workstation.

### Reconstruction workers

- Separate pinned GPU environments for TRELLIS.2 and Hunyuan3D. Do not combine
  mutually incompatible CUDA/PyTorch environments with the application runtime.
- Model weights with recorded source URL, license, commit/release, SHA-256, runtime
  GPU/VRAM, seed, input hashes, and command line.

## G. Milestone plan

1. **P0 contracts and ground truth** — immutable iteration contract; complete,
   identity-consistent view matrix; masks, landmarks and camera calibration.
2. **P1 reconstruction benchmark** — one pinned TRELLIS.2 and one Hunyuan3D run,
   common cleanup/renders/measurements, reproducible candidate ranking.
3. **P2 MetaHuman conform** — Identity Solve, DNA/RigLogic assembly, same-camera
   post-conform identity validation and a human likeness decision.
4. **P3 face systems** — high-resolution neutral, skin channels, eyes/mouth, facial
   contact and deformation tests.
5. **P4 hair/body/clothing** — production groom, UE skeleton body, modular garment,
   cloth and penetration/LOD tests.
6. **P5 performance** — expressions, ten Korean visemes, blink/gaze/breathing,
   gestures, sit/stand/walk, corrective deformation.
7. **P6 Unreal hero** — fixed QA scene, MRQ automation, performance budget, runtime
   AI-assistant integration and G1–G5 evidence chain.

Milestone numbers are not quality percentages. A milestone closes only with the
listed artifacts and review evidence.

## H. Implementation order

1. Implement and test immutable iteration creation/validation.
2. Materialize the canonical reference coverage report without generating false
   rear/profile authority.
3. Add reconstruction adapter interface and dry-run manifests.
4. Provision GPU workers and execute both reconstruction models independently.
5. Add Blender cleanup/measurement/render runner and deterministic camera bundle.
6. Build geometry scoring with calibrated landmarks and human-reviewed tolerances.
7. Install Unreal/MetaHuman toolchain and conform the selected shape.
8. Re-run identity scoring on MetaHuman output before downstream lookdev.
9. Implement skin/eyes, then groom, body/garment, deformation, and Unreal QA.

## I. Automated QA design

### Hard gates

- Provenance and inventory hashes match; output never overwrites an iteration.
- Mesh imports, normalized units/orientation/ground are known, and non-manifold,
  boundaries, duplicates and symmetry deviations are reported.
- All required reference/render views exist at declared cameras and resolution.
- MetaHuman candidate contains real DNA/RigLogic and required LOD/deformation data.
- Deformation tests detect lip/eyelid penetration, mesh inversion/collapse, garment
  penetration and excessive stretch; failure stops promotion.

### Scores

Scores are 0–100 only after metric calibration. Missing evidence produces `null`,
never zero or an invented estimate. Report components independently:

- Identity Similarity, Face Geometry, Body Geometry
- Skin, Eyes, Hair, Materials
- Rig, Facial Deformation, Body Deformation
- Lighting Robustness, Close-up Quality, Runtime Performance

Overall is computed only when all release-required components exist. Each defect
records view/metric evidence, likely cause, recommendation, confidence and whether
automation or a human artist owns the decision. Identity and geometry scores may
rank candidates, but cannot approve likeness without human review.

### Comparison policy

Every action begins with one falsifiable hypothesis. Same cameras, lighting,
reference set and evaluator version are used for before/after. The iteration stores
expected and actual score changes. Improvements may be kept; regressions are
reverted by selecting the prior immutable artifact, never by overwriting history.

## J. First concrete implementation task

The first implementation is the immutable iteration contract under
`character_pipeline/iterations/`, backed by `tools/create_iteration.py` and
`tools/verify_iteration.py`. It is deliberately model-agnostic so TRELLIS.2,
Hunyuan3D, Blender, MetaHuman and Unreal all emit the same auditable record.

The initial `v001` iteration records the hypothesis that v79 is useful only as
MetaHuman Identity Solve input—not production topology—and binds its verified
manifest. It makes no reconstruction, MetaHuman, likeness, or AAA completion claim.

## P0 implementation result

P0 was implemented rather than left as a design:

- `character_pipeline/tools/create_iteration.py` and `verify_iteration.py` create
  monotonic immutable versions and reject unsupported overall scores.
- `reference/coverage.json` audits the exact controlled-view matrix. Current
  authoritative coverage is face 5/11, body 2/6, expressions 0/16.
- Independent `generation/trellis/candidate_001` and
  `generation/hunyuan/candidate_001` workspaces exist. Both remain `planned` and
  cannot claim generation without pinned runner/repository/revision/weights.
- `v001` binds the verified MetaHuman solve input and records the failed local
  MetaHuman toolchain preflight rather than silently continuing.
- A fixed Looking Glass Go profile now uses the real 1440×2560 portrait panel for
  single-view QA and 66 views for the pinned Unreal runtime. Quilt columns, rows,
  and texture resolution remain null until a connected Bridge calibration attests
  them; panel resolution is not confused with quilt texture resolution.
- Face and body baselines were rendered at 1440×2560 and visually inspected. They
  expose blocking hairline/groom, face/skin/eye and garment defects; no quality
  score was invented.
- Two independent 768-square diagnostic runs established decoded-pixel
  reproducibility: face front was pixel-identical; body front had maximum 1/255
  difference and zero pixels above 2/255. Different PNG hashes alone are therefore
  not treated as visual nondeterminism.

The square diagnostic protocol is retained only for reproducibility evidence. All
new official single-view character QA uses the Looking Glass Go profile. Hologram
quilt acceptance still requires the actual Go, Bridge calibration, and Win64 Unreal
plugin attestation.
