"""Add an official MetaHuman modular default garment to the static desktop POC."""

import unreal


GARMENT_PATH = (
    "/MetaHumanCharacter/Optional/Clothing/DefaultGarment/ClothAssets/"
    "bodyShapeC/Meshes/DG_bodyShapeCcombined"
)
CHARACTER_LABEL = "Skotukeda_Medium_v027"

garment = unreal.EditorAssetLibrary.load_asset(GARMENT_PATH)
if garment is None:
    raise RuntimeError(f"default garment is unavailable: {GARMENT_PATH}")
if not isinstance(garment, unreal.StaticMesh):
    raise RuntimeError(f"default garment is not a StaticMesh: {garment.get_class().get_name()}")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
character = next(
    (actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == CHARACTER_LABEL),
    None,
)
if character is None:
    raise RuntimeError(f"character is unavailable: {CHARACTER_LABEL}")
garment_actor = actors.spawn_actor_from_class(
    unreal.StaticMeshActor,
    character.get_actor_location(),
    character.get_actor_rotation(),
)
if garment_actor is None:
    raise RuntimeError("failed to spawn default garment")
garment_actor.set_actor_label("DefaultGarment_BodyShapeC_v045")
garment_actor.static_mesh_component.set_static_mesh(garment)

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v045 default garment POC")
unreal.log(f"Gahyeon v045 default garment saved: {GARMENT_PATH}")
