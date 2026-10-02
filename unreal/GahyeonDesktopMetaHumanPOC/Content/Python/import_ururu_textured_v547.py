"""Import the texture-restored Ururu mesh against the validated v525 skeleton."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/living-character-poc-v545-ururu-textured/Ururu_Textured_v545.fbx"
SKELETON_PATH = "/Game/LivingCharacterPOC/v525/Characters/UruruPreview/Ururu_Normalized_v523_Skeleton"
DESTINATION = "/Game/LivingCharacterPOC/v547/Characters/UruruTextured"
REPORT = ROOT / "artifacts/living-character-poc-v547-ururu-textured-import/report.json"


def import_ururu_textured_v547() -> dict[str, object]:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True):
        raise RuntimeError("refusing to overwrite immutable v547 outputs")
    skeleton = unreal.load_asset(SKELETON_PATH)
    if skeleton is None:
        raise RuntimeError(f"missing validated Ururu skeleton: {SKELETON_PATH}")

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
    options.set_editor_property("skeleton", skeleton)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene", True)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene_unit", True)
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    imported = sorted(str(value) for value in task.get_editor_property("imported_object_paths"))
    meshes = []
    materials = []
    textures = []
    for object_path in imported:
        asset_path = object_path.split(".", 1)[0]
        asset = unreal.load_asset(asset_path)
        if isinstance(asset, unreal.SkeletalMesh):
            meshes.append(asset_path)
            if asset.get_editor_property("skeleton") != skeleton:
                raise RuntimeError(f"textured Ururu skeleton mismatch: {asset_path}")
        elif isinstance(asset, unreal.MaterialInterface):
            materials.append(asset_path)
        elif isinstance(asset, unreal.Texture):
            textures.append(asset_path)
    if len(meshes) != 1:
        raise RuntimeError(f"expected one textured Ururu mesh, got {meshes}; imported={imported}")

    report = {
        "schemaVersion": 1,
        "iteration": "v547",
        "status": "draft-textured-skeletal-character-imported",
        "source": str(SOURCE),
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "skeleton": SKELETON_PATH,
        "skeletalMesh": meshes[0],
        "materials": materials,
        "textures": textures,
        "importedObjects": imported,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_TEXTURED_IMPORT=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()
    return report


REPORT_VALUE = import_ururu_textured_v547()
