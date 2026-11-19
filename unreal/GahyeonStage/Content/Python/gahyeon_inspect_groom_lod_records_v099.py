"""Read exact UE 5.8 Groom LOD/card/helmet records using engine-header field names."""

import json
from pathlib import Path

import unreal


GROOM = (
    "/Game/Gahyeon/CharacterPipeline/v095/AssembledHigh/"
    "Skotukeda_WardrobeGroomHigh_v095/Grooms/Hair_L_StraightBangs."
    "Hair_L_StraightBangs"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v099-groom-lod-records/lod-records.json"
)


def value(owner, name):
    try:
        result = owner.get_editor_property(name)
    except Exception as error:
        return {"unavailable": str(error)}
    if result is None or isinstance(result, (bool, int, float, str)):
        return result
    try:
        return result.get_path_name()
    except Exception:
        return str(result)


def inspect_groom_lod_records():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v099 records: {OUTPUT}")
    groom = unreal.load_asset(GROOM)
    if groom is None:
        raise RuntimeError(f"High Groom asset unavailable: {GROOM}")
    lod_groups = []
    for group_index, group in enumerate(groom.get_editor_property("hair_groups_lod")):
        lods = []
        group_lods = group.get_editor_property("lods")
        for lod_index, lod in enumerate(group_lods):
            lods.append({
                "lodIndex": lod_index,
                "screenSize": value(lod, "screen_size"),
                "visible": value(lod, "visible"),
                "geometryType": value(lod, "geometry_type"),
                "bindingType": value(lod, "binding_type"),
                "curveDecimation": value(lod, "curve_decimation"),
                "vertexDecimation": value(lod, "vertex_decimation"),
                "thicknessScale": value(lod, "thickness_scale"),
            })
        lod_groups.append({"groupIndex": group_index, "autoLodBias": value(group, "auto_lod_bias"), "lods": lods})
    cards = []
    for card in groom.get_editor_property("hair_groups_cards"):
        cards.append({
            "groupIndex": value(card, "group_index"),
            "lodIndex": value(card, "lod_index"),
            "materialSlotName": value(card, "material_slot_name"),
            "importedMesh": value(card, "imported_mesh"),
            "textures": value(card, "textures"),
        })
    helmets = []
    for mesh in groom.get_editor_property("hair_groups_meshes"):
        helmets.append({
            "groupIndex": value(mesh, "group_index"),
            "lodIndex": value(mesh, "lod_index"),
            "materialSlotName": value(mesh, "material_slot_name"),
            "importedMesh": value(mesh, "imported_mesh"),
            "textures": value(mesh, "textures"),
        })
    materials = []
    for material in groom.get_editor_property("hair_groups_materials"):
        materials.append({
            "slotName": value(material, "slot_name"),
            "material": value(material, "material"),
        })
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v099",
        "state": "read-only-high-groom-lod-records",
        "groomAsset": GROOM,
        "lodGroups": lod_groups,
        "cards": cards,
        "helmets": helmets,
        "materials": materials,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v099 Groom LOD records written: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


inspect_groom_lod_records()
