"""Place the runtime default pawn outside the v032 QA camera view."""

import unreal


actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
player_start = actors.spawn_actor_from_class(
    unreal.PlayerStart, unreal.Vector(0.0, -2000.0, 0.0)
)
if player_start is None:
    raise RuntimeError("failed to spawn remote PlayerStart")
player_start.set_actor_label("PlayerStart_Outside_QA_View")
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v032 remote PlayerStart")
unreal.log("Gahyeon v032 remote PlayerStart saved")

