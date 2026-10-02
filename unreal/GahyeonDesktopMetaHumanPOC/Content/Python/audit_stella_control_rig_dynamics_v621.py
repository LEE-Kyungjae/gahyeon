"""Audit the compiled v620 Control Rig and discover runtime execution hooks."""

import json
from pathlib import Path

import unreal


RIG_PATH = "/Game/LivingCharacterPOC/v620/ControlRig/CR_Stella_HairDynamics_v620"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v621-stella-control-rig-runtime-audit/report.json"
)


def public_methods(value):
    return sorted(item for item in dir(value) if not item.startswith("_"))


def audit_stella_control_rig_dynamics_v621():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable output: {OUTPUT}")
    unreal.load_module("ControlRigDeveloper")
    rig = unreal.load_asset(RIG_PATH)
    if not rig:
        raise RuntimeError(f"missing Control Rig: {RIG_PATH}")

    generated_class = rig.get_control_rig_class()
    default_object = unreal.get_default_object(generated_class)
    graph = rig.get_default_model()
    hierarchy = rig.get_hierarchy()
    names = {str(key.name) for key in hierarchy.get_all_keys()}
    nodes = []
    for node in graph.get_nodes():
        struct = node.get_script_struct()
        nodes.append(
            {
                "name": node.get_name(),
                "structPath": struct.get_path_name() if struct else "",
                "structDefault": node.get_struct_default_value(),
            }
        )

    runtime_terms = ("execute", "initialize", "hierarchy", "event", "delta", "binding")
    report = {
        "schemaVersion": 1,
        "iteration": "v621",
        "status": "read-only-compiled-control-rig-runtime-audit",
        "controlRig": RIG_PATH,
        "generatedClass": generated_class.get_path_name(),
        "hierarchyElementCount": len(names),
        "requiredBones": {
            "Root": "Root" in names,
            "Ab-BK-HairA01": "Ab-BK-HairA01" in names,
            "Ab-BK-HairA03": "Ab-BK-HairA03" in names,
        },
        "nodes": nodes,
        "runtimeMethods": [
            item
            for item in public_methods(default_object)
            if any(term in item.lower() for term in runtime_terms)
        ],
        "controlRigClassMethods": [
            item
            for item in public_methods(getattr(unreal, "ControlRig", None))
            if any(term in item.lower() for term in runtime_terms)
        ],
        "controlRigComponent": {
            "available": getattr(unreal, "ControlRigComponent", None) is not None,
            "methods": [
                item
                for item in public_methods(getattr(unreal, "ControlRigComponent", None))
                if any(term in item.lower() for term in runtime_terms + ("map", "rig"))
            ],
        },
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.SystemLibrary.quit_editor()


audit_stella_control_rig_dynamics_v621()
