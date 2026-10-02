"""Add Stella's configured skirt chains to the retained full-hair Dynamics rig."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = "/Game/LivingCharacterPOC/v629/ControlRig/CR_Stella_FullHairDynamics_v629"
TARGET = "/Game/LivingCharacterPOC/v633/ControlRig/CR_Stella_HairClothingDynamics_v633"
PROFILE = ROOT / "character_pipeline/config/secondary-motion-profiles-v611.json"
OUTPUT = ROOT / "artifacts/living-character-poc-v633-stella-hair-clothing-dynamics/report.json"


def build_stella_hair_clothing_dynamics_v633():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError("refusing to overwrite immutable v633 output")
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    chains = profile["characters"]["stella-lily"]["groups"]["clothing"]["chains"]
    roots = [chain["root"] for chain in chains]
    if len(roots) != 6 or len(set(roots)) != len(roots):
        raise RuntimeError(f"unexpected Stella clothing roots: {roots}")
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET):
        raise RuntimeError("failed to duplicate v629 Control Rig")
    unreal.load_module("ControlRigDeveloper")
    rig = unreal.load_asset(TARGET)
    graph = rig.get_default_model()
    controller = rig.get_controller_by_name(graph.get_name())
    node = controller.add_unit_node_from_struct_path(
        "/Script/ControlRigDynamics.RigUnit_SpawnDynamicsChains",
        "Execute",
        unreal.Vector2D(1050.0, 0.0),
        "SpawnClothingChains",
        False,
    )
    if not node:
        raise RuntimeError("failed to add clothing dynamics node")
    roots_value = "(" + ",".join(f'(Type=Bone,Name="{root}")' for root in roots) + ")"
    properties = (
        "(Radius=4.000000,Mass=0.900000,MovementType=Simulated,"
        "GravityMultiplier=0.250000,Strength=2.500000,DampingRatio=0.780000,"
        "ExtraDamping=0.120000,bAccelerationMode=True,TargetVelocityInfluence=1.000000,"
        "TargetMode=0.500000,AngleLimit=14.000000,AngleLimitStrength=6.000000,"
        "Damping=0.000000,bScaleDampingByInverseMass=False,bCollideWithColliders=False)"
    )
    if not controller.set_pin_default_value("SpawnClothingChains.RootBones", roots_value, True, False, False):
        raise RuntimeError("failed to set clothing roots")
    if not controller.set_pin_default_value("SpawnClothingChains.ParticleProperties", properties, True, False, False):
        raise RuntimeError("failed to set clothing properties")
    if not controller.add_link(
        "SpawnHairChains.ExecutePin", "SpawnClothingChains.ExecutePin", False
    ):
        raise RuntimeError("failed to connect clothing construction")
    rig.recompile_vm()
    unreal.BlueprintEditorLibrary.compile_blueprint(rig)
    if not unreal.EditorAssetLibrary.save_asset(TARGET, only_if_is_dirty=False):
        raise RuntimeError("failed to save v633 Control Rig")
    report = {
        "schemaVersion": 1,
        "iteration": "v633",
        "status": "draft-hair-clothing-control-rig-ready",
        "source": SOURCE,
        "controlRig": TARGET,
        "hairChainCount": 11,
        "clothingChainCount": len(chains),
        "clothingRoots": roots,
        "clothingParticleProperties": properties,
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.SystemLibrary.quit_editor()


build_stella_hair_clothing_dynamics_v633()
