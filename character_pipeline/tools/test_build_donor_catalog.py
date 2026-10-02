from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from build_donor_catalog import build_donor_catalog, inspect_donor_archive, validate_donor_catalog


class DonorCatalogTest(unittest.TestCase):
    def make_archive(self, root: Path, name: str = "donor.zip") -> Path:
        path = root / name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("source/model.fbx", b"fbx")
            archive.writestr("textures/albedo.png", b"png")
        return path

    def test_builds_fail_closed_local_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = self.make_archive(Path(directory))
            catalog = build_donor_catalog({
                "schemaVersion": 1,
                "catalogId": "test",
                "policy": {"sourceAssetsAreImmutable": True},
                "sources": [{
                    "id": "donor",
                    "archive": str(archive),
                    "kind": "motion-donor",
                    "roles": ["idle"],
                    "productionUse": "motion-reference",
                    "notes": "test",
                }],
            })
            validate_donor_catalog(catalog)
            donor = catalog["donors"][0]
            self.assertFalse(donor["releaseEligible"])
            self.assertEqual(donor["archive"]["textureCount"], 1)
            self.assertEqual(donor["archive"]["sourceFiles"], ["source/model.fbx"])

    def test_rejects_archive_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../model.fbx", b"fbx")
            with self.assertRaisesRegex(ValueError, "unsafe archive paths"):
                inspect_donor_archive(path)

    def test_requires_model_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("textures/albedo.png", b"png")
            with self.assertRaisesRegex(ValueError, "no source model"):
                build_donor_catalog({
                    "schemaVersion": 1,
                    "catalogId": "test",
                    "sources": [{"id": "empty", "archive": str(path)}],
                })


if __name__ == "__main__":
    unittest.main()
