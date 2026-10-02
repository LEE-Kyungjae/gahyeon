"""Create v081 Groom binding and block until all asynchronous asset compilation completes."""

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


GROOM_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_StraightBangs/Hair_L_StraightBangs"
SOURCE_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomMesh/SKM_Groom_Head_Legacy01"
TARGET_PATH = "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/Face/SKM_MHC_Skotukeda_Baseline_v026_FaceMesh"
BINDING_PATH = "/Game/Gahyeon/CharacterPipeline/v081/Groom/Hair_L_StraightBangs_Skotukeda_v081_Binding"
RECEIPT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v081-groom-binding/binding-receipt.json")


if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(BINDING_PATH):
    raise RuntimeError("refusing to overwrite immutable v081 binding")
groom = unreal.EditorAssetLibrary.load_asset(GROOM_PATH)
source = unreal.EditorAssetLibrary.load_asset(SOURCE_PATH)
target = unreal.EditorAssetLibrary.load_asset(TARGET_PATH)
if groom is None or source is None or target is None:
    raise RuntimeError("v081 binding input unavailable")
binding = unreal.GroomLibrary.create_new_groom_binding_asset_with_path(
    BINDING_PATH, groom, target, 100, source, 0
)
if binding is None:
    raise RuntimeError("GroomLibrary returned no v081 binding")
if not hasattr(unreal, "AutomationUtilsBlueprintLibrary"):
    raise RuntimeError("UE 5.8 AutomationUtilsBlueprintLibrary is unavailable")
unreal.AutomationUtilsBlueprintLibrary.finish_all_asset_compilation()

actual_groom = binding.get_editor_property("groom")
actual_source = binding.get_editor_property("source_skeletal_mesh")
actual_target = binding.get_editor_property("target_skeletal_mesh")
if any(value is None for value in (actual_groom, actual_source, actual_target)):
    raise RuntimeError("compiled v081 binding lost required lineage")
if not unreal.EditorAssetLibrary.save_loaded_asset(binding, False):
    raise RuntimeError(f"failed to save compiled v081 binding: {BINDING_PATH}")

RECEIPT.parent.mkdir(parents=True, exist_ok=True)
RECEIPT.write_text(json.dumps({
    "schemaVersion": 1, "iteration": "v081", "state": "draft-compiled-binding-created",
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "bindingAsset": binding.get_path_name(), "groomAsset": actual_groom.get_path_name(),
    "sourceSkeletalMesh": actual_source.get_path_name(), "targetSkeletalMesh": actual_target.get_path_name(),
    "assetCompilationDrained": True, "numInterpolationPoints": 100, "matchingSection": 0,
    "automaticApproval": False, "productionReady": False,
}, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
