"""Fail-closed import of Hayley's verified v411 compound jawOpen FBX."""

import hashlib
import json
from pathlib import Path

import unreal


SOURCE = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v411-hayley-compound-jawopen/"
    "Hayley_CompoundJawOpen_v411.fbx"
)
DESTINATION = "/Game/LivingCharacterPOC/v413/CompoundJawOpenImport"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v413-hayley-compound-jawopen-import/report.json"
)


def import_hayley_compound_jawopen_v413():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if REPORT.exists():
        raise RuntimeError(f"refusing to overwrite v413 report: {REPORT}")
    existing = unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True)
    if existing:
        raise RuntimeError(f"refusing to overwrite v413 assets: {existing}")
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(SOURCE))
    task.set_editor_property("destination_path", DESTINATION)
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
    imported = sorted(str(value).split(".", 1)[0] for value in task.imported_object_paths)
    meshes = [path for path in imported if isinstance(unreal.load_asset(path), unreal.SkeletalMesh)]
    animations = [path for path in imported if isinstance(unreal.load_asset(path), unreal.AnimSequence)]
    if len(meshes) != 1 or len(animations) != 1:
        raise RuntimeError(f"expected one mesh and animation; meshes={meshes}, animations={animations}")
    report = {
        "schemaVersion": 1,
        "iteration": "v413",
        "status": "imported-draft-compound-jawopen",
        "source": str(SOURCE),
        "sourceSha256": source_hash,
        "destination": DESTINATION,
        "importedObjects": imported,
        "skeletalMesh": meshes[0],
        "animation": animations[0],
        "lineage": "v411-compound-jawopen",
        "calibrationOnly": True,
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_V413_COMPOUND_JAWOPEN=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


import_hayley_compound_jawopen_v413()
