#!/usr/bin/env python3
"""Build a read-only inventory of character-factory source archives."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


MODEL_SUFFIXES = {".abc", ".blend", ".fbx", ".glb", ".gltf", ".obj", ".usd", ".usdz"}
TEXTURE_SUFFIXES = {".bmp", ".exr", ".jpeg", ".jpg", ".png", ".tga", ".tif", ".tiff"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_archive(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        files = [entry for entry in archive.infolist() if not entry.is_dir()]
    models = [entry.filename for entry in files if Path(entry.filename).suffix.lower() in MODEL_SUFFIXES]
    textures = [entry.filename for entry in files if Path(entry.filename).suffix.lower() in TEXTURE_SUFFIXES]
    return {
        "path": str(path),
        "sha256": sha256(path),
        "sizeBytes": path.stat().st_size,
        "fileCount": len(files),
        "modelFiles": models,
        "textureCount": len(textures),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--download-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text())
    results = []
    missing = []
    for source in registry["sources"]:
        archive = args.download_dir / source["archive"]
        record = dict(source)
        if archive.is_file():
            record.update(inspect_archive(archive))
            record["available"] = True
        else:
            record["available"] = False
            missing.append(source["id"])
        results.append(record)

    report = {
        "schemaVersion": 1,
        "iteration": registry["iteration"],
        "status": "inventory-complete" if not missing else "inventory-incomplete",
        "sourceCount": len(results),
        "availableCount": len(results) - len(missing),
        "missing": missing,
        "sources": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
