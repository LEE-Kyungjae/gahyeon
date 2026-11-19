"""Build a fixed full-body QA map for Diana's primary-chain run candidate."""

import json

import unreal


MAP = "/Game/Gahyeon/Character2/Diana/v041/QA/L_Diana_PrimaryChainRun_v041"
MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
ANIMATION = (
    "/Game/Gahyeon/Character2/Diana/v040/Animation/"
    "AS_Diana_RunForward_v244_PrimaryLegs_v040"
)
MATERIAL_ROOT = "/Game/Gahyeon/Character2/Diana/v002/Materials"
HIDDEN = "/Game/Gahyeon/Character2/Diana/v034/QA/M_Diana_HiddenAccessories_v034"
HIDDEN_SLOTS = (14, 15, 16, 17)


def require_asset(path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def rect_light(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight,
        location,
        unreal.MathLibrary.find_look_at_rotation(location, target),
    )
    if light is None:
        raise RuntimeError(f"failed to spawn {label}")
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 100.0)
    component.set_editor_property("source_height", 120.0)


if unreal.EditorAssetLibrary.does_asset_exist(MAP):
    raise RuntimeError(f"refusing to overwrite immutable map: {MAP}")
mesh = require_asset(MESH)
animation = require_asset(ANIMATION)
materials = [
    require_asset(f"{MATERIAL_ROOT}/M_Diana_Slot{index:02d}_v002")
    for index in range(18)
]
hidden = require_asset(HIDDEN)
if not unreal.EditorLevelLibrary.new_level(MAP):
    raise RuntimeError("failed to create Diana primary-chain QA map")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
character = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
if character is None:
    raise RuntimeError("failed to spawn Diana")
character.set_actor_label("Diana_v041_PrimaryChainRunDraft")
component = character.get_component_by_class(unreal.SkeletalMeshComponent)
component.set_editor_property("skeletal_mesh_asset", mesh)
for index, material in enumerate(materials):
    component.set_material(index, hidden if index in HIDDEN_SLOTS else material)
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
    raise RuntimeError(f"unexpected Diana height: {height}")
target = unreal.Vector(origin.x, origin.y, origin.z)
camera_location = target + unreal.Vector(0.0, 430.0, 4.0)
camera = actors.spawn_actor_from_class(
    unreal.CineCameraActor,
    camera_location,
    unreal.MathLibrary.find_look_at_rotation(camera_location, target),
)
camera.set_actor_label("CAM_Diana_FullBody_v041")
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
camera.camera_component.set_editor_property("current_focal_length", 50.0)
camera.camera_component.set_editor_property("current_aperture", 5.6)
player = actors.spawn_actor_from_class(
    unreal.PlayerStart, unreal.Vector(2000.0, 2000.0, 1000.0), unreal.Rotator()
)
player.set_actor_label("PlayerStart_OffCamera_v041")
rect_light(actors, "KEY_Diana_v041", target + unreal.Vector(-100.0, 160.0, 70.0), target, 4200.0)
rect_light(actors, "FILL_Diana_v041", target + unreal.Vector(110.0, 145.0, 30.0), target, 2300.0)
rect_light(actors, "RIM_Diana_v041", target + unreal.Vector(0.0, -100.0, 55.0), target, 2800.0)
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
    raise RuntimeError("failed to save Diana v041 map")

report = {
    "schemaVersion": 1,
    "iteration": "v041",
    "status": "draft-primary-chain-run-qa",
    "map": MAP,
    "animation": ANIMATION,
    "heightCm": height,
    "hiddenMaterialSlots": list(HIDDEN_SLOTS),
    "preservedMaterialSlot": 13,
    "hypothesis": (
        "Leaving auxiliary thigh branches unmapped will keep NeoJacket2 sleeves and "
        "waist fragments stable while the primary legs run."
    ),
    "visualValidationPending": True,
    "automaticApproval": False,
}
unreal.log("DIANA_V041_READY=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
