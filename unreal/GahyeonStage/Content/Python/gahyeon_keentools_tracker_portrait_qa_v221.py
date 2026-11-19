"""Run the v218 portrait-only gate against the clean-normal v220 asset."""

from pathlib import Path


BASE = Path(__file__).with_name("gahyeon_keentools_tracker_portrait_qa_v218.py")
source = BASE.read_text(encoding="utf-8")
replacements = {
    "/Game/Gahyeon/CharacterPipeline/v217/Input/SM_Gahyeon_KeenTools_SmoothHead_Cm_v217":
        "/Game/Gahyeon/CharacterPipeline/v220/Input/SM_Gahyeon_KeenTools_CleanNormals_Cm_v220",
    "v218": "v221",
}
for old, new in replacements.items():
    if old not in source:
        raise RuntimeError(f"v218 reusable portrait contract changed: {old}")
    source = source.replace(old, new)
exec(compile(source, str(BASE), "exec"), {"__name__": "gahyeon_v221_portrait_qa", "__file__": str(BASE)})
