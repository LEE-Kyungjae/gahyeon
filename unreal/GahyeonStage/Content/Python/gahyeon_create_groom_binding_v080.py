"""Create and validate a v080 Groom binding for the current Face skeletal mesh."""

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


GROOM_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_StraightBangs/Hair_L_StraightBangs"
SOURCE_MESH_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomMesh/SKM_Groom_Head_Legacy01"
TARGET_MESH_PATH = "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/Face/SKM_MHC_Skotukeda_Baseline_v026_FaceMesh"
BINDING_PATH = "/Game/Gahyeon/CharacterPipeline/v080/Groom/Hair_L_StraightBangs_Skotukeda_v080_Binding"
RECEIPT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v080-groom-binding/binding-receipt.json")


if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(BINDING_PATH):
    raise RuntimeError("refusing to overwrite immutable v080 binding output")
groom = unreal.EditorAssetLibrary.load_asset(GROOM_PATH)
source_mesh = unreal.EditorAssetLibrary.load_asset(SOURCE_MESH_PATH)
target_mesh = unreal.EditorAssetLibrary.load_asset(TARGET_MESH_PATH)
if groom is None or source_mesh is None or target_mesh is None:
    raise RuntimeError(f"binding input unavailable: groom={groom}, source={source_mesh}, target={target_mesh}")

binding = unreal.GroomLibrary.create_new_groom_binding_asset_with_path(
    BINDING_PATH,
    groom,
    target_mesh,
    100,
    source_mesh,
    0,
)
if binding is None:
    raise RuntimeError("UE 5.8 GroomLibrary returned no binding asset")
actual_groom = binding.get_editor_property("groom")
actual_source = binding.get_editor_property("source_skeletal_mesh")
actual_target = binding.get_editor_property("target_skeletal_mesh")
if (
    actual_groom is None
    or actual_source is None
    or actual_target is None
    or actual_groom.get_path_name() != groom.get_path_name()
    or actual_source.get_path_name() != source_mesh.get_path_name()
    or actual_target.get_path_name() != target_mesh.get_path_name()
):
    raise RuntimeError(
        "created binding lineage mismatch: "
        f"groom={actual_groom}, source={actual_source}, target={actual_target}"
    )
if not unreal.EditorAssetLibrary.save_loaded_asset(binding, False):
    raise RuntimeError(f"failed to save v080 binding asset: {BINDING_PATH}")

RECEIPT.parent.mkdir(parents=True, exist_ok=True)
RECEIPT.write_text(json.dumps({
    "schemaVersion": 1,
    "iteration": "v080",
    "state": "draft-binding-created",
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "bindingAsset": binding.get_path_name(),
    "groomAsset": actual_groom.get_path_name(),
    "sourceSkeletalMesh": actual_source.get_path_name(),
    "targetSkeletalMesh": actual_target.get_path_name(),
    "numInterpolationPoints": binding.get_editor_property("num_interpolation_points"),
    "matchingSection": binding.get_editor_property("matching_section"),
    "automaticApproval": False,
    "productionReady": False,
}, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
