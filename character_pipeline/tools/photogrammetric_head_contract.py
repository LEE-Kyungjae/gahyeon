#!/usr/bin/env python3
"""Build and validate the coherent-head input boundary for MetaHuman conform."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def build_photogrammetric_head_job(config: dict[str, Any], identity_path: Path) -> dict[str, Any]:
    identity = read_object(identity_path)
    if (config.get("schemaVersion") != 1 or
            config.get("stage") != "coherent-photogrammetric-head-reconstruction"):
        raise ValueError("unsupported photogrammetric head contract")
    if identity.get("characterId") != config.get("characterId"):
        raise ValueError("identity authority differs from reconstruction contract")
    by_index = {item["index"]: item for item in identity.get("references", [])}
    source_root = identity_path.parent
    records = []
    for index in config.get("requiredCanonicalIndices", []):
        item = by_index.get(index)
        if not item or item.get("identityAuthority") != "canonical" or item.get("kind") != "face":
            raise ValueError(f"missing canonical face reference {index}")
        source = source_root / item["file"]
        if not source.is_file() or file_sha256(source) != item.get("sha256"):
            raise ValueError(f"canonical reference checksum differs: {index}")
        records.append({
            "index": index,
            "view": item["view"],
            "path": str(source.resolve()),
            "sha256": item["sha256"],
            "role": "identity-authority"
        })
    if len({record["view"] for record in records}) < 3:
        raise ValueError("coherent reconstruction needs front, oblique and profile coverage")
    return {
        "schemaVersion": 1,
        "characterId": config["characterId"],
        "iteration": config["iteration"],
        "stage": config["stage"],
        "state": "tool-installation-or-license-activation-required",
        "preferredTool": config["preferredTool"],
        "allowedTools": config["allowedTools"],
        "identityAuthority": {
            "path": str(identity_path.resolve()),
            "sha256": file_sha256(identity_path)
        },
        "references": records,
        "reconstructionRules": {
            "neutralExpressionRequired": config["neutralExpressionRequired"],
            "hairGeometryForbidden": config["hairGeometryForbidden"],
            "singleCoherentHeadSurfaceRequired": True,
            "preserveIdentityWithoutBeautification": True
        },
        "requiredOutput": config["requiredOutput"],
        "target": config["target"],
        "hypothesis": "A coherent multi-view head fit preserves jaw, skull and profile identity that 2D-to-PCA landmark approximation lost.",
        "automaticApproval": False,
        "productionMeshAllowed": False
    }


def validate_photogrammetric_head_job(job: dict[str, Any]) -> dict[str, Any]:
    if (job.get("schemaVersion") != 1 or
            job.get("stage") != "coherent-photogrammetric-head-reconstruction" or
            job.get("automaticApproval") is not False or
            job.get("productionMeshAllowed") is not False):
        raise ValueError("photogrammetric head job overclaims readiness")
    identity = job.get("identityAuthority", {})
    identity_path = Path(identity.get("path", ""))
    if (not identity_path.is_absolute() or not identity_path.is_file() or
            file_sha256(identity_path) != identity.get("sha256")):
        raise ValueError("identity authority lineage differs")
    references = job.get("references", [])
    if len(references) < 4 or len({item.get("view") for item in references}) < 3:
        raise ValueError("insufficient multi-view identity coverage")
    for item in references:
        source = Path(item.get("path", ""))
        if (not source.is_absolute() or not source.is_file() or
                file_sha256(source) != item.get("sha256") or
                item.get("role") != "identity-authority"):
            raise ValueError(f"reference lineage differs: {item.get('index')}")
    target = job.get("target", {})
    if (target.get("engine") != "Unreal Engine 5.8" or
            target.get("operation") != "MetaHuman From Custom Mesh" or
            target.get("exactPortraitCameraRequired") is not True or
            target.get("finalTopology") != "MetaHuman"):
        raise ValueError("MetaHuman custom-mesh target contract differs")
    return {"valid": True, "state": job["state"], "references": len(references)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path,
                        default=Path("character_pipeline/config/photogrammetric_head.json"))
    parser.add_argument("--identity", type=Path,
                        default=Path("artifacts/gahyeon-ch/identity-reference.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if args.verify:
        result = validate_photogrammetric_head_job(read_object(output))
    else:
        if output.exists():
            raise SystemExit(f"refusing to overwrite: {output}")
        result = build_photogrammetric_head_job(
            read_object(args.config.resolve()), args.identity.resolve())
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
