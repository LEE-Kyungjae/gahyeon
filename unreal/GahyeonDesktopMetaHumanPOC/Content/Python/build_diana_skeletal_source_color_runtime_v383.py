"""Promote source-color materials with explicit skeletal usage into a fresh runtime."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MATERIAL_ROOT = "/Game/Gahyeon/Character2/Diana/v380/Materials"
TARGET_MATERIAL_ROOT = "/Game/Gahyeon/Character2/Diana/v382/Materials"
MAP = "/Game/Gahyeon/Character2/Diana/v383/Runtime/L_DianaMacRuntimeSourceColor_v383"
MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
ANIMATION = "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_RunForward_v244_ComponentCopy_v375"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v383-diana-skeletal-source-color/report.json"
LABELS = [
    "Face", "Tooth", "EyeLeft", "EyeRight", "EyeShell", "Eyebrows",
    "Eyelash", "EyelashLower", "Hair", "Jacket1", "Leg", "Body", "Hand",
    "Jacket2", "Belt", "Emissive", "EmissiveNeck", "Reflector",
]


def require(path):
    value = unreal.EditorAssetLibrary.load_asset(path)
    if value is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return value


if unreal.EditorAssetLibrary.does_asset_exist(MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v383 runtime")
materials = []
for index, label in enumerate(LABELS):
    source = f"{SOURCE_MATERIAL_ROOT}/M_Diana_{index:02d}_{label}_SourceColor_v380"
    target = f"{TARGET_MATERIAL_ROOT}/M_Diana_{index:02d}_{label}_SkeletalSourceColor_v382"
    if unreal.EditorAssetLibrary.does_asset_exist(target):
        raise RuntimeError(f"refusing to overwrite {target}")
    material = unreal.EditorAssetLibrary.duplicate_asset(source, target)
    if material is None:
        raise RuntimeError(f"failed to duplicate {source}")
    material.set_editor_property("used_with_skeletal_mesh", True)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    materials.append(material)

mesh = require(MESH)
animation = require(ANIMATION)
if not unreal.EditorLevelLibrary.new_level(MAP):
    raise RuntimeError("failed to create Diana v383 runtime map")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
character = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
character.set_actor_label("Diana_Runtime_SkeletalSourceColor_v383")
component = character.get_component_by_class(unreal.SkeletalMeshComponent)
component.set_editor_property("skeletal_mesh_asset", mesh)
for index, material in enumerate(materials):
    component.set_material(index, material)
component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
component.set_editor_property(
    "animation_data",
    unreal.SingleAnimationPlayData(
        anim_to_play=animation, saved_looping=True, saved_playing=True,
        saved_position=0.0, saved_play_rate=1.0,
    ),
)
origin, extent = character.get_actor_bounds(False, True)
target = unreal.Vector(origin.x, origin.y, origin.z + 2.0)
camera_location = target + unreal.Vector(0.0, 345.0, 3.0)
camera = actors.spawn_actor_from_class(
    unreal.CineCameraActor, camera_location,
    unreal.MathLibrary.find_look_at_rotation(camera_location, target),
)
camera.set_actor_label("CAM_Diana_Runtime_SkeletalSourceColor_v383")
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
camera.camera_component.set_editor_property("current_focal_length", 52.0)
camera.camera_component.set_editor_property("current_aperture", 8.0)
actors.spawn_actor_from_class(
    unreal.PlayerStart, unreal.Vector(2000.0, 2000.0, 1000.0), unreal.Rotator()
)
post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
post.set_editor_property("unbound", True)
settings = post.get_editor_property("settings")
settings.set_editor_property("override_motion_blur_amount", True)
settings.set_editor_property("motion_blur_amount", 0.0)
post.set_editor_property("settings", settings)
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save Diana v383 runtime map")

report = {
    "schemaVersion": 1, "iteration": "v383",
    "status": "candidate-skeletal-source-color-macos-runtime", "map": MAP,
    "mesh": MESH, "animation": ANIMATION, "materialIteration": "v382",
    "sourceTextureCount": 19, "sourceTextureMaximum": [2048, 2048],
    "explicitRgbReconstruction": True, "skeletalUsageExplicit": True,
    "lightingIndependent": True, "humanAnimationApprovalInherited": True,
    "transparentDesktopOverlayPending": True,
    "runtimeVisualValidationPending": True, "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_SKELETAL_SOURCE_COLOR_V383=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
