"""Verify persistent Hair on/off component states before rendering."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v335/QA/L_GahyeonHairShadowCompare_v335"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v337-gahyeon-hair-shadow-runtime/report.json"
)


def inspect_gahyeon_hair_shadow_map_v337():
    if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
        raise RuntimeError(f"map unavailable: {MAP}")
    cases = []
    for actor in unreal.get_editor_subsystem(
        unreal.EditorActorSubsystem
    ).get_all_level_actors():
        label = actor.get_actor_label()
        if not label.startswith("Gahyeon_Hair"):
            continue
        hair = next(
            component for component in actor.get_components_by_class(unreal.GroomComponent)
            if str(component.get_name()) == "Hair"
        )
        cases.append(
            {
                "label": label,
                "visible": bool(hair.is_visible()),
                "hiddenInGame": bool(hair.get_editor_property("hidden_in_game")),
            }
        )
    cases.sort(key=lambda item: item["label"])
    states = {(item["visible"], item["hiddenInGame"]) for item in cases}
    if len(cases) != 2 or states != {(True, False), (False, True)}:
        raise RuntimeError(f"invalid Hair on/off states: {cases}")
    report = {
        "schemaVersion": 1,
        "iteration": "v337",
        "status": "runtime-hair-states-verified",
        "map": MAP,
        "cases": cases,
        "mutatedAssets": [],
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V337_HAIR_RUNTIME=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_gahyeon_hair_shadow_map_v337()
