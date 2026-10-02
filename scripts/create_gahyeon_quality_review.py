#!/usr/bin/env python3
"""Create a checksum-bound G1-G5 draft without silently skipping a gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import jsonschema

from verify_gahyeon_identity_reference import verify as verify_identity
from verify_gahyeon_modeling_input import verify as verify_modeling
from verify_gahyeon_g1_review import verify as verify_g1
from verify_gahyeon_g2_review import verify as verify_g2
from verify_gahyeon_g3_review import verify as verify_g3
from verify_gahyeon_g4_review import verify as verify_g4


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = {"G2": ("G1", "g1Review", verify_g1),
            "G3": ("G2", "g2Review", verify_g2),
            "G4": ("G3", "g3Review", verify_g3),
            "G5": ("G4", "g4Review", verify_g4)}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pack_local(output: Path, source: Path, label: str) -> Path:
    source = source.resolve()
    if source.parent != output.parent.resolve():
        raise ValueError(f"{label} must be in the same review workspace as the output")
    return source


def base(gate: str) -> dict:
    payload = {"schemaVersion": 1, "characterId": "gahyeon", "gate": gate,
               "status": "draft", "artifacts": [], "evidence": [],
               "findings": [], "approvals": []}
    if gate == "G1":
        payload.pop("artifacts")
        payload["sourceManifests"] = []
        payload["artistAuthoredRegions"] = [
            "rear-body", "rear-hair", "top-hair", "ears", "hands",
            "eye-interior", "mouth-interior", "rear-outfit"]
    elif gate == "G2":
        payload["topologyAudit"] = {"vertexCount": 0, "polygonCount": 0,
                                    "nonManifoldEdges": 0, "openBoundaryPolicy": "",
                                    "deformationTopologyReviewed": False}
    elif gate == "G3":
        payload["runtimeAudit"] = {"groomGroups": [], "lods": [],
                                   "observedBodyPenetrations": 0,
                                   "seatedPoseReviewed": False,
                                   "extremePoseReviewed": False}
    elif gate == "G4":
        payload["performanceAudit"] = {
            "visemes": [], "animationLayers": [], "neutralControlMaxAbs": 1,
            "lipSyncMaxAbsOffsetMs": 1000, "footSlideMaxCm": 100,
            "idleContinuesWithoutBackend": False,
            "reflexContinuesDuringCognition": False}
    elif gate == "G5":
        payload["runtimeAudit"] = {
            "testMachine": {"gpu": "NVIDIA GeForce GTX 1660 Ti", "vramMiB": 6144,
                            "resolution": "1920x1080", "engineVersion": "5.6",
                            "buildConfiguration": "Development"},
            "frameTimeP95Ms": 1000, "frameTimeP99Ms": 1000,
            "peakVramMiB": 999999, "loadTimeSeconds": 999999,
            "microphoneReflexP95Ms": 999999, "sttFirstPartialP95Ms": 999999,
            "behaviorTransitionP95Ms": 999999, "ttsFirstAudioP95Ms": 999999,
            "bargeInCancelP95Ms": 999999, "desktopWorksWithoutLookingGlass": False,
            "lookingGlassDisconnectPreservesWorld": False,
            "idleContinuesWithoutBackend": False, "reflexContinuesDuringCognition": False,
            "worldStateRestoredAfterRestart": False}
    return payload


def create(gate: str, output: Path, *, identity: Path | None = None,
           modeling: Path | None = None, previous: Path | None = None,
           allow_unapproved_predecessor: bool = False) -> dict:
    gate = gate.upper()
    if gate not in {"G1", "G2", "G3", "G4", "G5"}:
        raise ValueError(f"unsupported quality gate: {gate}")
    output = output.resolve()
    if output.exists():
        raise ValueError(f"refusing to overwrite existing review: {output}")
    if not output.parent.is_dir():
        raise ValueError(f"review workspace does not exist: {output.parent}")
    payload = base(gate)

    if gate == "G1":
        if identity is None or modeling is None or previous is not None:
            raise ValueError("G1 requires --identity and --modeling, and no --previous")
        identity = pack_local(output, identity, "identity manifest")
        modeling = pack_local(output, modeling, "modeling input")
        verify_identity(identity)
        verify_modeling(modeling)
        model_payload = json.loads(modeling.read_text(encoding="utf-8"))
        if (modeling.parent / model_payload["identityManifest"]).resolve() != identity:
            raise ValueError("modeling input does not bind the selected identity manifest")
        payload["sourceManifests"] = [
            {"kind": "identity-reference", "uri": identity.name, "sha256": digest(identity)},
            {"kind": "modeling-input", "uri": modeling.name, "sha256": digest(modeling)},
        ]
    else:
        if previous is None or identity is not None or modeling is not None:
            raise ValueError(f"{gate} requires --previous only")
        expected_gate, field, verifier = PREVIOUS[gate]
        previous = pack_local(output, previous, "predecessor review")
        previous_payload = json.loads(previous.read_text(encoding="utf-8"))
        if previous_payload.get("gate") != expected_gate:
            raise ValueError(f"{gate} requires a {expected_gate} predecessor")
        verifier(previous, require_approved=not allow_unapproved_predecessor)
        payload[field] = {"uri": previous.name, "sha256": digest(previous)}

    schema_path = ROOT / f"docs/contracts/gahyeon-{gate.lower()}-review.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()).validate(payload)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with output.open("x", encoding="utf-8") as handle:
        handle.write(serialized)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", required=True, choices=["G1", "G2", "G3", "G4", "G5"])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--identity", type=Path)
    parser.add_argument("--modeling", type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--allow-unapproved-predecessor", action="store_true",
                        help="planning only; production gate advancement requires approval")
    args = parser.parse_args()
    try:
        result = create(args.gate, args.output, identity=args.identity,
                        modeling=args.modeling, previous=args.previous,
                        allow_unapproved_predecessor=args.allow_unapproved_predecessor)
    except (ValueError, OSError, json.JSONDecodeError, jsonschema.ValidationError) as error:
        print(f"Quality review creation failed: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps({"created": str(args.output), "gate": result["gate"],
                      "status": result["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
