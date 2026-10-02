"""Remove only the two shoulder-penetrating duplicate hair-card actors."""

import json
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v232/Preview/L_Skotukeda_NoWardrobeDesktop_v232"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v233/Preview/L_Skotukeda_CleanNoWardrobeDesktop_v233"
HAIR_CARD_LABELS = {
    "HairCards_Straight_Group0_v042",
    "HairCards_Straight_Group1_v042",
}
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v233-skotukeda-clean-no-wardrobe/build-receipt.json"
)


def build_clean_no_wardrobe_desktop_v233():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
        raise RuntimeError("refusing to overwrite immutable v233 output")
    world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
    if world is None:
        raise RuntimeError(f"failed to load source map: {SOURCE_MAP}")
    hidden = []
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    for actor in actors:
        if actor.get_actor_label() not in HAIR_CARD_LABELS:
            continue
        components = actor.get_components_by_class(unreal.StaticMeshComponent)
        if len(components) != 1:
            raise RuntimeError(f"unexpected hair-card component count: {actor.get_actor_label()}")
        components[0].set_editor_property("visible", False)
        components[0].set_editor_property("hidden_in_game", True)
        hidden.append(actor.get_actor_label())
    if set(hidden) != HAIR_CARD_LABELS:
        raise RuntimeError(f"failed to isolate exact hair-card pair: {hidden}")
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
        raise RuntimeError(f"failed to save v233 map: {TARGET_MAP}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v233",
        "state": "clean-no-wardrobe-desktop-draft",
        "sourceMap": SOURCE_MAP,
        "targetMap": TARGET_MAP,
        "hiddenShoulderPenetratingHairCards": sorted(hidden),
        "metaHumanGroomPreserved": True,
        "wardrobeVisible": False,
        "faceModified": False,
        "automaticApproval": False,
        "productionReady": False
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v233 clean no-wardrobe map created: {TARGET_MAP}")
    unreal.SystemLibrary.quit_editor()


build_clean_no_wardrobe_desktop_v233()
