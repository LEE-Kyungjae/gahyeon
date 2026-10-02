"""Build an Ururu-native layered Control Rig Dynamics asset for hair and ribbons."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MESH = (
    "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/"
    "Ururu_CentimeterNormalized_v584"
)
TARGET = "/Game/LivingCharacterPOC/v636/ControlRig/CR_Ururu_HairClothingDynamics_v636"
PROFILE = ROOT / "character_pipeline/config/secondary-motion-profiles-v611.json"
OUTPUT = ROOT / "artifacts/living-character-poc-v636-ururu-hair-clothing-dynamics/report.json"


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


def node_struct_path(node):
    struct = node.get_script_struct()
    return struct.get_path_name() if struct else ""


def build_ururu_hair_clothing_dynamics_v636():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError("refusing to overwrite immutable v636 output")
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    groups = profile["characters"]["ururu"]["groups"]
    hair_roots = [chain["root"] for chain in groups["hair"]["chains"]]
    clothing_roots = [chain["root"] for chain in groups["clothing"]["chains"]]
    if len(hair_roots) != 15 or len(set(hair_roots)) != 15:
        raise RuntimeError(f"unexpected Ururu hair roots: {hair_roots}")
    if len(clothing_roots) != 2 or len(set(clothing_roots)) != 2:
        raise RuntimeError(f"unexpected Ururu clothing roots: {clothing_roots}")

    unreal.load_module("ControlRigDeveloper")
    mesh = unreal.load_asset(MESH)
    if not mesh:
        raise RuntimeError(f"missing Ururu skeletal mesh: {MESH}")
    factory = unreal.ControlRigBlueprintFactory()
    rig = factory.create_new_control_rig_asset(desired_package_path=TARGET)
    if not rig:
        raise RuntimeError("failed to create Ururu Control Rig")
    rig.set_preview_mesh(preview_mesh=mesh)
    imported = list(
        rig.get_hierarchy().get_controller().import_bones_from_asset(
            mesh.get_path_name(), "", True, True, False
        )
    )
    imported_names = {str(key.name) for key in imported}
    missing = [root for root in hair_roots + clothing_roots if root not in imported_names]
    if missing:
        raise RuntimeError(f"secondary roots missing from Ururu hierarchy: {missing}")

    graph = rig.get_default_model()
    controller = rig.get_controller_by_name(graph.get_name())
    existing = {node_struct_path(node): node for node in graph.get_nodes()}
    forward = existing.get("/Script/ControlRig.RigUnit_BeginExecution")
    if not forward:
        forward = add_unit(
            controller,
            "/Script/ControlRig.RigUnit_BeginExecution",
            (0.0, 500.0),
            "ForwardSolve",
        )
    construction = add_unit(
        controller,
        "/Script/ControlRig.RigUnit_PrepareForExecution",
        (0.0, 0.0),
        "Construction",
    )
    solver = add_unit(
        controller,
        "/Script/ControlRigDynamics.RigUnit_SpawnDynamicsSolver1",
        (350.0, 0.0),
        "SpawnSecondarySolver",
    )
    hair = add_unit(
        controller,
        "/Script/ControlRigDynamics.RigUnit_SpawnDynamicsChains",
        (700.0, 0.0),
        "SpawnHairChains",
    )
    clothing = add_unit(
        controller,
        "/Script/ControlRigDynamics.RigUnit_SpawnDynamicsChains",
        (1050.0, 0.0),
        "SpawnClothingChains",
    )
    step = add_unit(
        controller,
        "/Script/ControlRigDynamics.RigUnit_StepDynamicsSolver",
        (350.0, 500.0),
        "StepSecondarySolver",
    )
    add_unit(
        controller,
        "/Script/ControlRig.RigUnit_InverseExecution",
        (0.0, 850.0),
        "BackwardSolve",
    )

    for source, target in (
        (f"{construction.get_name()}.ExecuteContext", f"{solver.get_name()}.ExecuteContext"),
        (f"{solver.get_name()}.ExecuteContext", f"{hair.get_name()}.ExecuteContext"),
        (f"{hair.get_name()}.ExecuteContext", f"{clothing.get_name()}.ExecuteContext"),
        (f"{forward.get_name()}.ExecuteContext", f"{step.get_name()}.ExecuteContext"),
    ):
        if not controller.add_link(source, target, False):
            raise RuntimeError(f"failed to link {source} -> {target}")

    hair_value = "(" + ",".join(
        f'(Type=Bone,Name="{root}")' for root in hair_roots
    ) + ")"
    clothing_value = "(" + ",".join(
        f'(Type=Bone,Name="{root}")' for root in clothing_roots
    ) + ")"
    hair_properties = (
        "(Radius=3.000000,Mass=0.600000,MovementType=Simulated,"
        "GravityMultiplier=0.150000,Strength=1.500000,DampingRatio=0.720000,"
        "ExtraDamping=0.080000,bAccelerationMode=True,TargetVelocityInfluence=1.000000,"
        "TargetMode=0.350000,AngleLimit=18.000000,AngleLimitStrength=4.000000,"
        "Damping=0.000000,bScaleDampingByInverseMass=False,bCollideWithColliders=False)"
    )
    clothing_properties = (
        "(Radius=3.000000,Mass=0.750000,MovementType=Simulated,"
        "GravityMultiplier=0.200000,Strength=2.500000,DampingRatio=0.780000,"
        "ExtraDamping=0.120000,bAccelerationMode=True,TargetVelocityInfluence=1.000000,"
        "TargetMode=0.500000,AngleLimit=14.000000,AngleLimitStrength=6.000000,"
        "Damping=0.000000,bScaleDampingByInverseMass=False,bCollideWithColliders=False)"
    )
    for pin, value in (
        ("SpawnHairChains.RootBones", hair_value),
        ("SpawnHairChains.ParticleProperties", hair_properties),
        ("SpawnClothingChains.RootBones", clothing_value),
        ("SpawnClothingChains.ParticleProperties", clothing_properties),
    ):
        if not controller.set_pin_default_value(pin, value, True, False, False):
            raise RuntimeError(f"failed to configure {pin}")

    rig.recompile_vm()
    unreal.BlueprintEditorLibrary.compile_blueprint(rig)
    if not unreal.EditorAssetLibrary.save_asset(TARGET, only_if_is_dirty=False):
        raise RuntimeError("failed to save v636 Ururu Control Rig")
    report = {
        "schemaVersion": 1,
        "iteration": "v636",
        "status": "draft-hair-clothing-control-rig-ready",
        "sourceMesh": MESH,
        "controlRig": TARGET,
        "importedBoneCount": len(imported),
        "hairRoots": hair_roots,
        "clothingRoots": clothing_roots,
        "hairParticleProperties": hair_properties,
        "clothingParticleProperties": clothing_properties,
        "hypothesis": "Ururu-native hair and ribbon chains add restrained secondary motion after corrected body animation without changing the source mesh.",
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.SystemLibrary.quit_editor()


build_ururu_hair_clothing_dynamics_v636()
