"""Import the isolated Hayley jawOpen proof into a versioned UE path."""

import json
from pathlib import Path

import unreal


SOURCE = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v405-hayley-jawopen/"
    "Hayley_JawOpen_v405.fbx"
)
DESTINATION = "/Game/LivingCharacterPOC/v406/JawOpenImport"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v406-hayley-jawopen-import/report.json"
)


def import_hayley_jawopen_v406():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if REPORT.exists():
        raise RuntimeError(f"refusing to overwrite v406 report: {REPORT}")
    existing = unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True)
    if existing:
        raise RuntimeError(f"refusing to overwrite v406 assets: {existing}")
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
        "iteration": "v406",
        "status": "imported-draft-isolated-jawopen",
        "source": str(SOURCE),
        "destination": DESTINATION,
        "importedObjects": imported,
        "skeletalMesh": meshes[0],
        "animation": animations[0],
        "calibrationOnly": True,
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_V406_JAWOPEN_IMPORT=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


import_hayley_jawopen_v406()
