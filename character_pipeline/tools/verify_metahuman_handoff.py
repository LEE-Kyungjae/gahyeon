#!/usr/bin/env python3
"""Verify immutable input lineage for a future Unreal MetaHuman Identity solve."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(handoff: Path, uri: str) -> Path:
    result = (handoff.parent / uri).resolve()
    if not result.is_file():
        raise ValueError(f"missing handoff input: {result}")
    return result


def verify(handoff: Path) -> dict:
    value = json.loads(handoff.read_text(encoding="utf-8"))
    if value.get("schemaVersion") != 1 or value.get("stage") != "metahuman-identity-solve":
        raise ValueError("unsupported handoff schema/stage")
    source = value.get("input", {})
    if source.get("claim") != "neutral-static-mesh-input-not-metahuman-not-dna":
        raise ValueError("handoff overclaims the source")
    if source.get("scope") != "head-neck-and-eyes-only":
        raise ValueError("handoff must use the clean head-only package")
    for uri_key, sha_key in (("manifest", "manifestSha256"), ("mesh", "meshSha256")):
        path = resolve(handoff, source[uri_key])
        if digest(path) != source[sha_key]:
            raise ValueError(f"checksum mismatch: {uri_key}")
    package = json.loads(resolve(handoff, source["manifest"]).read_text(encoding="utf-8"))
    topology = package.get("topologyPolicy", {})
    declared = source.get("topology", {})
    if (package.get("scope") != source["scope"]
            or package.get("claim") != source["claim"]
            or package.get("mesh", {}).get("sourceObjects") != [
                "Gahyeon_G1_BodyFace_CC0", "Gahyeon_G1_Eyes_high-poly"]
            or declared != {"connectedComponents": 5, "boundaryEdges": 122, "boundaryLoops": 5}
            or any(topology.get(key) != value for key, value in declared.items())
            or not package.get("sourceBlendSha256")
            or not package.get("exporterSha256")):
        raise ValueError("handoff package lineage or reviewed topology policy differs")
    authority = value.get("referenceAuthority", {})
    if digest(resolve(handoff, authority["manifest"])) != authority["manifestSha256"]:
        raise ValueError("reference authority checksum mismatch")
    capture = value.get("captureProtocol", {})
    profile = json.loads(resolve(handoff, capture["profile"]).read_text(encoding="utf-8"))
    if capture.get("resolution") != [1440, 2560] or profile.get("profileId") != "looking-glass-go":
        raise ValueError("handoff is not bound to Looking Glass Go")
    if capture.get("quiltViewCount") != 66 or capture.get("quiltRequiresConnectedCalibration") is not True:
        raise ValueError("invalid quilt policy")
    if len(capture.get("views", [])) != 5 or len(set(capture["views"])) != 5:
        raise ValueError("five unique identity views are required")
    if not value.get("forbiddenClaimsUntilEvidence"):
        raise ValueError("fail-closed claim policy is missing")
    return {"valid": True, "iteration": value["iteration"], "views": 5,
            "displayProfile": "looking-glass-go", "state": value["state"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("handoff", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.handoff.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
