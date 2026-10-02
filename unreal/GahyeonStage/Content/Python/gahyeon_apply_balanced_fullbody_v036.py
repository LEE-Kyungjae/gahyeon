"""Balance exposure, frame the full body, and isolate the runtime pawn in v036."""

import unreal


CAMERA_LABEL = "CAM_Gahyeon_Desktop_v025b"
POST_LABEL = "PPV_Gahyeon_v025b"
CAMERA_LOCATION = unreal.Vector(0.0, 620.0, 95.0)
CAMERA_TARGET = unreal.Vector(0.0, 0.0, 90.0)

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_actors = actors.get_all_level_actors()
camera = next((a for a in level_actors if a.get_actor_label() == CAMERA_LABEL), None)
post = next((a for a in level_actors if a.get_actor_label() == POST_LABEL), None)
if camera is None or post is None:
    raise RuntimeError("v036 QA camera or post-process volume is unavailable")

camera.set_actor_location(CAMERA_LOCATION, False, False)
camera.set_actor_rotation(
    unreal.MathLibrary.find_look_at_rotation(CAMERA_LOCATION, CAMERA_TARGET), False
)
camera.camera_component.set_editor_property("current_focal_length", 50.0)

settings = post.get_editor_property("settings")
settings.set_editor_property("override_auto_exposure_method", True)
settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
settings.set_editor_property("override_auto_exposure_bias", True)
settings.set_editor_property("auto_exposure_bias", 1.0)
post.set_editor_property("settings", settings)

player_starts = [a for a in level_actors if isinstance(a, unreal.PlayerStart)]
if not player_starts:
    player_start = actors.spawn_actor_from_class(
        unreal.PlayerStart, unreal.Vector(0.0, -2000.0, 0.0)
    )
    if player_start is None:
        raise RuntimeError("failed to spawn remote PlayerStart")
    player_start.set_actor_label("PlayerStart_Outside_QA_View_v036")
else:
    for player_start in player_starts:
        player_start.set_actor_location(unreal.Vector(0.0, -2000.0, 0.0), False, False)

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v036 balanced full-body map")
unreal.log("Gahyeon v036 balanced full-body QA saved: exposure=1.0")
