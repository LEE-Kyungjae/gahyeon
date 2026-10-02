"""Reorient the immutable v059 OBJ from Y-up interchange into UE Z-up space."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def reorient_head_only_v060() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    source_obj = source / "gahyeon-metahuman-head-only-v059.obj"
    source_mtl = source_obj.with_suffix(".mtl")
    source_skin = source / "gahyeon-v059-skin-albedo.png"
    for path in (source_obj, source_mtl, source_skin, source / "manifest.json"):
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"invalid v059 lineage file: {path}")

    def digest(path: Path) -> str:
        value = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                value.update(block)
        return value.hexdigest()

    source_manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    expected = {item["uri"]: item["sha256"] for item in source_manifest["files"]}
    for path in (source_obj, source_mtl, source_skin):
        if expected.get(path.name) != digest(path):
            raise RuntimeError(f"v059 lineage checksum differs: {path}")

    target_obj = output / "gahyeon-metahuman-head-only-v060.obj"
    converted = []
    for line in source_obj.read_text(encoding="utf-8").splitlines():
        if line.startswith(("v ", "vn ")):
            prefix, x, y, z = line.split()[:4]
            # Existing Blender OBJ is (X, Z, -Y). UE needs (X, Y, Z).
            line = f"{prefix} {float(x):.6f} {-float(z):.6f} {float(y):.6f}"
        elif line.startswith("mtllib "):
            line = "mtllib gahyeon-metahuman-head-only-v060.mtl"
        converted.append(line)
    target_obj.write_text("\n".join(converted) + "\n", encoding="utf-8")

    target_mtl = output / "gahyeon-metahuman-head-only-v060.mtl"
    target_mtl.write_text(
        source_mtl.read_text(encoding="utf-8").replace(
            "gahyeon-v059-skin-albedo.png", "gahyeon-v060-skin-albedo.png"
        ),
        encoding="utf-8",
    )
    target_skin = output / "gahyeon-v060-skin-albedo.png"
    shutil.copyfile(source_skin, target_skin)

    mins, maxs = [float("inf")] * 3, [float("-inf")] * 3
    vertices = 0
    for line in target_obj.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            point = [float(value) for value in line.split()[1:4]]
            mins = [min(a, b) for a, b in zip(mins, point)]
            maxs = [max(a, b) for a, b in zip(maxs, point)]
            vertices += 1
    size = [high - low for low, high in zip(mins, maxs)]
    if not (size[2] > size[0] and size[2] > size[1]):
        raise RuntimeError(f"v060 is not Z-up after conversion: size={size}")

    files = (target_mtl, target_obj, target_skin)
    manifest = {
        "schemaVersion": 1,
        "characterId": "gahyeon",
        "iteration": "v060",
        "purpose": "unreal-z-up-head-only-metahuman-identity-solve-input",
        "source": {"manifest": str(source / "manifest.json"), "sha256": digest(source / "manifest.json")},
        "transform": {"from": "OBJ X,Z,-Y", "to": "UE X,Y,Z", "mapping": ["x", "-z", "y"]},
        "bounds": {"min": mins, "max": maxs, "size": size},
        "vertices": vertices,
        "status": "draft",
        "automaticApproval": False,
        "productionReady": False,
        "aaaQualityClaim": False,
        "files": [
            {"uri": path.name, "bytes": path.stat().st_size, "sha256": digest(path)}
            for path in files
        ],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(reorient_head_only_v060())
