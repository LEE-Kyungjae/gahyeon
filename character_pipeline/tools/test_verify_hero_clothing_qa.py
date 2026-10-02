#!/usr/bin/env python3

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from character_pipeline.tools.verify_hero_clothing_qa import validate_clothing_contract


class HeroClothingQaTest(unittest.TestCase):
    def fixture(self, root: Path):
        config = json.loads(Path("character_pipeline/config/hero_clothing_qa.json").read_text())
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
            "state": "candidate", "claim": "production-clothing-candidate-not-approved",
            "slots": {name: f"/Game/Clothing/{name}" for name in config["requiredSlots"]},
            "assets": {name: f"/Game/Clothing/{name}" for name in config["requiredAssets"]},
            "pbrChannels": {name: f"/Game/Clothing/{name}" for name in config["requiredPbrChannels"]},
            "modularity": config["modularity"],
            "lods": [{"index": 0, "screenSize": 1.0}, {"index": 1, "screenSize": 0.35}],
            "editorEvidence": editor.name,
            "captureManifest": str(manifest.relative_to(root)),
        }
        classes = {"skeletalMesh": "SkeletalMesh", "materials": "MaterialInstanceConstant",
                   "physicsAsset": "PhysicsAsset", "clothConfig": "ChaosClothConfig", "clothDataflow": "Dataflow"}
        editor.write_text(json.dumps({
            "schemaVersion": 1, "kind": "metahuman-production-clothing-editor-evidence",
            "engine": "5.6", "editorRuntimeVerified": True,
            "assets": {name: {"path": path, "class": classes[name]}
                       for name, path in binding["assets"].items()},
            "slots": {name: {"path": path, "class": "SkeletalMesh"}
                      for name, path in binding["slots"].items()},
            "observedBodyPenetrations": 0,
            "checks": {name: True for name in config["runtimeChecks"]},
            "automaticApproval": False, "qualityClaim": None,
        }))
        return config, binding

    def test_complete_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            config, binding = self.fixture(Path(directory))
            self.assertEqual(validate_clothing_contract(config, binding, Path(directory))["captures"], 16)

    def test_rejects_missing_cloth_dataflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, binding = self.fixture(root)
            del binding["assets"]["clothDataflow"]
            with self.assertRaisesRegex(ValueError, "assets"):
                validate_clothing_contract(config, binding, root)

    def test_rejects_body_reimport_swap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, binding = self.fixture(root)
            binding["modularity"] = dict(binding["modularity"])
            binding["modularity"]["outfitSwapWithoutBodyReimport"] = False
            with self.assertRaisesRegex(ValueError, "modularity"):
                validate_clothing_contract(config, binding, root)

    def test_rejects_observed_penetration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, binding = self.fixture(root)
            editor = json.loads((root / "editor.json").read_text())
            editor["observedBodyPenetrations"] = 1
            (root / "editor.json").write_text(json.dumps(editor))
            with self.assertRaisesRegex(ValueError, "penetration"):
                validate_clothing_contract(config, binding, root)

    def test_rejects_fake_chaos_dataflow_class(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, binding = self.fixture(root)
            editor = json.loads((root / "editor.json").read_text())
            editor["assets"]["clothDataflow"]["class"] = "StaticMesh"
            (root / "editor.json").write_text(json.dumps(editor))
            with self.assertRaisesRegex(ValueError, "clothDataflow"):
                validate_clothing_contract(config, binding, root)


if __name__ == "__main__":
    unittest.main()
