"""Fail-closed validation for the v488 Hayley living-character motion library."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MANIFEST = ROOT / "character_pipeline/config/hayley-living-character-v488.json"
OUTPUT = ROOT / "artifacts/living-character-poc-v489-hayley-motion-manifest-verification/report.json"


def verify_hayley_motion_manifest_v489():
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    skeleton = unreal.load_asset(manifest["character"]["skeleton"])
    production_mesh = unreal.load_asset(manifest["character"]["productionMesh"])
    face_mesh = unreal.load_asset(manifest["character"]["faceQaMesh"])
    if skeleton is None or production_mesh is None or face_mesh is None:
        raise RuntimeError("one or more Hayley character dependencies are unavailable")
    if production_mesh.get_editor_property("skeleton") != skeleton or face_mesh.get_editor_property("skeleton") != skeleton:
        raise RuntimeError("Hayley production and face-QA meshes must share the declared skeleton")
    records = []
    for motion_id, definition in manifest["motions"].items():
        animation = unreal.load_asset(definition["asset"])
        evidence = ROOT / definition["evidence"]
        if not isinstance(animation, unreal.AnimSequence):
            raise RuntimeError(f"motion is not an AnimSequence: {motion_id}={definition['asset']}")
        if animation.get_editor_property("skeleton") != skeleton:
            raise RuntimeError(f"motion skeleton mismatch: {motion_id}")
        if not evidence.is_file() or evidence.stat().st_size < 24:
            raise RuntimeError(f"missing motion evidence: {motion_id}={evidence}")
        records.append({
            "id": motion_id, "asset": definition["asset"],
            "durationSeconds": float(animation.get_play_length()),
            "sampledKeys": int(animation.get_editor_property("number_of_sampled_keys")),
            "evidence": str(evidence), "evidenceBytes": evidence.stat().st_size,
        })
    face_animation = unreal.load_asset(manifest["face"]["calibrationAsset"])
    face_evidence = ROOT / manifest["face"]["evidence"]
    if not isinstance(face_animation, unreal.AnimSequence) or face_animation.get_editor_property("skeleton") != skeleton:
        raise RuntimeError("face calibration animation is missing or has the wrong skeleton")
    if not face_evidence.is_file() or face_evidence.stat().st_size < 24:
        raise RuntimeError("face calibration evidence is missing")
    report = {
        "schemaVersion": 1, "iteration": "v489", "status": "verified-draft-motion-library",
        "manifest": str(MANIFEST), "productionMesh": manifest["character"]["productionMesh"],
        "faceQaMesh": manifest["character"]["faceQaMesh"], "skeleton": manifest["character"]["skeleton"],
        "motionCount": len(records), "motions": records,
        "faceCalibration": {"asset": manifest["face"]["calibrationAsset"], "evidence": str(face_evidence)},
        "knownGaps": manifest["knownGaps"], "humanApproved": False, "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_MOTION_MANIFEST_VERIFIED=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


verify_hayley_motion_manifest_v489()
