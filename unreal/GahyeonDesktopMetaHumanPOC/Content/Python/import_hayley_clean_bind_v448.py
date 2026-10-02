"""Import the immutable action-free Hayley bind-pose FBX into UE 5.8."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/living-character-poc-v447-hayley-clean-bind/Hayley_BindPoseClean_v447.fbx"
DESTINATION = "/Game/LivingCharacterPOC/v448/Characters/HayleyBindClean"
REPORT = ROOT / "artifacts/living-character-poc-v448-hayley-clean-bind-import/report.json"


def import_hayley_clean_bind_v448() -> dict[str, object]:
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
    options.set_editor_property("import_textures", True)
    options.set_editor_property("import_animations", False)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene", True)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene_unit", True)
    options.skeletal_mesh_import_data.set_editor_property("import_mesh_lo_ds", False)
    task.set_editor_property("options", options)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = sorted(str(item) for item in task.get_editor_property("imported_object_paths"))
    if not imported:
        raise RuntimeError("Unreal imported no clean Hayley assets")
    mesh_candidates = [path for path in imported if path.endswith(".Hayley_BindPoseClean_v447")]
    if len(mesh_candidates) != 1:
        raise RuntimeError(f"expected one clean skeletal mesh, got {mesh_candidates}")

    report = {
        "schemaVersion": 1,
        "iteration": "v448",
        "status": "draft-clean-bind-imported-visual-validation-required",
        "source": str(SOURCE),
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "destination": DESTINATION,
        "skeletalMesh": mesh_candidates[0].split(".", 1)[0],
        "importedObjects": imported,
        "embeddedAnimationImported": False,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log("HAYLEY_CLEAN_BIND_IMPORT=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()
    return report


REPORT_VALUE = import_hayley_clean_bind_v448()
