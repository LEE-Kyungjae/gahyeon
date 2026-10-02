"""Replace StraightBangs card meshes with the no-bangs long straight style."""

import unreal


OLD_PREFIX = "HairCards_StraightBangs_Group"
NEW_MESH_PATHS = (
    "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_Straight/"
    "Hair_L_Straight_CardsMesh_Group0_LOD0",
    "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_Straight/"
    "Hair_L_Straight_CardsMesh_Group1_LOD0",
)

meshes = [unreal.EditorAssetLibrary.load_asset(path) for path in NEW_MESH_PATHS]
if any(mesh is None for mesh in meshes):
    raise RuntimeError(f"no-bangs MetaHuman card meshes are unavailable: {NEW_MESH_PATHS}")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_actors = actors.get_all_level_actors()
old_hair = [actor for actor in level_actors if actor.get_actor_label().startswith(OLD_PREFIX)]
if len(old_hair) != 2:
    raise RuntimeError(f"expected two old hair-card actors, got {len(old_hair)}")
base_location = old_hair[0].get_actor_location()
base_rotation = old_hair[0].get_actor_rotation()
for actor in old_hair:
    actors.destroy_actor(actor)

for index, mesh in enumerate(meshes):
    hair_actor = actors.spawn_actor_from_class(
        unreal.StaticMeshActor, base_location, base_rotation
    )
    if hair_actor is None:
        raise RuntimeError(f"failed to spawn no-bangs hair-card actor {index}")
    hair_actor.set_actor_label(f"HairCards_Straight_Group{index}_v042")
    hair_actor.static_mesh_component.set_static_mesh(mesh)

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v042 no-bangs hair POC")
unreal.log("Gahyeon v042 no-bangs hair saved: removed=2, added=2")
