"""Import immutable local character and motion donors into an isolated UE 5.8 draft area."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


PROJECT_ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "artifacts" / "living-character-poc-v371" / "sources"
REPORT = PROJECT_ROOT / "artifacts" / "living-character-poc-v371" / "unreal-import-report.json"
DESTINATION_ROOT = "/Game/LivingCharacterPOC/v371"

IMPORTS = (
    ("hayley", SOURCE_ROOT / "hayley" / "Hayley2.fbx", f"{DESTINATION_ROOT}/Characters/Hayley", True),
    ("cyber-idle", SOURCE_ROOT / "cyber-idle" / "Idle.fbx", f"{DESTINATION_ROOT}/Donors/CyberIdle", True),
    ("gynoid-walk", SOURCE_ROOT / "gynoid-walk" / "FemBot_1000.fbx", f"{DESTINATION_ROOT}/Donors/GynoidWalk", True),
    ("stand-sit", SOURCE_ROOT / "stand-sit" / "standup_sitdown.fbx", f"{DESTINATION_ROOT}/Donors/StandSit", True),
    ("narration", SOURCE_ROOT / "narration" / "Joe_Rogan.fbx", f"{DESTINATION_ROOT}/Donors/Narration", True),
    ("hands-forward", SOURCE_ROOT / "hands-forward" / "Hands_Forward_Gesture.fbx", f"{DESTINATION_ROOT}/Donors/HandsForward", True),
)


def sha256_v371(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_living_character_source_v371(
    source: Path, destination: str, *, import_animation: bool
) -> list[str]:
    if not source.is_file():
        raise FileNotFoundError(source)
    if unreal.EditorAssetLibrary.does_directory_exist(destination):
        existing = unreal.EditorAssetLibrary.list_assets(destination, recursive=True, include_folder=False)
        if existing:
            raise RuntimeError(f"refusing to overwrite immutable donor destination: {destination}")

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(source))
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("save", True)

    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_textures", True)
    options.set_editor_property("import_animations", import_animation)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene", True)
    options.skeletal_mesh_import_data.set_editor_property("convert_scene_unit", True)
    options.skeletal_mesh_import_data.set_editor_property("import_mesh_lo_ds", False)
    options.anim_sequence_import_data.set_editor_property("import_bone_tracks", True)
    task.set_editor_property("options", options)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = list(task.get_editor_property("imported_object_paths"))
    if not imported:
        raise RuntimeError(f"Unreal imported no assets from {source}")
    return sorted(str(item) for item in imported)


def import_motion_donor_v371(source: Path, destination: str) -> list[str]:
    return import_living_character_source_v371(source, destination, import_animation=True)


def build_living_character_poc_v371() -> dict[str, object]:
    results = []
    for donor_id, source, destination, import_animation in IMPORTS:
        imported = (
            import_motion_donor_v371(source, destination)
            if import_animation and donor_id != "hayley"
            else import_living_character_source_v371(
                source, destination, import_animation=import_animation
            )
        )
        results.append({
            "id": donor_id,
            "source": str(source),
            "sourceSha256": sha256_v371(source),
            "destination": destination,
            "importedObjects": imported,
        })
    report = {
        "schemaVersion": 1,
        "iteration": "v371",
        "status": "draft-imported-local-poc-only",
        "releaseEligible": False,
        "gahyeonUsage": "archived-reference-only",
        "primaryCharacter": "hayley",
        "imports": results,
        "blockingFindings": [
            "Donor listing URLs and redistribution/commercial licenses are not recorded.",
            "No donor motion is approved until target retarget pose and deformation QA pass.",
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


REPORT_VALUE = build_living_character_poc_v371()
unreal.log(f"Living character v371 import complete: {len(REPORT_VALUE['imports'])} donors")
