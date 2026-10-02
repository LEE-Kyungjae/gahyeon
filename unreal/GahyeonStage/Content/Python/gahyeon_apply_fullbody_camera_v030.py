"""Reframe the already-open v030 preview map to show the entire character."""

import unreal


CAMERA_LABEL = "CAM_Gahyeon_Desktop_v025b"
CAMERA_LOCATION = unreal.Vector(0.0, 750.0, 95.0)
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
camera.camera_component.set_editor_property("current_focal_length", 50.0)
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v031 full-body camera")
unreal.log("Gahyeon v031 full-body camera saved")
