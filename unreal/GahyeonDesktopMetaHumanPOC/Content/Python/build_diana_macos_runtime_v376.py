"""Build Diana's first canonical macOS Unreal game-window runtime map."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MAP = "/Game/Gahyeon/Character2/Diana/v376/Runtime/L_DianaMacRuntime_v376"
MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
ANIMATION = "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_RunForward_v244_ComponentCopy_v375"
MATERIAL_ROOT = "/Game/Gahyeon/Character2/Diana/v002/Materials"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v376-diana-macos-runtime/report.json"


def require_asset(path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required runtime asset unavailable: {path}")
    return asset


def add_rect_light(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight, location, unreal.MathLibrary.find_look_at_rotation(location, target)
    )
    if light is None:
        raise RuntimeError(f"failed to spawn {label}")
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 100.0)
    component.set_editor_property("source_height", 120.0)


if unreal.EditorAssetLibrary.does_asset_exist(MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v376 runtime")
mesh = require_asset(MESH)
animation = require_asset(ANIMATION)
materials = [require_asset(f"{MATERIAL_ROOT}/M_Diana_Slot{index:02d}_v002") for index in range(18)]
if mesh.get_editor_property("skeleton") != animation.get_editor_property("skeleton"):
    raise RuntimeError("Diana runtime mesh and animation skeleton differ")
if not unreal.EditorLevelLibrary.new_level(MAP):
    raise RuntimeError("failed to create Diana v376 runtime map")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
character = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
if character is None:
    raise RuntimeError("failed to spawn Diana runtime character")
character.set_actor_label("Diana_Runtime_v376")
component = character.get_component_by_class(unreal.SkeletalMeshComponent)
component.set_editor_property("skeletal_mesh_asset", mesh)
for index, material in enumerate(materials):
    component.set_material(index, material)
component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
component.set_editor_property(
    "animation_data",
    unreal.SingleAnimationPlayData(
        anim_to_play=animation,
        saved_looping=True,
        saved_playing=True,
        saved_position=0.0,
        saved_play_rate=1.0,
    ),
)

origin, extent = character.get_actor_bounds(False, True)
height = extent.z * 2.0
if not 90.0 <= height <= 130.0:
    raise RuntimeError(f"unexpected Diana runtime height: {height}")
target = unreal.Vector(origin.x, origin.y, origin.z)
camera_location = target + unreal.Vector(0.0, 430.0, 4.0)
camera = actors.spawn_actor_from_class(
    unreal.CineCameraActor,
    camera_location,
    unreal.MathLibrary.find_look_at_rotation(camera_location, target),
)
if camera is None:
    raise RuntimeError("failed to spawn Diana runtime camera")
camera.set_actor_label("CAM_Diana_Runtime_v376")
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
camera.camera_component.set_editor_property("current_focal_length", 50.0)
camera.camera_component.set_editor_property("current_aperture", 5.6)
player = actors.spawn_actor_from_class(
    unreal.PlayerStart, unreal.Vector(2000.0, 2000.0, 1000.0), unreal.Rotator()
)
player.set_actor_label("PlayerStart_OffCamera_v376")
add_rect_light(actors, "KEY_Diana_Runtime_v376", target + unreal.Vector(-100.0, 160.0, 70.0), target, 4200.0)
add_rect_light(actors, "FILL_Diana_Runtime_v376", target + unreal.Vector(110.0, 145.0, 30.0), target, 2300.0)
add_rect_light(actors, "RIM_Diana_Runtime_v376", target + unreal.Vector(0.0, -100.0, 55.0), target, 2800.0)
sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.8)
post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
post.set_editor_property("unbound", True)
settings = post.get_editor_property("settings")
settings.set_editor_property("override_auto_exposure_method", True)
settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
settings.set_editor_property("override_auto_exposure_bias", True)
settings.set_editor_property("auto_exposure_bias", 1.0)
settings.set_editor_property("override_motion_blur_amount", True)
settings.set_editor_property("motion_blur_amount", 0.0)
post.set_editor_property("settings", settings)
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save Diana v376 runtime map")

report = {
    "schemaVersion": 1,
    "iteration": "v376",
    "status": "candidate-macos-unreal-game-window-runtime",
    "map": MAP,
    "mesh": MESH,
    "animation": ANIMATION,
    "animationProfile": "character_pipeline/config/diana-component-space-animation-v375.json",
    "heightCm": height,
    "materialSlots": len(materials),
    "humanAnimationApprovalInherited": True,
    "runtimeVisualValidationPending": True,
    "packagedApp": False,
    "productionReady": False
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_MACOS_RUNTIME_V376=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
