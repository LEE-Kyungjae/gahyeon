"""Build v049 from the known-good v045 populated preview and swap its garment."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v045/Preview/L_Skotukeda_DefaultGarment_v045"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v049/Preview/L_Skotukeda_ConformedGarment_v049"
GARMENT_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v048/Garment/"
    "SM_Skotukeda_DefaultGarment_Conformed_v048"
)
CHARACTER_LABEL = "Skotukeda_Medium_v027"
OLD_GARMENT_LABEL = "DefaultGarment_BodyShapeC_v045"
NEW_GARMENT_LABEL = "ConformedDefaultGarment_v049"

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite v049 preview: {TARGET_MAP}")
garment = unreal.EditorAssetLibrary.load_asset(GARMENT_PATH)
if garment is None or not isinstance(garment, unreal.StaticMesh):
    raise RuntimeError(f"conformed garment is unavailable: {GARMENT_PATH}")

preview = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP)
if preview is None:
    raise RuntimeError(f"failed to duplicate known-good preview: {SOURCE_MAP}")

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_actors = actor_subsystem.get_all_level_actors()
character = next(
    (actor for actor in level_actors if actor.get_actor_label() == CHARACTER_LABEL),
    None,
)
old_garment = next(
    (actor for actor in level_actors if actor.get_actor_label() == OLD_GARMENT_LABEL),
    None,
)
camera = next(
    (actor for actor in level_actors if actor.get_actor_label() == "CAM_Gahyeon_Desktop_v025b"),
    None,
)
if character is None or old_garment is None or camera is None:
    raise RuntimeError(
        "v049 duplication did not retain required actors: "
        f"character={character is not None}, garment={old_garment is not None}, camera={camera is not None}"
    )
actor_subsystem.destroy_actor(old_garment)
new_garment = actor_subsystem.spawn_actor_from_class(
    unreal.StaticMeshActor,
    character.get_actor_location(),
    character.get_actor_rotation(),
)
if new_garment is None:
    raise RuntimeError("failed to spawn v049 conformed garment")
new_garment.set_actor_label(NEW_GARMENT_LABEL)
new_garment.static_mesh_component.set_static_mesh(garment)
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save populated v049 preview")
unreal.log(f"Gahyeon populated v049 preview saved: {TARGET_MAP}")
