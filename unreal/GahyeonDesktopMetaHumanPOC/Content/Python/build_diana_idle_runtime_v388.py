import unreal


SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v385/Runtime/L_DianaMacRuntimeFullBody_v385"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v388/Runtime/L_DianaMacRuntimeIdle_v388"
IDLE_ANIMATION = "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_Idle_v244_ComponentCopy_v375"


if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP):
    raise RuntimeError(f"refusing to overwrite immutable iteration: {OUTPUT_MAP}")
if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, OUTPUT_MAP):
    raise RuntimeError(f"failed to duplicate {SOURCE_MAP} to {OUTPUT_MAP}")

unreal.EditorLoadingAndSavingUtils.load_map(OUTPUT_MAP)
idle = unreal.EditorAssetLibrary.load_asset(IDLE_ANIMATION)
if idle is None:
    raise RuntimeError(f"approved component-space idle is missing: {IDLE_ANIMATION}")

actors = unreal.EditorLevelLibrary.get_all_level_actors()
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
cameras = [actor for actor in actors if isinstance(actor, unreal.CineCameraActor)]
if len(characters) != 1 or len(cameras) != 1:
    raise RuntimeError(f"expected one character and one camera, got {len(characters)} and {len(cameras)}")

character = characters[0]
character.set_actor_label("Diana_Runtime_Idle_v388")
component = character.get_component_by_class(unreal.SkeletalMeshComponent)
component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
component.set_editor_property(
    "animation_data",
    unreal.SingleAnimationPlayData(
        anim_to_play=idle,
        saved_looping=True,
        saved_playing=True,
        saved_position=0.0,
        saved_play_rate=1.0,
    ),
)

camera = cameras[0]
camera.set_actor_label("CAM_Diana_Runtime_Idle_v388")
camera.camera_component.set_editor_property("current_focal_length", 40.0)

if not unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True):
    raise RuntimeError("failed to save v388 idle runtime map")

unreal.log(f"built {OUTPUT_MAP} with approved v375 idle and 40mm framing")
