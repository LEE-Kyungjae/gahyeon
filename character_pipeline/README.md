# Character Auto-Refinement Pipeline

This directory is the orchestration layer for the Gahyeon hero character. Large
model weights, generated meshes, private references and Unreal binary content do
not belong in Git. Manifests bind them by URI, byte size and SHA-256.

```text
config/       immutable pipeline policy
reference/    manifests, masks and landmarks (private images remain external)
generation/   TRELLIS.2 and Hunyuan3D candidate manifests
blender/      cleanup, measurement and export products
metahuman/    Identity, conform and validation manifests
textures/     skin/eyes/body authoring manifests
groom/        hair/brow/lash source and runtime manifests
clothing/     modular garment manifests
unreal/       fixed QA scene and render manifests
evaluation/   metric definitions and reports
iterations/   immutable experiment ledger
tools/        orchestration and validation commands
```

Create an iteration only with a stated hypothesis:

```bash
python3 character_pipeline/tools/create_iteration.py \
  --root character_pipeline \
  --hypothesis "..." --action "..." --expected "..."
```

No tool may silently overwrite an existing version.

