#!/usr/bin/env python3
"""Verify that the G1 modeling handoff only references canonical source evidence."""

import argparse
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "artifacts/gahyeon-ch/modeling-input.json"
SCHEMA = ROOT / "docs/contracts/gahyeon-modeling-input.schema.json"

FACE_ANCHORS = {
    "neutralFaceFront", "faceThreeQuarter", "faceLeftProfile",
    "faceRightProfile", "verticalFaceShape", "expressionRange", "hairFront",
}
BODY_ANCHORS = {"bodyFront", "bodyProfile", "bodyThreeQuarter", "bodyMotion"}
FACE_GEOMETRY = {
    "primaryFaceGeometry", "angleCrossChecks", "expressionOnly", "styleAndHairOnly",
}
BODY_GEOMETRY = {"primaryBodyGeometry", "bodyMotionAndOutfitOnly"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify(modeling_path: Path) -> tuple[int, int]:
    modeling = load_json(modeling_path)
    jsonschema.Draft202012Validator(load_json(SCHEMA)).validate(modeling)

    identity_path = (modeling_path.parent / modeling["identityManifest"]).resolve()
    try:
        identity_path.relative_to(modeling_path.parent.resolve())
    except ValueError as error:
        raise ValueError("identity manifest must stay inside the canonical pack") from error
    identity = load_json(identity_path)
    if identity.get("characterId") != modeling["characterId"]:
        raise ValueError("characterId does not match the identity manifest")
    if identity.get("canonicalSource") != "user-provided-originals":
        raise ValueError("G1 geometry must be rooted in user-provided originals")

    references = {item["index"]: item for item in identity.get("references", [])}
    if len(references) != len(identity.get("references", [])):
        raise ValueError("identity manifest contains duplicate indices")

    def require(indices: list[int], allowed_kinds: set[str], label: str) -> None:
        for index in indices:
            reference = references.get(index)
            if reference is None:
                raise ValueError(f"{label} references unknown canonical index {index}")
            if reference.get("identityAuthority") != "canonical":
                raise ValueError(f"{label} references non-canonical index {index}")
            if reference.get("kind") not in allowed_kinds:
                raise ValueError(f"{label} uses incompatible {reference.get('kind')} index {index}")

    for label, indices in modeling["anchors"].items():
        kinds = {"face", "upper-body"} if label in FACE_ANCHORS else (
            {"full-body"} if label in BODY_ANCHORS else {"face", "upper-body", "full-body"})
        require(indices, kinds, f"anchors.{label}")

    authority = modeling["geometryAuthority"]
    require([authority["masterNeutralFace"]], {"face", "upper-body"}, "masterNeutralFace")
    for label in FACE_GEOMETRY:
        require(authority[label], {"face", "upper-body"}, label)
    for label in BODY_GEOMETRY:
        require(authority[label], {"full-body"}, label)
    if authority["masterNeutralFace"] not in authority["primaryFaceGeometry"]:
        raise ValueError("masterNeutralFace must be included in primaryFaceGeometry")

    neutral = set(authority["primaryFaceGeometry"])
    non_geometry = set(authority["expressionOnly"]) | set(authority["styleAndHairOnly"])
    if neutral & non_geometry:
        raise ValueError("expression/style-only evidence cannot define neutral face geometry")
    if any(model.get("heroReferenceAllowed") for model in identity.get("auxiliaryModels", [])):
        raise ValueError("LoRA output cannot be promoted into the G1 hero authority")
    return len(references), sum(len(value) for value in modeling["anchors"].values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    references, anchors = verify(args.input.resolve())
    print(f"modeling input OK: {references} canonical references, {anchors} anchor assignments")


if __name__ == "__main__":
    main()
