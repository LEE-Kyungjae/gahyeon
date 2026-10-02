"""Diagnose UE 5.8 Groom assignment coercion without saving the map."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v077/Preview/L_Skotukeda_HairCardAligned_v077"
GROOM_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_StraightBangs/Hair_L_StraightBangs"
BINDING_PATH = "/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/Hair_L_StraightBangs_Binding"
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v078-groom-recovery/assignment-diagnostic.json")


if OUTPUT.exists():
    raise RuntimeError(f"refusing to overwrite diagnostic: {OUTPUT}")
if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
    raise RuntimeError(f"failed to load source map: {MAP}")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next((a for a in actors if a.get_actor_label() == "Skotukeda_Medium_v027"), None)
hair = next((c for c in character.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Hair"), None)
groom = unreal.EditorAssetLibrary.load_asset(GROOM_PATH)
binding = unreal.EditorAssetLibrary.load_asset(BINDING_PATH)
hair.set_editor_property("groom_asset", groom)
after_groom = hair.get_editor_property("groom_asset")
hair.set_editor_property("binding_asset", binding)
after_binding = hair.get_editor_property("binding_asset")
OUTPUT.write_text(json.dumps({
    "schemaVersion": 1,
    "iteration": "v078",
    "state": "unsaved-assignment-diagnostic",
    "requestedGroom": groom.get_path_name() if groom else None,
    "actualGroom": after_groom.get_path_name() if after_groom else None,
    "requestedBinding": binding.get_path_name() if binding else None,
    "actualBinding": after_binding.get_path_name() if after_binding else None,
    "groomClass": after_groom.get_class().get_name() if after_groom else None,
    "bindingClass": after_binding.get_class().get_name() if after_binding else None,
    "automaticApproval": False,
    "productionReady": False,
}, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
