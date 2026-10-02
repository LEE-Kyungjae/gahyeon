"""Build immutable v078 with the official UE 5.8 Groom and binding asset."""

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v077/Preview/L_Skotukeda_HairCardAligned_v077"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v078/Preview/L_Skotukeda_GroomRecovery_v078"
GROOM_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_StraightBangs/Hair_L_StraightBangs"
BINDING_PATH = "/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/Hair_L_StraightBangs_Binding"
CARD_LABELS = {"HairCards_Straight_Group0_v042", "HairCards_Straight_Group1_v042"}
RECEIPT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v078-groom-recovery/build-receipt.json")


if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError("refusing to overwrite immutable v078 output")
world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None:
    raise RuntimeError(f"failed to load v077 source map: {SOURCE_MAP}")
groom = unreal.EditorAssetLibrary.load_asset(GROOM_PATH)
binding = unreal.EditorAssetLibrary.load_asset(BINDING_PATH)
if groom is None or binding is None:
    raise RuntimeError(f"official Groom pair unavailable: groom={groom}, binding={binding}")

actor_system = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = actor_system.get_all_level_actors()
character = next((actor for actor in actors if actor.get_actor_label() == "Skotukeda_Medium_v027"), None)
if character is None:
    raise RuntimeError("v077 character actor is unavailable")
hair = next((component for component in character.get_components_by_class(unreal.GroomComponent) if component.get_name() == "Hair"), None)
if hair is None:
    raise RuntimeError("MetaHuman Hair component is unavailable")
hair.set_editor_property("groom_asset", groom)
hair.set_editor_property("visible", True)
hair.set_editor_property("hidden_in_game", False)
assigned_groom = hair.get_editor_property("groom_asset")
if (
    assigned_groom is None
    or assigned_groom.get_path_name() != groom.get_path_name()
):
    raise RuntimeError("Groom asset did not persist on the Hair component")

hidden_cards = []
for actor in actors:
    if actor.get_actor_label() not in CARD_LABELS:
        continue
    components = actor.get_components_by_class(unreal.StaticMeshComponent)
    if len(components) != 1:
        raise RuntimeError(f"unexpected hair-card component count: {actor.get_actor_label()}")
    components[0].set_editor_property("visible", False)
    components[0].set_editor_property("hidden_in_game", True)
    hidden_cards.append(actor.get_actor_label())
if set(hidden_cards) != CARD_LABELS:
    raise RuntimeError(f"failed to hide exact fallback card pair: {hidden_cards}")

if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError(f"failed to save v078 map: {TARGET_MAP}")
RECEIPT.parent.mkdir(parents=True, exist_ok=True)
RECEIPT.write_text(json.dumps({
    "schemaVersion": 1,
    "iteration": "v078",
    "state": "draft-unbound-groom-poc-built",
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "hypothesis": "Hair did not render because the visible Groom component had no Groom or binding asset.",
    "action": "Assign the official UE 5.8 StraightBangs Groom without the rejected incompatible binding, then hide only the two static fallback cards.",
    "expectedResult": "The Groom renders as a static visual POC without the floating static shell; deformation remains blocked.",
    "sourceMap": SOURCE_MAP,
    "targetMap": TARGET_MAP,
    "groomAsset": groom.get_path_name(),
    "requestedBindingAsset": binding.get_path_name(),
    "bindingAsset": None,
    "bindingCompatible": False,
    "hiddenFallbackCards": sorted(hidden_cards),
    "automaticApproval": False,
    "productionReady": False,
}, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
