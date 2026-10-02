"""Import Diana's rigid-Hip belt attachment mesh and build v442 runtime QA."""

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/gahyeon-ch/iterations/v440-diana-belt-attachment-rigid-hip/SK_Diana_BeltAttachmentRigidHip_v440.fbx"
DESTINATION = "/Game/Gahyeon/Character2/Diana/v441/Source"
SOURCE_MESH = "/Game/Gahyeon/Character2/Diana/v417/Source/SK_Diana_ShoulderOccluded_v417"
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v421/Runtime/L_DianaMacRuntimeAttachmentGravity_v421"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v442/Runtime/L_DianaMacRuntimeBeltRigidHip_v442"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v442-diana-belt-rigid-hip-runtime/report.json"


if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True) or unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP):
    raise RuntimeError("refusing to overwrite immutable Diana v441/v442 outputs")
source_mesh = unreal.load_asset(SOURCE_MESH)
if source_mesh is None or not SOURCE.is_file():
    raise RuntimeError("Diana source mesh or v440 FBX unavailable")
task = unreal.AssetImportTask()
task.filename = str(SOURCE)
task.destination_path = DESTINATION
task.automated = True
task.replace_existing = False
task.save = True
options = unreal.FbxImportUI()
options.import_mesh = True
options.import_as_skeletal = True
options.import_materials = False
options.import_textures = False
options.import_animations = False
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
options.skeleton = source_mesh.get_editor_property("skeleton")
options.skeletal_mesh_import_data.convert_scene = True
options.skeletal_mesh_import_data.convert_scene_unit = True
options.skeletal_mesh_import_data.import_mesh_lo_ds = False
task.options = options
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
imported = [str(value).split(".", 1)[0] for value in task.imported_object_paths]
meshes = [path for path in imported if isinstance(unreal.load_asset(path), unreal.SkeletalMesh)]
if len(meshes) != 1:
    raise RuntimeError(f"expected one imported Diana mesh, got {meshes}; imported={imported}")
mesh = unreal.load_asset(meshes[0])
if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, OUTPUT_MAP):
    raise RuntimeError("failed to duplicate retained v421 runtime")
unreal.EditorLoadingAndSavingUtils.load_map(OUTPUT_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
if world is None or len(characters) != 1:
    raise RuntimeError("retained runtime character composition changed unexpectedly")
component = characters[0].get_component_by_class(unreal.SkeletalMeshComponent)
component.set_editor_property("skeletal_mesh_asset", mesh)
characters[0].set_actor_label("Diana_BeltRigidHip_v442")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v442 runtime")
report = {
    "schemaVersion": 1,
    "iterations": ["v440", "v441", "v442"],
    "status": "draft-runtime-visual-validation-required",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "mesh": meshes[0],
    "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "method": "rigidly reweight waist NeoBelt/weapon islands to Hip while preserving the retained animation and transparent runtime",
    "expectedResult": "belt weapons retain their hanging bind orientation instead of rotating horizontally with thigh/twist bones",
    "humanApproved": False,
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_BELT_RIGID_RUNTIME_V442=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
