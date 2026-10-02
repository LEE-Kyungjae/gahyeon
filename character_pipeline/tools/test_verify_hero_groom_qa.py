#!/usr/bin/env python3

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from character_pipeline.tools.verify_hero_groom_qa import validate_groom_contract


class HeroGroomQaTest(unittest.TestCase):
    def fixture(self, root: Path):
        config = json.loads(Path("character_pipeline/config/hero_groom_qa.json").read_text())
        editor = root / "editor.json"
        captures_dir = root / "captures"
        captures_dir.mkdir()
        image = Image.new("RGB", (1440, 2560), "gray")
        captures = []
        for capture_id in config["captures"]:
            path = captures_dir / f"{capture_id}.png"
            image.save(path, optimize=True)
            captures.append({"id": capture_id, "file": path.name,
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        manifest = captures_dir / "manifest.json"
        manifest.write_text(json.dumps({"resolution": [1440, 2560], "captures": captures}))
        binding = {
            "state": "candidate", "claim": "production-groom-candidate-not-approved",
            "groups": {name: f"/Game/Groom/{name}" for name in config["requiredGroups"]},
            "features": {name: True for name in config["requiredFeatures"]},
            "bindings": {name: f"/Game/Groom/{name}" for name in config["requiredBindings"]},
            "lods": [{"mode": "strands", "screenSize": 1.0}, {"mode": "cards", "screenSize": 0.35}],
            "editorEvidence": editor.name,
            "captureManifest": str(manifest.relative_to(root)),
        }
        editor.write_text(json.dumps({
            "schemaVersion": 1, "kind": "metahuman-production-groom-editor-evidence",
            "engine": "5.6", "editorRuntimeVerified": True,
            "assets": {
                "groom": {"path": binding["bindings"]["groom-asset"], "class": "GroomAsset"},
                "binding": {"path": binding["bindings"]["groom-binding-asset"], "class": "GroomBindingAsset"},
                "targetSkeletalMesh": {"path": binding["bindings"]["target-skeletal-mesh"], "class": "SkeletalMesh"},
                "physicsAsset": {"path": binding["bindings"]["physics-asset"], "class": "PhysicsAsset"},
                "materialInstance": {"path": binding["bindings"]["material-instance"], "class": "MaterialInstanceConstant"},
            },
            "lods": binding["lods"],
            "checks": {name: True for name in config["runtimeChecks"]},
            "automaticApproval": False, "qualityClaim": None,
        }))
        return config, binding

    def test_complete_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            config, binding = self.fixture(Path(directory))
            self.assertEqual(validate_groom_contract(config, binding, Path(directory))["captures"], 14)

    def test_rejects_missing_flyaways(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, binding = self.fixture(root)
            del binding["groups"]["flyaways"]
            with self.assertRaisesRegex(ValueError, "groups"):
                validate_groom_contract(config, binding, root)

    def test_rejects_no_fallback_lod(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, binding = self.fixture(root)
            binding["lods"] = [{"mode": "strands", "screenSize": 1.0}]
            with self.assertRaisesRegex(ValueError, "fallback"):
                validate_groom_contract(config, binding, root)

    def test_rejects_failed_runtime_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, binding = self.fixture(root)
            editor = json.loads((root / "editor.json").read_text())
            editor["checks"]["eye-occlusion"] = False
            (root / "editor.json").write_text(json.dumps(editor))
            with self.assertRaisesRegex(ValueError, "runtime checks"):
                validate_groom_contract(config, binding, root)

    def test_rejects_fake_editor_groom_class(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, binding = self.fixture(root)
            editor = json.loads((root / "editor.json").read_text())
            editor["assets"]["groom"]["class"] = "StaticMesh"
            (root / "editor.json").write_text(json.dumps(editor))
            with self.assertRaisesRegex(ValueError, "groom"):
                validate_groom_contract(config, binding, root)


if __name__ == "__main__":
    unittest.main()
