"""Build v086 by assigning the standard MetaHuman head attachment to the Groom."""

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v077/Preview/L_Skotukeda_HairCardAligned_v077"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v086/Preview/L_Skotukeda_HeadAttachedGroom_v086"
GROOM_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_StraightBangs/Hair_L_StraightBangs"
BINDING_PATH = "/Game/Gahyeon/CharacterPipeline/v084/Groom/Hair_L_StraightBangs_Skotukeda_v084_Binding"
CARD_LABELS = {"HairCards_Straight_Group0_v042", "HairCards_Straight_Group1_v042"}
RECEIPT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v086-head-attached-groom/build-receipt.json")


if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError("refusing to overwrite immutable v086 output")
world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None:
    raise RuntimeError(f"failed to load v077 source map: {SOURCE_MAP}")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next((a for a in actors if a.get_actor_label() == "Skotukeda_Medium_v027"), None)
hair = next((c for c in character.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Hair"), None)
groom = unreal.EditorAssetLibrary.load_asset(GROOM_PATH)
binding = unreal.EditorAssetLibrary.load_asset(BINDING_PATH)
if hair is None or groom is None or binding is None:
    raise RuntimeError("v086 Groom lineage unavailable")
hair.set_editor_property("groom_asset", groom)
hair.set_editor_property("binding_asset", binding)
hair.set_editor_property("attachment_name", "head")
hair.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, 0.0))
hair.set_editor_property("relative_rotation", unreal.Rotator(0.0, 0.0, 0.0))
hair.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 1.0))
if str(hair.get_editor_property("attachment_name")) != "head":
    raise RuntimeError("v086 head attachment did not persist")
if hair.get_editor_property("binding_asset") is None:
    raise RuntimeError("v086 section-6 Binding was rejected")
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
    raise RuntimeError(f"failed to save v086 map: {TARGET_MAP}")
RECEIPT.parent.mkdir(parents=True, exist_ok=True)
RECEIPT.write_text(json.dumps({
    "schemaVersion": 1, "iteration": "v086", "state": "draft-head-attached-groom-built",
    "observedAt": datetime.now(timezone.utc).isoformat(), "sourceMap": SOURCE_MAP, "targetMap": TARGET_MAP,
    "attachmentName": "head", "manualOffset": [0, 0, 0],
    "automaticApproval": False, "productionReady": False,
}, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
