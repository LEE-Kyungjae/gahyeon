"""Build v085 with the validated section-6 direct Groom binding."""

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v077/Preview/L_Skotukeda_HairCardAligned_v077"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v085/Preview/L_Skotukeda_BoundGroom_v085"
GROOM_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_StraightBangs/Hair_L_StraightBangs"
BINDING_PATH = "/Game/Gahyeon/CharacterPipeline/v084/Groom/Hair_L_StraightBangs_Skotukeda_v084_Binding"
CARD_LABELS = {"HairCards_Straight_Group0_v042", "HairCards_Straight_Group1_v042"}
RECEIPT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v085-bound-groom/preview-receipt.json")


if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError("refusing to overwrite immutable v085 preview")
world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
groom = unreal.EditorAssetLibrary.load_asset(GROOM_PATH)
binding = unreal.EditorAssetLibrary.load_asset(BINDING_PATH)
if world is None or groom is None or binding is None:
    raise RuntimeError("v085 input unavailable")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next((a for a in actors if a.get_actor_label() == "Skotukeda_Medium_v027"), None)
hair = next((c for c in character.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Hair"), None)
hair.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, 0.0))
hair.set_editor_property("relative_rotation", unreal.Rotator(0.0, 0.0, 0.0))
hair.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 1.0))
hair.set_editor_property("groom_asset", groom)
hair.set_editor_property("binding_asset", binding)
hair.set_editor_property("visible", True)
hair.set_editor_property("hidden_in_game", False)
actual_binding = hair.get_editor_property("binding_asset")
if actual_binding is None or actual_binding.get_path_name() != binding.get_path_name():
    raise RuntimeError("validated v084 Binding was rejected by the v085 Hair component")

hidden = []
for actor in actors:
    if actor.get_actor_label() in CARD_LABELS:
        component = actor.get_components_by_class(unreal.StaticMeshComponent)[0]
        component.set_editor_property("visible", False)
        component.set_editor_property("hidden_in_game", True)
        hidden.append(actor.get_actor_label())
if set(hidden) != CARD_LABELS:
    raise RuntimeError(f"failed to hide exact fallback cards: {hidden}")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError(f"failed to save v085 map: {TARGET_MAP}")
RECEIPT.parent.mkdir(parents=True, exist_ok=True)
RECEIPT.write_text(json.dumps({
    "schemaVersion": 1, "iteration": "v085", "state": "draft-bound-groom-preview-built",
    "observedAt": datetime.now(timezone.utc).isoformat(), "sourceMap": SOURCE_MAP, "targetMap": TARGET_MAP,
    "groomAsset": groom.get_path_name(), "bindingAsset": actual_binding.get_path_name(),
    "componentTransform": {"location": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
    "hiddenFallbackCards": sorted(hidden), "automaticApproval": False, "productionReady": False,
}, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
