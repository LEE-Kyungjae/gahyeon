#!/usr/bin/env python3
"""Verify the sealed FaceBuilder → UE 5.8 conform package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest_v160(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def verify_facebuilder_conform_input(package_dir: Path) -> dict:
    root = package_dir.resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("missing manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1 or manifest.get("iteration") != "v159":
        raise ValueError("unsupported FaceBuilder conform manifest")
    if manifest.get("purpose") != "ue58-metahuman-from-custom-mesh-input":
        raise ValueError("package purpose is not UE 5.8 Custom Mesh conform")

    topology = manifest.get("topology", {})
    if topology.get("vertices", 0) < 1_000 or topology.get("polygons", 0) < 1_000:
        raise ValueError("head topology is unexpectedly sparse")
    if topology.get("nonManifoldEdgesOverTwoFaces") != 0:
        raise ValueError("head contains over-connected non-manifold edges")
    if topology.get("looseEdges") != 0:
        raise ValueError("head contains loose edges")

    cameras = manifest.get("canonicalCameras", [])
    if len(cameras) != 4:
        raise ValueError(f"expected four canonical cameras, found {len(cameras)}")
    if any(camera.get("pinCount", 0) < 4 for camera in cameras):
        raise ValueError("one or more canonical cameras lacks a solved pin set")
    image_paths = [camera.get("imagePath") for camera in cameras]
    if len(set(image_paths)) != 4 or any(not value for value in image_paths):
        raise ValueError("canonical camera image lineage is incomplete or duplicated")

    declared = manifest.get("files", [])
    by_uri = {entry.get("uri"): entry for entry in declared}
    if not {"gahyeon-facebuilder-v159.obj", "gahyeon-facebuilder-v159.fbx"} <= set(by_uri):
        raise ValueError("package must contain both OBJ and FBX mesh payloads")
    for uri, entry in by_uri.items():
        if not uri or Path(uri).name != uri:
            raise ValueError(f"unsafe payload URI: {uri!r}")
        path = root / uri
        if not path.is_file():
            raise ValueError(f"missing payload: {uri}")
        if path.stat().st_size != entry.get("bytes") or digest_v160(path) != entry.get("sha256"):
            raise ValueError(f"payload lineage mismatch: {uri}")

    claims = manifest.get("claims", {})
    if claims.get("identityApproved") is not False:
        raise ValueError("reconstruction package must not self-approve identity")
    if claims.get("metaHumanConformed") is not False:
        raise ValueError("pre-conform package must not claim MetaHuman conform")
    if claims.get("productionReady") is not False:
        raise ValueError("pre-conform package must not claim production readiness")
    return {
        "valid": True,
        "iteration": "v159",
        "payloadCount": len(declared),
        "cameraCount": len(cameras),
        "minimumPinCount": min(camera["pinCount"] for camera in cameras),
        "identityApproved": False,
        "metaHumanConformed": False,
        "productionReady": False,
    }


def main_v160() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_facebuilder_conform_input(args.package_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main_v160())
