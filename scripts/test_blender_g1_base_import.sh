#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
blender_bin="${GAHYEON_BLENDER_BIN:-$(command -v blender || true)}"
[[ -n "$blender_bin" && -x "$blender_bin" ]] || exit 3
root="$(mktemp -d "${TMPDIR:-/tmp}/gahyeon-g1-import.XXXXXX")"
trap '[[ -d "$root" ]] && rm -rf "$root"' EXIT

"$blender_bin" --background --factory-startup --python-expr \
  "import bpy; bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False); bpy.ops.mesh.primitive_cube_add(); bpy.ops.export_scene.gltf(filepath='$root/base.glb', export_format='GLB')" >/dev/null
cp "$repo_root/artifacts/gahyeon-g1-authoring/gahyeon-g1-authoring-bootstrap.blend" "$root/scene.blend"
"$blender_bin" "$root/scene.blend" --background \
  --python "$repo_root/scripts/blender_import_gahyeon_g1_base.py" -- \
  --base "$root/base.glb" --output "$root/imported.blend" >/dev/null
audit="$($blender_bin "$root/imported.blend" --background --python-expr \
  'import bpy; meshes=[o for o in bpy.data.collections["G1_MODEL_BODY"].objects if o.type == "MESH"]; valid=bpy.context.scene["gahyeon_base_review_status"] == "unreviewed" and len(meshes)==1 and not bool(meshes[0]["gahyeon_identity_approved"]); print("GAHYEON_BASE_IMPORT_AUDIT=status:%s,meshes:%d,approved:%s" % (bpy.context.scene["gahyeon_base_review_status"],len(meshes),[bool(o["gahyeon_identity_approved"]) for o in meshes])); print("GAHYEON_BASE_IMPORT_VALID="+str(valid))' 2>&1)"
grep -Fq 'GAHYEON_BASE_IMPORT_VALID=True' <<<"$audit" || {
  printf '%s\n' "$audit" >&2
  exit 4
}
echo "Gahyeon G1 base import physical smoke passed"
