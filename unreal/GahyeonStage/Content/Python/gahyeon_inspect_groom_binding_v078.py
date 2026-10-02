"""Read-only inspection of the v077 MetaHuman Hair Groom component and dependencies."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v077/Preview/L_Skotukeda_HairCardAligned_v077"
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v078-groom-recovery/inspection.json")


def asset_path(value):
    return value.get_path_name() if value is not None else None


if OUTPUT.exists():
    raise RuntimeError(f"refusing to overwrite immutable v078 inspection: {OUTPUT}")
if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
    raise RuntimeError(f"failed to load v077 map: {MAP}")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next((actor for actor in actors if actor.get_actor_label() == "Skotukeda_Medium_v027"), None)
if character is None:
    raise RuntimeError("v077 character actor is unavailable")
hair = next((component for component in character.get_components_by_class(unreal.GroomComponent) if component.get_name() == "Hair"), None)
if hair is None:
    raise RuntimeError("MetaHuman Hair Groom component is unavailable")

parent = hair.get_attach_parent()
record = {
    "schemaVersion": 1,
    "iteration": "v078",
    "state": "read-only-groom-inspection",
    "sourceMap": MAP,
    "component": {
        "name": hair.get_name(),
        "path": hair.get_path_name(),
        "visible": hair.get_editor_property("visible"),
        "hiddenInGame": hair.get_editor_property("hidden_in_game"),
        "groomAsset": asset_path(hair.get_editor_property("groom_asset")),
        "bindingAsset": asset_path(hair.get_editor_property("binding_asset")),
        "groomCache": asset_path(hair.get_editor_property("groom_cache")),
        "attachParent": parent.get_path_name() if parent is not None else None,
        "attachParentClass": parent.get_class().get_name() if parent is not None else None,
        "attachSocket": str(hair.get_attach_socket_name()),
        "relativeLocation": [
            hair.get_editor_property("relative_location").x,
            hair.get_editor_property("relative_location").y,
            hair.get_editor_property("relative_location").z,
        ],
        "materials": [asset_path(hair.get_material(index)) for index in range(hair.get_num_materials())],
    },
    "automaticApproval": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
unreal.log(f"Gahyeon v078 groom inspection written: {OUTPUT}")
unreal.SystemLibrary.quit_editor()
