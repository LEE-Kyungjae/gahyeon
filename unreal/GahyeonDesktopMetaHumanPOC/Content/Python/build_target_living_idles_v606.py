"""Retarget the validated gentle Hayley living idle to Stella and Ururu."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MESH = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean/Hayley_BindPoseClean_v447"
SOURCE_ANIMATION = "/Game/LivingCharacterPOC/v511/Animation/Hayley_LivingIdle_v509"
OUTPUT_ROOT = "/Game/LivingCharacterPOC/v606"
REPORT = ROOT / "artifacts/living-character-poc-v606-target-living-idles/report.json"
TARGETS = {
    "stella": {
        "mesh": "/Game/LivingCharacterPOC/v572/Characters/StellaCentimeterNormalized/StellaLily_CentimeterNormalized_v571",
        "retargeter": "/Game/LivingCharacterPOC/v577/Retarget/RTG_Hayley_StellaLily_v577",
        "name": "AS_Stella_LivingIdle_v606",
    },
    "ururu": {
        "mesh": "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584",
        "retargeter": "/Game/LivingCharacterPOC/v599/Retarget/RTG_Ururu_Head_roll_neg20_v599",
        "name": "AS_Ururu_LivingIdle_Corrected_v606",
    },
}


def require_asset(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"missing required asset: {path}")
    return asset


def generated_path(item):
    if isinstance(item, unreal.AssetData):
        return str(item.package_name)
    return item.get_path_name().split(".", 1)[0]


def build_target_living_idles_v606():
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True):
        raise RuntimeError("refusing to overwrite immutable v606 outputs")
    source_mesh = require_asset(SOURCE_MESH)
    source_data = unreal.EditorAssetLibrary.find_asset_data(SOURCE_ANIMATION)
    if not source_data.is_valid():
        raise RuntimeError(f"missing source animation: {SOURCE_ANIMATION}")
    records = {}
    for character_id, target in TARGETS.items():
        generated = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            [source_data], source_mesh, require_asset(target["mesh"]),
            require_asset(target["retargeter"]),
            search="Hayley_LivingIdle_v509", replace=target["name"],
            prefix="", suffix="",
        )
        if len(generated) != 1:
            raise RuntimeError(f"{character_id}: expected one living idle, got {len(generated)}")
        destination = f"{OUTPUT_ROOT}/Animation/{character_id}/{target['name']}"
        source_path = generated_path(generated[0])
        if not unreal.EditorAssetLibrary.rename_asset(source_path, destination):
            raise RuntimeError(f"failed to move {source_path} -> {destination}")
        records[character_id] = {**target, "animation": destination}
    unreal.EditorAssetLibrary.save_directory(OUTPUT_ROOT, only_if_is_dirty=False, recursive=True)
    report = {
        "schemaVersion": 1,
        "iteration": "v606",
        "status": "draft-gentle-living-idles-generated",
        "sourceAnimation": SOURCE_ANIMATION,
        "sourceDurationSeconds": require_asset(SOURCE_ANIMATION).get_play_length(),
        "targets": records,
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("TARGET_LIVING_IDLES_V606=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_target_living_idles_v606()
