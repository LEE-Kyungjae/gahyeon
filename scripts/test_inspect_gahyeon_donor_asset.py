#!/usr/bin/env python3
"""Tests for the read-only donor-asset inventory."""

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("inspect_gahyeon_donor_asset.py")
SPEC = importlib.util.spec_from_file_location("donor_inspector", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DonorInspectorTest(unittest.TestCase):
    def test_zip_inventory_finds_assets_without_extracting(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "donor.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("Meshes/Leather_Jacket.fbx", b"mesh")
                archive.writestr("Textures/Jacket_Normal.png", b"texture")
            report = MODULE.inspect(archive_path)
            self.assertEqual(2, report["summary"]["fileCount"])
            self.assertEqual(1, report["summary"]["sourceGeometryCount"])
            self.assertEqual(2, report["summary"]["garmentCandidateCount"])
            self.assertTrue(report["summary"]["safeToExtract"])
            self.assertFalse((Path(directory) / "Meshes").exists())

    def test_zip_slip_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../escaped.fbx", b"mesh")
            report = MODULE.inspect(archive_path)
            self.assertEqual(1, report["archive"]["unsafeMemberCount"])
            self.assertFalse(report["summary"]["safeToExtract"])


if __name__ == "__main__":
    unittest.main()
