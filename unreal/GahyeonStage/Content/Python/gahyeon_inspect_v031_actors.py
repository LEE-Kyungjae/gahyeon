"""Log actors in the already-open v031 full-body preview map."""

import unreal


actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for actor in actors.get_all_level_actors():
    location = actor.get_actor_location()
    unreal.log(
        f"GAHYEON_ACTOR label={actor.get_actor_label()} class={actor.get_class().get_name()} "
        f"location=({location.x:.1f},{location.y:.1f},{location.z:.1f})"
    )
