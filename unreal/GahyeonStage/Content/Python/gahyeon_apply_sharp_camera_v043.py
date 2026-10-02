"""Disable cinematic blur sources for deterministic character QA."""

import unreal


CAMERA_LABEL = "CAM_Gahyeon_Desktop_v025b"
POST_LABEL = "PPV_Gahyeon_v025b"

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_actors = actors.get_all_level_actors()
camera = next((a for a in level_actors if a.get_actor_label() == CAMERA_LABEL), None)
post = next((a for a in level_actors if a.get_actor_label() == POST_LABEL), None)
if camera is None or post is None:
    raise RuntimeError("v043 QA camera or post-process volume is unavailable")

focus = camera.camera_component.get_editor_property("focus_settings")
focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
camera.camera_component.set_editor_property("focus_settings", focus)

settings = post.get_editor_property("settings")
settings.set_editor_property("override_motion_blur_amount", True)
settings.set_editor_property("motion_blur_amount", 0.0)
post.set_editor_property("settings", settings)

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v043 sharp camera settings")
unreal.log("Gahyeon v043 sharp camera saved: dof=disabled, motionBlur=0")
