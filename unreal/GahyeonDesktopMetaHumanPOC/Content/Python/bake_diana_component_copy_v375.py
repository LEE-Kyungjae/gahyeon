"""Bake component-space body-to-face/hair transform propagation for Diana."""

import json
import math
from pathlib import Path

import unreal


MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
SOURCES = (
    "/Game/Gahyeon/Character2/Diana/v372/Animation/AS_Diana_Idle_v244_NeckHead_v372",
    "/Game/Gahyeon/Character2/Diana/v372/Animation/AS_Diana_WalkForward_v244_NeckHead_v372",
    "/Game/Gahyeon/Character2/Diana/v372/Animation/AS_Diana_RunForward_v244_NeckHead_v372",
)
OUTPUT_ROOT = "/Game/Gahyeon/Character2/Diana/v375/Animation"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v375-diana-component-copy-bake/report.json"
)
DRIVERS = {
    "Neck_1": "Neck_1_001",
    "Head": "Head_002",
    "Head_001": "Head_002",
}


def quat_angle(first, other):
    dot = abs(first.x * other.x + first.y * other.y + first.z * other.z + first.w * other.w)
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def transform_record(value):
    rotation = value.rotation.rotator()
    return {
        "translation": [round(value.translation.x, 5), round(value.translation.y, 5), round(value.translation.z, 5)],
        "rotation": [round(rotation.roll, 5), round(rotation.pitch, 5), round(rotation.yaw, 5)],
    }


mesh = unreal.load_asset(MESH)
if mesh is None:
    raise RuntimeError(f"Diana mesh unavailable: {MESH}")
modifier = unreal.SkeletonModifier()
if not modifier.set_skeletal_mesh(mesh):
    raise RuntimeError("could not inspect Diana skeleton")
names = [str(value) for value in modifier.get_all_bone_names()]
parents = {name: str(modifier.get_parent_name(name)) for name in names}
ref_local = {name: modifier.get_bone_transform(name, False) for name in names}
ref_global = {name: modifier.get_bone_transform(name, True) for name in names}


def compose(local, parent_global):
    return unreal.MathLibrary.compose_transforms(local, parent_global)


def relative(child_global, parent_global):
    return unreal.MathLibrary.make_relative_transform(child_global, parent_global)


def validate_reference_composition():
    for bone in ("Neck_1_001", "Head_002", "Neck_1", "FacialDef_Neck", "Head", "Head_001"):
        parent = parents[bone]
        computed = ref_local[bone] if parent.lower() in ("none", "") else compose(ref_local[bone], ref_global[parent])
        distance = unreal.MathLibrary.vector_distance(computed.translation, ref_global[bone].translation)
        angle = quat_angle(computed.rotation, ref_global[bone].rotation)
        if distance > 0.02 or angle > 0.05:
            raise RuntimeError(f"reference composition mismatch {bone}: {distance}cm {angle}deg")


validate_reference_composition()
offsets = {
    target: relative(ref_global[target], ref_global[driver])
    for target, driver in DRIVERS.items()
}


def bake_animation(source_path):
    source = unreal.load_asset(source_path)
    if source is None:
        raise RuntimeError(f"source animation unavailable: {source_path}")
    source_name = source_path.rsplit("/", 1)[1]
    target_name = source_name.replace("_NeckHead_v372", "_ComponentCopy_v375")
    target_path = f"{OUTPUT_ROOT}/{target_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(target_path):
        raise RuntimeError(f"refusing to overwrite immutable animation: {target_path}")
    target = unreal.EditorAssetLibrary.duplicate_asset(source_path, target_path)
    if target is None:
        raise RuntimeError(f"failed to duplicate animation: {source_path}")
    frame_count = int(unreal.AnimationLibrary.get_num_frames(target))

    def local_pose(frame, bone):
        return unreal.AnimationLibrary.get_bone_pose_for_frame(target, bone, frame, False)

    def global_pose(frame, bone, cache):
        if bone in cache:
            return cache[bone]
        parent = parents[bone]
        local = local_pose(frame, bone)
        value = local if parent.lower() in ("none", "") else compose(local, global_pose(frame, parent, cache))
        cache[bone] = value
        return value

    keys = {name: {"position": [], "rotation": [], "scale": []} for name in DRIVERS}
    samples = []
    for frame in range(frame_count):
        cache = {}
        driver_neck = global_pose(frame, "Neck_1_001", cache)
        driver_head = global_pose(frame, "Head_002", cache)
        target_neck_global = compose(offsets["Neck_1"], driver_neck)
        target_head_global = compose(offsets["Head"], driver_head)
        target_hair_global = compose(offsets["Head_001"], driver_head)
        armature_global = global_pose(frame, parents["Neck_1"], cache)
        neck_local = relative(target_neck_global, armature_global)
        facial_neck_global = compose(ref_local["FacialDef_Neck"], target_neck_global)
        head_local = relative(target_head_global, facial_neck_global)
        hair_parent_global = global_pose(frame, parents["Head_001"], cache)
        hair_local = relative(target_hair_global, hair_parent_global)
        for bone, value in (("Neck_1", neck_local), ("Head", head_local), ("Head_001", hair_local)):
            keys[bone]["position"].append(value.translation)
            keys[bone]["rotation"].append(value.rotation)
            keys[bone]["scale"].append(value.scale3d)
        if frame in (0, frame_count // 2, frame_count - 1):
            samples.append({
                "frame": frame,
                "driverNeck": transform_record(driver_neck),
                "targetNeck": transform_record(target_neck_global),
                "driverHead": transform_record(driver_head),
                "targetHead": transform_record(target_head_global),
            })
    controller = target.get_editor_property("controller")
    controller.open_bracket("Bake Diana component-space face and hair propagation", False)
    try:
        for bone, values in keys.items():
            if not controller.set_bone_track_keys(
                bone, values["position"], values["rotation"], values["scale"], False
            ):
                raise RuntimeError(f"failed to set baked bone track: {bone}")
    finally:
        controller.close_bracket(False)
    if not unreal.EditorAssetLibrary.save_loaded_asset(target, False):
        raise RuntimeError(f"failed to save baked animation: {target_path}")
    return {"source": source_path, "animation": target_path, "frames": frame_count, "samples": samples}


results = [bake_animation(path) for path in SOURCES]
report = {
    "schemaVersion": 1,
    "iteration": "v375",
    "status": "draft-component-copy-bake-complete",
    "method": "component-space Copy Bone equivalent baked into immutable animation copies",
    "mesh": MESH,
    "driverMap": DRIVERS,
    "referenceOffsets": {name: transform_record(value) for name, value in offsets.items()},
    "animations": results,
    "hypothesis": "Driving the disconnected face and hair roots from the body neck/head chain removes independent neck rotation while preserving donor offsets.",
    "visualValidationPending": True,
    "humanApproved": False,
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n")
unreal.log("DIANA_V375_COMPONENT_COPY=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
