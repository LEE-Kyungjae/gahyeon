"""Compare inherited skin parameters used by Gahyeon's body and face."""

import json
from pathlib import Path

import unreal


MATERIALS = {
    "body": (
        "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
        "Gahyeon_AnimationPOC_v244/Body/Materials/MI_Body_Baked"
    ),
    "faceLod3": (
        "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
        "Gahyeon_AnimationPOC_v244/Face/Materials/MI_Face_Skin_Baked_LOD3"
    ),
}
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v301-gahyeon-skin-material-inspection/report.json"
)


def object_path(value):
    if value is None:
        return None
    try:
        return str(value.get_path_name())
    except Exception:
        return str(value)


def safe_property(value, name):
    try:
        return value.get_editor_property(name)
    except Exception:
        return None


def inspect_material_parameters(path):
    material = unreal.EditorAssetLibrary.load_asset(path)
    if material is None:
        raise RuntimeError(f"material unavailable: {path}")
    texture_values = {}
    for name in unreal.MaterialEditingLibrary.get_texture_parameter_names(material):
        try:
            texture_values[str(name)] = object_path(
                unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
                    material, name
                )
            )
        except Exception as exc:
            texture_values[str(name)] = f"ERROR: {exc}"
    scalar_values = {}
    for name in unreal.MaterialEditingLibrary.get_scalar_parameter_names(material):
        try:
            scalar_values[str(name)] = round(
                float(
                    unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
                        material, name
                    )
                ),
                6,
            )
        except Exception as exc:
            scalar_values[str(name)] = f"ERROR: {exc}"
    return {
        "path": path,
        "parent": object_path(safe_property(material, "parent")),
        "textureParameters": texture_values,
        "scalarParameters": scalar_values,
    }


report = {
    "schemaVersion": 1,
    "iteration": "v301",
    "status": "read-only-skin-material-inspection",
    "materials": {
        name: inspect_material_parameters(path) for name, path in MATERIALS.items()
    },
    "mutatedAssets": [],
    "humanApproved": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("GAHYEON_V301_SKIN_MATERIALS=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
