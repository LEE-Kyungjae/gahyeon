"""Import Diana's sleeve-occluded arm mesh and build an immutable runtime candidate."""

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/gahyeon-ch/iterations/v417-diana-shoulder-shell-clearance/SK_Diana_ShoulderOccluded_v417.fbx"
DESTINATION = "/Game/Gahyeon/Character2/Diana/v417/Source"
SOURCE_MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v410/Runtime/L_DianaMacRuntimeHighKeyClearance_v410"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v417/Runtime/L_DianaMacRuntimeShoulderOccluded_v417"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v417-diana-shoulder-shell-clearance/unreal-report.json"

if REPORT.exists() or unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True) or unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP):
    raise RuntimeError("refusing to overwrite immutable Diana v417 Unreal outputs")
source_mesh = unreal.load_asset(SOURCE_MESH)
if source_mesh is None or not SOURCE.is_file():
    raise RuntimeError("Diana source mesh or edited FBX unavailable")

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
    raise RuntimeError("failed to duplicate v410 runtime")
unreal.EditorLoadingAndSavingUtils.load_map(OUTPUT_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
if world is None or len(characters) != 1:
    raise RuntimeError("v410 character composition changed unexpectedly")
component = characters[0].get_component_by_class(unreal.SkeletalMeshComponent)
component.set_editor_property("skeletal_mesh_asset", mesh)
characters[0].set_actor_label("Diana_ShoulderOccluded_v417")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save v417 runtime")

report = {
    "schemaVersion": 1,
    "iteration": "v417-diana-shoulder-shell-clearance",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "mesh": meshes[0],
    "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "method": "garment occlusion: remove arm skin beneath sleeves while preserving wrists and hands",
    "humanApproved": False,
    "productionReady": False,
}
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
