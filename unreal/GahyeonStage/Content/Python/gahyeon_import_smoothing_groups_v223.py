"""Import v222 with explicit UE-computed normals for portrait diagnostics."""

from pathlib import Path


BASE = Path(__file__).with_name("gahyeon_import_smooth_keentools_input_v217.py")
source = BASE.read_text(encoding="utf-8")
replacements = {
    "v216-keentools-smooth-head-input/gahyeon-keentools-smooth-head-target-v216.fbx":
        "v222-keentools-smoothing-group-input/gahyeon-keentools-smoothing-groups-v222.fbx",
    'TARGET_ROOT = "/Game/Gahyeon/CharacterPipeline/v217/Input"':
        'TARGET_ROOT = "/Game/Gahyeon/CharacterPipeline/v223/Input"',
    'TARGET_MESH = f"{TARGET_ROOT}/SM_Gahyeon_KeenTools_SmoothHead_Cm_v217"':
        'TARGET_MESH = f"{TARGET_ROOT}/SM_Gahyeon_KeenTools_SmoothingGroups_Cm_v223"',
    "v217-keentools-smooth-head-centimetre-import/report.json":
        "v223-keentools-smoothing-group-centimetre-import/report.json",
    "SM_Gahyeon_KeenTools_SmoothHead_Cm_v217":
        "SM_Gahyeon_KeenTools_SmoothingGroups_Cm_v223",
    "FBXNIM_IMPORT_NORMALS_AND_TANGENTS": "FBXNIM_COMPUTE_NORMALS",
    '"normalImportMethod": "IMPORT_NORMALS_AND_TANGENTS"':
        '"normalImportMethod": "COMPUTE_NORMALS"',
    "v217": "v223",
}
for old, new in replacements.items():
    if old not in source:
        raise RuntimeError(f"v217 reusable import contract changed: {old}")
    source = source.replace(old, new)
exec(compile(source, str(BASE), "exec"), {"__name__": "gahyeon_v223_import", "__file__": str(BASE)})
