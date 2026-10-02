#!/usr/bin/env python3
"""Seal locally downloaded character and motion donors into an auditable catalog."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


SOURCE_EXTENSIONS = {".abc", ".blend", ".fbx", ".glb", ".gltf", ".rar", ".usd", ".usdz"}
TEXTURE_EXTENSIONS = {".bmp", ".exr", ".jpeg", ".jpg", ".png", ".tga", ".tif", ".tiff"}
LICENSE_NAMES = {"copying", "copyright", "license", "license.txt", "readme", "readme.md"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_donor_archive(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".zip":
        raise ValueError(f"unsupported donor archive: {path}")
    with zipfile.ZipFile(path) as archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        names = [PurePosixPath(item.filename) for item in members]
        unsafe = [str(name) for name in names if name.is_absolute() or ".." in name.parts]
        if unsafe:
            raise ValueError(f"unsafe archive paths: {unsafe}")
        sources = sorted(str(name) for name in names if name.suffix.lower() in SOURCE_EXTENSIONS)
        textures = sorted(str(name) for name in names if name.suffix.lower() in TEXTURE_EXTENSIONS)
        licenses = sorted(
            str(name) for name in names
            if name.name.lower() in LICENSE_NAMES or "license" in name.name.lower()
        )
        return {
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "memberCount": len(members),
            "sourceFiles": sources,
            "textureCount": len(textures),
            "licenseEvidence": licenses,
        }


def validate_donor_catalog(catalog: dict[str, object]) -> None:
    if catalog.get("schemaVersion") != 1:
        raise ValueError("unsupported donor catalog schema")
    donors = catalog.get("donors")
    if not isinstance(donors, list) or not donors:
        raise ValueError("donors must be a non-empty list")
    seen: set[str] = set()
    for donor in donors:
        if not isinstance(donor, dict):
            raise ValueError("donor must be an object")
        donor_id = donor.get("id")
        if not isinstance(donor_id, str) or not donor_id or donor_id in seen:
            raise ValueError("donor id is missing or duplicated")
        seen.add(donor_id)
        archive = donor.get("archive")
        if not isinstance(archive, dict) or len(str(archive.get("sha256", ""))) != 64:
            raise ValueError(f"invalid archive evidence for {donor_id}")
        if not archive.get("sourceFiles"):
            raise ValueError(f"no source model found for {donor_id}")
        if donor.get("releaseEligible") is not False:
            raise ValueError(f"unlicensed donor cannot be release eligible: {donor_id}")


def build_donor_catalog(config: dict[str, object]) -> dict[str, object]:
    sources = config.get("sources")
    if config.get("schemaVersion") != 1 or not isinstance(sources, list):
        raise ValueError("invalid donor source config")
    donors = []
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("source entry must be an object")
        archive = inspect_donor_archive(Path(str(source["archive"])))
        donor = {key: value for key, value in source.items() if key != "archive"}
        donor["archive"] = archive
        donor["releaseEligible"] = bool(archive["licenseEvidence"]) and False
        donor["blockingFindings"] = [
            "Original listing URL and redistribution/commercial license are not recorded."
        ]
        donors.append(donor)
    catalog = {
        "schemaVersion": 1,
        "catalogId": config.get("catalogId"),
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "policy": config.get("policy"),
        "status": "draft-local-poc-only",
        "donors": donors,
    }
    validate_donor_catalog(catalog)
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    catalog = build_donor_catalog(config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite catalog: {args.output}")
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
