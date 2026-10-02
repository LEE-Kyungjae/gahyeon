"""Export Diana's current skeletal mesh as the immutable v417 geometry-edit source."""

from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
OUTPUT = ROOT / "artifacts/gahyeon-ch/iterations/v417-diana-shoulder-shell-clearance/source/SK_Diana_CM_v024.fbx"

if OUTPUT.exists():
    raise RuntimeError(f"refusing to overwrite immutable export: {OUTPUT}")
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
asset = unreal.load_asset(MESH)
if asset is None:
    raise RuntimeError(f"mesh unavailable: {MESH}")
task = unreal.AssetExportTask()
task.object = asset
task.filename = str(OUTPUT)
task.automated = True
task.prompt = False
task.replace_identical = False
task.write_empty_files = False
task.exporter = unreal.SkeletalMeshExporterFBX()
if not unreal.Exporter.run_asset_export_task(task):
    raise RuntimeError("Diana skeletal mesh FBX export failed")
unreal.SystemLibrary.quit_editor()
