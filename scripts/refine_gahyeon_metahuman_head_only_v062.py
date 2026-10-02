#!/usr/bin/env python3
"""Create a conservative landmark-driven v062 MetaHuman scan refinement."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "artifacts/gahyeon-ch/metahuman-identity-head-only-v060"
OUTPUT_DIR = ROOT / "artifacts/gahyeon-ch/metahuman-identity-head-only-v062"
SOURCE_OBJ = SOURCE_DIR / "gahyeon-metahuman-head-only-v060.obj"
OUTPUT_OBJ = OUTPUT_DIR / "gahyeon-metahuman-head-only-v062.obj"


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def refine_head_only_v062() -> dict:
    if OUTPUT_DIR.exists():
        raise RuntimeError(f"refusing to overwrite v062 output: {OUTPUT_DIR}")
    if not SOURCE_OBJ.is_file():
        raise RuntimeError(f"missing v060 source OBJ: {SOURCE_OBJ}")
    OUTPUT_DIR.mkdir(parents=True)

    source_mtl = SOURCE_DIR / "gahyeon-metahuman-head-only-v060.mtl"
    output_mtl = OUTPUT_DIR / "gahyeon-metahuman-head-only-v062.mtl"
    source_skin = SOURCE_DIR / "gahyeon-v060-skin-albedo.png"
    output_skin = OUTPUT_DIR / "gahyeon-v062-skin-albedo.png"
    shutil.copy2(source_skin, output_skin)
    output_mtl.write_text(
        source_mtl.read_text(encoding="utf-8").replace(source_skin.name, output_skin.name),
        encoding="utf-8",
    )

    bounds_before = [[float("inf")] * 3, [float("-inf")] * 3]
    bounds_after = [[float("inf")] * 3, [float("-inf")] * 3]
    vertex_count = 0
    output_lines: list[str] = []
    for line in SOURCE_OBJ.read_text(encoding="utf-8").splitlines():
        if line.startswith("mtllib "):
            output_lines.append(f"mtllib {output_mtl.name}")
            continue
        if not line.startswith("v "):
            output_lines.append(line)
            continue
        fields = line.split()
        x, y, z = map(float, fields[1:4])
        source = (x, y, z)

        # Preserve the neck seam. Narrow the front facial envelope more than the
        # rear skull so eye/mouth widths gain proportion without flattening depth.
        neck_weight = smoothstep((z - 140.0) / 5.0)
        # OBJ depth is sign-flipped by Unreal's import path. The facial surface
        # is therefore at negative OBJ Y even though the solve sees positive Y.
        front_weight = smoothstep((-y - 1.0) / 13.0)
        horizontal_scale = 1.0 - neck_weight * (0.06 + 0.10 * front_weight)
        x *= horizontal_scale

        # v061 measured a +30–42% lower-face excess. Compress only below the
        # mouth/nose transition and keep the neck boundary continuous.
        if z < 153.5:
            lower_weight = smoothstep((z - 141.0) / 12.5) * front_weight
            z += (153.5 - z) * 0.14 * lower_weight

        # The face width/height ratio was +24%. Add height primarily above the
        # eye line instead of lengthening the already excessive lower face.
        if z > 157.5:
            upper_weight = smoothstep((z - 157.5) / 10.0)
            z += (z - 157.5) * 0.12 * upper_weight

        refined = (x, y, z)
        for axis in range(3):
            bounds_before[0][axis] = min(bounds_before[0][axis], source[axis])
            bounds_before[1][axis] = max(bounds_before[1][axis], source[axis])
            bounds_after[0][axis] = min(bounds_after[0][axis], refined[axis])
            bounds_after[1][axis] = max(bounds_after[1][axis], refined[axis])
        output_lines.append(f"v {x:.9f} {y:.9f} {z:.9f}" + (" " + " ".join(fields[4:]) if len(fields) > 4 else ""))
        vertex_count += 1

    OUTPUT_OBJ.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    topology_audit = json.loads((SOURCE_DIR / "topology-audit.json").read_text(encoding="utf-8"))
    topology_audit.update({
        "sourceIteration": "v060",
        "iteration": "v062",
        "vertexCount": vertex_count,
        "topologyChanged": False,
        "boundsBefore": bounds_before,
        "boundsAfter": bounds_after,
    })
    (OUTPUT_DIR / "topology-audit.json").write_text(
        json.dumps(topology_audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "schemaVersion": 1,
        "status": "draft",
        "iteration": "v062",
        "source": {"file": str(SOURCE_OBJ.relative_to(ROOT)), "sha256": sha256(SOURCE_OBJ)},
        "hypothesis": "The v061 likeness fails because its frontal envelope is too wide, upper face too short, and lower face too long.",
        "action": {
            "frontFaceHorizontalScale": 0.84,
            "rearSkullHorizontalScale": 0.94,
            "lowerFaceCompression": 0.14,
            "upperCraniumExtension": 0.12,
            "neckSeamPreserved": True,
        },
        "expectedResult": "Reduced face aspect, larger relative eye/mouth widths, and a shorter mouth-to-chin region without topology change.",
        "actualResult": None,
        "decision": "pending MetaHuman solve and fixed-camera comparison",
        "files": [
            {"file": OUTPUT_OBJ.name, "sha256": sha256(OUTPUT_OBJ)},
            {"file": output_mtl.name, "sha256": sha256(output_mtl)},
            {"file": output_skin.name, "sha256": sha256(output_skin)},
        ],
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"ready": True, "vertices": vertex_count, "boundsAfter": bounds_after}


if __name__ == "__main__":
    print(json.dumps(refine_head_only_v062(), ensure_ascii=False))
