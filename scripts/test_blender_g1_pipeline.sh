#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
blender_bin="${GAHYEON_BLENDER_BIN:-$(command -v blender || true)}"
if [[ -z "$blender_bin" || ! -x "$blender_bin" ]]; then
  echo "Blender is required; set GAHYEON_BLENDER_BIN to its executable" >&2
  exit 3
fi

smoke_root="$(mktemp -d "${TMPDIR:-/tmp}/gahyeon-blender-g1.XXXXXX")"
cleanup() {
  if [[ "$smoke_root" == "${TMPDIR:-/tmp}/gahyeon-blender-g1."* && -d "$smoke_root" ]]; then
    rm -rf "$smoke_root"
  fi
}
trap cleanup EXIT

handoff="$smoke_root/handoff"
plan="$smoke_root/scene-plan.json"
blend="$smoke_root/gahyeon-g1-smoke.blend"
evidence="$smoke_root/evidence"
submission="$smoke_root/submission.zip"

unzip -q "$repo_root/artifacts/gahyeon-g1-handoff.zip" -d "$handoff"
python3 "$handoff/tools/build-g1-scene-plan.py" \
  --handoff-dir "$handoff" --output "$plan" >/dev/null
"$blender_bin" --background --factory-startup \
  --python "$handoff/tools/blender-bootstrap-g1.py" -- \
  --plan "$plan" --handoff-dir "$handoff" --output "$blend" >/dev/null

# This synthetic capsule proves tool execution only. It is created under a disposable
# directory and is never copied into artifacts/gahyeon-ch or counted as G1 authoring.
"$blender_bin" "$blend" --background --python-expr \
  'import bpy; bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=(0,0,90), scale=(35,25,90)); o=bpy.context.object; o.name="SMOKE_ONLY_NOT_G1_MODEL"; [c.objects.unlink(o) for c in tuple(o.users_collection)]; bpy.data.collections["G1_MODEL_BODY"].objects.link(o); bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)' \
  >/dev/null
"$blender_bin" "$blend" --background \
  --python "$handoff/tools/blender-render-g1-evidence.py" -- \
  --plan "$plan" --output-dir "$evidence" >/dev/null

count="$(find "$evidence" -maxdepth 1 -type f -name '*.png' | wc -l | tr -d ' ')"
[[ "$count" == "15" ]] || { echo "expected 15 Blender evidence renders, found $count" >&2; exit 4; }
python3 "$handoff/tools/package-g1-submission.py" \
  --handoff-dir "$handoff" --model "$blend" --format blend \
  --evidence-dir "$evidence" --output "$submission" >/dev/null
python3 "$repo_root/scripts/verify_gahyeon_g1_submission.py" "$submission" >/dev/null

version="$($blender_bin --version | head -1)"
echo "Gahyeon G1 Blender physical smoke passed: $version, 15 renders, sealed candidate fixture"
