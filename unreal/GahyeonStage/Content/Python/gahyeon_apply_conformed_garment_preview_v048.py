"""Complete the v048 preview after import/map duplication in a fresh editor process."""

import unreal


ASSET_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v048/Garment/"
    "SM_Skotukeda_DefaultGarment_Conformed_v048"
)
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v048/Preview/L_Skotukeda_ConformedGarment_v048"
CHARACTER_LABEL = "Skotukeda_Medium_v027"

garment = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
if garment is None or not isinstance(garment, unreal.StaticMesh):
    raise RuntimeError(f"v048 conformed garment is unavailable: {ASSET_PATH}")
if not unreal.EditorLoadingAndSavingUtils.load_map(TARGET_MAP):
    raise RuntimeError(f"failed to load v048 preview: {TARGET_MAP}")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if any(actor.get_actor_label() == "ConformedDefaultGarment_v048" for actor in actors.get_all_level_actors()):
    raise RuntimeError("refusing to add a duplicate v048 conformed garment actor")
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
    raise RuntimeError("failed to spawn v048 conformed garment")
garment_actor.set_actor_label("ConformedDefaultGarment_v048")
garment_actor.static_mesh_component.set_static_mesh(garment)

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v048 conformed garment preview")
unreal.log(f"Gahyeon v048 conformed garment actor saved: {TARGET_MAP}")
