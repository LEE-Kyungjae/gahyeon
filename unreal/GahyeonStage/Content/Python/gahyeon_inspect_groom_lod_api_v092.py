"""Inspect UE 5.8 Groom LOD controls and asset metadata without mutation."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v089/Preview/L_Skotukeda_WardrobeGroom_v089"
LABEL = "Skotukeda_WardrobeGroomQA_v088"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v092-groom-lod-diagnostic/lod-api.json"
)


def readable(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [readable(item) for item in value]
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def inspect_groom_lod_api():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v092 inventory: {OUTPUT}")
    if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
        raise RuntimeError(f"failed to load source map: {MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    actor = next((value for value in actors if value.get_actor_label() == LABEL), None)
    if actor is None:
        raise RuntimeError(f"assembled actor unavailable: {LABEL}")
    hair = next((value for value in actor.get_components_by_class(unreal.GroomComponent) if value.get_name() == "Hair"), None)
    if hair is None:
        raise RuntimeError("Hair GroomComponent unavailable")
    groom = hair.get_editor_property("groom_asset")
    candidates = [
        "forced_lod", "lod_selection_type", "hair_groups_info", "hair_groups_lod",
        "enable_simulation", "use_cards", "groom_asset", "binding_asset",
    ]
    properties = {}
    for owner_name, owner in (("component", hair), ("asset", groom)):
        properties[owner_name] = {}
        for name in candidates:
            try:
                properties[owner_name][name] = readable(owner.get_editor_property(name))
            except Exception as error:
                properties[owner_name][name] = {"unavailable": str(error)}
    component_api = sorted(name for name in dir(hair) if "lod" in name.lower() or "groom" in name.lower() or "card" in name.lower())
    asset_api = sorted(name for name in dir(groom) if "lod" in name.lower() or "group" in name.lower() or "card" in name.lower())
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v092",
        "state": "read-only-groom-lod-api-diagnostic",
        "sourceMap": MAP,
        "groomAsset": groom.get_path_name(),
        "componentApi": component_api,
        "assetApi": asset_api,
        "properties": properties,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v092 Groom LOD API inventory written: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


inspect_groom_lod_api()
