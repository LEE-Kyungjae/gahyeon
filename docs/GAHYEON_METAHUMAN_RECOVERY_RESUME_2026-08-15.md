# Gahyeon MetaHuman identity recovery — 2026-08-15

## Current decision

v072 is structurally assembled but visually rejected. It is immutable failure evidence, not a production candidate. Do not delete it and do not use its geometry as the source of another iteration.

The failure came from solving a heavily edited low-resolution MPFB head from one front camera, accepting a brow-region warning, and assembling before fixed-camera multi-view human review. MetaHuman rigging cannot repair incorrect identity geometry; it preserves and animates it.

## New hard gate

No MetaHuman character assembly may proceed without all of the following:

1. a successful, unapproved Identity solve receipt;
2. five 1440x2560 head-only renders: front, left/right 45, left/right profile;
3. comparison against canonical references 03/06/07/08;
4. an explicit named human `keep-and-build-surfaces` decision with no blocking findings;
5. a checksum-bound authorization produced by `character_pipeline/tools/authorize_metahuman_assembly.py`.

The authorization additionally proves that the render job, solve receipt, solved Identity asset, reviewed iteration, and decision all refer to the same candidate. A rejected decision cannot produce authorization.

## Resume point

Start from `character_pipeline/metahuman/identity/v073/recovery-work-order.json`. Build a clean MetaHuman-template-based neutral head and constrain the fit across all five views. Do not add final skin, groom, clothing, body assembly, autorig polish, or Looking Glass quilt work until the identity checkpoint is kept by the character owner.

Verification commands:

```bash
python3 -m unittest character_pipeline.tools.test_post_conform_identity_checkpoint_v002
python3 -m unittest character_pipeline.tools.test_authorize_metahuman_assembly
```

After a real five-view review is accepted:

```bash
python3 character_pipeline/tools/authorize_metahuman_assembly.py \
  --decision /absolute/path/to/decision.json \
  --solve-receipt /absolute/path/to/solve.json \
  --output /absolute/path/to/assembly-authorization.json
```

Never hand-edit an authorization or mark a draft/candidate as approved.
