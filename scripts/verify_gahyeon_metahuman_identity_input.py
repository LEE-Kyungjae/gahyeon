#!/usr/bin/env python3
"""Verify the portable Mesh-to-MetaHuman input package without claiming a solve."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    root = args.package.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("claim") != "neutral-static-mesh-input-not-metahuman-not-dna":
        raise SystemExit("package makes an invalid MetaHuman completion claim")
    if manifest.get("scope") != "head-neck-and-eyes-only":
        raise SystemExit("solve package does not declare a head-only identity scope")
    if (manifest.get("mesh", {}).get("vertices", 0) < 4_000
            or manifest.get("mesh", {}).get("polygons", 0) < 4_000):
        raise SystemExit("solve mesh is unexpectedly incomplete")
    if manifest.get("mesh", {}).get("sourceObjects") != [
        "Gahyeon_G1_BodyFace_CC0", "Gahyeon_G1_Eyes_high-poly"
    ]:
        raise SystemExit("solve package contains unreviewed render-helper geometry")
    topology = manifest.get("topologyPolicy", {})
    if (topology.get("connectedComponents") != 5
            or topology.get("boundaryEdges") != 122
            or topology.get("boundaryLoops") != 5
            or not topology.get("auditSha256")
            or "semantic iris render helpers excluded" not in topology.get("openBoundaryPolicy", "")):
        raise SystemExit("solve package topology/open-boundary policy is missing or differs")
    if not manifest.get("sourceBlendSha256") or not manifest.get("exporterSha256"):
        raise SystemExit("solve package lacks source/exporter lineage")
    materials = manifest.get("mesh", {}).get("materials", [])
    if not any("body" in name.lower() for name in materials):
        raise SystemExit("skin material is not separated")
    if not any("high-poly" in name.lower() for name in materials):
        raise SystemExit("sclera material is not separated")
    names = {record["uri"] for record in manifest.get("files", [])}
    required = {
        "gahyeon-metahuman-identity-v79.obj",
        "gahyeon-metahuman-identity-v79.mtl",
        "gahyeon-v79-skin-albedo.png",
        "gahyeon-v79-eye-albedo.png",
    }
    if names != required:
        raise SystemExit(f"unexpected package inventory: {sorted(names)}")
    for record in manifest["files"]:
        path = root / record["uri"]
        if not path.is_file() or path.stat().st_size != record["bytes"]:
            raise SystemExit(f"missing or resized package file: {path.name}")
        if digest(path) != record["sha256"]:
            raise SystemExit(f"checksum mismatch: {path.name}")
    mtl = (root / "gahyeon-metahuman-identity-v79.mtl").read_text(encoding="utf-8")
    if "map_Kd gahyeon-v79-skin-albedo.png" not in mtl:
        raise SystemExit("skin albedo is not connected in MTL")
    if "map_Kd gahyeon-v79-eye-albedo.png" not in mtl:
        raise SystemExit("eye albedo is not connected in MTL")
    if "brown_eye.png" in mtl:
        raise SystemExit("MTL retains a stale eye texture reference")
    print(json.dumps({
        "valid": True,
        "claim": manifest["claim"],
        "vertices": manifest["mesh"]["vertices"],
        "polygons": manifest["mesh"]["polygons"],
        "files": len(manifest["files"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
