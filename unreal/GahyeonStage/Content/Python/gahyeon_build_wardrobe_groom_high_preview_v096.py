"""Place the High official Wardrobe assembly in the retained QA environment."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v053/Preview/L_Skotukeda_RefinedGarment_v053"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v096/Preview/L_Skotukeda_WardrobeGroomHigh_v096"
BLUEPRINT = (
    "/Game/Gahyeon/CharacterPipeline/v095/AssembledHigh/"
    "Skotukeda_WardrobeGroomHigh_v095/BP_Skotukeda_WardrobeGroomHigh_v095"
)
OLD_LABEL = "Skotukeda_Medium_v027"
NEW_LABEL = "Skotukeda_WardrobeGroomHigh_v095"


def build_high_preview():
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
        raise RuntimeError(f"refusing to overwrite immutable v096 map: {TARGET_MAP}")
    character_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT)
    if character_class is None:
        raise RuntimeError(f"v095 Blueprint unavailable: {BLUEPRINT}")
    world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
    if world is None:
        raise RuntimeError(f"stable QA source map unavailable: {SOURCE_MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    old = next((actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == OLD_LABEL), None)
    if old is None:
        raise RuntimeError(f"retained source actor unavailable: {OLD_LABEL}")
    location = old.get_actor_location()
    rotation = old.get_actor_rotation()
    actors.destroy_actor(old)
    character = actors.spawn_actor_from_class(character_class, location, rotation)
    if character is None:
        raise RuntimeError("failed to spawn official v095 High Blueprint")
    character.set_actor_label(NEW_LABEL)
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
        raise RuntimeError(f"failed to save v096 map: {TARGET_MAP}")
    unreal.log(f"Gahyeon v096 High Wardrobe Groom preview saved: {TARGET_MAP}")


build_high_preview()
