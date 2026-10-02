"""Attach official MetaHuman hair-card LOD meshes for the desktop POC."""

import unreal


MESH_PATHS = (
    "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_StraightBangs/"
    "Hair_L_StraightBangs_CardsMesh_Group0_LOD0",
    "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_StraightBangs/"
    "Hair_L_StraightBangs_CardsMesh_Group1_LOD0",
)
POST_LABEL = "PPV_Gahyeon_v025b"

meshes = [unreal.EditorAssetLibrary.load_asset(path) for path in MESH_PATHS]
if any(mesh is None for mesh in meshes):
    raise RuntimeError(f"MetaHuman hair-card meshes are unavailable: {MESH_PATHS}")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_actors = actors.get_all_level_actors()
character = next((a for a in level_actors if a.get_actor_label() == "Skotukeda_Medium_v027"), None)
post = next((a for a in level_actors if a.get_actor_label() == POST_LABEL), None)
if character is None or post is None:
    raise RuntimeError("v038 character or post-process volume is unavailable")

for index, mesh in enumerate(meshes):
    hair_actor = actors.spawn_actor_from_class(
        unreal.StaticMeshActor,
        character.get_actor_location(),
        character.get_actor_rotation(),
    )
    if hair_actor is None:
        raise RuntimeError(f"failed to spawn hair-card actor {index}")
    hair_actor.set_actor_label(f"HairCards_StraightBangs_Group{index}_v038")
    hair_actor.static_mesh_component.set_static_mesh(mesh)

settings = post.get_editor_property("settings")
settings.set_editor_property("override_auto_exposure_bias", True)
settings.set_editor_property("auto_exposure_bias", 2.0)
post.set_editor_property("settings", settings)

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v038 hair-cards POC")
unreal.log("Gahyeon v038 hair-cards POC saved: groups=2, exposure=2.0")
