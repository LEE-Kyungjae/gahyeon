"""Build Diana's immutable source-PBR macOS runtime without map duplication."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MAP = "/Game/Gahyeon/Character2/Diana/v379/Runtime/L_DianaMacRuntimePBR_v379"
MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
ANIMATION = "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_RunForward_v244_ComponentCopy_v375"
MATERIAL_ROOT = "/Game/Gahyeon/Character2/Diana/v377/Materials"
MATERIAL_NAMES = [
    "M_Diana_00_Face_PBR_v377", "M_Diana_01_Tooth_PBR_v377",
    "M_Diana_02_EyeLeft_PBR_v377", "M_Diana_03_EyeRight_PBR_v377",
    "M_Diana_04_EyeShell_PBR_v377", "M_Diana_05_Eyebrows_PBR_v377",
    "M_Diana_06_Eyelash_PBR_v377", "M_Diana_07_EyelashLower_PBR_v377",
    "M_Diana_08_Hair_PBR_v377", "M_Diana_09_Jacket1_PBR_v377",
    "M_Diana_10_Leg_PBR_v377", "M_Diana_11_Body_PBR_v377",
    "M_Diana_12_Hand_PBR_v377", "M_Diana_13_Jacket2_PBR_v377",
    "M_Diana_14_Belt_PBR_v377", "M_Diana_15_Emissive_PBR_v377",
    "M_Diana_16_EmissiveNeck_PBR_v377", "M_Diana_17_Reflector_PBR_v377",
]
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v379-diana-source-pbr-runtime/report.json"


def require(path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def add_rect_light(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 100.0)
    component.set_editor_property("source_height", 120.0)


if unreal.EditorAssetLibrary.does_asset_exist(MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v379 runtime")
mesh = require(MESH)
animation = require(ANIMATION)
materials = [require(f"{MATERIAL_ROOT}/{name}") for name in MATERIAL_NAMES]
if not unreal.EditorLevelLibrary.new_level(MAP):
    raise RuntimeError("failed to create Diana v379 map")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
character = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
character.set_actor_label("Diana_Runtime_PBR_v379")
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
height = extent.z * 2.0
target = unreal.Vector(origin.x, origin.y, origin.z + 3.0)
camera_location = target + unreal.Vector(0.0, 315.0, 3.0)
camera = actors.spawn_actor_from_class(
    unreal.CineCameraActor, camera_location,
    unreal.MathLibrary.find_look_at_rotation(camera_location, target),
)
camera.set_actor_label("CAM_Diana_Runtime_PBR_v379")
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
camera.camera_component.set_editor_property("current_focal_length", 58.0)
camera.camera_component.set_editor_property("current_aperture", 8.0)
actors.spawn_actor_from_class(
    unreal.PlayerStart, unreal.Vector(2000.0, 2000.0, 1000.0), unreal.Rotator()
)
add_rect_light(actors, "KEY_Diana_PBR_v379", target + unreal.Vector(-95.0, 150.0, 70.0), target, 3800.0)
add_rect_light(actors, "FILL_Diana_PBR_v379", target + unreal.Vector(105.0, 145.0, 25.0), target, 1900.0)
add_rect_light(actors, "RIM_Diana_PBR_v379", target + unreal.Vector(0.0, -100.0, 55.0), target, 2500.0)
sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.6)
post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
post.set_editor_property("unbound", True)
settings = post.get_editor_property("settings")
settings.set_editor_property("override_auto_exposure_method", True)
settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
settings.set_editor_property("override_auto_exposure_bias", True)
settings.set_editor_property("auto_exposure_bias", 0.5)
settings.set_editor_property("override_motion_blur_amount", True)
settings.set_editor_property("motion_blur_amount", 0.0)
post.set_editor_property("settings", settings)
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save Diana v379 runtime map")

report = {
    "schemaVersion": 1, "iteration": "v379",
    "status": "candidate-source-pbr-macos-runtime", "map": MAP,
    "mesh": MESH, "animation": ANIMATION, "materialIteration": "v377",
    "sourceTextureCount": 19, "sourceTextureMaximum": [2048, 2048],
    "materialSlots": len(materials), "heightCm": height,
    "humanAnimationApprovalInherited": True,
    "transparentDesktopOverlayPending": True,
    "runtimeVisualValidationPending": True, "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_MACOS_RUNTIME_PBR_V379=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
