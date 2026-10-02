"""Inspect UE 5.8 Groom card texture records and assembled material bindings."""

import json
from pathlib import Path

import unreal


GROOM = (
    "/Game/Gahyeon/CharacterPipeline/v095/AssembledHigh/"
    "Skotukeda_WardrobeGroomHigh_v095/Grooms/Hair_L_StraightBangs."
    "Hair_L_StraightBangs"
)
MATERIALS = [
    (
        "/Game/Gahyeon/CharacterPipeline/v095/AssembledHigh/"
        "Skotukeda_WardrobeGroomHigh_v095/Grooms/"
        "MI_WI_Hair_L_StraightBangs_Hair_Cards."
        "MI_WI_Hair_L_StraightBangs_Hair_Cards"
    ),
    (
        "/Game/Gahyeon/CharacterPipeline/v095/CommonHigh/Materials/"
        "MI_Hair_Cards.MI_Hair_Cards"
    ),
]
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v100-groom-card-material-diagnostic/card-materials.json"
)


def property_value(owner, name):
    try:
        return owner.get_editor_property(name)
    except Exception as error:
        return {"unavailable": str(error)}


def serialize(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): serialize(item) for key, item in value.items()}
    try:
        return [serialize(item) for item in value]
    except Exception:
        pass
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def parameter_record(parameter):
    info = property_value(parameter, "parameter_info")
    return {
        "name": serialize(property_value(info, "name")) if not isinstance(info, dict) else info,
        "association": serialize(property_value(info, "association")) if not isinstance(info, dict) else None,
        "index": serialize(property_value(info, "index")) if not isinstance(info, dict) else None,
        "value": serialize(property_value(parameter, "parameter_value")),
        "expressionGuid": serialize(property_value(parameter, "expression_guid")),
    }


def material_record(path):
    material = unreal.load_asset(path)
    if material is None:
        return {"asset": path, "missing": True}
    record = {
        "asset": material.get_path_name(),
        "class": material.get_class().get_name(),
        "parent": serialize(property_value(material, "parent")),
    }
    for property_name in (
        "texture_parameter_values",
        "scalar_parameter_values",
        "vector_parameter_values",
        "double_vector_parameter_values",
        "runtime_virtual_texture_parameter_values",
        "font_parameter_values",
    ):
        parameters = property_value(material, property_name)
        if isinstance(parameters, dict):
            record[property_name] = parameters
        else:
            record[property_name] = [parameter_record(parameter) for parameter in parameters]
    return record


def card_texture_record(texture_set):
    return {
        "layout": serialize(property_value(texture_set, "layout")),
        "textures": serialize(property_value(texture_set, "textures")),
    }


def inspect_groom_card_materials():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v100 diagnostic: {OUTPUT}")
    groom = unreal.load_asset(GROOM)
    if groom is None:
        raise RuntimeError(f"High Groom asset unavailable: {GROOM}")
    cards = []
    for card in groom.get_editor_property("hair_groups_cards"):
        cards.append({
            "groupIndex": serialize(property_value(card, "group_index")),
            "lodIndex": serialize(property_value(card, "lod_index")),
            "materialSlotName": serialize(property_value(card, "material_slot_name")),
            "importedMesh": serialize(property_value(card, "imported_mesh")),
            "textureSet": card_texture_record(property_value(card, "textures")),
        })
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v100",
        "state": "read-only-groom-card-material-diagnostic",
        "groomAsset": GROOM,
        "cards": cards,
        "materials": [material_record(path) for path in MATERIALS],
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v100 card material diagnostic written: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


inspect_groom_card_materials()
