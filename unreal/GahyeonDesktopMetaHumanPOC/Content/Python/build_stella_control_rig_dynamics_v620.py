"""Create a versioned Stella Control Rig Dynamics graph scaffold in UE 5.8."""

import json
from pathlib import Path

import unreal


MESH_PATH = (
    "/Game/LivingCharacterPOC/v572/Characters/StellaCentimeterNormalized/"
    "StellaLily_CentimeterNormalized_v571"
)
RIG_PATH = "/Game/LivingCharacterPOC/v620/ControlRig/CR_Stella_HairDynamics_v620"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v620-stella-control-rig-dynamics/report.json"
)
HAIR_ROOT = "Ab-BK-HairA01"


def add_unit(controller, struct_path, position, node_name):
    node = controller.add_unit_node_from_struct_path(
        struct_path,
        "Execute",
        unreal.Vector2D(*position),
        node_name,
        False,
    )
    if not node:
        raise RuntimeError(f"failed to add {struct_path}")
    return node


def pin_records(node):
    return [
        {
            "name": pin.get_name(),
            "path": pin.get_pin_path(),
            "direction": str(pin.get_direction()),
            "default": pin.get_default_value(),
        }
        for pin in node.get_pins()
    ]


def node_struct_path(node):
    script_struct = node.get_script_struct()
    return script_struct.get_path_name() if script_struct else ""


def build_stella_control_rig_dynamics_v620():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable output: {OUTPUT}")
    unreal.load_module("ControlRigDeveloper")
    mesh = unreal.load_asset(MESH_PATH)
    if not mesh:
        raise RuntimeError(f"missing skeletal mesh: {MESH_PATH}")

    resumed_after_report_failure = unreal.EditorAssetLibrary.does_asset_exist(RIG_PATH)
    if resumed_after_report_failure:
        rig = unreal.load_asset(RIG_PATH)
        if not rig:
            raise RuntimeError(f"failed to load existing draft asset: {RIG_PATH}")
        graph = rig.get_default_model()
        imported = list(rig.get_hierarchy().get_all_keys())
        links = [
            {
                "source": link.get_source_pin().get_pin_path(),
                "target": link.get_target_pin().get_pin_path(),
                "added": True,
            }
            for link in graph.get_links()
        ]
        root_set = any(
            pin.get_name() == "RootBones" and HAIR_ROOT in pin.get_default_value()
            for node in graph.get_nodes()
            for pin in node.get_pins()
        )
    else:
        factory = unreal.ControlRigBlueprintFactory()
        rig = factory.create_new_control_rig_asset(desired_package_path=RIG_PATH)
        if not rig:
            raise RuntimeError("failed to create Control Rig asset")
        rig.set_preview_mesh(preview_mesh=mesh)

        hierarchy = rig.get_hierarchy()
        hierarchy_controller = hierarchy.get_controller()
        imported = list(
            hierarchy_controller.import_bones_from_asset(
                mesh.get_path_name(), "", True, True, False
            )
        )
        imported_names = {str(key.name) for key in imported}
        if HAIR_ROOT not in imported_names:
            raise RuntimeError(f"hair root not imported: {HAIR_ROOT}")

        graph = rig.get_default_model()
        controller = rig.get_controller_by_name(graph.get_name())
        existing = {node_struct_path(node): node for node in graph.get_nodes()}
        begin = existing.get("/Script/ControlRig.RigUnit_BeginExecution")
        if not begin:
            begin = add_unit(controller, "/Script/ControlRig.RigUnit_BeginExecution", (0.0, 500.0), "ForwardSolve")
        construction = add_unit(controller, "/Script/ControlRig.RigUnit_PrepareForExecution", (0.0, 0.0), "Construction")
        solver = add_unit(controller, "/Script/ControlRigDynamics.RigUnit_SpawnDynamicsSolver1", (350.0, 0.0), "SpawnHairSolver")
        chains = add_unit(controller, "/Script/ControlRigDynamics.RigUnit_SpawnDynamicsChains", (700.0, 0.0), "SpawnHairChains")
        step = add_unit(controller, "/Script/ControlRigDynamics.RigUnit_StepDynamicsSolver", (350.0, 500.0), "StepHairSolver")

        links = []
        for source, target in (
            (f"{construction.get_name()}.ExecuteContext", f"{solver.get_name()}.ExecuteContext"),
            (f"{solver.get_name()}.ExecuteContext", f"{chains.get_name()}.ExecuteContext"),
            (f"{begin.get_name()}.ExecuteContext", f"{step.get_name()}.ExecuteContext"),
        ):
            ok = controller.add_link(source, target, False)
            links.append({"source": source, "target": target, "added": bool(ok)})

        root_value = f"((Type=Bone,Name=\"{HAIR_ROOT}\"))"
        root_pin = f"{chains.get_name()}.RootBones"
        root_set = controller.set_pin_default_value(root_pin, root_value, True, False, False)

        rig.recompile_vm()
        unreal.BlueprintEditorLibrary.compile_blueprint(rig)
        if not unreal.EditorAssetLibrary.save_asset(RIG_PATH, only_if_is_dirty=False):
            raise RuntimeError(f"failed to save {RIG_PATH}")

    nodes = list(graph.get_nodes())
    report = {
        "schemaVersion": 1,
        "iteration": "v620",
        "status": "draft-control-rig-dynamics-scaffold",
        "sourceMesh": MESH_PATH,
        "controlRig": RIG_PATH,
        "importedBoneCount": len(imported),
        "hairRoot": HAIR_ROOT,
        "rootPinDefaultSet": bool(root_set),
        "links": links,
        "nodes": [
            {
                "name": node.get_name(),
                "structPath": node_struct_path(node),
                "pins": pin_records(node),
            }
            for node in nodes
        ],
        "checks": {
            "assetExists": unreal.EditorAssetLibrary.does_asset_exist(RIG_PATH),
            "constructionPresent": any(
                node_struct_path(node)
                == "/Script/ControlRig.RigUnit_PrepareForExecution"
                for node in nodes
            ),
            "spawnChainsPresent": any(
                node_struct_path(node)
                == "/Script/ControlRigDynamics.RigUnit_SpawnDynamicsChains"
                for node in nodes
            ),
            "stepSolverPresent": any(
                node_struct_path(node)
                == "/Script/ControlRigDynamics.RigUnit_StepDynamicsSolver"
                for node in nodes
            ),
        },
        "hypothesis": "UE-native Control Rig Dynamics can add hair motion without re-exporting body animation.",
        "resumedAfterReportFailure": resumed_after_report_failure,
        "decision": "structural-scaffold-only; runtime render required before promotion",
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.SystemLibrary.quit_editor()


build_stella_control_rig_dynamics_v620()
