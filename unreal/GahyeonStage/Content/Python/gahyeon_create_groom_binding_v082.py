"""Create v082 Groom binding and synchronize through protected group info access."""

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


GROOM_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_StraightBangs/Hair_L_StraightBangs"
SOURCE_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomMesh/SKM_Groom_Head_Legacy01"
TARGET_PATH = "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/Face/SKM_MHC_Skotukeda_Baseline_v026_FaceMesh"
BINDING_PATH = "/Game/Gahyeon/CharacterPipeline/v082/Groom/Hair_L_StraightBangs_Skotukeda_v082_Binding"
RECEIPT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v082-groom-binding/binding-receipt.json")


if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(BINDING_PATH):
    raise RuntimeError("refusing to overwrite immutable v082 binding")
groom = unreal.EditorAssetLibrary.load_asset(GROOM_PATH)
source = unreal.EditorAssetLibrary.load_asset(SOURCE_PATH)
target = unreal.EditorAssetLibrary.load_asset(TARGET_PATH)
binding = unreal.GroomLibrary.create_new_groom_binding_asset_with_path(
    BINDING_PATH, groom, target, 100, source, 0
)
if binding is None:
    raise RuntimeError("GroomLibrary returned no v082 binding")

# GroupInfos is protected by the binding async-property lock. Reading it blocks
# until the build worker releases the property, avoiding a premature save/exit.
group_infos = binding.get_editor_property("group_infos")
if not group_infos:
    raise RuntimeError("compiled v082 binding contains no hair group information")
if not unreal.EditorAssetLibrary.save_loaded_asset(binding, False):
    raise RuntimeError(f"failed to save compiled v082 binding: {BINDING_PATH}")

RECEIPT.parent.mkdir(parents=True, exist_ok=True)
RECEIPT.write_text(json.dumps({
    "schemaVersion": 1, "iteration": "v082", "state": "draft-synchronized-binding-created",
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "bindingAsset": binding.get_path_name(), "groomAsset": binding.get_editor_property("groom").get_path_name(),
    "sourceSkeletalMesh": binding.get_editor_property("source_skeletal_mesh").get_path_name(),
    "targetSkeletalMesh": binding.get_editor_property("target_skeletal_mesh").get_path_name(),
    "hairGroupCount": len(group_infos), "asyncBarrier": "group_infos-read",
    "automaticApproval": False, "productionReady": False,
}, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
