"""Set the measured portrait camera distance for a complete body frame."""

import unreal


CAMERA_LABEL = "CAM_Gahyeon_Desktop_v025b"
CAMERA_LOCATION = unreal.Vector(0.0, 1400.0, 95.0)
CAMERA_TARGET = unreal.Vector(0.0, 0.0, 90.0)

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
camera = next(
    (actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == CAMERA_LABEL),
    None,
)
if camera is None:
    raise RuntimeError(f"preview camera is unavailable: {CAMERA_LABEL}")
camera.set_actor_location(CAMERA_LOCATION, False, False)
camera.set_actor_rotation(
    unreal.MathLibrary.find_look_at_rotation(CAMERA_LOCATION, CAMERA_TARGET), False
)
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v041 portrait full-body camera")
unreal.log("Gahyeon v041 portrait full-body camera saved: distanceCm=1400")
