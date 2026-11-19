"""Expand the validated Stella Dynamics scaffold to all configured hair chains."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = "/Game/LivingCharacterPOC/v623/ControlRig/CR_Stella_HairDynamics_Layered_v623"
TARGET = "/Game/LivingCharacterPOC/v629/ControlRig/CR_Stella_FullHairDynamics_v629"
PROFILE = ROOT / "character_pipeline/config/secondary-motion-profiles-v611.json"
OUTPUT = ROOT / "artifacts/living-character-poc-v629-stella-full-hair-dynamics/report.json"


def build_stella_full_hair_dynamics_rig_v629():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError("refusing to overwrite immutable v629 output")
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    chains = profile["characters"]["stella-lily"]["groups"]["hair"]["chains"]
    roots = [chain["root"] for chain in chains]
    if len(roots) != 11 or len(set(roots)) != len(roots):
        raise RuntimeError(f"unexpected Stella hair roots: {roots}")
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET):
        raise RuntimeError("failed to duplicate v623 Control Rig")
    unreal.load_module("ControlRigDeveloper")
    rig = unreal.load_asset(TARGET)
    graph = rig.get_default_model()
    controller = rig.get_controller_by_name(graph.get_name())
    root_value = "(" + ",".join(f'(Type=Bone,Name="{root}")' for root in roots) + ")"
    particle_properties = (
        "(Radius=3.000000,Mass=0.600000,MovementType=Simulated,"
        "GravityMultiplier=0.150000,Strength=1.500000,DampingRatio=0.650000,"
        "ExtraDamping=0.080000,bAccelerationMode=True,TargetVelocityInfluence=1.000000,"
        "TargetMode=0.350000,AngleLimit=18.000000,AngleLimitStrength=4.000000,"
        "Damping=0.000000,bScaleDampingByInverseMass=False,bCollideWithColliders=False)"
    )
    root_set = controller.set_pin_default_value(
        "SpawnHairChains.RootBones", root_value, True, False, False
    )
    properties_set = controller.set_pin_default_value(
        "SpawnHairChains.ParticleProperties", particle_properties, True, False, False
    )
    if not root_set or not properties_set:
        raise RuntimeError("failed to configure full Stella hair dynamics")
    rig.recompile_vm()
    unreal.BlueprintEditorLibrary.compile_blueprint(rig)
    if not unreal.EditorAssetLibrary.save_asset(TARGET, only_if_is_dirty=False):
        raise RuntimeError("failed to save v629 Control Rig")
    report = {
        "schemaVersion": 1,
        "iteration": "v629",
        "status": "draft-full-hair-control-rig-ready",
        "source": SOURCE,
        "controlRig": TARGET,
        "profile": str(PROFILE.relative_to(ROOT)),
        "hairChainCount": len(chains),
        "hairRoots": roots,
        "particleProperties": particle_properties,
        "hypothesis": "All configured Stella hair roots with conservative lag produce visible secondary motion while preserving body animation.",
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.SystemLibrary.quit_editor()


build_stella_full_hair_dynamics_rig_v629()
