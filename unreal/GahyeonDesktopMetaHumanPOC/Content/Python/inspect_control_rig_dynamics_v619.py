"""Inspect UE 5.8 Control Rig Dynamics nodes and Python graph-authoring APIs."""

import json
from pathlib import Path

import unreal


OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v619-control-rig-dynamics-api/report.json"
)
DYNAMICS_TERMS = ("dynamics", "particle", "constraint", "collider", "confiner")


def public_methods(value):
    return sorted(item for item in dir(value) if not item.startswith("_"))


def inspect_control_rig_dynamics_v619():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable output: {OUTPUT}")

    blueprint_class = getattr(unreal, "ControlRigBlueprint", None)
    factory_class = getattr(unreal, "ControlRigBlueprintFactory", None)
    registry_class = getattr(unreal, "RigVMRegistry", None)
    candidate_types = sorted(
        name
        for name in dir(unreal)
        if any(term in name.lower() for term in DYNAMICS_TERMS)
    )
    dynamics_units = [name for name in candidate_types if name.startswith("RigUnit_")]

    report = {
        "schemaVersion": 1,
        "iteration": "v619",
        "status": "read-only-control-rig-dynamics-api-inspection",
        "engineVersion": unreal.SystemLibrary.get_engine_version(),
        "pluginLoaded": len(dynamics_units) > 0,
        "dynamicsUnits": dynamics_units,
        "candidateTypes": candidate_types,
        "authoring": {
            "ControlRigBlueprint": {
                "available": blueprint_class is not None,
                "methods": public_methods(blueprint_class) if blueprint_class else [],
            },
            "ControlRigBlueprintFactory": {
                "available": factory_class is not None,
                "methods": public_methods(factory_class) if factory_class else [],
            },
            "RigVMRegistry": {
                "available": registry_class is not None,
                "methods": public_methods(registry_class) if registry_class else [],
            },
        },
        "decision": {
            "canAttemptVersionedControlRig": bool(
                blueprint_class and factory_class and dynamics_units
            ),
            "existingAnimationAssetsMutated": False,
        },
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("CONTROL_RIG_DYNAMICS_V619=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_control_rig_dynamics_v619()
