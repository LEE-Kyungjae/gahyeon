"""Clone v620 and add the Backward Solve event required by layered Control Rig."""

import json
from pathlib import Path

import unreal


SOURCE = "/Game/LivingCharacterPOC/v620/ControlRig/CR_Stella_HairDynamics_v620"
TARGET = "/Game/LivingCharacterPOC/v623/ControlRig/CR_Stella_HairDynamics_Layered_v623"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v623-stella-layered-dynamics-rig/report.json"
)


def struct_path(node):
    struct = node.get_script_struct()
    return struct.get_path_name() if struct else ""


def build_stella_layered_dynamics_rig_v623():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError("refusing to overwrite immutable v623 output")
    unreal.load_module("ControlRigDeveloper")
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET):
        raise RuntimeError("failed to duplicate v620 Control Rig")
    rig = unreal.load_asset(TARGET)
    graph = rig.get_default_model()
    controller = rig.get_controller_by_name(graph.get_name())
    if any(struct_path(node) == "/Script/ControlRig.RigUnit_InverseExecution" for node in graph.get_nodes()):
        raise RuntimeError("unexpected pre-existing Backward Solve event")
    inverse = controller.add_unit_node_from_struct_path(
        "/Script/ControlRig.RigUnit_InverseExecution",
        "Execute",
        unreal.Vector2D(0.0, 850.0),
        "BackwardSolve",
        False,
    )
    if not inverse:
        raise RuntimeError("failed to add Backward Solve event")
    rig.recompile_vm()
    unreal.BlueprintEditorLibrary.compile_blueprint(rig)
    if not unreal.EditorAssetLibrary.save_asset(TARGET, only_if_is_dirty=False):
        raise RuntimeError("failed to save v623 Control Rig")
    nodes = [
        {"name": node.get_name(), "structPath": struct_path(node)}
        for node in graph.get_nodes()
    ]
    report = {
        "schemaVersion": 1,
        "iteration": "v623",
        "status": "draft-layered-control-rig-ready",
        "source": SOURCE,
        "controlRig": TARGET,
        "nodes": nodes,
        "checks": {
            "assetExists": unreal.EditorAssetLibrary.does_asset_exist(TARGET),
            "backwardSolvePresent": any(
                node["structPath"] == "/Script/ControlRig.RigUnit_InverseExecution"
                for node in nodes
            ),
            "dynamicsPreserved": all(
                required in {node["structPath"] for node in nodes}
                for required in (
                    "/Script/ControlRigDynamics.RigUnit_SpawnDynamicsChains",
                    "/Script/ControlRigDynamics.RigUnit_StepDynamicsSolver",
                )
            ),
        },
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.SystemLibrary.quit_editor()


build_stella_layered_dynamics_rig_v623()
