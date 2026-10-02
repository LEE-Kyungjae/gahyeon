"""Disable 16:9 camera letterboxing for the portrait desktop window."""

import unreal


CAMERA_LABEL = "CAM_Gahyeon_Desktop_v025b"

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
camera = next(
    (actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == CAMERA_LABEL),
    None,
)
if camera is None:
    raise RuntimeError(f"preview camera is unavailable: {CAMERA_LABEL}")
camera.camera_component.set_editor_property("constrain_aspect_ratio", False)
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v040 portrait camera")
unreal.log("Gahyeon v040 portrait camera saved: constrainAspectRatio=false")
