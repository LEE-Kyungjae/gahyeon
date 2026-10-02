"""Export v219 geometry with explicit FBX smooth-face groups."""

from pathlib import Path


BASE = Path(__file__).with_name("export_keentools_clean_normals_v219.py")
source = BASE.read_text(encoding="utf-8")
replacements = {
    'mesh_smooth_type="OFF"': 'mesh_smooth_type="FACE"',
    "v219": "v222",
    "clean-normal": "smoothing-group",
    "clean_normals": "smoothing_groups",
    "CleanNormals": "SmoothingGroups",
}
for old, new in replacements.items():
    if old not in source:
        raise RuntimeError(f"v219 reusable export contract changed: {old}")
    source = source.replace(old, new)
exec(compile(source, str(BASE), "exec"), {"__name__": "__main__", "__file__": str(BASE)})
