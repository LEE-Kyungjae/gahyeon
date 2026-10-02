#!/usr/bin/env python3
"""Fail closed when a donor outfit is too weak for MetaHuman weight transfer."""

import argparse
import json
from pathlib import Path


MIN_VERTICES_PER_MAJOR_PIECE = 2000
MIN_VERTEX_GROUPS = 4


def verify(extraction, evaluation=None):
    defects = []
    if extraction.get("state") != "extracted-donor-candidate":
        defects.append("extraction state is not extracted-donor-candidate")
    if extraction.get("identityAuthority") is not False:
        defects.append("donor must explicitly be non-authoritative for identity")
    source = extraction.get("source")
    if not isinstance(source, dict) or not source.get("file") or len(source.get("sha256", "")) != 64:
        defects.append("source provenance file and SHA-256 are required")
    objects = extraction.get("objects", {})
    for role in ("top", "bottom"):
        piece = objects.get(role)
        if not isinstance(piece, dict):
            defects.append(f"missing separate {role} object")
            continue
        if int(piece.get("vertices", 0)) < MIN_VERTICES_PER_MAJOR_PIECE:
            defects.append(
                f"{role} has {piece.get('vertices', 0)} vertices; minimum is {MIN_VERTICES_PER_MAJOR_PIECE}"
            )
        if int(piece.get("vertexGroups", 0)) < MIN_VERTEX_GROUPS:
            defects.append(f"{role} lacks usable deformation weight groups")
        materials = piece.get("materials")
        if not isinstance(materials, list) or not any(materials):
            defects.append(f"{role} lacks a material assignment")
    rig = objects.get("rig", {})
    if int(rig.get("deformBones", 0)) < 1:
        defects.append("donor rig has no deform bones")
    if extraction.get("productionReady") is not False:
        defects.append("extraction must not claim production readiness")

    render_retained = None
    if evaluation is not None:
        render_retained = evaluation.get("retainForWeightTransfer") is True
        if evaluation.get("pipelinePocSucceeded") is not True:
            defects.append("render pipeline POC did not succeed")
        if not render_retained:
            defects.append("render evaluation rejected weight transfer")

    return {
        "schemaVersion": 1,
        "readyForStaticConform": not defects,
        "readyForWeightTransfer": not defects and render_retained is True,
        "thresholds": {
            "minVerticesPerMajorPiece": MIN_VERTICES_PER_MAJOR_PIECE,
            "minVertexGroups": MIN_VERTEX_GROUPS,
        },
        "defects": defects,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extraction", required=True, type=Path)
    parser.add_argument("--evaluation", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    extraction = json.loads(args.extraction.read_text(encoding="utf-8"))
    evaluation = (
        json.loads(args.evaluation.read_text(encoding="utf-8")) if args.evaluation else None
    )
    result = verify(extraction, evaluation)
    rendered = json.dumps(result, indent=2)
    if args.output:
        if args.output.exists():
            raise RuntimeError(f"refusing to overwrite donor gate report: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["readyForStaticConform"] else 1)


if __name__ == "__main__":
    main()
