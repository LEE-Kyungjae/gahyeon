"""Inspect UE 5.8's exposed Python authoring surface for secondary-motion graphs."""

import json
from pathlib import Path

import unreal


OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v617-anim-dynamics-authoring-api/report.json"
)
CLASS_NAMES = (
    "AnimGraphNode_AnimDynamics",
    "AnimGraphNode_RigidBody",
    "AnimGraphNode_RigidBodyWithControl",
    "AnimationBlueprintLibrary",
    "AnimationBlueprintEditorLibrary",
    "BlueprintEditorLibrary",
    "ControlRigBlueprint",
    "PhysicsControlAsset",
    "PhysicsControlComponent",
)


def inspect_anim_dynamics_authoring_api_v617():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable output: {OUTPUT}")
    classes = {}
    for name in CLASS_NAMES:
        value = getattr(unreal, name, None)
        classes[name] = {
            "available": value is not None,
            "methods": sorted(
                item for item in dir(value)
                if not item.startswith("_")
            ) if value is not None else [],
        }
    report = {
        "schemaVersion": 1,
        "iteration": "v617",
        "status": "read-only-python-authoring-api-inspection",
        "engineVersion": unreal.SystemLibrary.get_engine_version(),
        "classes": classes,
        "decision": {
            "animDynamicsGraphAutomationAvailable": classes["AnimGraphNode_AnimDynamics"]["available"],
            "physicsControlGraphAutomationAvailable": classes["AnimGraphNode_RigidBodyWithControl"]["available"],
            "controlRigAutomationAvailable": classes["ControlRigBlueprint"]["available"],
        },
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("ANIM_DYNAMICS_API_V617=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_anim_dynamics_authoring_api_v617()
