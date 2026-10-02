#!/usr/bin/env python3
"""Find reusable high-motion windows in long FBX performance donors."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy


SEMANTIC_TOKENS = ("hips", "pelvis", "spine", "neck", "head", "shoulder", "arm", "forearm", "hand")


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--iteration", default="v477")
    parser.add_argument("--window-seconds", type=float, default=2.5)
    parser.add_argument("--candidate-count", type=int, default=6)
    return parser.parse_args(values)


def quaternion_angle_degrees(first, second) -> float:
    dot = min(1.0, max(-1.0, abs(first.dot(second))))
    return math.degrees(2.0 * math.acos(dot))


def moving_average(values: list[float], radius: int) -> list[float]:
    prefix = [0.0]
    for value in values:
        prefix.append(prefix[-1] + value)
    result = []
    for index in range(len(values)):
        low = max(0, index - radius)
        high = min(len(values), index + radius + 1)
        result.append((prefix[high] - prefix[low]) / max(1, high - low))
    return result


def analyze_fbx_motion_segments_v477(
    source: Path, output: Path, iteration: str, window_seconds: float, candidate_count: int
) -> dict[str, object]:
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable analysis: {output}")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE" and obj.animation_data and obj.animation_data.action]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one animated armature, found {[obj.name for obj in armatures]}")
    armature = armatures[0]
    action = armature.animation_data.action
    start = int(math.floor(action.frame_range[0]))
    end = int(math.ceil(action.frame_range[1]))
    fps = float(bpy.context.scene.render.fps) / float(bpy.context.scene.render.fps_base)
    selected = [
        bone for bone in armature.pose.bones
        if any(token in bone.name.lower() for token in SEMANTIC_TOKENS)
        and not any(token in bone.name.lower() for token in ("finger", "twist", "weapon", "socket", "end"))
    ]
    if not selected:
        raise RuntimeError("no semantic body bones found")
    previous = None
    energies: list[float] = []
    per_bone_peak = {bone.name: 0.0 for bone in selected}
    for frame in range(start, end + 1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        current = {bone.name: (bone.matrix.to_quaternion(), bone.matrix.to_translation()) for bone in selected}
        if previous is None:
            energy = 0.0
        else:
            energy = 0.0
            for name, (rotation, location) in current.items():
                old_rotation, old_location = previous[name]
                value = quaternion_angle_degrees(old_rotation, rotation) + (location - old_location).length * 0.15
                per_bone_peak[name] = max(per_bone_peak[name], value)
                energy += value
        energies.append(energy)
        previous = current
    radius = max(1, round(window_seconds * fps / 2.0))
    smoothed = moving_average(energies, radius)
    order = sorted(range(len(smoothed)), key=lambda index: smoothed[index], reverse=True)
    chosen: list[int] = []
    minimum_gap = max(1, round(window_seconds * fps * 0.8))
    for index in order:
        if all(abs(index - existing) >= minimum_gap for existing in chosen):
            chosen.append(index)
        if len(chosen) >= candidate_count:
            break
    chosen.sort()
    half_window = max(1, round(window_seconds * fps / 2.0))
    candidates = []
    for rank, index in enumerate(chosen, start=1):
        center = start + index
        segment_start = max(start, center - half_window)
        segment_end = min(end, center + half_window)
        candidates.append({
            "id": f"segment-{rank:02d}", "startFrame": segment_start, "endFrame": segment_end,
            "centerFrame": center, "startSeconds": (segment_start - start) / fps,
            "endSeconds": (segment_end - start) / fps, "meanMotionEnergy": smoothed[index],
            "classification": "candidate-requires-visual-review",
        })
    shape_actions = []
    for candidate in bpy.data.actions:
        if candidate == action:
            continue
        curves = list(getattr(candidate, "fcurves", ()))
        channel_bags = []
        for layer in getattr(candidate, "layers", ()):
            for strip in getattr(layer, "strips", ()):
                for bag in getattr(strip, "channelbags", ()):
                    channel_bags.append(bag)
                    curves.extend(getattr(bag, "fcurves", ()))
        if curves or channel_bags:
            shape_actions.append({
                "name": candidate.name, "frameRange": list(candidate.frame_range),
                "curveCount": len(curves), "keyframeCount": sum(len(curve.keyframe_points) for curve in curves),
                "channelBagCount": len(channel_bags),
            })
    report = {
        "schemaVersion": 1, "iteration": iteration, "status": "motion-segments-analyzed-draft",
        "source": str(source.resolve()), "sourceBytes": source.stat().st_size,
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "armature": armature.name, "action": action.name, "fps": fps,
        "frameRange": [start, end], "durationSeconds": (end - start) / fps,
        "selectedBones": [bone.name for bone in selected],
        "highestPerFrameBones": [
            {"bone": name, "peakDelta": value}
            for name, value in sorted(per_bone_peak.items(), key=lambda item: item[1], reverse=True)[:12]
        ],
        "candidateSegments": candidates, "shapeActions": shape_actions,
        "humanApproved": False, "releaseEligible": False,
    }
    output.parent.mkdir(parents=True, exist_ok=False)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    args = parse_args()
    report = analyze_fbx_motion_segments_v477(
        args.input, args.output, args.iteration, args.window_seconds, args.candidate_count
    )
    print(json.dumps({"iteration": report["iteration"], "durationSeconds": report["durationSeconds"], "candidateSegments": report["candidateSegments"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
