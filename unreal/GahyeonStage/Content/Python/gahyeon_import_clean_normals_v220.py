"""Reuse the validated v217 import contract for the clean-normal v219 FBX."""

from pathlib import Path


BASE = Path(__file__).with_name("gahyeon_import_smooth_keentools_input_v217.py")
source = BASE.read_text(encoding="utf-8")
replacements = {
    "v216-keentools-smooth-head-input/gahyeon-keentools-smooth-head-target-v216.fbx":
        "v219-keentools-clean-normal-input/gahyeon-keentools-clean-normals-v219.fbx",
    'TARGET_ROOT = "/Game/Gahyeon/CharacterPipeline/v217/Input"':
        'TARGET_ROOT = "/Game/Gahyeon/CharacterPipeline/v220/Input"',
    'TARGET_MESH = f"{TARGET_ROOT}/SM_Gahyeon_KeenTools_SmoothHead_Cm_v217"':
        'TARGET_MESH = f"{TARGET_ROOT}/SM_Gahyeon_KeenTools_CleanNormals_Cm_v220"',
    "v217-keentools-smooth-head-centimetre-import/report.json":
        "v220-keentools-clean-normal-centimetre-import/report.json",
    "SM_Gahyeon_KeenTools_SmoothHead_Cm_v217":
        "SM_Gahyeon_KeenTools_CleanNormals_Cm_v220",
    "v217": "v220",
}
for old, new in replacements.items():
    if old not in source:
        raise RuntimeError(f"v217 reusable import contract changed: {old}")
    source = source.replace(old, new)
exec(compile(source, str(BASE), "exec"), {"__name__": "gahyeon_v220_import", "__file__": str(BASE)})
