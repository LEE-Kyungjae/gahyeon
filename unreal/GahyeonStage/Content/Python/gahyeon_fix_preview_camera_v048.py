"""Reassert the fixed desktop QA camera as player 0 view for v048."""

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v048/Preview/L_Skotukeda_ConformedGarment_v048"
CAMERA_LABEL = "CAM_Gahyeon_Desktop_v025b"

if not unreal.EditorLoadingAndSavingUtils.load_map(MAP):
    raise RuntimeError(f"failed to load v048 preview: {MAP}")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
cameras = [actor for actor in actors if isinstance(actor, unreal.CameraActor)]
camera = next((actor for actor in cameras if actor.get_actor_label() == CAMERA_LABEL), None)
if camera is None:
    raise RuntimeError(f"fixed desktop camera is unavailable: {CAMERA_LABEL}")
for other in cameras:
    other.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.DISABLED)
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
camera.camera_component.set_editor_property("constrain_aspect_ratio", False)

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v048 fixed camera")
unreal.log(
    f"Gahyeon v048 fixed camera saved: label={CAMERA_LABEL}, "
    f"location={camera.get_actor_location()}, rotation={camera.get_actor_rotation()}"
)
