"""Import Blender-cleaned motion donors without overwriting raw v371 evidence."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path("/Users/ze/work/gahyeonbot")
REPORT = ROOT / "artifacts/living-character-poc-v371/processed-v001/unreal-v374-report.json"
SOURCES = (
    (
        "stand-sit-clean",
        ROOT / "artifacts/living-character-poc-v371/processed-v001/stand-sit/StandSit_Clean_v001.fbx",
        "/Game/LivingCharacterPOC/v374/Donors/StandSitClean",
    ),
    (
        "narration-clean",
        ROOT / "artifacts/living-character-poc-v371/processed-v001/narration/Narration_Clean_v001.fbx",
        "/Game/LivingCharacterPOC/v374/Donors/NarrationClean",
    ),
)


def import_processed_motion_v374(source: Path, destination: str) -> list[str]:
    if not source.is_file():
        raise FileNotFoundError(source)
    if unreal.EditorAssetLibrary.does_directory_exist(destination):
        existing = unreal.EditorAssetLibrary.list_assets(destination, recursive=True, include_folder=False)
        if existing:
            raise RuntimeError(f"refusing to overwrite immutable processed donor: {destination}")
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(source))
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", True)
    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    options.set_editor_property("import_animations", True)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene", True)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene_unit", True)
    options.anim_sequence_import_data.set_editor_property("import_bone_tracks", True)
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = sorted(str(item) for item in task.get_editor_property("imported_object_paths"))
    if not imported:
        raise RuntimeError(f"processed donor import produced no assets: {source}")
    return imported


def build_processed_motion_imports_v374() -> dict[str, object]:
    results = []
    for donor_id, source, destination in SOURCES:
        results.append({
            "id": donor_id,
            "source": str(source),
            "destination": destination,
            "importedObjects": import_processed_motion_v374(source, destination),
        })
    report = {
        "schemaVersion": 1,
        "iteration": "v374",
        "status": "processed-donors-imported-draft",
        "imports": results,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log("PROCESSED_DONORS_V374=" + json.dumps(report, sort_keys=True))
    return report


REPORT_VALUE = build_processed_motion_imports_v374()
