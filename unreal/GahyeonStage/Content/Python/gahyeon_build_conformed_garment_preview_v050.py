"""Save-As the populated v045 world, then replace its garment for v050."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v045/Preview/L_Skotukeda_DefaultGarment_v045"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v050/Preview/L_Skotukeda_ConformedGarment_v050"
GARMENT_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v048/Garment/"
    "SM_Skotukeda_DefaultGarment_Conformed_v048"
)

if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite v050 preview: {TARGET_MAP}")
world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None:
    raise RuntimeError(f"failed to load populated source map: {SOURCE_MAP}")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError(f"failed to save populated world as: {TARGET_MAP}")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_actors = actors.get_all_level_actors()
required = {
    label: next((actor for actor in level_actors if actor.get_actor_label() == label), None)
    for label in (
        "Skotukeda_Medium_v027",
        "DefaultGarment_BodyShapeC_v045",
        "CAM_Gahyeon_Desktop_v025b",
    )
}
if any(actor is None for actor in required.values()):
    raise RuntimeError(
        "source map is not populated: "
        + ", ".join(f"{label}={actor is not None}" for label, actor in required.items())
    )
garment = unreal.EditorAssetLibrary.load_asset(GARMENT_PATH)
if garment is None or not isinstance(garment, unreal.StaticMesh):
    raise RuntimeError(f"conformed garment is unavailable: {GARMENT_PATH}")

actors.destroy_actor(required["DefaultGarment_BodyShapeC_v045"])
character = required["Skotukeda_Medium_v027"]
new_garment = actors.spawn_actor_from_class(
    unreal.StaticMeshActor,
    character.get_actor_location(),
    character.get_actor_rotation(),
)
if new_garment is None:
    raise RuntimeError("failed to spawn v050 conformed garment")
new_garment.set_actor_label("ConformedDefaultGarment_v050")
new_garment.static_mesh_component.set_static_mesh(garment)
required["CAM_Gahyeon_Desktop_v025b"].set_editor_property(
    "auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0
)
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save populated v050 preview")
unreal.log(f"Gahyeon populated v050 preview saved: {TARGET_MAP}")
