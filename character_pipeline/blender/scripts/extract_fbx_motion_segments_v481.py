#!/usr/bin/env python3
"""Export selected immutable motion-analysis windows as short FBX donor clips."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--analysis", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--segments", required=True, help="Comma-separated segment ids")
    parser.add_argument("--iteration", default="v481")
    return parser.parse_args(values)


def extract_fbx_motion_segments_v481(
    source: Path, analysis_path: Path, output_dir: Path, segment_ids: list[str], iteration: str
) -> dict[str, object]:
    if not source.is_file() or not analysis_path.is_file():
        raise FileNotFoundError(f"missing source or analysis: {source}, {analysis_path}")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite immutable clip directory: {output_dir}")
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    by_id = {segment["id"]: segment for segment in analysis["candidateSegments"]}
    missing = sorted(set(segment_ids) - set(by_id))
    if missing:
        raise RuntimeError(f"unknown candidate segments: {missing}")
    output_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE" and obj.animation_data and obj.animation_data.action]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one animated armature, found {[obj.name for obj in armatures]}")
    armature = armatures[0]
    meshes = [
        obj for obj in bpy.context.scene.objects if obj.type == "MESH"
        and any(mod.type == "ARMATURE" and mod.object == armature for mod in obj.modifiers)
    ]
    if not meshes:
        raise RuntimeError("animated donor has no skinned meshes")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [armature, *meshes]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    exports = []
    for segment_id in segment_ids:
        segment = by_id[segment_id]
        start = int(segment["startFrame"])
        end = int(segment["endFrame"])
        bpy.context.scene.frame_start = start
        bpy.context.scene.frame_end = end
        bpy.context.scene.frame_set(start)
        output = output_dir / f"{segment_id}-frames-{start:04d}-{end:04d}.fbx"
        bpy.ops.export_scene.fbx(
            filepath=str(output), use_selection=True, object_types={"ARMATURE", "MESH"},
            apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False,
            use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
            bake_anim_step=1.0, bake_anim_simplify_factor=0.0,
            path_mode="COPY", embed_textures=False,
        )
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(f"clip export failed: {segment_id}")
        exports.append({
            "segment": segment_id, "startFrame": start, "endFrame": end,
            "file": str(output.resolve()), "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        })
    report = {
        "schemaVersion": 1, "iteration": iteration, "status": "selected-motion-clips-exported-draft",
        "source": str(source.resolve()), "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "analysis": str(analysis_path.resolve()), "armature": armature.name,
        "boneCount": len(armature.data.bones), "exports": exports,
        "humanApproved": False, "releaseEligible": False,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    args = parse_args()
    report = extract_fbx_motion_segments_v481(
        args.input, args.analysis, args.output_dir,
        [value.strip() for value in args.segments.split(",") if value.strip()], args.iteration,
    )
    print(json.dumps({"iteration": report["iteration"], "clipCount": len(report["exports"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
