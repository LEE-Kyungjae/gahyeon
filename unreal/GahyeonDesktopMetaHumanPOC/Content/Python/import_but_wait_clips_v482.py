"""Import three visually selected But-wait gesture clips without materials."""

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_DIR = ROOT / "artifacts/living-character-poc-v481-but-wait-selected-clips"
DESTINATION = "/Game/LivingCharacterPOC/v482/Donors/ButWait"
REPORT = ROOT / "artifacts/living-character-poc-v482-but-wait-clips-import/report.json"


def import_but_wait_clips_v482():
    sources = sorted(SOURCE_DIR.glob("segment-*.fbx"))
    if len(sources) != 3:
        raise RuntimeError(f"expected three selected clips, got {sources}")
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True):
        raise RuntimeError("refusing to overwrite immutable v482 outputs")
    imports = []
    for source in sources:
        destination = f"{DESTINATION}/{source.stem.split('-frames-', 1)[0]}"
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
        imported = sorted(str(value) for value in task.get_editor_property("imported_object_paths"))
        if not imported:
            raise RuntimeError(f"clip import produced no assets: {source}")
        imports.append({
            "segment": source.stem.split("-frames-", 1)[0], "source": str(source),
            "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "destination": destination, "importedObjects": imported,
        })
    report = {
        "schemaVersion": 1, "iteration": "v482", "status": "selected-gesture-clips-imported-draft",
        "imports": imports, "humanApproved": False, "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("BUT_WAIT_CLIPS_IMPORT=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


import_but_wait_clips_v482()
