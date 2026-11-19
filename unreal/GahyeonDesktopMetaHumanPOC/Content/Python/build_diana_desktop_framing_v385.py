import unreal


SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v383/Runtime/L_DianaMacRuntimeSourceColor_v383"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v385/Runtime/L_DianaMacRuntimeFullBody_v385"


if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP):
    raise RuntimeError(f"refusing to overwrite immutable iteration: {OUTPUT_MAP}")
if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, OUTPUT_MAP):
    raise RuntimeError(f"failed to duplicate {SOURCE_MAP} to {OUTPUT_MAP}")

unreal.EditorLoadingAndSavingUtils.load_map(OUTPUT_MAP)
cameras = [actor for actor in unreal.EditorLevelLibrary.get_all_level_actors() if isinstance(actor, unreal.CineCameraActor)]
if len(cameras) != 1:
    raise RuntimeError(f"expected one CineCameraActor, found {len(cameras)}")

camera = cameras[0]
camera.set_actor_label("CAM_Diana_Runtime_FullBody_v385")
camera.camera_component.set_editor_property("current_focal_length", 44.0)

if not unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True):
    raise RuntimeError("failed to save v385 full-body runtime map")

unreal.log(f"built {OUTPUT_MAP} with 44mm full-body framing")
