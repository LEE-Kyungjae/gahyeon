"""Import the validated Stella/Lily modular FBX as a UE preview-only skeletal assembly."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/living-character-poc-v518-stella-lily-unreal-export/StellaLily_Modular_v518.fbx"
DESTINATION = "/Game/LivingCharacterPOC/v520/Characters/StellaLilyPreview"
REPORT = ROOT / "artifacts/living-character-poc-v520-stella-lily-preview-import/report.json"


def import_stella_lily_preview_v520() -> dict[str, object]:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if REPORT.exists():
        raise FileExistsError(f"refusing to overwrite immutable report: {REPORT}")
    if unreal.EditorAssetLibrary.does_directory_exist(DESTINATION):
        existing = unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True, include_folder=False)
        if existing:
            raise RuntimeError(f"refusing to overwrite immutable assets: {existing}")

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(SOURCE))
    task.set_editor_property("destination_path", DESTINATION)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("save", True)

    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_textures", False)
    options.set_editor_property("import_animations", False)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene", True)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene_unit", True)
    options.skeletal_mesh_import_data.set_editor_property("import_mesh_lo_ds", False)
    task.set_editor_property("options", options)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = sorted(str(item) for item in task.get_editor_property("imported_object_paths"))
    skeletal_meshes = []
    for object_path in imported:
        asset = unreal.load_asset(object_path)
        if isinstance(asset, unreal.SkeletalMesh):
            skeletal_meshes.append(object_path.split(".", 1)[0])
    if not skeletal_meshes:
        raise RuntimeError(f"Unreal imported no Stella/Lily skeletal mesh: {imported}")

    report = {
        "schemaVersion": 1,
        "iteration": "v520",
        "status": "draft-preview-only-skeletal-import",
        "source": str(SOURCE),
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "destination": DESTINATION,
        "skeletalMeshes": skeletal_meshes,
        "importedObjects": imported,
        "sourceModularMeshCount": 13,
        "sourceBoneCount": 219,
        "previewOnly": True,
        "productionModularityPreservedInSource": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("STELLA_LILY_PREVIEW_IMPORT=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()
    return report


REPORT_VALUE = import_stella_lily_preview_v520()
