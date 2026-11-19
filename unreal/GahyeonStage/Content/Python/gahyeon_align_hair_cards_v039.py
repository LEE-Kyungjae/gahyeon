"""Apply the measured vertical correction to the v039 hair-card groups."""

import unreal


HAIR_PREFIX = "HairCards_StraightBangs_Group"
Z_OFFSET_CM = 20.0

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
hair_actors = [
    actor
    for actor in actors.get_all_level_actors()
    if actor.get_actor_label().startswith(HAIR_PREFIX)
]
if len(hair_actors) != 2:
    raise RuntimeError(f"expected two hair-card actors, got {len(hair_actors)}")
for actor in hair_actors:
    location = actor.get_actor_location()
    actor.set_actor_location(
        unreal.Vector(location.x, location.y, location.z + Z_OFFSET_CM), False, False
    )

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v039 aligned hair-card POC")
unreal.log(f"Gahyeon v039 hair cards aligned: zOffsetCm={Z_OFFSET_CM}")
