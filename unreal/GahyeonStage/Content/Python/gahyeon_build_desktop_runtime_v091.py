"""Create an immutable Desktop runtime map from the retained v089 QA map."""

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v089/Preview/L_Skotukeda_WardrobeGroom_v089"
TARGET_MAP = "/Game/Gahyeon/DesktopRuntime/v091/L_GahyeonDesktopRuntime_v091"


def build():
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
        raise RuntimeError(f"refusing to overwrite immutable Desktop map: {TARGET_MAP}")
    world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
    if world is None:
        raise RuntimeError(f"source QA map unavailable: {SOURCE_MAP}")

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    made_movable = 0
    for actor in actor_subsystem.get_all_level_actors():
        for component in actor.get_components_by_class(unreal.SceneComponent):
            try:
                if component.get_editor_property("mobility") != unreal.ComponentMobility.MOVABLE:
                    component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
                    made_movable += 1
            except Exception:
                pass

    if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
        raise RuntimeError(f"failed to save Desktop runtime map: {TARGET_MAP}")
    unreal.log(
        f"Gahyeon Desktop runtime v091 saved: {TARGET_MAP}; "
        f"movable_components={made_movable}"
    )


build()
