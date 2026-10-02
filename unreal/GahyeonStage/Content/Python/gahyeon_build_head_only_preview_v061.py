"""Build an immutable fixed-camera preview for the corrected v061 MetaHuman."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v053/Preview/L_Skotukeda_RefinedGarment_v053"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v061/Preview/L_Gahyeon_HeadOnly_v061"
BLUEPRINT = (
    "/Game/Gahyeon/CharacterPipeline/v061/AssembledMedium/Gahyeon_HeadOnly_v061/"
    "BP_Gahyeon_HeadOnly_v061"
)


def build_head_only_preview_v061():
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
        raise RuntimeError(f"refusing to overwrite v061 preview: {TARGET_MAP}")
    character_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT)
    if character_class is None:
        raise RuntimeError(f"v061 assembled Blueprint is unavailable: {BLUEPRINT}")
    world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
    if world is None:
        raise RuntimeError(f"stable QA source map is unavailable: {SOURCE_MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    old_character = next(
        (actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == "Skotukeda_Medium_v027"),
        None,
    )
    if old_character is None:
        raise RuntimeError("stable source character actor is unavailable")
    location = old_character.get_actor_location()
    rotation = old_character.get_actor_rotation()
    actors.destroy_actor(old_character)
    character = actors.spawn_actor_from_class(character_class, location, rotation)
    if character is None:
        raise RuntimeError("failed to spawn v061 assembled Blueprint")
    character.set_actor_label("Gahyeon_HeadOnly_v061")
    camera = next(
        (actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == "CAM_Gahyeon_Desktop_v025b"),
        None,
    )
    if camera is None:
        raise RuntimeError("fixed QA camera is unavailable")
    camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
        raise RuntimeError(f"failed to save v061 preview map: {TARGET_MAP}")
    unreal.log(f"Gahyeon v061 fixed-camera preview saved: {TARGET_MAP}")


build_head_only_preview_v061()
