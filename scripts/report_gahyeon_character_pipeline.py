#!/usr/bin/env python3
"""Report evidence-backed character production progress without counting templates as work."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from verify_gahyeon_identity_reference import verify as verify_identity
from verify_gahyeon_modeling_input import verify as verify_modeling
from verify_gahyeon_g1_review import verify as verify_g1
from verify_gahyeon_g2_review import verify as verify_g2
from verify_gahyeon_g3_review import verify as verify_g3
from verify_gahyeon_g4_review import verify as verify_g4
from verify_gahyeon_g5_review import verify as verify_g5
from verify_gahyeon_hero_asset import verify as verify_hero


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE = ROOT / "artifacts/gahyeon-ch"
VERIFIERS = {"G1": verify_g1, "G2": verify_g2, "G3": verify_g3,
             "G4": verify_g4, "G5": verify_g5}
EXPECTED_MISSING = {"G1": 15, "G2": 21, "G3": 23, "G4": 27, "G5": 21}
EXPECTED_ERRORS = (ValueError, OSError, KeyError, TypeError,
                   json.JSONDecodeError, jsonschema.ValidationError)
MODEL_ARTIFACT_SUFFIXES = {
    ".blend", ".fbx", ".glb", ".gltf", ".usd", ".usdz", ".uasset", ".ztl"
}


def report(workspace: Path, *, hero_manifest: Path | None = None) -> dict:
    workspace = workspace.resolve()
    result = {
        "schemaVersion": 1,
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "workspace": str(workspace),
        "source": {"status": "missing"},
        "authoring": {
            "candidateModelArtifactCount": 0,
            "candidateModelArtifacts": [],
            "hasCandidateModel": False,
        },
        "gates": [],
        "hero": {"status": "not-started", "ready": False},
    }

    model_artifacts = sorted(
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file() and path.suffix.lower() in MODEL_ARTIFACT_SUFFIXES
    )
    result["authoring"] = {
        "candidateModelArtifactCount": len(model_artifacts),
        "candidateModelArtifacts": model_artifacts,
        "hasCandidateModel": bool(model_artifacts),
    }

    identity = workspace / "identity-reference.json"
    modeling = workspace / "modeling-input.json"
    source_valid = False
    if identity.is_file() and modeling.is_file():
        try:
            source_count, face_count, body_count = verify_identity(identity)
            canonical_count, anchor_count = verify_modeling(modeling)
            result["source"] = {
                "status": "valid", "classifiedReferences": source_count,
                "canonicalReferences": canonical_count, "canonicalFace": face_count,
                "canonicalFullBody": body_count, "anchorAssignments": anchor_count,
            }
            source_valid = True
        except EXPECTED_ERRORS as error:
            result["source"] = {"status": "invalid", "error": str(error)}
    elif identity.is_file() or modeling.is_file():
        result["source"] = {"status": "incomplete",
                            "missing": [name for name, path in
                                        (("identity-reference.json", identity),
                                         ("modeling-input.json", modeling)) if not path.is_file()]}

    first_incomplete = None
    all_approved = source_valid
    for gate, verifier in VERIFIERS.items():
        actual = workspace / f"{gate.lower()}-review.json"
        template = workspace / f"{gate.lower()}-review-template.json"
        item = {"gate": gate, "status": "not-started", "review": str(actual),
                "templateAvailable": template.is_file(),
                "requiredEvidence": EXPECTED_MISSING[gate], "evidenceCount": 0,
                "missingEvidence": EXPECTED_MISSING[gate]}
        if actual.is_file():
            try:
                verified = verifier(actual)
                item.update({"status": verified["status"],
                             "evidenceCount": verified["evidenceCount"],
                             "missingEvidence": len(verified["missingRequiredViews"])})
            except EXPECTED_ERRORS as error:
                item.update({"status": "invalid", "error": str(error)})
        if item["status"] != "approved":
            all_approved = False
            if first_incomplete is None:
                first_incomplete = gate
        result["gates"].append(item)

    hero_path = (hero_manifest.resolve() if hero_manifest else workspace / "hero-asset.json")
    if hero_path.is_file():
        try:
            verified = verify_hero(hero_path, require_approved=True,
                                   renderer="hero-engine", verify_files=True)
            result["hero"] = {"status": verified["status"], "ready": True,
                              "manifest": str(hero_path)}
        except EXPECTED_ERRORS as error:
            result["hero"] = {"status": "invalid", "ready": False,
                              "manifest": str(hero_path), "error": str(error)}

    if not source_valid:
        result["activeGate"] = "G0"
    elif first_incomplete is not None:
        result["activeGate"] = first_incomplete
    elif all_approved and not result["hero"]["ready"]:
        result["activeGate"] = "HERO_PACKAGE"
    else:
        result["activeGate"] = "COMPLETE"
    result["qualityChainApproved"] = all_approved
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--hero-manifest", type=Path)
    args = parser.parse_args()
    print(json.dumps(report(args.workspace, hero_manifest=args.hero_manifest),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
