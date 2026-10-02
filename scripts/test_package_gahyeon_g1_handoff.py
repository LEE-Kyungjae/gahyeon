#!/usr/bin/env python3

import json
import csv
import io
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from package_gahyeon_g1_handoff import DEFAULT_INPUT, package
from verify_gahyeon_g1_handoff import verify_archive


class PackageG1HandoffTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / "handoff.zip"

    def tearDown(self):
        self.temp.cleanup()

    def test_package_contains_bound_work_order_and_non_authoritative_drafts(self):
        result = package(DEFAULT_INPUT, self.output)
        verified = verify_archive(self.output)
        self.assertEqual(4, result["nonAuthoritativeDraftCount"])
        self.assertEqual(4, verified["nonAuthoritativeDraftCount"])
        with zipfile.ZipFile(self.output) as archive:
            work_order = json.loads(archive.read("g1-authoring-work-order.json"))
            drafts = json.loads(archive.read("g1-drafts/drafts-manifest.json"))
            inventory = json.loads(archive.read("package-manifest.json"))
        self.assertEqual(15, len(work_order["requiredEvidence"]))
        self.assertFalse(drafts["identityAuthority"])
        self.assertEqual(
            ["tools/build-g1-scene-plan.py", "tools/blender-bootstrap-g1.py",
             "tools/blender-import-g1-base.py",
             "tools/blender-render-g1-evidence.py",
             "tools/package-g1-submission.py"],
            inventory["workstationTools"],
        )

    def test_packaging_is_deterministic(self):
        first = package(DEFAULT_INPUT, self.output)["archiveSha256"]
        second = package(DEFAULT_INPUT, self.output)["archiveSha256"]
        self.assertEqual(first, second)

    def test_packaged_scene_plan_tool_runs_without_repository_imports(self):
        package(DEFAULT_INPUT, self.output)
        extracted = Path(self.temp.name) / "extracted"
        with zipfile.ZipFile(self.output) as archive:
            archive.extractall(extracted)
        output = extracted / "work/gahyeon-g1-scene-plan.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(extracted / "tools/build-g1-scene-plan.py"),
                "--handoff-dir",
                str(extracted),
                "--output",
                str(output),
            ],
            cwd=extracted,
            capture_output=True,
            text=True,
            check=True,
        )
        result = json.loads(completed.stdout)
        plan = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(result["valid"])
        self.assertEqual(15, result["cameras"])
        self.assertEqual("blender-authoring-bootstrap", plan["purpose"])

    def test_reference_assets_use_portable_aliases_and_preserve_source_names(self):
        package(DEFAULT_INPUT, self.output)
        with zipfile.ZipFile(self.output) as archive:
            inventory = json.loads(archive.read("package-manifest.json"))
            aliases = [item["packagedPath"] for item in inventory["references"]]
            source_names = [item["sourceFile"] for item in inventory["references"]]
            map_rows = list(csv.DictReader(io.StringIO(
                archive.read("reference-map.csv").decode("utf-8-sig"))))
            guide = archive.read("README.md").decode("utf-8")
        self.assertEqual(2, inventory["schemaVersion"])
        self.assertEqual("portable-ascii-alias-v1", inventory["referencePathPolicy"])
        self.assertEqual(29, len(aliases))
        self.assertTrue(all(name.isascii() and " " not in name for name in aliases))
        self.assertTrue(all(name.startswith("references/") for name in aliases))
        self.assertTrue(any(name != alias for name, alias in zip(source_names, aliases)))
        self.assertEqual(29, len(map_rows))
        self.assertIn("non-authoritative generated drafts", guide)
        self.assertIn("python3 tools/build-g1-scene-plan.py", guide)
        self.assertIn("tools/blender-bootstrap-g1.py", guide)
        self.assertIn("tools/blender-render-g1-evidence.py", guide)
        self.assertIn("tools/package-g1-submission.py", guide)

    def test_undeclared_candidate_is_rejected(self):
        package(DEFAULT_INPUT, self.output)
        changed = Path(self.temp.name) / "changed.zip"
        with zipfile.ZipFile(self.output) as source, zipfile.ZipFile(changed, "w") as target:
            for info in source.infolist():
                target.writestr(info, source.read(info.filename))
            target.writestr("unclassified-candidate.png", b"candidate")
        with self.assertRaisesRegex(ValueError, "do not match package manifest"):
            verify_archive(changed)


if __name__ == "__main__":
    unittest.main()
