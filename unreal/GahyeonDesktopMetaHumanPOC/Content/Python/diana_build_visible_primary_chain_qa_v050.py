"""Build Diana primary-chain motion QA with every source material visible."""

import json

import unreal


MAP = "/Game/Gahyeon/Character2/Diana/v050/QA/L_Diana_VisiblePrimaryChain_v050"
SEQUENCE_ROOT = "/Game/Gahyeon/Character2/Diana/v051/Sequence"
SEQUENCE_NAME = "LS_Diana_VisiblePrimaryChain_v051"
SEQUENCE_PATH = f"{SEQUENCE_ROOT}/{SEQUENCE_NAME}"
MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
ANIMATION = (
    "/Game/Gahyeon/Character2/Diana/v040/Animation/"
    "AS_Diana_RunForward_v244_PrimaryLegs_v040"
)
MATERIAL_ROOT = "/Game/Gahyeon/Character2/Diana/v002/Materials"
CHARACTER_LABEL = "Diana_v050_VisiblePrimaryChainDraft"
CAMERA_LABEL = "CAM_Diana_FullBody_v050"
START_FRAME = 0
END_FRAME = 90


def require_asset(path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def add_rect_light(actors, label, location, target, intensity):
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
if unreal.EditorAssetLibrary.does_asset_exist(SEQUENCE_PATH):
    raise RuntimeError(f"refusing to overwrite immutable sequence: {SEQUENCE_PATH}")

mesh = require_asset(MESH)
animation = require_asset(ANIMATION)
materials = [
    require_asset(f"{MATERIAL_ROOT}/M_Diana_Slot{index:02d}_v002")
    for index in range(18)
]
if not unreal.EditorLevelLibrary.new_level(MAP):
    raise RuntimeError("failed to create Diana visible-material QA map")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
character = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
if character is None:
    raise RuntimeError("failed to spawn Diana")
character.set_actor_label(CHARACTER_LABEL)
component = character.get_component_by_class(unreal.SkeletalMeshComponent)
component.set_editor_property("skeletal_mesh_asset", mesh)
for index, material in enumerate(materials):
    component.set_material(index, material)

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
if camera is None:
    raise RuntimeError("failed to spawn Diana QA camera")
camera.set_actor_label(CAMERA_LABEL)
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
camera.camera_component.set_editor_property("current_focal_length", 50.0)
camera.camera_component.set_editor_property("current_aperture", 5.6)

player = actors.spawn_actor_from_class(
    unreal.PlayerStart, unreal.Vector(2000.0, 2000.0, 1000.0), unreal.Rotator()
)
player.set_actor_label("PlayerStart_OffCamera_v050")
add_rect_light(
    actors, "KEY_Diana_v050", target + unreal.Vector(-100.0, 160.0, 70.0), target, 4200.0
)
add_rect_light(
    actors, "FILL_Diana_v050", target + unreal.Vector(110.0, 145.0, 30.0), target, 2300.0
)
add_rect_light(
    actors, "RIM_Diana_v050", target + unreal.Vector(0.0, -100.0, 55.0), target, 2800.0
)
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
    raise RuntimeError("failed to save Diana v050 map")

sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    SEQUENCE_NAME,
    SEQUENCE_ROOT,
    unreal.LevelSequence,
    unreal.LevelSequenceFactoryNew(),
)
if sequence is None:
    raise RuntimeError("failed to create Diana v051 Level Sequence")
sequence.set_display_rate(unreal.FrameRate(30, 1))
sequence.set_tick_resolution(unreal.FrameRate(24000, 1))
sequence.set_playback_start(START_FRAME)
sequence.set_playback_end(END_FRAME)
if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
    raise RuntimeError("failed to open Diana v051 Level Sequence")

sequencer = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
bindings = sequencer.add_actors([character, camera])
binding_by_name = {str(binding.get_name()): binding for binding in bindings}
character_binding = binding_by_name.get(CHARACTER_LABEL)
camera_binding = binding_by_name.get(CAMERA_LABEL)
if character_binding is None or camera_binding is None:
    raise RuntimeError(f"unexpected Diana bindings: {sorted(binding_by_name)}")

animation_track = character_binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
animation_section = animation_track.add_section()
animation_section.set_range(START_FRAME, END_FRAME)
animation_section.params.animation = animation
camera_cut_track = sequence.add_track(unreal.MovieSceneCameraCutTrack)
camera_cut_section = camera_cut_track.add_section()
camera_cut_section.set_range(START_FRAME, END_FRAME)
camera_binding_id = unreal.MovieSceneObjectBindingID()
camera_binding_id.set_editor_property("guid", camera_binding.get_id())
camera_cut_section.set_camera_binding_id(camera_binding_id)

unreal.LevelSequenceEditorBlueprintLibrary.refresh_current_level_sequence()
if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
    raise RuntimeError("failed to save Diana v051 sequence")

report = {
    "schemaVersion": 1,
    "iterations": ["v050", "v051"],
    "status": "draft-visible-primary-chain-qa-ready",
    "map": MAP,
    "sequence": SEQUENCE_PATH,
    "mesh": MESH,
    "animation": ANIMATION,
    "heightCm": height,
    "materialSlots": len(materials),
    "hiddenMaterialSlots": [],
    "hypothesis": (
        "Restoring all original source materials will prove whether v049's missing "
        "body regions came from mixed accessory/body slots rather than retarget deformation."
    ),
    "visualValidationPending": True,
    "humanApproved": False,
    "productionReady": False,
    "automaticApproval": False,
}
unreal.log("DIANA_V050_V051_READY=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
