"""Build immutable v080 using the newly generated Face-target Groom binding."""

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v077/Preview/L_Skotukeda_HairCardAligned_v077"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v080/Preview/L_Skotukeda_BoundGroom_v080"
GROOM_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_StraightBangs/Hair_L_StraightBangs"
BINDING_PATH = "/Game/Gahyeon/CharacterPipeline/v080/Groom/Hair_L_StraightBangs_Skotukeda_v080_Binding"
CARD_LABELS = {"HairCards_Straight_Group0_v042", "HairCards_Straight_Group1_v042"}
RECEIPT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v080-groom-binding/preview-receipt.json")


if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError("refusing to overwrite immutable v080 preview")
world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None:
    raise RuntimeError(f"failed to load v077 source map: {SOURCE_MAP}")
groom = unreal.EditorAssetLibrary.load_asset(GROOM_PATH)
binding = unreal.EditorAssetLibrary.load_asset(BINDING_PATH)
if groom is None or binding is None:
    raise RuntimeError(f"v080 Groom pair unavailable: groom={groom}, binding={binding}")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next((a for a in actors if a.get_actor_label() == "Skotukeda_Medium_v027"), None)
hair = next((c for c in character.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Hair"), None)
if hair is None:
    raise RuntimeError("MetaHuman Hair component is unavailable")
hair.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, 0.0))
hair.set_editor_property("relative_rotation", unreal.Rotator(0.0, 0.0, 0.0))
hair.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 1.0))
hair.set_editor_property("groom_asset", groom)
hair.set_editor_property("binding_asset", binding)
hair.set_editor_property("visible", True)
hair.set_editor_property("hidden_in_game", False)
actual_groom = hair.get_editor_property("groom_asset")
actual_binding = hair.get_editor_property("binding_asset")
if actual_groom is None or actual_binding is None:
    raise RuntimeError("v080 Groom or Binding was rejected by the Hair component")
if actual_groom.get_path_name() != groom.get_path_name() or actual_binding.get_path_name() != binding.get_path_name():
    raise RuntimeError("v080 Hair component retained the wrong Groom lineage")

hidden_cards = []
for actor in actors:
    if actor.get_actor_label() not in CARD_LABELS:
        continue
    components = actor.get_components_by_class(unreal.StaticMeshComponent)
    if len(components) != 1:
        raise RuntimeError(f"unexpected fallback card component count: {actor.get_actor_label()}")
    components[0].set_editor_property("visible", False)
    components[0].set_editor_property("hidden_in_game", True)
    hidden_cards.append(actor.get_actor_label())
if set(hidden_cards) != CARD_LABELS:
    raise RuntimeError(f"failed to hide exact fallback card pair: {hidden_cards}")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError(f"failed to save v080 preview map: {TARGET_MAP}")

RECEIPT.write_text(json.dumps({
    "schemaVersion": 1, "iteration": "v080", "state": "draft-bound-groom-preview-built",
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "sourceMap": SOURCE_MAP, "targetMap": TARGET_MAP,
    "groomAsset": actual_groom.get_path_name(), "bindingAsset": actual_binding.get_path_name(),
    "componentTransform": {"location": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0]},
    "hiddenFallbackCards": sorted(hidden_cards),
    "automaticApproval": False, "productionReady": False,
}, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
